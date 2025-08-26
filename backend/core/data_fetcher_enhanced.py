from typing import Any, List
import pandas as pd


class SimpleCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self._store.get(key)

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = value


class DummySource:
    def fetch(self, symbol: str, freq: str) -> pd.DataFrame:
        return pd.DataFrame()


class EnhancedDataFetcher:
    """带缓存与后备数据源的简单数据抓取器"""

    def __init__(self) -> None:
        self.primary_source = DummySource()
        self.backup_sources: List[DummySource] = [DummySource(), DummySource()]
        self.cache = SimpleCache()

    async def fetch_with_fallback(self, symbol: str, freq: str) -> pd.DataFrame:
        key = f"{symbol}:{freq}"
        cached = await self.cache.get(key)
        if cached is not None:
            return cached

        try:
            data = self.primary_source.fetch(symbol, freq)
        except Exception:
            data = None

        if data is None or data.empty:
            for source in self.backup_sources:
                try:
                    data = source.fetch(symbol, freq)
                    if data is not None and not data.empty:
                        break
                except Exception:
                    continue
        if data is None:
            raise RuntimeError("all data sources failed")

        await self.cache.set(key, data)
        return data
