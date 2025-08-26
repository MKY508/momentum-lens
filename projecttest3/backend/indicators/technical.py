"""
Technical indicators calculation
技术指标计算
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from loguru import logger


class TechnicalIndicators:
    """
    技术指标计算类
    包含MA、ATR、CHOP等指标的计算
    """
    
    @staticmethod
    def calculate_ma(prices: pd.Series, window: int) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            prices: 价格序列
            window: 窗口期
            
        Returns:
            移动平均线序列
        """
        return prices.rolling(window=window, min_periods=1).mean()
        
    @staticmethod
    def calculate_atr(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        计算ATR (Average True Range)
        
        Args:
            df: DataFrame with high, low, close columns
            window: 计算窗口期，默认20
            
        Returns:
            ATR序列
        """
        try:
            # 计算True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            # True Range是三者的最大值
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # ATR是True Range的移动平均
            atr = true_range.rolling(window=window, min_periods=1).mean()
            
            return atr
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            return pd.Series()
            
    @staticmethod
    def calculate_chop(df: pd.DataFrame, window: int = 14) -> pd.Series:
        """
        计算CHOP震荡指标
        公式: CHOP = 100 * log10(sum(TR,N) / (High(N)-Low(N))) / log10(N)
        
        Args:
            df: DataFrame with high, low, close columns
            window: 计算窗口期，默认14
            
        Returns:
            CHOP指标序列
        """
        try:
            # 计算True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # 计算窗口内的True Range总和
            tr_sum = true_range.rolling(window=window, min_periods=window).sum()
            
            # 计算窗口内的最高价和最低价
            high_n = df['high'].rolling(window=window, min_periods=window).max()
            low_n = df['low'].rolling(window=window, min_periods=window).min()
            
            # 计算CHOP
            # 避免除零错误
            range_n = high_n - low_n
            range_n = range_n.replace(0, np.nan)
            
            chop = 100 * np.log10(tr_sum / range_n) / np.log10(window)
            
            # 限制CHOP在0-100之间
            chop = chop.clip(0, 100)
            
            return chop
            
        except Exception as e:
            logger.error(f"Error calculating CHOP: {str(e)}")
            return pd.Series()
            
    @staticmethod
    def calculate_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
        """
        计算滚动波动率
        
        Args:
            returns: 收益率序列
            window: 计算窗口期
            
        Returns:
            波动率序列
        """
        return returns.rolling(window=window, min_periods=1).std() * np.sqrt(252)
        
    @staticmethod
    def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            prices: 价格序列
            window: 计算窗口期，默认14
            
        Returns:
            RSI序列
        """
        try:
            # 计算价格变化
            delta = prices.diff()
            
            # 分离上涨和下跌
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            
            # 避免除零
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return pd.Series()
            
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, window: int = 20, 
                                 num_std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带
        
        Args:
            prices: 价格序列
            window: 计算窗口期
            num_std: 标准差倍数
            
        Returns:
            (上轨, 中轨, 下轨)
        """
        try:
            # 中轨为移动平均线
            middle = prices.rolling(window=window, min_periods=1).mean()
            
            # 计算标准差
            std = prices.rolling(window=window, min_periods=1).std()
            
            # 上下轨
            upper = middle + (std * num_std)
            lower = middle - (std * num_std)
            
            return upper, middle, lower
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            return pd.Series(), pd.Series(), pd.Series()
            
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        
        Args:
            prices: 价格序列
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            (MACD线, 信号线, 柱状图)
        """
        try:
            # 计算EMA
            ema_fast = prices.ewm(span=fast, adjust=False).mean()
            ema_slow = prices.ewm(span=slow, adjust=False).mean()
            
            # MACD线
            macd_line = ema_fast - ema_slow
            
            # 信号线
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            
            # 柱状图
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return pd.Series(), pd.Series(), pd.Series()
            
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率（年化）
            
        Returns:
            夏普比率
        """
        try:
            # 年化收益率
            annual_return = returns.mean() * 252
            
            # 年化波动率
            annual_volatility = returns.std() * np.sqrt(252)
            
            # 夏普比率
            if annual_volatility == 0:
                return 0
                
            sharpe = (annual_return - risk_free_rate) / annual_volatility
            
            return sharpe
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0
            
    @staticmethod
    def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        计算最大回撤
        
        Args:
            prices: 价格序列
            
        Returns:
            (最大回撤率, 开始日期, 结束日期)
        """
        try:
            # 计算累计最高值
            cummax = prices.expanding().max()
            
            # 计算回撤
            drawdown = (prices - cummax) / cummax
            
            # 找到最大回撤
            max_dd = drawdown.min()
            
            # 找到最大回撤的开始和结束日期
            if max_dd < 0:
                end_date = drawdown.idxmin()
                # 找到结束日期之前的最高点
                start_date = prices[:end_date].idxmax()
            else:
                start_date = prices.index[0]
                end_date = prices.index[0]
                
            return max_dd, start_date, end_date
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return 0, pd.Timestamp.now(), pd.Timestamp.now()