"""动量指标计算模块"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

# 尝试导入talib，如果失败则使用备用实现
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    logger = logging.getLogger(__name__)
    logger.warning("TA-Lib not installed, using pandas implementation")

logger = logging.getLogger(__name__)


class MarketState(Enum):
    """市场状态枚举"""
    BULL = "bull"           # 牛市
    BEAR = "bear"           # 熊市
    SIDEWAYS = "sideways"   # 震荡市
    UNCERTAIN = "uncertain" # 不确定


@dataclass
class MomentumScore:
    """动量评分数据类"""
    code: str
    name: str
    r3m: float      # 3月动量
    r6m: float      # 6月动量
    r63: float      # 63日动量
    r126: float     # 126日动量
    total_score: float
    rank: int
    ma200_state: str
    atr20: float
    chop: float
    volume_ratio: float
    timestamp: datetime


class MomentumCalculator:
    """动量指标计算器"""
    
    def __init__(self, lookback_days: int = 252):
        """
        初始化动量计算器
        
        Args:
            lookback_days: 回看天数，默认252个交易日（约1年）
        """
        self.lookback_days = lookback_days
        
    def calculate_ma200(self, prices: pd.Series) -> Tuple[pd.Series, str]:
        """
        计算200日移动平均线和状态
        
        Args:
            prices: 价格序列
            
        Returns:
            (MA200序列, 当前状态)
        """
        if len(prices) < 200:
            return pd.Series(), "insufficient_data"
        
        ma200 = prices.rolling(window=200).mean()
        current_price = prices.iloc[-1]
        current_ma200 = ma200.iloc[-1]
        
        if pd.isna(current_ma200):
            return ma200, "insufficient_data"
        
        # 判断年线状态
        ratio = current_price / current_ma200
        
        if ratio > 1.05:
            state = "above_strong"  # 强势站上年线
        elif ratio > 1.0:
            state = "above_weak"    # 弱势站上年线
        elif ratio > 0.95:
            state = "below_weak"    # 弱势跌破年线
        else:
            state = "below_strong"  # 强势跌破年线
        
        return ma200, state
    
    def calculate_atr20(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """
        计算20日ATR（平均真实波动率）
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            
        Returns:
            ATR20序列
        """
        if len(high) < 21:
            return pd.Series()
        
        if HAS_TALIB:
            atr = talib.ATR(high.values, low.values, close.values, timeperiod=20)
            return pd.Series(atr, index=high.index)
        else:
            # 使用pandas实现ATR
            prev_close = close.shift(1)
            true_range = pd.DataFrame({
                'hl': high - low,
                'hc': abs(high - prev_close),
                'lc': abs(low - prev_close)
            }).max(axis=1)
            
            # 计算20日ATR
            atr = true_range.rolling(window=20).mean()
            return atr
    
    def calculate_chop(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                      period: int = 14) -> pd.Series:
        """
        计算CHOP震荡指数
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 计算周期
            
        Returns:
            CHOP指数序列
        """
        if len(high) < period + 1:
            return pd.Series()
        
        # 计算ATR总和
        if HAS_TALIB:
            atr = talib.ATR(high.values, low.values, close.values, timeperiod=1)
            atr_sum = pd.Series(atr).rolling(window=period).sum()
        else:
            # 使用pandas实现ATR(1)
            prev_close = close.shift(1)
            true_range = pd.DataFrame({
                'hl': high - low,
                'hc': abs(high - prev_close),
                'lc': abs(low - prev_close)
            }).max(axis=1)
            atr_sum = true_range.rolling(window=period).sum()
        
        # 计算期间最高最低差
        highest = high.rolling(window=period).max()
        lowest = low.rolling(window=period).min()
        range_hl = highest - lowest
        
        # 计算CHOP
        chop = 100 * np.log10(atr_sum / range_hl) / np.log10(period)
        
        return chop
    
    def calculate_momentum_window(self, prices: pd.Series, window: int) -> float:
        """
        计算指定窗口的动量
        
        Args:
            prices: 价格序列
            window: 窗口大小（天数）
            
        Returns:
            动量值（收益率）
        """
        if len(prices) < window + 1:
            return np.nan
        
        current_price = prices.iloc[-1]
        past_price = prices.iloc[-window-1]
        
        if past_price == 0:
            return np.nan
        
        return (current_price - past_price) / past_price
    
    def calculate_dual_momentum(self, prices: pd.Series) -> Dict[str, float]:
        """
        计算双窗口动量
        
        Args:
            prices: 价格序列
            
        Returns:
            包含各窗口动量的字典
        """
        momentum = {
            'r21': self.calculate_momentum_window(prices, 21),    # 1月
            'r63': self.calculate_momentum_window(prices, 63),    # 3月
            'r126': self.calculate_momentum_window(prices, 126),  # 6月
            'r252': self.calculate_momentum_window(prices, 252),  # 12月
        }
        
        # 计算3月和6月的加权动量
        if not np.isnan(momentum['r63']) and not np.isnan(momentum['r126']):
            momentum['r3m'] = momentum['r63']
            momentum['r6m'] = momentum['r126']
            # 双窗口加权分数（3月60%，6月40%）
            momentum['dual_score'] = momentum['r3m'] * 0.6 + momentum['r6m'] * 0.4
        else:
            momentum['dual_score'] = np.nan
        
        return momentum
    
    def calculate_correlation_matrix(self, price_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        计算相关性矩阵
        
        Args:
            price_dict: {代码: 价格序列}字典
            
        Returns:
            相关性矩阵DataFrame
        """
        # 构建价格DataFrame
        price_df = pd.DataFrame(price_dict)
        
        # 计算日收益率
        returns = price_df.pct_change().dropna()
        
        # 计算相关性矩阵
        correlation_matrix = returns.corr()
        
        return correlation_matrix
    
    def calculate_volume_momentum(self, volume: pd.Series, window: int = 20) -> float:
        """
        计算成交量动量
        
        Args:
            volume: 成交量序列
            window: 窗口大小
            
        Returns:
            成交量比率
        """
        if len(volume) < window + 1:
            return np.nan
        
        recent_avg = volume.iloc[-window:].mean()
        historical_avg = volume.iloc[-window*3:-window].mean()
        
        if historical_avg == 0:
            return np.nan
        
        return recent_avg / historical_avg
    
    def score_etf_momentum(self, code: str, name: str, data: pd.DataFrame,
                           r3m_weight: float = 0.6, r6m_weight: float = 0.4) -> MomentumScore:
        """
        计算ETF的动量评分
        
        Args:
            code: ETF代码
            name: ETF名称
            data: 包含OHLCV的DataFrame
            r3m_weight: 3月动量权重
            r6m_weight: 6月动量权重
            
        Returns:
            动量评分对象
        """
        try:
            # 确保数据有足够的历史
            if len(data) < 200:
                logger.warning(f"ETF {code} 历史数据不足200天")
                return None
            
            # 计算MA200
            ma200, ma200_state = self.calculate_ma200(data['close'])
            
            # 计算ATR20
            atr20 = self.calculate_atr20(data['high'], data['low'], data['close'])
            current_atr = atr20.iloc[-1] if not atr20.empty else np.nan
            
            # 计算CHOP
            chop = self.calculate_chop(data['high'], data['low'], data['close'])
            current_chop = chop.iloc[-1] if not chop.empty else np.nan
            
            # 计算动量
            momentum = self.calculate_dual_momentum(data['close'])
            
            # 计算成交量动量
            vol_momentum = self.calculate_volume_momentum(data['volume'])
            
            # 计算总分
            if not np.isnan(momentum['dual_score']):
                total_score = momentum['dual_score']
            else:
                total_score = 0
            
            # 创建评分对象
            score = MomentumScore(
                code=code,
                name=name,
                r3m=momentum.get('r3m', np.nan),
                r6m=momentum.get('r6m', np.nan),
                r63=momentum.get('r63', np.nan),
                r126=momentum.get('r126', np.nan),
                total_score=total_score,
                rank=0,  # 排名稍后计算
                ma200_state=ma200_state,
                atr20=current_atr,
                chop=current_chop,
                volume_ratio=vol_momentum,
                timestamp=datetime.now()
            )
            
            return score
            
        except Exception as e:
            logger.error(f"计算ETF {code} 动量评分失败: {e}")
            return None
    
    def rank_momentum_scores(self, scores: List[MomentumScore]) -> List[MomentumScore]:
        """
        对动量评分进行排名
        
        Args:
            scores: 动量评分列表
            
        Returns:
            排名后的评分列表
        """
        # 过滤掉None值
        valid_scores = [s for s in scores if s is not None]
        
        # 按总分降序排序
        valid_scores.sort(key=lambda x: x.total_score, reverse=True)
        
        # 设置排名
        for i, score in enumerate(valid_scores):
            score.rank = i + 1
        
        return valid_scores
    
    def identify_market_state(self, index_data: pd.DataFrame) -> MarketState:
        """
        识别市场状态
        
        Args:
            index_data: 指数数据（如沪深300）
            
        Returns:
            市场状态枚举
        """
        if len(index_data) < 200:
            return MarketState.UNCERTAIN
        
        # 计算MA200
        ma200, ma200_state = self.calculate_ma200(index_data['close'])
        
        # 计算ATR和CHOP
        atr20 = self.calculate_atr20(index_data['high'], index_data['low'], index_data['close'])
        chop = self.calculate_chop(index_data['high'], index_data['low'], index_data['close'])
        
        current_atr = atr20.iloc[-1] if not atr20.empty else np.nan
        current_chop = chop.iloc[-1] if not chop.empty else np.nan
        
        # 判断市场状态
        if ma200_state in ["above_strong", "above_weak"]:
            if current_chop < 50:
                return MarketState.BULL  # 趋势向上
            else:
                return MarketState.SIDEWAYS  # 震荡向上
        elif ma200_state in ["below_strong", "below_weak"]:
            if current_chop < 50:
                return MarketState.BEAR  # 趋势向下
            else:
                return MarketState.SIDEWAYS  # 震荡向下
        else:
            return MarketState.UNCERTAIN


