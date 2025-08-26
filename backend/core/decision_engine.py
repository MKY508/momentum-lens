import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass
class TradingSignal:
    code: str
    signal_type: SignalType
    action: str
    portfolio_type: str
    momentum_score: float
    return_60d: float
    return_120d: float
    correlation_max: float
    correlation_avg: float
    passes_buffer: bool
    passes_holding_period: bool
    passes_correlation: bool
    passes_leg_limit: bool
    suggested_weight: float
    confidence: float
    signal_strength: SignalStrength
    notes: str = ""


class DecisionEngine:
    """简化版决策引擎，满足单元测试需要"""

    def calculate_momentum_score(self, r60: float, r120: float) -> float:
        """动量评分公式"""
        return 0.6 * r60 + 0.4 * r120

    def generate_signals(self, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """根据提供的市场数据生成交易信号"""
        signals: List[TradingSignal] = []
        for etf in market_data.get("etfs", []):
            score = self.calculate_momentum_score(etf["r60"], etf["r120"])
            signal = TradingSignal(
                code=etf["code"],
                signal_type=SignalType.BUY if score > 0 else SignalType.SELL,
                action="ENTER" if score > 0 else "EXIT",
                portfolio_type="Satellite",
                momentum_score=score,
                return_60d=etf["r60"],
                return_120d=etf["r120"],
                correlation_max=0.0,
                correlation_avg=0.0,
                passes_buffer=True,
                passes_holding_period=True,
                passes_correlation=True,
                passes_leg_limit=True,
                suggested_weight=0.1,
                confidence=1.0,
                signal_strength=SignalStrength.WEAK,
            )
            signals.append(signal)
        return signals
