"""
技术指标计算层
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(data: pd.Series, period: int) -> pd.Series:
        """计算移动平均线"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """计算ATR（平均真实波幅）"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_chop(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算CHOP震荡指标"""
        # ATR总和
        atr = IndicatorCalculator.calculate_atr(high, low, close, 1)
        atr_sum = atr.rolling(window=period).sum()
        
        # 高低点范围
        highest = high.rolling(window=period).max()
        lowest = low.rolling(window=period).min()
        range_hl = highest - lowest
        
        # CHOP = 100 * LOG10(ATR总和 / (最高-最低)) / LOG10(周期)
        chop = 100 * np.log10(atr_sum / range_hl) / np.log10(period)
        
        return chop
    
    @staticmethod
    def calculate_momentum(close: pd.Series, periods: list = [60, 120]) -> Dict[str, float]:
        """计算动量（收益率）"""
        momentum = {}
        
        for period in periods:
            if len(close) >= period:
                ret = (close.iloc[-1] / close.iloc[-period] - 1) * 100
                momentum[f'r{period}'] = ret
            else:
                momentum[f'r{period}'] = 0
                
        return momentum
    
    @staticmethod
    def calculate_momentum_score(r60: float, r120: float, r60_weight: float = 0.6) -> float:
        """计算动量综合得分"""
        return r60 * r60_weight + r120 * (1 - r60_weight)
    
    @staticmethod
    def check_ma_state(close: pd.Series, ma_period: int = 200) -> str:
        """检查均线状态"""
        if len(close) < ma_period:
            return "UNKNOWN"
            
        ma = close.rolling(window=ma_period).mean()
        current = close.iloc[-1]
        ma_value = ma.iloc[-1]
        
        if pd.isna(ma_value):
            return "UNKNOWN"
            
        ratio = current / ma_value
        
        if ratio > 1.02:
            return "ABOVE"  # 站上均线
        elif ratio < 0.98:
            return "BELOW"  # 跌破均线
        else:
            return "NEAR"   # 均线附近
    
    @staticmethod
    def calculate_volatility(returns: pd.Series, period: int = 20) -> float:
        """计算波动率"""
        return returns.rolling(window=period).std() * np.sqrt(252)
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """计算夏普比率"""
        excess_returns = returns - risk_free_rate / 252
        if returns.std() == 0:
            return 0
        return np.sqrt(252) * excess_returns.mean() / returns.std()
    
    @staticmethod
    def calculate_max_drawdown(close: pd.Series) -> float:
        """计算最大回撤"""
        cummax = close.expanding().max()
        drawdown = (close - cummax) / cummax
        return drawdown.min()
    
    @staticmethod
    def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        ma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)
        
        return upper, ma, lower
    
    @staticmethod
    def analyze_etf(data: pd.DataFrame) -> Dict:
        """综合分析ETF"""
        if data.empty or len(data) < 200:
            return {}
            
        result = {
            'ma200': data['close'].rolling(window=200).mean().iloc[-1],
            'ma200_state': IndicatorCalculator.check_ma_state(data['close']),
            'atr20': IndicatorCalculator.calculate_atr(
                data['high'], data['low'], data['close'], 20
            ).iloc[-1],
            'chop': IndicatorCalculator.calculate_chop(
                data['high'], data['low'], data['close']
            ).iloc[-1] if len(data) >= 14 else 50,
            'momentum': IndicatorCalculator.calculate_momentum(data['close']),
            'volatility': IndicatorCalculator.calculate_volatility(
                data['close'].pct_change().dropna()
            ),
            'max_drawdown': IndicatorCalculator.calculate_max_drawdown(data['close']),
            'rsi': IndicatorCalculator.calculate_rsi(data['close']).iloc[-1]
        }
        
        # 计算动量得分
        if 'r60' in result['momentum'] and 'r120' in result['momentum']:
            result['momentum_score'] = IndicatorCalculator.calculate_momentum_score(
                result['momentum']['r60'],
                result['momentum']['r120']
            )
        
        return result

if __name__ == "__main__":
    # 测试代码
    import yfinance as yf
    
    # 获取测试数据
    ticker = yf.Ticker("SPY")
    data = ticker.history(period="1y")
    
    if not data.empty:
        # 统一列名
        data.columns = [c.lower() for c in data.columns]
        
        # 计算指标
        calc = IndicatorCalculator()
        
        # MA200
        ma200 = calc.calculate_ma(data['close'], 200)
        print(f"MA200 最新值: {ma200.iloc[-1]:.2f}")
        
        # ATR
        atr = calc.calculate_atr(data['high'], data['low'], data['close'])
        print(f"ATR20 最新值: {atr.iloc[-1]:.2f}")
        
        # 动量
        momentum = calc.calculate_momentum(data['close'])
        print(f"动量: {momentum}")
        
        # 综合分析
        analysis = calc.analyze_etf(data)
        print(f"\n综合分析:")
        for key, value in analysis.items():
            print(f"  {key}: {value}")