"""RQAlpha 数据包管理

处理数据包状态检查、元数据加载等功能。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Optional

from ..utils.parsers import parse_bundle_version, try_parse_datetime

# Bundle 相关路径
BUNDLE_ROOT = Path.home() / ".rqalpha" / "bundle"
BUNDLE_VERSION_FILE = BUNDLE_ROOT / "bundle_version.json"


def load_bundle_metadata() -> Optional[dict[str, Any]]:
    """加载 Bundle 元数据

    从 bundle_version.json 读取元数据信息。

    Returns:
        元数据字典，失败返回 None

    Examples:
        >>> metadata = load_bundle_metadata()  # doctest: +SKIP
        >>> metadata.get("bundle_version") if metadata else None  # doctest: +SKIP
        '202401'
    """
    if not BUNDLE_VERSION_FILE.exists():
        return None
    try:
        return json.loads(BUNDLE_VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def bundle_status(force_refresh: bool = False, cache: dict | None = None) -> dict[str, Any]:
    """获取 Bundle 状态信息

    检查数据包的版本、更新时间和新鲜度。

    Args:
        force_refresh: 是否强制刷新（忽略缓存）
        cache: 缓存字典的引用（用于读取和更新）

    Returns:
        包含以下字段的状态字典:
        - state: "fresh"/"stale"/"missing"/"unknown"
        - metadata: 元数据字典或 None
        - has_files: 是否存在 .h5 文件
        - version_raw: 原始版本字符串
        - version: 格式化版本（YYYYMM）
        - year/month: 解析后的年月
        - months_behind: 落后月数
        - updated_at: 更新时间
        - days_since_update: 距离更新天数

    Examples:
        >>> status = bundle_status()  # doctest: +SKIP
        >>> status["state"] in ["fresh", "stale", "missing", "unknown"]  # doctest: +SKIP
        True
    """
    if not force_refresh and cache is not None and len(cache) > 0:
        return cache

    metadata = load_bundle_metadata()
    today = dt.date.today()
    has_files = False

    if BUNDLE_ROOT.exists():
        for candidate in BUNDLE_ROOT.glob("*.h5"):
            has_files = True
            break

    status: dict[str, Any] = {
        "state": "missing",
        "metadata": metadata,
        "has_files": has_files,
    }

    if not metadata:
        if has_files:
            status["state"] = "fresh"
            status["version_raw"] = None
            status["version"] = None
        if cache is not None:
            cache.update(status)
        return status

    # 解析版本信息
    version_raw = (
        metadata.get("bundle_version")
        or metadata.get("version")
        or metadata.get("bundle")
        or ""
    )
    parsed_version = parse_bundle_version(str(version_raw))
    updated_raw = (
        metadata.get("updated_at")
        or metadata.get("created_at")
        or metadata.get("generated_at")
    )
    updated_dt = try_parse_datetime(str(updated_raw)) if updated_raw else None

    status.update(
        {
            "state": "unknown",
            "version_raw": version_raw,
            "version": None,
            "updated_at": updated_dt,
        }
    )

    if parsed_version:
        year, month = parsed_version
        status["version"] = f"{year}{month:02d}"
        status["year"] = year
        status["month"] = month

        months_delta = (today.year - year) * 12 + (today.month - month)
        status["months_behind"] = months_delta
        status["state"] = "fresh" if months_delta <= 0 else "stale"

    if updated_dt:
        now = dt.datetime.now(updated_dt.tzinfo) if updated_dt.tzinfo else dt.datetime.now()
        delta_days = (now - updated_dt).days
        status["days_since_update"] = delta_days

        if status["state"] == "unknown" and delta_days <= 7:
            status["state"] = "fresh"

    if cache is not None:
        cache.update(status)
    return status
