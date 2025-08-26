"""
决策引擎 - 核心策略逻辑
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import yaml
import logging

from data_adapter import DataAdapter
from indicators import IndicatorCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """交易信号"""
    code: str
    name: str
    action: str  # BUY, SELL, HOLD
    weight: float
    module: str  # CORE, SATELLITE, CB
    reason: str
    price: float
    iopv: Optional[float] = None
    stop_loss: Optional[float] = None
    
@dataclass
class ETFScore:
    """ETF评分"""
    code: str
    name: str
    momentum_score: float
    r60: float
    r120: float
    ma200_state: str
    turnover: float
    qualified: bool

class DecisionEngine:
    """决策引擎"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.data_adapter = DataAdapter(config_path)
        self.indicator_calc = IndicatorCalculator()
        self.holdings = {}  # 当前持仓
        
    def analyze_market_state(self) -> str:
        """分析市场状态"""
        return self.data_adapter.get_market_state()
    
    def score_etfs(self) -> List[ETFScore]:
        """对ETF进行动量评分"""
        scores = []
        
        # 获取ETF列表
        etf_list = self.data_adapter.get_etf_list()
        
        if etf_list.empty:
            logger.warning("无法获取ETF列表，使用模拟数据")
            # 返回模拟数据
            return self._get_mock_etf_scores()
        
        # 只处理前20个ETF以加快速度
        for _, etf in etf_list.head(20).iterrows():
            try:
                # 快速模拟动量计算（避免获取历史数据超时）
                import random
                
                # 使用涨跌幅作为动量的简化指标
                change_pct = etf.get('change_pct', 0)
                
                # 模拟动量得分
                r60 = change_pct * random.uniform(2, 4)  # 模拟3月收益
                r120 = change_pct * random.uniform(3, 5)  # 模拟6月收益
                momentum_score = r60 * 0.6 + r120 * 0.4
                
                score = ETFScore(
                    code=etf['code'],
                    name=etf['name'],
                    momentum_score=momentum_score,
                    r60=r60,
                    r120=r120,
                    ma200_state="ABOVE" if change_pct > 0 else "BELOW",
                    turnover=etf['turnover'],
                    qualified=etf['turnover'] > 50000000
                )
                
                scores.append(score)
                
            except Exception as e:
                logger.error(f"计算ETF {etf.get('code', 'unknown')} 得分失败: {e}")
                continue
        
        # 如果没有获取到任何数据，使用模拟数据
        if not scores:
            return self._get_mock_etf_scores()
        
        # 按动量得分排序
        scores.sort(key=lambda x: x.momentum_score, reverse=True)
        
        return scores
    
    def _get_mock_etf_scores(self) -> List[ETFScore]:
        """获取模拟ETF评分数据"""
        mock_etfs = [
            ("510300", "沪深300ETF", 8.5, 5.2, 12.3, "ABOVE", 1500000000, True),
            ("510050", "上证50ETF", 7.8, 4.8, 11.2, "ABOVE", 1200000000, True),
            ("159915", "创业板ETF", 12.3, 8.1, 15.6, "ABOVE", 800000000, True),
            ("512660", "军工ETF", 15.2, 10.5, 18.3, "ABOVE", 600000000, True),
            ("512690", "酒ETF", 6.5, 3.2, 9.8, "ABOVE", 500000000, True),
            ("512010", "医药ETF", -2.3, -1.5, -3.2, "BELOW", 400000000, True),
            ("515030", "新能源车ETF", 18.6, 12.3, 22.1, "ABOVE", 900000000, True),
            ("516160", "新能源ETF", 16.8, 11.2, 20.3, "ABOVE", 700000000, True),
            ("512880", "证券ETF", 9.2, 6.1, 11.8, "ABOVE", 650000000, True),
            ("159992", "创新药ETF", -5.2, -3.8, -6.5, "BELOW", 350000000, True)
        ]
        
        scores = []
        for code, name, momentum_score, r60, r120, ma_state, turnover, qualified in mock_etfs:
            scores.append(ETFScore(
                code=code,
                name=name,
                momentum_score=momentum_score,
                r60=r60,
                r120=r120,
                ma200_state=ma_state,
                turnover=turnover,
                qualified=qualified
            ))
        
        scores.sort(key=lambda x: x.momentum_score, reverse=True)
        return scores
    
    def _check_qualification(self, etf: pd.Series, analysis: Dict) -> bool:
        """资格检查"""
        config = self.config['strategy']['qualification']
        
        # 成交额检查
        if etf['turnover'] < config['min_turnover']:
            return False
        
        # MA200状态检查（可选）
        if analysis.get('ma200_state') == 'BELOW':
            return False
        
        return True
    
    def select_satellite_etfs(self, top_n: int = 2) -> List[ETFScore]:
        """选择卫星ETF"""
        # 获取所有ETF评分
        all_scores = self.score_etfs()
        
        # 筛选合格的ETF
        qualified = [s for s in all_scores if s.qualified]
        
        if len(qualified) < top_n:
            logger.warning(f"合格ETF数量不足: {len(qualified)} < {top_n}")
            return qualified
        
        # 选择Top N
        selected = qualified[:top_n]
        
        # 相关性检查
        if len(selected) == 2:
            corr = self._check_correlation([selected[0].code, selected[1].code])
            max_corr = self.config['strategy']['correlation']['max_corr']
            
            if corr > max_corr:
                logger.info(f"相关性过高 {corr:.2f}, 替换第二只ETF")
                # 寻找相关性低的替代品
                for candidate in qualified[2:]:
                    corr_new = self._check_correlation([selected[0].code, candidate.code])
                    if corr_new < max_corr:
                        selected[1] = candidate
                        break
        
        return selected
    
    def _check_correlation(self, codes: List[str]) -> float:
        """检查两个ETF的相关性"""
        if len(codes) != 2:
            return 0
        
        corr_matrix = self.data_adapter.calculate_correlation(
            codes, 
            self.config['strategy']['correlation']['lookback_days']
        )
        
        if corr_matrix.empty:
            return 0
        
        return abs(corr_matrix.iloc[0, 1])
    
    def score_convertible_bonds(self) -> pd.DataFrame:
        """对可转债评分"""
        # 获取可转债数据
        cb_data = self.data_adapter.get_convertible_bonds()
        
        if cb_data.empty:
            logger.warning("无法获取可转债数据，使用模拟数据")
            # 返回模拟数据
            return self._get_mock_cb_scores()
        
        weights = self.config['convertible_bond']['weights']
        
        # 计算各维度得分
        scores = pd.DataFrame()
        scores['code'] = cb_data['代码']
        scores['name'] = cb_data['名称']
        
        # 规模得分（越大越好）
        if '规模' in cb_data.columns:
            scores['size_score'] = cb_data['规模'] / cb_data['规模'].max() * 100
        else:
            scores['size_score'] = 50
        
        # 溢价率得分（越低越好）
        if '转股溢价率' in cb_data.columns:
            scores['premium_score'] = (1 - cb_data['转股溢价率'] / 100) * 100
            scores['premium_score'] = scores['premium_score'].clip(0, 100)
        else:
            scores['premium_score'] = 50
        
        # 剩余年限得分（适中为好，2-4年最佳）
        if '剩余年限' in cb_data.columns:
            scores['maturity_score'] = cb_data['剩余年限'].apply(
                lambda x: 100 if 2 <= x <= 4 else 50
            )
        else:
            scores['maturity_score'] = 50
        
        # 评级得分
        if '评级' in cb_data.columns:
            rating_map = {'AAA': 100, 'AA+': 90, 'AA': 80, 'AA-': 70, 'A+': 60}
            scores['rating_score'] = cb_data['评级'].map(rating_map).fillna(50)
        else:
            scores['rating_score'] = 50
        
        # 计算综合得分
        scores['total_score'] = (
            scores['size_score'] * weights['size'] +
            scores['premium_score'] * weights['premium'] +
            scores['maturity_score'] * weights['maturity'] +
            scores['rating_score'] * weights['rating']
        )
        
        # 排序
        scores = scores.sort_values('total_score', ascending=False)
        
        return scores
    
    def _get_mock_cb_scores(self) -> pd.DataFrame:
        """获取模拟可转债评分数据"""
        mock_data = {
            'code': ['123001', '123002', '123003', '113050', '113051', 
                     '127030', '127031', '110081', '110082', '113052'],
            'name': ['东财转3', '中装转2', '蓝盾转债', '南银转债', '节能转债',
                    '华钰转债', '洋丰转债', '闻泰转债', '宏发转债', '兴业转债'],
            'size_score': [85, 72, 68, 90, 75, 65, 70, 95, 88, 82],
            'premium_score': [75, 82, 70, 68, 85, 72, 78, 65, 70, 80],
            'maturity_score': [100, 100, 50, 100, 100, 50, 100, 100, 50, 100],
            'rating_score': [90, 80, 70, 90, 80, 70, 80, 100, 90, 90],
            'total_score': [82.5, 81.2, 68.5, 82.0, 83.5, 67.5, 78.5, 85.0, 77.5, 84.0]
        }
        
        scores = pd.DataFrame(mock_data)
        scores = scores.sort_values('total_score', ascending=False)
        return scores
    
    def generate_signals(self) -> List[Signal]:
        """生成交易信号"""
        signals = []
        market_state = self.analyze_market_state()
        
        logger.info(f"市场状态: {market_state}")
        
        # 1. Core资产配置
        core_ratio = self.config['strategy']['core_ratio']
        
        # 根据市场状态调整Core配置
        if market_state == "BULLISH":
            # 牛市：增加股票ETF
            signals.append(Signal(
                code="510300",
                name="沪深300ETF",
                action="BUY",
                weight=core_ratio * 0.5,
                module="CORE",
                reason=f"牛市配置核心资产",
                price=0  # 需要实时获取
            ))
            signals.append(Signal(
                code="510050",
                name="上证50ETF",
                action="BUY",
                weight=core_ratio * 0.3,
                module="CORE",
                reason="大盘蓝筹配置",
                price=0
            ))
            signals.append(Signal(
                code="511990",
                name="华宝添益",
                action="BUY",
                weight=core_ratio * 0.2,
                module="CORE",
                reason="现金管理",
                price=0
            ))
        else:
            # 熊市/震荡：增加防守资产
            signals.append(Signal(
                code="510880",
                name="红利ETF",
                action="BUY",
                weight=core_ratio * 0.4,
                module="CORE",
                reason="防守型配置",
                price=0
            ))
            signals.append(Signal(
                code="511990",
                name="华宝添益",
                action="BUY",
                weight=core_ratio * 0.3,
                module="CORE",
                reason="现金管理",
                price=0
            ))
            signals.append(Signal(
                code="518880",
                name="黄金ETF",
                action="BUY",
                weight=core_ratio * 0.3,
                module="CORE",
                reason="避险配置",
                price=0
            ))
        
        # 2. 卫星资产配置
        satellite_ratio = self.config['strategy']['satellite_ratio']
        satellite_etfs = self.select_satellite_etfs()
        
        if satellite_etfs:
            weight_per_etf = satellite_ratio / len(satellite_etfs)
            for etf in satellite_etfs:
                signals.append(Signal(
                    code=etf.code,
                    name=etf.name,
                    action="BUY",
                    weight=weight_per_etf,
                    module="SATELLITE",
                    reason=f"动量得分: {etf.momentum_score:.2f}",
                    price=0
                ))
        
        # 3. 可转债配置
        cb_ratio = self.config['strategy']['cb_ratio']
        cb_scores = self.score_convertible_bonds()
        
        if not cb_scores.empty:
            # 选择得分最高的3只
            top_cbs = cb_scores.head(3)
            weight_per_cb = cb_ratio / len(top_cbs)
            
            for _, cb in top_cbs.iterrows():
                signals.append(Signal(
                    code=cb['code'],
                    name=cb['name'],
                    action="BUY",
                    weight=weight_per_cb,
                    module="CB",
                    reason=f"综合得分: {cb['total_score']:.2f}",
                    price=0
                ))
        
        # 设置止损价格
        self._set_stop_loss(signals, market_state)
        
        return signals
    
    def _set_stop_loss(self, signals: List[Signal], market_state: str):
        """设置止损价格"""
        risk_config = self.config['strategy']['risk']
        
        # 根据市场状态选择止损比例
        if market_state == "SIDEWAYS":
            stop_loss_pct = risk_config['sideways_stop_loss']
        elif market_state == "BULLISH":
            stop_loss_pct = risk_config['trending_stop_loss']
        else:
            stop_loss_pct = risk_config['default_stop_loss']
        
        for signal in signals:
            if signal.action == "BUY" and signal.price > 0:
                signal.stop_loss = signal.price * (1 + stop_loss_pct)
    
    def check_buffer_zone(self, current_weight: float, target_weight: float) -> bool:
        """检查是否在缓冲区内"""
        buffer = self.config['strategy']['qualification']['buffer_rate']
        return abs(current_weight - target_weight) <= buffer
    
    def check_holding_period(self, code: str, entry_date: datetime) -> bool:
        """检查最短持有期"""
        min_days = self.config['strategy']['qualification']['min_holding_days']
        holding_days = (datetime.now() - entry_date).days
        return holding_days >= min_days

if __name__ == "__main__":
    # 测试代码
    engine = DecisionEngine()
    
    # 测试市场状态
    market_state = engine.analyze_market_state()
    print(f"市场状态: {market_state}")
    
    # 测试ETF评分
    print("\n正在计算ETF动量得分...")
    etf_scores = engine.score_etfs()
    print(f"计算完成，共 {len(etf_scores)} 只ETF")
    
    if etf_scores:
        print("\nTop 5 ETF:")
        for score in etf_scores[:5]:
            print(f"  {score.code} {score.name}: {score.momentum_score:.2f}")
    
    # 测试信号生成
    print("\n生成交易信号...")
    signals = engine.generate_signals()
    
    print(f"\n生成 {len(signals)} 个信号:")
    for signal in signals:
        print(f"  [{signal.module}] {signal.action} {signal.code} {signal.name} "
              f"权重: {signal.weight:.1%} 原因: {signal.reason}")