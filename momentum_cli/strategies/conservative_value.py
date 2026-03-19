"""
策略1: 保守价值策略

特点:
- 低波动、高稳定度
- 月度调仓，长观察期
- 严格相关性控制
- 偏好价值/红利风格
"""

from typing import List, Optional, Dict
import pandas as pd
import numpy as np

from .base import BaseStrategy, StrategyConfig


class ConservativeValueStrategy(BaseStrategy):
    """保守价值策略"""
    
    def __init__(self):
        config = StrategyConfig(
            name="保守价值策略",
            description="低波动、高稳定度、价值风格偏好。适合风险厌恶型投资者，追求稳健收益。",
            
            # 持仓参数
            max_positions=2,
            position_size=0.15,  # 保守仓位
            
            # 调仓参数
            rebalance_frequency="monthly",
            observation_period=3,  # 长观察期，避免频繁换仓
            
            # 动量参数
            momentum_windows=[126, 252],  # 长周期动量
            momentum_weights=[0.5, 0.5],
            momentum_skip_windows=[21, 21],
            
            # 过滤参数
            min_momentum_percentile=65.0,  # 较高阈值
            max_correlation=0.75,  # 严格相关性控制
            use_correlation_filter=True,
            
            # 稳定度参数
            stability_weight=0.4,  # 高稳定度权重
            stability_window=60,  # 长稳定度窗口
            
            # 风控参数
            stop_loss_pct=-0.10,  # 严格止损
            portfolio_drawdown_limit=-0.15,  # 严格回撤限制
            
            # 市场状态
            use_market_regime=True,
        )
        super().__init__(config)
    
    def select_assets(
        self,
        momentum_scores: pd.Series,
        momentum_percentiles: pd.Series,
        market_data: Optional[pd.DataFrame],
        correlation_matrix: Optional[pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> List[str]:
        """
        选择资产 - 保守策略
        
        优先级:
        1. 动量分位数 >= 65%
        2. 稳定度高（通过高权重体现）
        3. 相关性低
        4. 偏好低波动资产
        """
        # 过滤动量阈值
        candidates = momentum_percentiles[momentum_percentiles >= self.config.min_momentum_percentile]
        
        if len(candidates) == 0:
            return []
        
        # 按动量得分排序
        candidates_sorted = candidates.sort_values(ascending=False)
        
        # 贪心选择，控制相关性
        selected = []
        for code in candidates_sorted.index:
            if len(selected) >= self.config.max_positions:
                break
            
            # 检查相关性
            if len(selected) > 0 and correlation_matrix is not None:
                correlations = []
                for s in selected:
                    if code in correlation_matrix.index and s in correlation_matrix.columns:
                        corr = correlation_matrix.loc[code, s]
                        if pd.notna(corr):
                            correlations.append(abs(corr))
                
                if correlations and max(correlations) > self.config.max_correlation:
                    continue
            
            selected.append(code)
        
        return selected
    
    def calculate_position_sizes(
        self,
        selected_assets: List[str],
        market_data: Optional[pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        计算仓位 - 保守策略
        
        等权配置，总仓位不超过30%
        """
        if not selected_assets:
            return {}
        
        # 等权
        weight = self.config.position_size
        
        # 市场弱势时降低仓位
        if market_data is not None and current_date in market_data.index:
            above_ma200 = market_data.loc[current_date, 'above_ma200']
            if not above_ma200:
                weight *= 0.7  # 降低30%
        
        return {code: weight for code in selected_assets}

