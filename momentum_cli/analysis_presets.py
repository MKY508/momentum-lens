"""预设的分析配置，支持用户自定义覆盖与扩展。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .indicators import MomentumConfig


@dataclass(frozen=True)
class AnalysisPreset:
    key: str
    name: str
    description: str
    momentum_windows: Sequence[int]
    momentum_weights: Sequence[float] | None
    momentum_skip_windows: Sequence[int] | None
    corr_window: int
    chop_window: int
    trend_window: int
    rank_lookback: int
    notes: str | None = None

    def momentum_config(self) -> MomentumConfig:
        weights: Tuple[float, ...] | None = (
            tuple(float(weight) for weight in self.momentum_weights)
            if self.momentum_weights is not None
            else None
        )
        skip: Tuple[int, ...] | None = (
            tuple(int(value) for value in self.momentum_skip_windows)
            if self.momentum_skip_windows is not None
            else None
        )
        return MomentumConfig(
            windows=tuple(int(win) for win in self.momentum_windows),
            weights=weights,
            skip_windows=skip,
        )


_ANALYSIS_PRESET_STORE_PATH = Path(__file__).resolve().parent / "analysis_presets_store.json"


def _normalize_key(key: str) -> str:
    normalized = str(key).strip().lower()
    if not normalized:
        raise ValueError("preset key cannot be empty")
    return normalized


def _load_analysis_preset_store() -> Dict[str, dict]:
    if not _ANALYSIS_PRESET_STORE_PATH.exists():
        return {}
    try:
        raw = json.loads(_ANALYSIS_PRESET_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(raw, dict):
        if "analysis_presets" in raw and isinstance(raw["analysis_presets"], dict):
            return {str(k): dict(v) for k, v in raw["analysis_presets"].items()}
        return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}
    return {}


def _write_analysis_preset_store(store: Dict[str, dict]) -> None:
    _ANALYSIS_PRESET_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"analysis_presets": {key: dict(value) for key, value in store.items()}}
    _ANALYSIS_PRESET_STORE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _sanitize_windows(values: Iterable[int | float | str]) -> List[int]:
    windows: List[int] = []
    for value in values:
        try:
            window = int(value)
        except (TypeError, ValueError):
            raise ValueError("momentum_windows must be integers")
        if window <= 0:
            raise ValueError("momentum_windows must be positive")
        windows.append(window)
    if not windows:
        raise ValueError("momentum_windows cannot be empty")
    return windows


def _sanitize_weights(windows: Sequence[int], weights: Optional[Iterable[float | int | str]]) -> Optional[List[float]]:
    if weights is None:
        return None
    parsed: List[float] = []
    for value in weights:
        try:
            parsed.append(float(value))
        except (TypeError, ValueError):
            raise ValueError("momentum_weights must be numeric")
    if len(parsed) != len(windows):
        raise ValueError("momentum_weights length must match momentum_windows")
    return parsed


def _sanitize_skip_windows(windows: Sequence[int], values: Optional[Iterable[int | float | str]]) -> Optional[List[int]]:
    if values is None:
        return None
    parsed: List[int] = []
    for value in values:
        try:
            parsed.append(int(value))
        except (TypeError, ValueError):
            raise ValueError("momentum_skip_windows must be integers")
    if len(parsed) != len(windows):
        raise ValueError("momentum_skip_windows length must match momentum_windows")
    return parsed


def _deserialize_analysis_preset(key: str, payload: dict) -> AnalysisPreset:
    windows_raw = payload.get("momentum_windows")
    if not isinstance(windows_raw, list):  # type: ignore[arg-type]
        raise ValueError("momentum_windows must be a list")
    windows = _sanitize_windows(windows_raw)
    weights_raw = payload.get("momentum_weights")
    weights = _sanitize_weights(windows, weights_raw) if weights_raw is not None else None
    skip_windows = _sanitize_skip_windows(windows, payload.get("momentum_skip_windows"))
    try:
        corr_window = int(payload.get("corr_window"))
        chop_window = int(payload.get("chop_window"))
        trend_window = int(payload.get("trend_window"))
        rank_lookback = int(payload.get("rank_lookback"))
    except (TypeError, ValueError):
        raise ValueError("window fields must be integers")
    name = str(payload.get("name") or key)
    description = str(payload.get("description") or "")
    notes = payload.get("notes")
    notes_text = str(notes) if notes is not None else None
    return AnalysisPreset(
        key=key,
        name=name,
        description=description,
        momentum_windows=tuple(windows),
        momentum_weights=tuple(weights) if weights is not None else None,
        momentum_skip_windows=tuple(skip_windows) if skip_windows is not None else None,
        corr_window=corr_window,
        chop_window=chop_window,
        trend_window=trend_window,
        rank_lookback=rank_lookback,
        notes=notes_text,
    )


def _serialize_analysis_preset(preset: AnalysisPreset) -> dict:
    return {
        "name": preset.name,
        "description": preset.description,
        "momentum_windows": [int(win) for win in preset.momentum_windows],
        "momentum_weights": (
            [float(weight) for weight in preset.momentum_weights]
            if preset.momentum_weights is not None
            else None
        ),
        "momentum_skip_windows": (
            [int(value) for value in preset.momentum_skip_windows]
            if preset.momentum_skip_windows is not None
            else None
        ),
        "corr_window": int(preset.corr_window),
        "chop_window": int(preset.chop_window),
        "trend_window": int(preset.trend_window),
        "rank_lookback": int(preset.rank_lookback),
        "notes": preset.notes,
    }


DEFAULT_ANALYSIS_PRESETS: Dict[str, AnalysisPreset] = {
    "slow-core": AnalysisPreset(
        key="slow-core",
        name="慢腿·核心监控",
        description="3M-1M · 6M-1M 加权（60/40），兼顾反转与趋势",
        momentum_windows=(63, 126),
        momentum_weights=(0.6, 0.4),
        momentum_skip_windows=(21, 21),
        corr_window=60,
        chop_window=14,
        trend_window=90,
        rank_lookback=5,
        notes="默认分析配置，剔除近月噪音并突出核心慢腿。",
    ),
    "blend-dual": AnalysisPreset(
        key="blend-dual",
        name="双窗·原始动量",
        description="3M / 6M 原始动量，不剔除近月，加权等分",
        momentum_windows=(63, 126),
        momentum_weights=(0.5, 0.5),
        momentum_skip_windows=None,
        corr_window=60,
        chop_window=14,
        trend_window=75,
        rank_lookback=5,
        notes="用于对比未剔除近月的动量表现。",
    ),
    "twelve-minus-one": AnalysisPreset(
        key="twelve-minus-one",
        name="12M-1M 长波",
        description="12 个月动量剔除最近 1 个月，聚焦年度趋势",
        momentum_windows=(252,),
        momentum_weights=(1.0,),
        momentum_skip_windows=(21,),
        corr_window=120,
        chop_window=20,
        trend_window=180,
        rank_lookback=10,
        notes="适合长周期配置或年度体检。",
    ),
    "fast-rotation": AnalysisPreset(
        key="fast-rotation",
        name="快线·轮动观察",
        description="20 日 / 3M 动量组合（60/40），捕捉短期轮动",
        momentum_windows=(20, 63),
        momentum_weights=(0.6, 0.4),
        momentum_skip_windows=None,
        corr_window=40,
        chop_window=10,
        trend_window=45,
        rank_lookback=3,
        notes="用于高频复盘，提升对短线拐点的敏感度。",
    ),
}


ANALYSIS_PRESETS: Dict[str, AnalysisPreset] = {}


def refresh_analysis_presets() -> None:
    ANALYSIS_PRESETS.clear()
    ANALYSIS_PRESETS.update(DEFAULT_ANALYSIS_PRESETS)
    store = _load_analysis_preset_store()
    for key, payload in store.items():
        try:
            normalized_key = _normalize_key(key)
        except ValueError:
            continue
        try:
            preset = _deserialize_analysis_preset(normalized_key, payload)
        except ValueError:
            continue
        ANALYSIS_PRESETS[normalized_key] = preset


refresh_analysis_presets()


def get_custom_analysis_preset_keys() -> List[str]:
    return sorted(_load_analysis_preset_store().keys())


def has_custom_analysis_override(key: str) -> bool:
    return _normalize_key(key) in _load_analysis_preset_store()


def get_analysis_preset_payload(key: str) -> Optional[dict]:
    store = _load_analysis_preset_store()
    normalized_key = _normalize_key(key)
    payload = store.get(normalized_key)
    return dict(payload) if payload else None


def upsert_analysis_preset(
    *,
    key: str,
    name: str,
    description: str,
    momentum_windows: Iterable[int | float | str],
    momentum_weights: Optional[Iterable[int | float | str]],
    momentum_skip_windows: Optional[Iterable[int | float | str]] = None,
    corr_window: int,
    chop_window: int,
    trend_window: int,
    rank_lookback: int,
    notes: Optional[str] = None,
) -> AnalysisPreset:
    normalized_key = _normalize_key(key)
    windows = _sanitize_windows(momentum_windows)
    weights = _sanitize_weights(windows, momentum_weights)
    skips = _sanitize_skip_windows(windows, momentum_skip_windows)
    preset = AnalysisPreset(
        key=normalized_key,
        name=name.strip() or normalized_key,
        description=description.strip(),
        momentum_windows=tuple(windows),
        momentum_weights=tuple(weights) if weights is not None else None,
        momentum_skip_windows=tuple(skips) if skips is not None else None,
        corr_window=int(corr_window),
        chop_window=int(chop_window),
        trend_window=int(trend_window),
        rank_lookback=int(rank_lookback),
        notes=notes.strip() if notes else None,
    )
    store = _load_analysis_preset_store()
    store[normalized_key] = _serialize_analysis_preset(preset)
    _write_analysis_preset_store(store)
    refresh_analysis_presets()
    return ANALYSIS_PRESETS[normalized_key]


def delete_analysis_preset(key: str) -> bool:
    normalized_key = _normalize_key(key)
    store = _load_analysis_preset_store()
    if normalized_key not in store:
        return False
    del store[normalized_key]
    _write_analysis_preset_store(store)
    refresh_analysis_presets()
    return True


def reset_analysis_preset(key: str) -> bool:
    normalized_key = _normalize_key(key)
    removed = delete_analysis_preset(normalized_key)
    if removed:
        return True
    return normalized_key in DEFAULT_ANALYSIS_PRESETS
