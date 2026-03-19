"""解析相关工具函数

处理日期时间、版本号、数值等格式的解析。
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional


def try_parse_datetime(value: str) -> Optional[dt.datetime]:
    """尝试解析日期时间字符串

    支持多种常见的日期时间格式，包括 ISO 8601 和自定义格式。

    Args:
        value: 日期时间字符串

    Returns:
        解析成功返回 datetime 对象，失败返回 None

    Examples:
        >>> try_parse_datetime("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0)
        >>> try_parse_datetime("2024-01-15 14:30:00")
        datetime.datetime(2024, 1, 15, 14, 30)
        >>> try_parse_datetime("invalid")
        None
    """
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None

    # 处理 ISO 8601 格式的 Z 后缀
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    # 首先尝试 ISO 8601 格式
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        pass

    # 尝试常见格式
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for pattern in patterns:
        try:
            return dt.datetime.strptime(normalized, pattern)
        except ValueError:
            continue

    return None


def parse_bundle_version(value: str) -> Optional[tuple[int, int]]:
    """解析 Bundle 版本号字符串

    从字符串中提取 YYYYMM 格式的版本号，例如 "202401" 表示 2024年1月。

    Args:
        value: 包含版本号的字符串

    Returns:
        解析成功返回 (年份, 月份) 元组，失败返回 None

    Examples:
        >>> parse_bundle_version("bundle_202401.tar.gz")
        (2024, 1)
        >>> parse_bundle_version("v202412")
        (2024, 12)
        >>> parse_bundle_version("invalid")
        None
    """
    if not value:
        return None

    # 匹配 YYYYMM 格式（20开头的6位数字）
    match = re.search(r"(20\d{4})", value)
    if not match:
        return None

    digits = match.group(1)
    year = int(digits[:4])
    month = int(digits[4:])

    # 验证月份有效性
    if 1 <= month <= 12:
        return year, month

    return None


def extract_float(text: str) -> Optional[float]:
    """从文本中提取第一个浮点数

    Args:
        text: 包含数值的文本

    Returns:
        提取成功返回浮点数，失败返回 None

    Examples:
        >>> extract_float("价格: 123.45")
        123.45
        >>> extract_float("-0.5")
        -0.5
        >>> extract_float("no number here")
        None
    """
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None
