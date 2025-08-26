"""
Correlation analysis for portfolio optimization
相关性分析用于投资组合优化
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.stats import pearsonr
from loguru import logger


class CorrelationAnalyzer:
    """
    相关性分析器
    计算资产间的相关性，用于投资组合优化
    """
    
    def __init__(self, window: int = 90):
        """
        初始化相关性分析器
        
        Args:
            window: 相关性计算窗口（默认90个交易日）
        """
        self.window = window
        
    def calculate_correlation_matrix(self, price_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        计算相关性矩阵
        
        Args:
            price_data: {asset_code: price_dataframe} 字典
            
        Returns:
            相关性矩阵DataFrame
        """
        try:
            # 提取收益率数据
            returns_dict = {}
            
            for code, df in price_data.items():
                if df.empty or 'close' not in df.columns:
                    continue
                    
                # 计算对数收益率
                returns = np.log(df['close'] / df['close'].shift(1))
                returns_dict[code] = returns.iloc[-self.window:] if len(returns) > self.window else returns
                
            if not returns_dict:
                return pd.DataFrame()
                
            # 创建收益率DataFrame
            returns_df = pd.DataFrame(returns_dict)
            
            # 计算相关性矩阵
            correlation_matrix = returns_df.corr(method='pearson')
            
            logger.info(f"Calculated correlation matrix for {len(returns_dict)} assets")
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {str(e)}")
            return pd.DataFrame()
            
    def find_low_correlation_pairs(self, correlation_matrix: pd.DataFrame,
                                  threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        查找低相关性的资产对
        
        Args:
            correlation_matrix: 相关性矩阵
            threshold: 相关性阈值
            
        Returns:
            [(asset1, asset2, correlation)] 列表
        """
        try:
            pairs = []
            
            # 获取矩阵的上三角部分（避免重复）
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    asset1 = correlation_matrix.columns[i]
                    asset2 = correlation_matrix.columns[j]
                    corr = correlation_matrix.iloc[i, j]
                    
                    # 如果相关性低于阈值，添加到列表
                    if abs(corr) < threshold:
                        pairs.append((asset1, asset2, corr))
                        
            # 按相关性排序（从低到高）
            pairs.sort(key=lambda x: abs(x[2]))
            
            logger.info(f"Found {len(pairs)} low correlation pairs (threshold: {threshold})")
            return pairs
            
        except Exception as e:
            logger.error(f"Error finding low correlation pairs: {str(e)}")
            return []
            
    def calculate_rolling_correlation(self, prices1: pd.Series, prices2: pd.Series,
                                     window: Optional[int] = None) -> pd.Series:
        """
        计算滚动相关性
        
        Args:
            prices1: 第一个资产的价格序列
            prices2: 第二个资产的价格序列
            window: 滚动窗口（默认使用实例的window）
            
        Returns:
            滚动相关性序列
        """
        try:
            if window is None:
                window = self.window
                
            # 计算收益率
            returns1 = prices1.pct_change()
            returns2 = prices2.pct_change()
            
            # 计算滚动相关性
            rolling_corr = returns1.rolling(window=window).corr(returns2)
            
            return rolling_corr
            
        except Exception as e:
            logger.error(f"Error calculating rolling correlation: {str(e)}")
            return pd.Series()
            
    def check_correlation_stability(self, prices1: pd.Series, prices2: pd.Series,
                                   lookback_periods: int = 3) -> Dict[str, float]:
        """
        检查相关性的稳定性
        
        Args:
            prices1: 第一个资产的价格序列
            prices2: 第二个资产的价格序列
            lookback_periods: 回看期数
            
        Returns:
            包含相关性稳定性指标的字典
        """
        try:
            correlations = []
            
            # 计算不同时期的相关性
            for i in range(lookback_periods):
                start_idx = -self.window * (i+1)
                end_idx = -self.window * i if i > 0 else None
                
                period_prices1 = prices1.iloc[start_idx:end_idx]
                period_prices2 = prices2.iloc[start_idx:end_idx]
                
                if len(period_prices1) < self.window // 2:
                    continue
                    
                # 计算该时期的相关性
                returns1 = period_prices1.pct_change().dropna()
                returns2 = period_prices2.pct_change().dropna()
                
                if len(returns1) > 0 and len(returns2) > 0:
                    corr, _ = pearsonr(returns1, returns2)
                    correlations.append(corr)
                    
            if not correlations:
                return {
                    'current_correlation': 0,
                    'mean_correlation': 0,
                    'std_correlation': 0,
                    'stability_score': 0
                }
                
            # 计算稳定性指标
            current_corr = correlations[0] if correlations else 0
            mean_corr = np.mean(correlations)
            std_corr = np.std(correlations)
            
            # 稳定性得分（标准差越小越稳定）
            stability_score = 1 / (1 + std_corr) if std_corr >= 0 else 0
            
            return {
                'current_correlation': current_corr,
                'mean_correlation': mean_corr,
                'std_correlation': std_corr,
                'stability_score': stability_score
            }
            
        except Exception as e:
            logger.error(f"Error checking correlation stability: {str(e)}")
            return {
                'current_correlation': 0,
                'mean_correlation': 0,
                'std_correlation': 0,
                'stability_score': 0
            }
            
    def suggest_diversification(self, current_holdings: List[str],
                               correlation_matrix: pd.DataFrame,
                               candidate_pool: List[str],
                               max_correlation: float = 0.7) -> List[Tuple[str, float]]:
        """
        建议分散化的资产
        
        Args:
            current_holdings: 当前持仓列表
            correlation_matrix: 相关性矩阵
            candidate_pool: 候选资产池
            max_correlation: 最大相关性阈值
            
        Returns:
            [(asset_code, avg_correlation_with_holdings)] 推荐列表
        """
        try:
            suggestions = []
            
            for candidate in candidate_pool:
                if candidate in current_holdings:
                    continue
                    
                if candidate not in correlation_matrix.columns:
                    continue
                    
                # 计算候选资产与当前持仓的平均相关性
                correlations_with_holdings = []
                for holding in current_holdings:
                    if holding in correlation_matrix.columns:
                        corr = correlation_matrix.loc[candidate, holding]
                        correlations_with_holdings.append(abs(corr))
                        
                if correlations_with_holdings:
                    avg_correlation = np.mean(correlations_with_holdings)
                    
                    # 如果平均相关性低于阈值，添加到建议列表
                    if avg_correlation < max_correlation:
                        suggestions.append((candidate, avg_correlation))
                        
            # 按相关性排序（从低到高）
            suggestions.sort(key=lambda x: x[1])
            
            logger.info(f"Suggested {len(suggestions)} assets for diversification")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting diversification: {str(e)}")
            return []
            
    def calculate_portfolio_correlation(self, weights: Dict[str, float],
                                      correlation_matrix: pd.DataFrame) -> float:
        """
        计算投资组合的整体相关性
        
        Args:
            weights: {asset_code: weight} 权重字典
            correlation_matrix: 相关性矩阵
            
        Returns:
            投资组合的平均相关性
        """
        try:
            assets = list(weights.keys())
            n = len(assets)
            
            if n < 2:
                return 0
                
            total_correlation = 0
            count = 0
            
            for i in range(n):
                for j in range(i+1, n):
                    asset1 = assets[i]
                    asset2 = assets[j]
                    
                    if asset1 in correlation_matrix.columns and asset2 in correlation_matrix.columns:
                        corr = correlation_matrix.loc[asset1, asset2]
                        weight1 = weights[asset1]
                        weight2 = weights[asset2]
                        
                        # 加权相关性
                        total_correlation += abs(corr) * weight1 * weight2
                        count += weight1 * weight2
                        
            if count > 0:
                avg_correlation = total_correlation / count
            else:
                avg_correlation = 0
                
            return avg_correlation
            
        except Exception as e:
            logger.error(f"Error calculating portfolio correlation: {str(e)}")
            return 0