from datetime import datetime, timedelta
from typing import List

from dataclasses import dataclass


@dataclass
class TradingSignal:
    code: str
    signal_type: str
    action: str


class RiskManager:
    """简化版风险管理器"""

    def get_stop_loss(self, profile: str) -> float:
        mapping = {
            'aggressive': -0.10,
            'balanced': -0.12,
            'conservative': -0.15,
        }
        return mapping.get(profile, -0.12)

    def check_correlation(self, rho: float) -> bool:
        return rho <= 0.8

    def check_min_holding_period(self, entry_date: datetime, min_days: int) -> bool:
        return datetime.now() - entry_date >= timedelta(days=min_days)

    def check_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """示例实现：直接返回原始信号"""
        return signals
