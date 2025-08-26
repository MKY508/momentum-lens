"""
Signal generator for trading decisions
交易信号生成器
"""
from typing import Dict, List
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalGenerator:
    """信号生成器"""
    
    def generate_signal(self, market_state: str, momentum_score: float) -> SignalType:
        """生成交易信号"""
        if market_state == "OFFENSE" and momentum_score > 0.1:
            return SignalType.BUY
        elif market_state == "DEFENSE" or momentum_score < -0.05:
            return SignalType.SELL
        else:
            return SignalType.HOLD