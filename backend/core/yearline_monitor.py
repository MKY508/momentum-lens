from datetime import datetime


class YearlineMonitor:
    """简单年线解锁监控"""

    def __init__(self) -> None:
        self.above_yearline_count = 0
        self.unlock_status = False
        self.unlock_date: datetime | None = None

    def check_yearline_unlock(self, price: float, ma200: float) -> bool:
        if price > ma200:
            self.above_yearline_count += 1
        else:
            self.above_yearline_count = 0
            return False

        if self.above_yearline_count >= 5 and price >= ma200 * 1.01:
            self.unlock_status = True
            self.unlock_date = datetime.now()
            return True
        return False

    def check_yearline_fallback(self, price: float, ma200: float) -> bool:
        if not self.unlock_status or not self.unlock_date:
            return False
        if (datetime.now() - self.unlock_date).days <= 3 and price <= ma200 * 0.99:
            self.unlock_status = False
            self.above_yearline_count = 0
            return True
        return False
