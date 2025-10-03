"""Indicator calculations for momentum and trend analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MomentumConfig:
    windows: Sequence[int] = (60, 120)
    weights: Sequence[float] | None = (0.6, 0.4)
    skip_windows: Sequence[int] | None = None


def normalize_weights(values: Sequence[float], size: int) -> np.ndarray:
    if not values:
        return np.ones(size) / size
    arr = np.array(list(values), dtype=float)
    if arr.size != size:
        raise ValueError("Momentum weights must match number of windows")
    total = arr.sum()
    if not np.isfinite(total) or total == 0:
        return np.ones(size) / size
    return arr / total


def compute_returns(series: pd.Series, window: int) -> pd.Series:
    return series / series.shift(window) - 1.0


def momentum_score(series: pd.Series, config: MomentumConfig) -> pd.Series:
    windows = list(config.windows)
    weights = normalize_weights(config.weights or [], len(windows))
    if config.skip_windows is not None:
        if len(config.skip_windows) != len(windows):
            raise ValueError("skip_windows length must match momentum windows")
        skip_values = [int(value) if value is not None else 0 for value in config.skip_windows]
    else:
        skip_values = [0] * len(windows)

    stacked = []
    column_names = []
    for win, skip, weight in zip(windows, skip_values, weights):
        skip = max(0, int(skip))
        component: pd.Series
        if skip > 0 and skip < win:
            recent = series.shift(skip)
            past = series.shift(win)
            component = recent / past - 1.0
            column_names.append(f"mom_{win}_minus_{skip}")
        else:
            component = compute_returns(series, win)
            column_names.append(f"mom_{win}")
        stacked.append(component * weight)
    total = pd.concat(stacked, axis=1)
    total.columns = column_names
    return total.sum(axis=1), total


def true_range(frame: pd.DataFrame) -> pd.Series:
    prev_close = frame["close"].shift(1)
    ranges = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def average_true_range(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    return true_range(frame).rolling(window=window, min_periods=1).mean()


def directional_movement(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    up_move = frame["high"].diff()
    down_move = frame["low"].diff().mul(-1)
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    return pd.Series(plus_dm, index=frame.index), pd.Series(minus_dm, index=frame.index)


def average_directional_index(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    tr = true_range(frame)
    atr = tr.rolling(window=window, min_periods=window).sum()
    plus_dm, minus_dm = directional_movement(frame)
    plus_di = 100 * plus_dm.rolling(window=window, min_periods=window).sum() / atr
    minus_di = 100 * minus_dm.rolling(window=window, min_periods=window).sum() / atr
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = dx.rolling(window=window, min_periods=window).mean()
    return adx


def choppiness_index(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    tr_sum = true_range(frame).rolling(window).sum()
    high_max = frame["high"].rolling(window).max()
    low_min = frame["low"].rolling(window).min()
    denom = (high_max - low_min).replace(0, np.nan)
    chop = 100 * np.log10((tr_sum / denom).replace(0, np.nan)) / np.log10(window)
    return chop


def moving_average(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def exponential_moving_average(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def linear_trend(series: pd.Series, window: int = 90) -> pd.Series:
    log_price = np.log(series.replace(0, np.nan))

    def _slope(values: np.ndarray) -> float:
        if np.any(~np.isfinite(values)):
            return np.nan
        x = np.arange(values.size)
        slope, _ = np.polyfit(x, values, 1)
        return slope

    return log_price.rolling(window).apply(_slope, raw=True)


def rolling_rank(frame: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    return frame.rank(axis=1, method="min", ascending=ascending)
