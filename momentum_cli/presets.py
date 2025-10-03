"""预设的 ETF 券池分组，便于在命令行快速调取，并支持用户自定义覆盖。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    description: str
    tickers: List[str]


_PRESET_STORE_PATH = Path(__file__).resolve().parent / "presets_store.json"


def _normalize_codes(codes: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for code in codes:
        if not code:
            continue
        normalized = str(code).strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_key(key: str) -> str:
    normalized = str(key).strip().lower()
    if not normalized:
        raise ValueError("preset key cannot be empty")
    return normalized


def _serialize_preset(preset: Preset) -> dict:
    return {
        "name": preset.name,
        "description": preset.description,
        "tickers": list(preset.tickers),
    }


def _deserialize_preset(key: str, payload: dict) -> Preset:
    tickers_raw = payload.get("tickers")
    if not isinstance(tickers_raw, list):  # type: ignore[arg-type]
        raise ValueError("tickers must be a list of strings")
    tickers = _normalize_codes(tickers_raw)
    if not tickers:
        raise ValueError("tickers list cannot be empty")
    name = str(payload.get("name") or key)
    description = str(payload.get("description") or "")
    return Preset(key=key, name=name, description=description, tickers=tickers)


def _load_preset_store() -> Dict[str, dict]:
    if not _PRESET_STORE_PATH.exists():
        return {}
    try:
        raw = json.loads(_PRESET_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(raw, dict):
        if "presets" in raw and isinstance(raw["presets"], dict):
            return {str(k): dict(v) for k, v in raw["presets"].items()}
        # 兼容旧格式：直接是一个 dict
        return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}
    return {}


def _write_preset_store(store: Dict[str, dict]) -> None:
    _PRESET_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"presets": {key: dict(value) for key, value in store.items()}}
    _PRESET_STORE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


DEFAULT_PRESETS: Dict[str, Preset] = {
    "core": Preset(
        key="core",
        name="核心仓",
        description="以稳健宽基与防御型资产为主",
        tickers=[
            "510300.XSHG",  # 沪深300ETF
            "510880.XSHG",  # 红利ETF
            "511360.XSHG",  # 短融ETF
            "511020.XSHG",  # 国债ETF5-10年
            "518880.XSHG",  # 黄金ETF
            "513500.XSHG",  # 标普500ETF
        ],
    ),
    "satellite": Preset(
        key="satellite",
        name="卫星仓",
        description="进攻型或主题型 ETF",
        tickers=[
            "159915.XSHE",  # 创业板ETF
            "159949.XSHE",  # 创业板50ETF
            "512400.XSHG",  # 有色金属ETF
            "516010.XSHG",  # 游戏动漫ETF
            "159842.XSHE",  # 券商ETF
            "512800.XSHG",  # 银行ETF
            "515030.XSHG",  # 新能源车ETF
            "516160.XSHG",  # 新能源ETF
            "515790.XSHG",  # 光伏ETF
            "512720.XSHG",  # 计算机ETF
            "512760.XSHG",  # 芯片ETF
            "588000.XSHG",  # 科创50ETF
            "159796.XSHE",  # 电池50ETF
            "515050.XSHG",  # 5G通信ETF
            "516510.XSHG",  # 中证云计算ETF
            "159611.XSHE",  # 电力ETF
            "516780.XSHG",  # 稀土ETF
            "513180.XSHG",  # 恒生科技指数ETF
            "159792.XSHE",  # 港股通互联网ETF
            "512690.XSHG",  # 酒ETF
            "159840.XSHE",  # 锂电池ETF（工银瑞信）
        ],
    ),
}


PRESETS: Dict[str, Preset] = {}


def refresh_presets() -> None:
    PRESETS.clear()
    PRESETS.update(DEFAULT_PRESETS)
    store = _load_preset_store()
    for key, payload in store.items():
        try:
            normalized_key = _normalize_key(key)
        except ValueError:
            continue
        try:
            preset = _deserialize_preset(normalized_key, payload)
        except ValueError:
            continue
        PRESETS[normalized_key] = preset


refresh_presets()


def get_custom_preset_keys() -> List[str]:
    return sorted(_load_preset_store().keys())


def has_custom_override(key: str) -> bool:
    return _normalize_key(key) in _load_preset_store()


def get_preset_payload(key: str) -> Optional[dict]:
    store = _load_preset_store()
    normalized_key = _normalize_key(key)
    payload = store.get(normalized_key)
    return dict(payload) if payload else None


def upsert_preset(
    *,
    key: str,
    name: str,
    description: str,
    tickers: Iterable[str],
) -> Preset:
    normalized_key = _normalize_key(key)
    normalized_codes = _normalize_codes(tickers)
    if not normalized_codes:
        raise ValueError("至少需要保留 1 只 ETF")
    preset = Preset(
        key=normalized_key,
        name=name.strip() or normalized_key,
        description=description.strip(),
        tickers=normalized_codes,
    )
    store = _load_preset_store()
    store[normalized_key] = _serialize_preset(preset)
    _write_preset_store(store)
    refresh_presets()
    return PRESETS[normalized_key]


def delete_preset(key: str) -> bool:
    normalized_key = _normalize_key(key)
    store = _load_preset_store()
    if normalized_key not in store:
        return False
    del store[normalized_key]
    _write_preset_store(store)
    refresh_presets()
    return True


def reset_preset(key: str) -> bool:
    """删除自定义覆盖，恢复到内置定义。"""
    normalized_key = _normalize_key(key)
    removed = delete_preset(normalized_key)
    if removed:
        return True
    return normalized_key in DEFAULT_PRESETS
