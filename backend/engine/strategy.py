"""
Momentum strategy implementation
动量策略实现
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

try:
    from indicators import MomentumCalculator, CorrelationAnalyzer
    from engine.state_machine import MarketState
except ImportError:
    # 备用导入方式
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from indicators import MomentumCalculator, CorrelationAnalyzer
    from .state_machine import MarketState


class MomentumStrategy:
    """
    动量策略类
    实现基于动量的选股和持仓管理
    """
    
    def __init__(self, 
                 min_hold_days: int = 20,
                 buffer_zone: float = 0.05,
                 stop_loss: float = -0.08,
                 correlation_threshold: float = 0.7):
        """
        初始化动量策略
        
        Args:
            min_hold_days: 最短持有天数
            buffer_zone: 缓冲区（避免频繁换腿）
            stop_loss: 止损线
            correlation_threshold: 相关性阈值
        """
        self.min_hold_days = min_hold_days
        self.buffer_zone = buffer_zone
        self.stop_loss = stop_loss
        self.correlation_threshold = correlation_threshold
        
        self.momentum_calc = MomentumCalculator()
        self.correlation_analyzer = CorrelationAnalyzer()
        
        # 持仓记录
        self.holdings = {}
        self.holding_start_dates = {}
        self.entry_prices = {}
        
    def select_etfs(self, 
                    momentum_ranking: pd.DataFrame,
                    market_state: MarketState,
                    existing_holdings: Optional[List[str]] = None) -> List[str]:
        """
        根据动量排名选择ETF
        
        Args:
            momentum_ranking: 动量排名DataFrame
            market_state: 市场状态
            existing_holdings: 现有持仓
            
        Returns:
            推荐的ETF代码列表
        """
        try:
            if momentum_ranking.empty:
                return []
                
            # 根据市场状态确定选择数量
            if market_state == MarketState.OFFENSE:
                n_select = 4
                min_momentum = 0.05  # 最低动量要求5%
            elif market_state == MarketState.NEUTRAL:
                n_select = 3
                min_momentum = 0.03
            else:  # DEFENSE
                n_select = 2
                min_momentum = 0.00
                
            # 筛选满足最低动量要求的ETF
            qualified = momentum_ranking[momentum_ranking['momentum_score'] > min_momentum]
            
            if qualified.empty:
                logger.warning("No ETFs meet minimum momentum requirement")
                return []
                
            # 如果有现有持仓，考虑缓冲区
            if existing_holdings:
                selected = self._apply_buffer_zone(qualified, existing_holdings, n_select)
            else:
                # 直接选择前N个
                selected = qualified.head(n_select)['code'].tolist()
                
            logger.info(f"Selected {len(selected)} ETFs: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"Error selecting ETFs: {str(e)}")
            return []
            
    def check_rotation_signal(self, 
                             current_holding: str,
                             momentum_ranking: pd.DataFrame,
                             holding_days: int) -> Tuple[bool, Optional[str]]:
        """
        检查是否需要换腿
        
        Args:
            current_holding: 当前持仓代码
            momentum_ranking: 最新动量排名
            holding_days: 已持有天数
            
        Returns:
            (是否需要换腿, 新的ETF代码)
        """
        try:
            # 检查最短持有期
            if holding_days < self.min_hold_days:
                return False, None
                
            # 获取当前持仓的排名
            current_rank = momentum_ranking[momentum_ranking['code'] == current_holding]['rank'].values
            
            if len(current_rank) == 0:
                logger.warning(f"Current holding {current_holding} not in ranking")
                return False, None
                
            current_rank = current_rank[0]
            
            # 检查是否跌出前10名
            if current_rank > 10:
                # 选择新的ETF（排名第一且相关性低的）
                top_etf = momentum_ranking.iloc[0]['code']
                if top_etf != current_holding:
                    logger.info(f"Rotation signal: {current_holding} (rank {current_rank}) -> {top_etf}")
                    return True, top_etf
                    
            # 检查是否触发止损
            if current_holding in self.entry_prices:
                current_price = momentum_ranking[momentum_ranking['code'] == current_holding]['last_price'].values
                if len(current_price) > 0:
                    returns = (current_price[0] - self.entry_prices[current_holding]) / self.entry_prices[current_holding]
                    if returns < self.stop_loss:
                        logger.warning(f"Stop loss triggered for {current_holding}: {returns:.2%}")
                        # 选择防守型ETF
                        return True, self._select_defensive_etf(momentum_ranking)
                        
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking rotation signal: {str(e)}")
            return False, None
            
    def _apply_buffer_zone(self, 
                          qualified: pd.DataFrame,
                          existing_holdings: List[str],
                          n_select: int) -> List[str]:
        """
        应用缓冲区逻辑，避免频繁换腿
        
        Args:
            qualified: 符合条件的ETF
            existing_holdings: 现有持仓
            n_select: 需要选择的数量
            
        Returns:
            考虑缓冲区后的选择列表
        """
        selected = []
        
        # 先保留仍在前列的现有持仓
        for holding in existing_holdings:
            holding_data = qualified[qualified['code'] == holding]
            if not holding_data.empty:
                rank = holding_data.iloc[0]['rank']
                # 如果排名在缓冲区内，继续持有
                if rank <= n_select * (1 + self.buffer_zone):
                    selected.append(holding)
                    
        # 如果还需要更多，从排名靠前的选择
        if len(selected) < n_select:
            for _, row in qualified.iterrows():
                if row['code'] not in selected:
                    selected.append(row['code'])
                    if len(selected) >= n_select:
                        break
                        
        return selected
        
    def _select_defensive_etf(self, momentum_ranking: pd.DataFrame) -> str:
        """
        选择防守型ETF
        
        Args:
            momentum_ranking: 动量排名
            
        Returns:
            防守型ETF代码
        """
        # 优先选择红利、银行等防守型ETF
        defensive_etfs = ['510880', '512800', '511990']  # 红利、银行、货币
        
        for etf in defensive_etfs:
            if etf in momentum_ranking['code'].values:
                return etf
                
        # 如果没有防守型，选择动量最低但为正的
        positive_momentum = momentum_ranking[momentum_ranking['momentum_score'] > 0]
        if not positive_momentum.empty:
            return positive_momentum.iloc[-1]['code']
            
        # 实在没有，返回第一个
        return momentum_ranking.iloc[0]['code']
        
    def update_holdings(self, new_holdings: Dict[str, float], prices: Dict[str, float]):
        """
        更新持仓记录
        
        Args:
            new_holdings: 新的持仓 {code: weight}
            prices: 当前价格 {code: price}
        """
        current_date = datetime.now().date()
        
        for code, weight in new_holdings.items():
            if code not in self.holdings:
                # 新建仓
                self.holding_start_dates[code] = current_date
                self.entry_prices[code] = prices.get(code, 0)
                logger.info(f"New position: {code} at {self.entry_prices[code]}")
                
        # 清理已平仓的记录
        for code in list(self.holdings.keys()):
            if code not in new_holdings:
                if code in self.holding_start_dates:
                    del self.holding_start_dates[code]
                if code in self.entry_prices:
                    del self.entry_prices[code]
                logger.info(f"Closed position: {code}")
                
        self.holdings = new_holdings
        
    def get_holding_days(self, code: str) -> int:
        """
        获取持有天数
        
        Args:
            code: ETF代码
            
        Returns:
            持有天数
        """
        if code not in self.holding_start_dates:
            return 0
            
        return (datetime.now().date() - self.holding_start_dates[code]).days