from dataclasses import dataclass
from typing import List, Tuple

from backend.core.decision_engine import TradingSignal, SignalType


@dataclass
class Order:
    code: str
    side: str
    weight: float
    iopv_band: Tuple[float, float]


class PortfolioManager:
    """简化版组合管理器"""

    def create_orders(self, signals: List[TradingSignal]) -> List[Order]:
        orders: List[Order] = []
        for sig in signals:
            if sig.signal_type == SignalType.HOLD:
                continue
            side = 'BUY' if sig.signal_type == SignalType.BUY else 'SELL'
            orders.append(
                Order(
                    code=sig.code,
                    side=side,
                    weight=sig.suggested_weight,
                    iopv_band=(0.999, 1.001),
                )
            )
        return orders
