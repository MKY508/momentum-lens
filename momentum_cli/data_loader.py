import contextlib
import datetime as dt
from pathlib import Path
from typing import Dict, Iterable, Optional

import h5py
import numpy as np
import pandas as pd


_BUNDLE_FILE_CANDIDATES = {
    "funds": "funds.h5",
    "stocks": "stocks.h5",
    "indexes": "indexes.h5",
}


class BundleDataLoader:
    """Load daily bar data from the local RQAlpha bundle."""

    def __init__(self, bundle_path: Optional[Path] = None) -> None:
        self.bundle_path = Path(bundle_path or Path.home() / ".rqalpha" / "bundle").expanduser()
        self._files: Dict[str, h5py.File] = {}

    def _ensure_file(self, category: str) -> Optional[h5py.File]:
        if category in self._files:
            return self._files[category]
        file_name = _BUNDLE_FILE_CANDIDATES.get(category)
        if not file_name:
            return None
        file_path = self.bundle_path / file_name
        if not file_path.exists():
            return None
        self._files[category] = h5py.File(file_path, "r")
        return self._files[category]

    def _discover_dataset(self, order_book_id: str) -> Optional[h5py.Dataset]:
        for category in _BUNDLE_FILE_CANDIDATES:
            file_obj = self._ensure_file(category)
            if not file_obj:
                continue
            if order_book_id in file_obj:
                return file_obj[order_book_id]
        return None

    def available_categories(self) -> Iterable[str]:
        return list(_BUNDLE_FILE_CANDIDATES)

    @staticmethod
    def _to_timestamp(raw: np.ndarray) -> pd.DatetimeIndex:
        # Datetime stored as int64 like 20120528000000
        return pd.to_datetime(raw.astype(str), format="%Y%m%d%H%M%S")

    def load_bars(
        self,
        order_book_id: str,
        start_date: Optional[str | dt.date | dt.datetime] = None,
        end_date: Optional[str | dt.date | dt.datetime] = None,
    ) -> pd.DataFrame:
        dataset = self._discover_dataset(order_book_id)
        if dataset is None:
            raise ValueError(f"Instrument {order_book_id} not found in bundle at {self.bundle_path}")
        raw = dataset[:]
        frame = pd.DataFrame(raw)
        frame["datetime"] = self._to_timestamp(frame.pop("datetime").values)
        frame = frame.set_index("datetime").sort_index()
        if start_date:
            start_ts = pd.to_datetime(start_date)
            frame = frame.loc[frame.index >= start_ts]
        if end_date:
            end_ts = pd.to_datetime(end_date)
            frame = frame.loc[frame.index <= end_ts]
        return frame

    def close(self) -> None:
        for file_obj in self._files.values():
            with contextlib.suppress(Exception):
                file_obj.close()
        self._files.clear()

    def __enter__(self) -> "BundleDataLoader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
