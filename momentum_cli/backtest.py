"""
回测引擎模块 - 支持多策略回测

提供三种策略的回测功能：
1. 核心+慢腿轮动（月度调仓，含完整风控）
2. 核心+快腿轮动（周度调仓，20日动量）
3. 核心+宏观驱动（12M-1M长波动量）
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_loader import BundleDataLoader


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 万三手续费
    slippage_rate: float = 0.001  # 千一滑点


@dataclass
class Position:
    """持仓信息"""
    code: str
    shares: float
    entry_price: float
    entry_date: dt.date
    stop_loss_price: float


@dataclass
class Trade:
    """交易记录"""
    date: dt.date
    code: str
    action: str  # 'BUY' or 'SELL'
    price: float
    shares: float
    amount: float
    commission: float
    reason: str  # 交易原因


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades: List[Trade]
    equity_curve: pd.Series
    positions_history: pd.DataFrame
    metrics: Dict[str, Any]


class BacktestEngine:
    """回测引擎基类"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_history: List[Tuple[dt.date, float]] = []

        # 组合级风控
        self.peak_equity: Optional[float] = None
        self.risk_level: int = 0  # 0=正常, 1=-15%, 2=-20%, 3=-30%
        self.drawdown_thresholds = [-0.15, -0.20, -0.30]
        self.satellite_exposure_limits = [0.40, 0.25, 0.10]  # 对应的卫星仓位上限

    def load_data(self, etf_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        加载ETF价格数据

        Args:
            etf_codes: ETF代码列表

        Returns:
            字典，键为ETF代码，值为包含OHLC的DataFrame
        """
        data = {}
        with BundleDataLoader() as loader:
            for code in etf_codes:
                try:
                    df = loader.load_bars(
                        code,
                        start_date=self.config.start_date,
                        end_date=self.config.end_date
                    )
                    data[code] = df
                except Exception as e:
                    print(f"警告: 无法加载 {code} 的数据: {e}")
        return data

    def load_market_index(self) -> pd.DataFrame:
        """
        加载沪深300指数数据

        Returns:
            包含价格和MA200的DataFrame
        """
        with BundleDataLoader() as loader:
            df = loader.load_bars(
                "000300.XSHG",
                start_date=self.config.start_date,
                end_date=self.config.end_date
            )
            # 计算MA200
            df['ma200'] = df['close'].rolling(window=200, min_periods=1).mean()
            df['above_ma200'] = df['close'] > df['ma200']
            # 计算ATR
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = abs(df['high'] - df['close'].shift())
            df['low_close'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            df['atr20'] = df['tr'].rolling(window=20, min_periods=1).mean()
            df['atr20_pct'] = (df['atr20'] / df['close']) * 100
            return df

    def calculate_position_value(self, date: dt.date, prices: Dict[str, float]) -> float:
        """计算当前持仓市值"""
        total_value = 0.0
        for code, position in self.positions.items():
            if code in prices:
                total_value += position.shares * prices[code]
        return total_value

    def execute_trade(
        self,
        date: dt.date,
        code: str,
        action: str,
        price: float,
        shares: float,
        reason: str
    ) -> None:
        """
        执行交易

        Args:
            date: 交易日期
            code: 标的代码
            action: 'BUY' 或 'SELL'
            price: 成交价格
            shares: 股数
            reason: 交易原因
        """
        # 考虑滑点
        actual_price = price * (1 + self.config.slippage_rate) if action == 'BUY' else price * (1 - self.config.slippage_rate)
        amount = actual_price * shares
        commission = amount * self.config.commission_rate

        if action == 'BUY':
            cost = amount + commission
            if cost > self.cash:
                # 资金不足，调整买入数量
                shares = (self.cash / (1 + self.config.commission_rate)) / actual_price
                amount = actual_price * shares
                commission = amount * self.config.commission_rate
                cost = amount + commission

            self.cash -= cost

            # 记录持仓
            self.positions[code] = Position(
                code=code,
                shares=shares,
                entry_price=actual_price,
                entry_date=date,
                stop_loss_price=0.0  # 由策略设置
            )

        elif action == 'SELL':
            if code in self.positions:
                self.cash += amount - commission
                del self.positions[code]

        # 记录交易
        trade = Trade(
            date=date,
            code=code,
            action=action,
            price=actual_price,
            shares=shares,
            amount=amount,
            commission=commission,
            reason=reason
        )
        self.trades.append(trade)

    def rebalance(
        self,
        date: dt.date,
        target_positions: Dict[str, float],
        prices: Dict[str, float],
        reason: str = "定期调仓"
    ) -> None:
        """
        调仓到目标权重

        Args:
            date: 调仓日期
            target_positions: 目标持仓权重 {code: weight}
            prices: 当前价格 {code: price}
            reason: 调仓原因
        """
        # 先卖出不在目标中的持仓
        current_codes = set(self.positions.keys())
        target_codes = set(target_positions.keys())

        for code in current_codes - target_codes:
            if code in prices:
                self.execute_trade(
                    date=date,
                    code=code,
                    action='SELL',
                    price=prices[code],
                    shares=self.positions[code].shares,
                    reason=f"{reason}-卖出"
                )

        # 计算总资产
        position_value = self.calculate_position_value(date, prices)
        total_asset = self.cash + position_value

        # 买入或调整目标持仓
        for code, target_weight in target_positions.items():
            if code not in prices:
                continue

            target_value = total_asset * target_weight
            current_value = 0.0

            if code in self.positions:
                current_value = self.positions[code].shares * prices[code]

            diff = target_value - current_value

            if abs(diff) < 100:  # 差异太小不调整
                continue

            if diff > 0:  # 需要买入
                shares = diff / prices[code]
                self.execute_trade(
                    date=date,
                    code=code,
                    action='BUY',
                    price=prices[code],
                    shares=shares,
                    reason=f"{reason}-买入"
                )
            else:  # 需要卖出
                shares = abs(diff) / prices[code]
                if code in self.positions and shares <= self.positions[code].shares:
                    self.execute_trade(
                        date=date,
                        code=code,
                        action='SELL',
                        price=prices[code],
                        shares=shares,
                        reason=f"{reason}-减仓"
                    )

    def check_stop_loss(self, date: dt.date, prices: Dict[str, float]) -> None:
        """检查并执行止损"""
        for code, position in list(self.positions.items()):
            if code not in prices:
                continue

            current_price = prices[code]

            # 检查是否触发止损
            if position.stop_loss_price > 0 and current_price <= position.stop_loss_price:
                self.execute_trade(
                    date=date,
                    code=code,
                    action='SELL',
                    price=current_price,
                    shares=position.shares,
                    reason="触发止损"
                )

    def update_equity(self, date: dt.date, prices: Dict[str, float]) -> None:
        """更新权益曲线"""
        position_value = self.calculate_position_value(date, prices)
        total_equity = self.cash + position_value
        self.equity_history.append((date, total_equity))

        # 更新组合风控状态
        self._update_portfolio_risk(date, total_equity)

    def _update_portfolio_risk(self, date: dt.date, current_value: float) -> None:
        """
        更新组合风控状态

        Args:
            date: 当前日期
            current_value: 当前权益
        """
        if self.peak_equity is None:
            self.peak_equity = current_value
        else:
            self.peak_equity = max(self.peak_equity, current_value)

        # 计算回撤
        drawdown = (current_value - self.peak_equity) / self.peak_equity

        # 确定风控等级
        old_level = self.risk_level
        self.risk_level = 0
        for i, threshold in enumerate(self.drawdown_thresholds):
            if drawdown <= threshold:
                self.risk_level = i + 1

        # 风控等级变化时打印日志
        if self.risk_level != old_level:
            if self.risk_level > 0:
                print(f"⚠️  [{date}] 组合风控触发: 回撤{drawdown:.2%}, "
                      f"等级{self.risk_level}, 卫星仓位上限{self.satellite_exposure_limits[self.risk_level-1]:.1%}")
            else:
                print(f"✅ [{date}] 组合风控解除: 回撤{drawdown:.2%}")

    def get_max_satellite_exposure(self) -> float:
        """
        获取当前允许的最大卫星仓位

        Returns:
            最大卫星仓位比例
        """
        if self.risk_level == 0:
            return 0.40  # 正常情况
        elif self.risk_level <= len(self.satellite_exposure_limits):
            return self.satellite_exposure_limits[self.risk_level - 1]
        else:
            return 0.0  # 极端情况，清仓

    def calculate_metrics(self) -> Dict[str, Any]:
        """计算回测指标"""
        if not self.equity_history:
            return {}

        dates, values = zip(*self.equity_history)
        equity_series = pd.Series(values, index=pd.DatetimeIndex(dates))

        # 计算收益率
        returns = equity_series.pct_change().dropna()

        # 总收益率
        total_return = (equity_series.iloc[-1] / self.config.initial_capital - 1) * 100

        # 年化收益率
        days = (dates[-1] - dates[0]).days
        annual_return = ((equity_series.iloc[-1] / self.config.initial_capital) ** (365 / days) - 1) * 100 if days > 0 else 0

        # 夏普比率
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() > 0 else 0

        # 最大回撤
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax * 100
        max_dd = drawdown.min()

        # 胜率
        win_trades = [t for t in self.trades if t.action == 'SELL']
        if win_trades:
            # 这里简化处理，实际需要匹配买卖对
            win_rate = 0.0  # TODO: 实现精确的胜率计算
        else:
            win_rate = 0.0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'final_equity': equity_series.iloc[-1]
        }

    def run(self) -> BacktestResult:
        """运行回测 - 由子类实现具体策略"""
        raise NotImplementedError("子类需实现run方法")


def run_slow_leg_strategy(
    etf_codes: List[str],
    start_date: str,
    end_date: str,
    momentum_params: Dict[str, Any]
) -> BacktestResult:
    """
    策略1：核心+慢腿轮动（月度调仓）

    规则：
    - 每月最后一个交易日调仓
    - 使用3M-1M和6M-1M动量选股
    - 沪深300在MA200上方：2条腿 × 20%
    - 沪深300在MA200下方：1条腿 × 15%
    - 止损：基线-12%，强趋势-10%，震荡-15%

    Args:
        etf_codes: ETF代码列表
        start_date: 开始日期
        end_date: 结束日期
        momentum_params: 动量参数

    Returns:
        回测结果
    """
    config = BacktestConfig(start_date=start_date, end_date=end_date)
    engine = BacktestEngine(config)

    # 加载数据
    etf_data = engine.load_data(etf_codes)
    market_data = engine.load_market_index()

    if not etf_data:
        raise ValueError("无法加载ETF数据")

    # 获取所有交易日
    all_dates = sorted(set().union(*[set(df.index.date) for df in etf_data.values()]))

    # 参数设置
    windows = momentum_params.get('momentum_windows', [63, 126])
    weights = momentum_params.get('momentum_weights', [0.6, 0.4])
    skip_windows = momentum_params.get('momentum_skip_windows', [21, 21])
    stability_weight = momentum_params.get('stability_weight', 0.2)
    stability_window = momentum_params.get('stability_window', 30)

    # 稳定度历史：用于计算稳定度得分
    rank_history: List[Dict[str, int]] = []

    # 开始回测循环
    for i, current_date in enumerate(all_dates):
        # 获取当前价格
        prices = {}
        for code, df in etf_data.items():
            if current_date in df.index.date:
                idx = pd.Timestamp(current_date)
                prices[code] = float(df.loc[idx, 'close'])

        # 更新权益
        engine.update_equity(current_date, prices)

        # 检查止损
        engine.check_stop_loss(current_date, prices)

        # 判断是否为月末最后一个交易日
        is_month_end = False
        if i < len(all_dates) - 1:
            next_date = all_dates[i + 1]
            is_month_end = current_date.month != next_date.month
        else:
            is_month_end = True

        if not is_month_end:
            continue

        # 月末调仓
        # 1. 计算每个ETF的原始动量得分
        momentum_scores = {}
        for code, df in etf_data.items():
            if current_date not in df.index.date:
                continue

            idx = pd.Timestamp(current_date)
            score = 0.0

            for window, weight, skip in zip(windows, weights, skip_windows):
                if len(df.loc[:idx]) < window + skip:
                    continue

                # 计算动量：(当前价 - N日前价) / N日前价
                history = df.loc[:idx].tail(window + skip + 1)
                if len(history) < window + skip:
                    continue

                current_price = history.iloc[-1]['close']
                past_price = history.iloc[-(window + skip)]['close']

                if past_price > 0:
                    momentum = (current_price - past_price) / past_price
                    score += momentum * weight

            momentum_scores[code] = score

        # 1.5. 计算排名并记录历史（用于稳定度）
        sorted_by_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        current_ranks = {code: rank + 1 for rank, (code, _) in enumerate(sorted_by_momentum)}
        rank_history.append(current_ranks)

        # 保持稳定度窗口大小
        if len(rank_history) > stability_window:
            rank_history.pop(0)

        # 1.6. 计算稳定度得分
        stability_scores = {}
        if len(rank_history) >= 2:
            for code in momentum_scores.keys():
                appearances_in_top10 = sum(
                    1 for ranks in rank_history
                    if code in ranks and ranks[code] <= 10
                )
                stability_scores[code] = appearances_in_top10 / len(rank_history)
        else:
            stability_scores = {code: 1.0 for code in momentum_scores.keys()}

        # 1.7. 应用稳定度权重调整动量得分
        adjusted_scores = {}
        for code, mom_score in momentum_scores.items():
            stability = stability_scores.get(code, 1.0)
            factor = (1.0 - stability_weight) + stability_weight * stability
            adjusted_scores[code] = mom_score * factor

        # 2. 获取市场状态(沪深300与MA200关系)
        market_above_ma200 = False
        market_atr_pct = 0.0

        if current_date in market_data.index.date:
            market_idx = pd.Timestamp(current_date)
            market_above_ma200 = bool(market_data.loc[market_idx, 'above_ma200'])
            market_atr_pct = float(market_data.loc[market_idx, 'atr20_pct'])

        # 3. 根据市场状态确定持仓数和权重
        if market_above_ma200:
            num_positions = 2
            position_weight = 0.20  # 20%/腿
        else:
            num_positions = 1
            position_weight = 0.15  # 15%/腿

        # 3.5. 应用组合风控约束
        max_satellite_exposure = engine.get_max_satellite_exposure()
        total_target_exposure = num_positions * position_weight

        if total_target_exposure > max_satellite_exposure:
            # 需要降低仓位
            if max_satellite_exposure > 0:
                position_weight = max_satellite_exposure / num_positions
            else:
                # 极端情况，清仓
                num_positions = 0
                position_weight = 0.0

        # 4. 选择调整后得分最高的N只ETF（使用稳定度调整后的得分）
        sorted_etfs = sorted(adjusted_scores.items(), key=lambda x: x[1], reverse=True)
        selected_etfs = sorted_etfs[:num_positions] if num_positions > 0 else []

        # 5. 构建目标持仓
        target_positions = {}
        for code, score in selected_etfs:
            target_positions[code] = position_weight

        # 6. 执行调仓
        engine.rebalance(
            date=current_date,
            target_positions=target_positions,
            prices=prices,
            reason="月度调仓"
        )

        # 7. 设置止损价
        for code in target_positions:
            if code not in engine.positions:
                continue

            position = engine.positions[code]

            # 根据市场状态设置止损
            if market_above_ma200 and market_atr_pct < 4.0:
                stop_loss_pct = -0.10  # 强趋势止损-10%
            elif market_above_ma200:
                stop_loss_pct = -0.12  # 基线止损-12%
            else:
                stop_loss_pct = -0.15  # 震荡/高波动止损-15%

            position.stop_loss_price = position.entry_price * (1 + stop_loss_pct)

    # 生成回测结果
    metrics = engine.calculate_metrics()

    dates, values = zip(*engine.equity_history) if engine.equity_history else ([], [])
    equity_curve = pd.Series(values, index=pd.DatetimeIndex(dates))

    # 构建持仓历史DataFrame
    positions_data = []
    for trade in engine.trades:
        if trade.action == 'BUY':
            positions_data.append({
                'date': trade.date,
                'code': trade.code,
                'shares': trade.shares,
                'price': trade.price
            })

    positions_history = pd.DataFrame(positions_data) if positions_data else pd.DataFrame()

    return BacktestResult(
        strategy_name="核心+慢腿轮动(月度)",
        total_return=metrics.get('total_return', 0),
        annual_return=metrics.get('annual_return', 0),
        sharpe_ratio=metrics.get('sharpe_ratio', 0),
        max_drawdown=metrics.get('max_drawdown', 0),
        win_rate=metrics.get('win_rate', 0),
        trades=engine.trades,
        equity_curve=equity_curve,
        positions_history=positions_history,
        metrics=metrics
    )


def run_fast_leg_strategy(
    etf_codes: List[str],
    start_date: str,
    end_date: str,
    momentum_params: Dict[str, Any]
) -> BacktestResult:
    """
    策略2：核心+快腿轮动（周度调仓）

    规则：
    - 每周五调仓
    - 使用20日收益率作为动量信号
    - 市场择时规则同慢腿（基于沪深300与MA200）
    - 止损：跌破20日最低价即止损

    Args:
        etf_codes: ETF代码列表
        start_date: 开始日期
        end_date: 结束日期
        momentum_params: 动量参数

    Returns:
        回测结果
    """
    config = BacktestConfig(start_date=start_date, end_date=end_date)
    engine = BacktestEngine(config)

    # 加载数据
    etf_data = engine.load_data(etf_codes)
    market_data = engine.load_market_index()

    if not etf_data:
        raise ValueError("无法加载ETF数据")

    # 获取所有交易日
    all_dates = sorted(set().union(*[set(df.index.date) for df in etf_data.values()]))

    # 开始回测循环
    for i, current_date in enumerate(all_dates):
        # 获取当前价格
        prices = {}
        for code, df in etf_data.items():
            if current_date in df.index.date:
                idx = pd.Timestamp(current_date)
                prices[code] = float(df.loc[idx, 'close'])

        # 更新权益
        engine.update_equity(current_date, prices)

        # 检查止损(基于20日最低价)
        for code, position in list(engine.positions.items()):
            if code not in etf_data or code not in prices:
                continue

            df = etf_data[code]
            idx = pd.Timestamp(current_date)

            # 计算20日最低价
            if idx in df.index:
                history_20d = df.loc[:idx].tail(20)
                if len(history_20d) >= 20:
                    low_20d = history_20d['low'].min()
                    if prices[code] <= low_20d:
                        engine.execute_trade(
                            date=current_date,
                            code=code,
                            action='SELL',
                            price=prices[code],
                            shares=position.shares,
                            reason="跌破20日最低价止损"
                        )

        # 判断是否为周五
        is_friday = current_date.weekday() == 4

        if not is_friday:
            continue

        # 周五调仓
        # 1. 计算每个ETF的20日动量
        momentum_scores = {}
        for code, df in etf_data.items():
            if current_date not in df.index.date:
                continue

            idx = pd.Timestamp(current_date)
            history_20d = df.loc[:idx].tail(20)

            if len(history_20d) >= 20:
                current_price = history_20d.iloc[-1]['close']
                past_price = history_20d.iloc[0]['close']

                if past_price > 0:
                    momentum = (current_price - past_price) / past_price
                    momentum_scores[code] = momentum

        # 2. 获取市场状态
        market_above_ma200 = False
        if current_date in market_data.index.date:
            market_idx = pd.Timestamp(current_date)
            market_above_ma200 = bool(market_data.loc[market_idx, 'above_ma200'])

        # 3. 根据市场状态确定持仓数和权重
        if market_above_ma200:
            num_positions = 2
            position_weight = 0.20
        else:
            num_positions = 1
            position_weight = 0.15

        # 4. 选择动量最高的N只ETF
        sorted_etfs = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        selected_etfs = sorted_etfs[:num_positions]

        # 5. 构建目标持仓
        target_positions = {}
        for code, score in selected_etfs:
            target_positions[code] = position_weight

        # 6. 执行调仓
        engine.rebalance(
            date=current_date,
            target_positions=target_positions,
            prices=prices,
            reason="周度调仓"
        )

    # 生成回测结果
    metrics = engine.calculate_metrics()

    dates, values = zip(*engine.equity_history) if engine.equity_history else ([], [])
    equity_curve = pd.Series(values, index=pd.DatetimeIndex(dates))

    positions_data = []
    for trade in engine.trades:
        if trade.action == 'BUY':
            positions_data.append({
                'date': trade.date,
                'code': trade.code,
                'shares': trade.shares,
                'price': trade.price
            })

    positions_history = pd.DataFrame(positions_data) if positions_data else pd.DataFrame()

    return BacktestResult(
        strategy_name="核心+快腿轮动(周度)",
        total_return=metrics.get('total_return', 0),
        annual_return=metrics.get('annual_return', 0),
        sharpe_ratio=metrics.get('sharpe_ratio', 0),
        max_drawdown=metrics.get('max_drawdown', 0),
        win_rate=metrics.get('win_rate', 0),
        trades=engine.trades,
        equity_curve=equity_curve,
        positions_history=positions_history,
        metrics=metrics
    )


def run_macro_driven_strategy(
    etf_codes: List[str],
    start_date: str,
    end_date: str,
    momentum_params: Dict[str, Any]
) -> BacktestResult:
    """
    策略3：核心+宏观驱动（12M-1M长波）

    规则：
    - 月度调仓（月末最后一个交易日）
    - 使用12个月动量剔除最近1个月（252日-21日）
    - 市场择时规则同慢腿
    - 风控：基线止损-12%，根据市场状态调整

    Args:
        etf_codes: ETF代码列表
        start_date: 开始日期
        end_date: 结束日期
        momentum_params: 动量参数

    Returns:
        回测结果
    """
    config = BacktestConfig(start_date=start_date, end_date=end_date)
    engine = BacktestEngine(config)

    # 加载数据
    etf_data = engine.load_data(etf_codes)
    market_data = engine.load_market_index()

    if not etf_data:
        raise ValueError("无法加载ETF数据")

    # 获取所有交易日
    all_dates = sorted(set().union(*[set(df.index.date) for df in etf_data.values()]))

    # 参数设置: 12M-1M动量
    momentum_window = 252  # 12个月
    skip_window = 21  # 跳过最近1个月

    # 开始回测循环
    for i, current_date in enumerate(all_dates):
        # 获取当前价格
        prices = {}
        for code, df in etf_data.items():
            if current_date in df.index.date:
                idx = pd.Timestamp(current_date)
                prices[code] = float(df.loc[idx, 'close'])

        # 更新权益
        engine.update_equity(current_date, prices)

        # 检查止损
        engine.check_stop_loss(current_date, prices)

        # 判断是否为月末
        is_month_end = False
        if i < len(all_dates) - 1:
            next_date = all_dates[i + 1]
            is_month_end = current_date.month != next_date.month
        else:
            is_month_end = True

        if not is_month_end:
            continue

        # 月末调仓
        # 1. 计算每个ETF的12M-1M动量
        momentum_scores = {}
        for code, df in etf_data.items():
            if current_date not in df.index.date:
                continue

            idx = pd.Timestamp(current_date)
            history = df.loc[:idx]

            if len(history) < momentum_window + skip_window:
                continue

            # 获取当前价和252-21日前的价格
            current_price = history.iloc[-1]['close']
            past_price = history.iloc[-(momentum_window + skip_window)]['close']

            if past_price > 0:
                momentum = (current_price - past_price) / past_price
                momentum_scores[code] = momentum

        # 2. 获取市场状态
        market_above_ma200 = False
        market_atr_pct = 0.0

        if current_date in market_data.index.date:
            market_idx = pd.Timestamp(current_date)
            market_above_ma200 = bool(market_data.loc[market_idx, 'above_ma200'])
            market_atr_pct = float(market_data.loc[market_idx, 'atr20_pct'])

        # 3. 根据市场状态确定持仓数和权重
        if market_above_ma200:
            num_positions = 2
            position_weight = 0.20
        else:
            num_positions = 1
            position_weight = 0.15

        # 4. 选择动量最高的N只ETF
        sorted_etfs = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        selected_etfs = sorted_etfs[:num_positions]

        # 5. 构建目标持仓
        target_positions = {}
        for code, score in selected_etfs:
            target_positions[code] = position_weight

        # 6. 执行调仓
        engine.rebalance(
            date=current_date,
            target_positions=target_positions,
            prices=prices,
            reason="12M-1M月度调仓"
        )

        # 7. 设置止损价
        for code in target_positions:
            if code not in engine.positions:
                continue

            position = engine.positions[code]

            # 长波策略使用基线止损
            if market_above_ma200 and market_atr_pct < 4.0:
                stop_loss_pct = -0.10
            elif market_above_ma200:
                stop_loss_pct = -0.12
            else:
                stop_loss_pct = -0.15

            position.stop_loss_price = position.entry_price * (1 + stop_loss_pct)

    # 生成回测结果
    metrics = engine.calculate_metrics()

    dates, values = zip(*engine.equity_history) if engine.equity_history else ([], [])
    equity_curve = pd.Series(values, index=pd.DatetimeIndex(dates))

    positions_data = []
    for trade in engine.trades:
        if trade.action == 'BUY':
            positions_data.append({
                'date': trade.date,
                'code': trade.code,
                'shares': trade.shares,
                'price': trade.price
            })

    positions_history = pd.DataFrame(positions_data) if positions_data else pd.DataFrame()

    return BacktestResult(
        strategy_name="核心+宏观驱动(12M-1M)",
        total_return=metrics.get('total_return', 0),
        annual_return=metrics.get('annual_return', 0),
        sharpe_ratio=metrics.get('sharpe_ratio', 0),
        max_drawdown=metrics.get('max_drawdown', 0),
        win_rate=metrics.get('win_rate', 0),
        trades=engine.trades,
        equity_curve=equity_curve,
        positions_history=positions_history,
        metrics=metrics
    )


def run_improved_slow_leg_strategy(
    etf_codes: List[str],
    start_date: str,
    end_date: str,
    momentum_params: Dict[str, Any]
) -> BacktestResult:
    """
    改进策略：核心+慢腿轮动（观察期机制）

    改进点：
    1. 每周检查动量排名（而非每月）
    2. 观察期机制：连续2周掉出前2才换仓
    3. 集成稳定度权重（降低追高风险）
    4. 止损优先：触发止损立即卖出，无视观察期

    规则：
    - 检查频率：每周五
    - 动量计算：0.6×(3M-1M) + 0.4×(6M-1M)
    - 稳定度调整：20%权重
    - 持仓数量：市场强势2条腿×20%，弱势1条腿×15%
    - 换仓条件：连续2周排名<3，或触发止损
    - 重新入选：观察期内重回前2，取消换仓
    - 止损：强势市场-10%，正常市场-12%，弱势市场-15%

    Args:
        etf_codes: ETF代码列表
        start_date: 开始日期
        end_date: 结束日期
        momentum_params: 动量参数

    Returns:
        回测结果
    """
    config = BacktestConfig(start_date=start_date, end_date=end_date)
    engine = BacktestEngine(config)

    # 加载数据
    etf_data = engine.load_data(etf_codes)
    market_data = engine.load_market_index()

    if not etf_data:
        raise ValueError("无法加载ETF数据")

    # 获取所有交易日
    all_dates = sorted(set().union(*[set(df.index.date) for df in etf_data.values()]))

    # 参数设置
    windows = momentum_params.get('momentum_windows', [63, 126])
    weights = momentum_params.get('momentum_weights', [0.6, 0.4])
    skip_windows = momentum_params.get('momentum_skip_windows', [21, 21])
    stability_weight = momentum_params.get('stability_weight', 0.2)
    stability_window = momentum_params.get('stability_window', 30)
    observation_weeks = momentum_params.get('observation_weeks', 2)  # 观察期周数

    # 观察期跟踪：{code: weeks_out_of_top}
    observation_tracker: Dict[str, int] = {}

    # 稳定度历史：用于计算稳定度得分
    rank_history: List[Dict[str, int]] = []

    # 开始回测循环
    for i, current_date in enumerate(all_dates):
        # 获取当前价格
        prices = {}
        for code, df in etf_data.items():
            if current_date in df.index.date:
                idx = pd.Timestamp(current_date)
                prices[code] = float(df.loc[idx, 'close'])

        # 更新权益
        engine.update_equity(current_date, prices)

        # 检查止损（优先级最高，立即执行）
        engine.check_stop_loss(current_date, prices)

        # 判断是否为周五
        is_friday = current_date.weekday() == 4

        if not is_friday:
            continue

        # 每周五检查动量排名
        # 1. 计算每个ETF的原始动量得分
        momentum_scores = {}
        for code, df in etf_data.items():
            if current_date not in df.index.date:
                continue

            idx = pd.Timestamp(current_date)
            score = 0.0

            for window, weight, skip in zip(windows, weights, skip_windows):
                if len(df.loc[:idx]) < window + skip:
                    continue

                # 计算动量：(当前价 - N日前价) / N日前价
                history = df.loc[:idx].tail(window + skip + 1)
                if len(history) < window + skip:
                    continue

                current_price = history.iloc[-1]['close']
                past_price = history.iloc[-(window + skip)]['close']

                if past_price > 0:
                    momentum = (current_price - past_price) / past_price
                    score += momentum * weight

            momentum_scores[code] = score

        # 2. 计算排名并记录历史
        sorted_by_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        current_ranks = {code: rank + 1 for rank, (code, _) in enumerate(sorted_by_momentum)}
        rank_history.append(current_ranks)

        # 保持稳定度窗口大小
        if len(rank_history) > stability_window:
            rank_history.pop(0)

        # 3. 计算稳定度得分（基于排名历史）
        stability_scores = {}
        if len(rank_history) >= 2:
            for code in momentum_scores.keys():
                # 计算该标的在历史窗口内出现在前10的频率
                appearances_in_top10 = sum(
                    1 for ranks in rank_history
                    if code in ranks and ranks[code] <= 10
                )
                stability_scores[code] = appearances_in_top10 / len(rank_history)
        else:
            # 历史不足，稳定度设为1（不调整）
            stability_scores = {code: 1.0 for code in momentum_scores.keys()}

        # 4. 应用稳定度权重调整动量得分
        adjusted_scores = {}
        for code, mom_score in momentum_scores.items():
            stability = stability_scores.get(code, 1.0)
            # 调整公式：adjusted = momentum × [(1-w) + w×stability]
            factor = (1.0 - stability_weight) + stability_weight * stability
            adjusted_scores[code] = mom_score * factor

        # 5. 获取市场状态
        market_above_ma200 = False
        market_atr_pct = 0.0

        if current_date in market_data.index.date:
            market_idx = pd.Timestamp(current_date)
            market_above_ma200 = bool(market_data.loc[market_idx, 'above_ma200'])
            market_atr_pct = float(market_data.loc[market_idx, 'atr20_pct'])

        # 6. 根据市场状态确定持仓数和权重
        if market_above_ma200:
            num_positions = 2
            position_weight = 0.20  # 20%/腿
        else:
            num_positions = 1
            position_weight = 0.15  # 15%/腿

        # 6.5. 应用组合风控约束
        max_satellite_exposure = engine.get_max_satellite_exposure()
        total_target_exposure = num_positions * position_weight

        if total_target_exposure > max_satellite_exposure:
            # 需要降低仓位
            if max_satellite_exposure > 0:
                position_weight = max_satellite_exposure / num_positions
            else:
                # 极端情况，清仓
                num_positions = 0
                position_weight = 0.0

        # 7. 选择调整后得分最高的N只ETF作为候选
        sorted_adjusted = sorted(adjusted_scores.items(), key=lambda x: x[1], reverse=True)
        top_candidates = [code for code, _ in sorted_adjusted[:num_positions]] if num_positions > 0 else []

        # 8. 观察期机制：检查当前持仓
        current_holdings = set(engine.positions.keys())
        target_positions = {}

        for code in current_holdings:
            # 检查持仓是否还在前N
            if code in top_candidates:
                # 仍在前N，保持持仓，重置观察期
                target_positions[code] = position_weight
                observation_tracker[code] = 0
            else:
                # 掉出前N，增加观察期计数
                observation_tracker[code] = observation_tracker.get(code, 0) + 1

                # 检查是否达到观察期阈值
                if observation_tracker[code] >= observation_weeks:
                    # 连续N周掉出前N，执行换仓
                    # 不加入target_positions，将被卖出
                    pass
                else:
                    # 还在观察期内，暂时保持持仓
                    target_positions[code] = position_weight

        # 9. 填补空位：如果持仓数不足，从候选中补充
        if len(target_positions) < num_positions:
            for code in top_candidates:
                if code not in target_positions:
                    target_positions[code] = position_weight
                    observation_tracker[code] = 0  # 新持仓，重置观察期

                if len(target_positions) >= num_positions:
                    break

        # 10. 执行调仓
        engine.rebalance(
            date=current_date,
            target_positions=target_positions,
            prices=prices,
            reason="周度检查调仓"
        )

        # 11. 设置止损价
        for code in target_positions:
            if code not in engine.positions:
                continue

            position = engine.positions[code]

            # 根据市场状态设置止损
            if market_above_ma200 and market_atr_pct < 4.0:
                stop_loss_pct = -0.10  # 强趋势止损-10%
            elif market_above_ma200:
                stop_loss_pct = -0.12  # 基线止损-12%
            else:
                stop_loss_pct = -0.15  # 震荡/高波动止损-15%

            position.stop_loss_price = position.entry_price * (1 + stop_loss_pct)

    # 生成回测结果
    metrics = engine.calculate_metrics()

    dates, values = zip(*engine.equity_history) if engine.equity_history else ([], [])
    equity_curve = pd.Series(values, index=pd.DatetimeIndex(dates))

    positions_data = []
    for trade in engine.trades:
        if trade.action == 'BUY':
            positions_data.append({
                'date': trade.date,
                'code': trade.code,
                'shares': trade.shares,
                'price': trade.price
            })

    positions_history = pd.DataFrame(positions_data) if positions_data else pd.DataFrame()

    return BacktestResult(
        strategy_name="改进慢腿轮动(观察期)",
        total_return=metrics.get('total_return', 0),
        annual_return=metrics.get('annual_return', 0),
        sharpe_ratio=metrics.get('sharpe_ratio', 0),
        max_drawdown=metrics.get('max_drawdown', 0),
        win_rate=metrics.get('win_rate', 0),
        trades=engine.trades,
        equity_curve=equity_curve,
        positions_history=positions_history,
        metrics=metrics
    )
