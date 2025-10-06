"""配置验证工具

提供各类配置值的验证函数。
"""

from __future__ import annotations


def validate_corr_threshold(value, default: float = 0.8) -> float:
    """验证相关性阈值

    Args:
        value: 待验证的值
        default: 默认值

    Returns:
        验证后的浮点数，范围 (0, 1]

    Examples:
        >>> validate_corr_threshold(0.75)
        0.75
        >>> validate_corr_threshold(-0.5, 0.8)
        0.8
        >>> validate_corr_threshold("invalid", 0.8)
        0.8
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not (0 < numeric <= 1):
        return default
    return numeric


def validate_ratio_setting(
    value, default: float, *, min_value: float = 0.0, max_value: float = 1.0
) -> float:
    """验证比率设置

    Args:
        value: 待验证的值
        default: 默认值
        min_value: 最小值（含）
        max_value: 最大值（含）

    Returns:
        验证后的浮点数

    Examples:
        >>> validate_ratio_setting(0.6, 0.5)
        0.6
        >>> validate_ratio_setting(1.5, 0.5, max_value=1.0)
        0.5
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if numeric < min_value or numeric > max_value:
        return default
    return numeric


def validate_positive_int_setting(
    value, default: int, *, minimum: int = 1, maximum: int | None = None
) -> int:
    """验证正整数设置

    Args:
        value: 待验证的值
        default: 默认值
        minimum: 最小值（含）
        maximum: 最大值（含），None 表示无上限

    Returns:
        验证后的整数

    Examples:
        >>> validate_positive_int_setting(10, 5)
        10
        >>> validate_positive_int_setting(-5, 5)
        5
        >>> validate_positive_int_setting(100, 5, maximum=50)
        5
    """
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return default
    if numeric < minimum:
        return default
    if maximum is not None and numeric > maximum:
        return default
    return numeric


def validate_float_range_setting(
    value,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """验证浮点数范围设置

    Args:
        value: 待验证的值
        default: 默认值
        minimum: 最小值（含），None 表示无下限
        maximum: 最大值（含），None 表示无上限

    Returns:
        验证后的浮点数

    Examples:
        >>> validate_float_range_setting(2.5, 1.0, minimum=0, maximum=10)
        2.5
        >>> validate_float_range_setting(-5, 1.0, minimum=0)
        1.0
        >>> validate_float_range_setting(100, 1.0, maximum=50)
        1.0
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and numeric < minimum:
        return default
    if maximum is not None and numeric > maximum:
        return default
    return numeric