class MomentumFilter:
    """动量过滤器"""
    
    @staticmethod
    def filter_by_turnover(scores: List[MomentumScore], etf_data: pd.DataFrame, 
                           min_turnover: float) -> List[MomentumScore]:
        """
        按成交额过滤
        
        Args:
            scores: 动量评分列表
            etf_data: ETF数据
            min_turnover: 最小成交额
            
        Returns:
            过滤后的评分列表
        """
        filtered = []
        for score in scores:
            etf_row = etf_data[etf_data['code'] == score.code]
            if not etf_row.empty:
                turnover = etf_row.iloc[0].get('turnover', 0)
                if turnover >= min_turnover:
                    filtered.append(score)
        
        return filtered
    
    @staticmethod
    def filter_by_correlation(scores: List[MomentumScore], correlation_matrix: pd.DataFrame,
                             max_correlation: float = 0.8) -> List[MomentumScore]:
        """
        按相关性过滤，避免过度集中
        
        Args:
            scores: 动量评分列表
            correlation_matrix: 相关性矩阵
            max_correlation: 最大相关性阈值
            
        Returns:
            过滤后的评分列表
        """
        if correlation_matrix.empty:
            return scores
        
        selected = []
        selected_codes = []
        
        for score in scores:
            if score.code not in correlation_matrix.columns:
                continue
                
            # 检查与已选标的的相关性
            can_add = True
            for selected_code in selected_codes:
                if selected_code in correlation_matrix.columns:
                    corr = correlation_matrix.loc[score.code, selected_code]
                    if abs(corr) > max_correlation:
                        can_add = False
                        break
            
            if can_add:
                selected.append(score)
                selected_codes.append(score.code)
        
        return selected
    
    @staticmethod
    def filter_by_volatility(scores: List[MomentumScore], max_atr: float = 0.03) -> List[MomentumScore]:
        """
        按波动率过滤
        
        Args:
            scores: 动量评分列表
            max_atr: 最大ATR阈值
            
        Returns:
            过滤后的评分列表
        """
        return [s for s in scores if not np.isnan(s.atr20) and s.atr20 <= max_atr]