"""
Momentum calculation and ranking
动量计算与排名
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger


class MomentumCalculator:
    """
    动量计算器
    计算ETF的动量分数并进行排名
    """
    
    def __init__(self, short_window: int = 63, long_window: int = 126,
                 short_weight: float = 0.6, long_weight: float = 0.4):
        """
        初始化动量计算器
        
        Args:
            short_window: 短期动量窗口（默认63个交易日，约3个月）
            long_window: 长期动量窗口（默认126个交易日，约6个月）
            short_weight: 短期动量权重
            long_weight: 长期动量权重
        """
        self.short_window = short_window
        self.long_window = long_window
        self.short_weight = short_weight
        self.long_weight = long_weight
        
        # 验证权重和为1
        if abs(short_weight + long_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {short_weight + long_weight}, normalizing...")
            total = short_weight + long_weight
            self.short_weight = short_weight / total
            self.long_weight = long_weight / total
            
    def calculate_momentum(self, prices: pd.Series) -> Dict[str, float]:
        """
        计算单个资产的动量指标
        
        Args:
            prices: 价格序列
            
        Returns:
            包含各种动量指标的字典
        """
        try:
            if len(prices) < self.long_window:
                logger.warning(f"Insufficient data for momentum calculation: {len(prices)} < {self.long_window}")
                return self._empty_momentum()
                
            # 计算收益率
            r63 = self._calculate_return(prices, self.short_window)
            r126 = self._calculate_return(prices, self.long_window)
            
            # 计算其他时间窗口的收益率
            r20 = self._calculate_return(prices, 20)  # 1个月
            r252 = self._calculate_return(prices, min(252, len(prices)-1))  # 1年
            
            # 计算动量趋势（收益率的变化）
            momentum_trend = self._calculate_momentum_trend(prices)
            
            # 计算风险调整后的动量
            risk_adjusted_r63 = self._calculate_risk_adjusted_return(prices, self.short_window)
            risk_adjusted_r126 = self._calculate_risk_adjusted_return(prices, self.long_window)
            
            result = {
                'r20': r20,
                'r63': r63,
                'r126': r126,
                'r252': r252,
                'risk_adj_r63': risk_adjusted_r63,
                'risk_adj_r126': risk_adjusted_r126,
                'momentum_trend': momentum_trend,
                'last_price': prices.iloc[-1],
                'data_points': len(prices)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating momentum: {str(e)}")
            return self._empty_momentum()
            
    def calculate_momentum_score(self, momentum_data: Dict[str, float]) -> float:
        """
        计算动量综合得分
        公式: Score = 0.6 * r63 + 0.4 * r126
        
        Args:
            momentum_data: 动量数据字典
            
        Returns:
            动量得分
        """
        r63 = momentum_data.get('r63', 0)
        r126 = momentum_data.get('r126', 0)
        
        score = self.short_weight * r63 + self.long_weight * r126
        
        return score
        
    def rank_by_momentum(self, etf_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        对多个ETF进行动量排名
        
        Args:
            etf_data: {etf_code: price_dataframe} 字典
            
        Returns:
            排名后的DataFrame
        """
        try:
            results = []
            
            for etf_code, df in etf_data.items():
                if df.empty or 'close' not in df.columns:
                    logger.warning(f"Skipping {etf_code}: invalid data")
                    continue
                    
                # 计算动量
                momentum = self.calculate_momentum(df['close'])
                
                # 计算综合得分
                score = self.calculate_momentum_score(momentum)
                
                # 添加到结果列表
                results.append({
                    'code': etf_code,
                    'r20': momentum['r20'],
                    'r63': momentum['r63'],
                    'r126': momentum['r126'],
                    'r252': momentum['r252'],
                    'momentum_score': score,
                    'risk_adj_r63': momentum['risk_adj_r63'],
                    'risk_adj_r126': momentum['risk_adj_r126'],
                    'momentum_trend': momentum['momentum_trend'],
                    'last_price': momentum['last_price']
                })
                
            # 创建DataFrame
            df_results = pd.DataFrame(results)
            
            if df_results.empty:
                return df_results
                
            # 计算排名
            df_results['rank_r63'] = df_results['r63'].rank(ascending=False, method='dense')
            df_results['rank_r126'] = df_results['r126'].rank(ascending=False, method='dense')
            df_results['rank_score'] = df_results['momentum_score'].rank(ascending=False, method='dense')
            
            # 按综合得分排序
            df_results = df_results.sort_values('momentum_score', ascending=False)
            
            # 添加排名
            df_results['rank'] = range(1, len(df_results) + 1)
            
            logger.info(f"Ranked {len(df_results)} ETFs by momentum")
            return df_results
            
        except Exception as e:
            logger.error(f"Error ranking ETFs: {str(e)}")
            return pd.DataFrame()
            
    def get_top_momentum(self, ranking_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        获取动量前N名
        
        Args:
            ranking_df: 排名DataFrame
            n: 前N名
            
        Returns:
            前N名的DataFrame
        """
        if ranking_df.empty:
            return ranking_df
            
        return ranking_df.head(n).copy()
        
    def check_momentum_reversal(self, prices: pd.Series, lookback: int = 20) -> bool:
        """
        检查动量是否出现反转
        
        Args:
            prices: 价格序列
            lookback: 回看期
            
        Returns:
            是否出现反转
        """
        try:
            if len(prices) < lookback * 2:
                return False
                
            # 计算近期和前期的动量
            recent_return = self._calculate_return(prices[-lookback:], lookback-1)
            previous_return = self._calculate_return(prices[-lookback*2:-lookback], lookback-1)
            
            # 如果符号相反且幅度较大，则认为出现反转
            if recent_return * previous_return < 0 and abs(recent_return - previous_return) > 0.1:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking momentum reversal: {str(e)}")
            return False
            
    def _calculate_return(self, prices: pd.Series, window: int) -> float:
        """
        计算收益率
        
        Args:
            prices: 价格序列
            window: 计算窗口
            
        Returns:
            收益率
        """
        if len(prices) <= window:
            return 0
            
        start_price = prices.iloc[-window-1]
        end_price = prices.iloc[-1]
        
        if start_price == 0:
            return 0
            
        return (end_price - start_price) / start_price
        
    def _calculate_risk_adjusted_return(self, prices: pd.Series, window: int) -> float:
        """
        计算风险调整后的收益率
        
        Args:
            prices: 价格序列
            window: 计算窗口
            
        Returns:
            风险调整后的收益率（夏普比率的简化版）
        """
        if len(prices) <= window:
            return 0
            
        # 计算收益率序列
        returns = prices.pct_change().dropna()
        
        if len(returns) < window:
            return 0
            
        # 计算窗口期内的收益率和波动率
        window_returns = returns.iloc[-window:]
        mean_return = window_returns.mean()
        std_return = window_returns.std()
        
        if std_return == 0:
            return 0
            
        # 简化的夏普比率（未年化）
        return mean_return / std_return
        
    def _calculate_momentum_trend(self, prices: pd.Series) -> str:
        """
        计算动量趋势
        
        Args:
            prices: 价格序列
            
        Returns:
            趋势描述: 'accelerating', 'decelerating', 'stable'
        """
        try:
            if len(prices) < self.long_window:
                return 'stable'
                
            # 计算不同时期的动量
            r1 = self._calculate_return(prices[-self.short_window:], self.short_window-1)
            r2 = self._calculate_return(prices[-self.long_window:-self.short_window], 
                                      self.long_window-self.short_window-1)
            
            # 判断趋势
            if r1 > r2 * 1.2:  # 动量加速
                return 'accelerating'
            elif r1 < r2 * 0.8:  # 动量减速
                return 'decelerating'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error calculating momentum trend: {str(e)}")
            return 'stable'
            
    def _empty_momentum(self) -> Dict[str, float]:
        """返回空的动量数据"""
        return {
            'r20': 0,
            'r63': 0,
            'r126': 0,
            'r252': 0,
            'risk_adj_r63': 0,
            'risk_adj_r126': 0,
            'momentum_trend': 'stable',
            'last_price': 0,
            'data_points': 0
        }