"""显示相关工具函数

处理终端文本显示宽度、ANSI 转义序列等。
"""

from __future__ import annotations

import functools
import re
import unicodedata

try:
    from wcwidth import wcswidth as _wcwidth_wcswidth
except ImportError:  # pragma: no cover - 可选依赖
    _wcwidth_wcswidth = None


# ANSI 转义序列匹配模式
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

# 常见"视觉等宽但被标记为 Ambiguous 的字符"，在多数终端里仍按单宽显示
_AMBIGUOUS_NARROW = {
    "·",
    "•",
    "°",
    "×",
    "÷",
}


@functools.lru_cache(maxsize=2048)
def strip_ansi(text: str) -> str:
    """移除文本中的 ANSI 转义序列

    Args:
        text: 可能包含 ANSI 转义序列的文本

    Returns:
        移除 ANSI 序列后的纯文本
    """
    return _ANSI_PATTERN.sub("", text)


def _fallback_display_width(text: str) -> int:
    """后备的显示宽度计算方法（当 wcwidth 不可用时）

    使用 Unicode 数据库判断字符宽度。

    Args:
        text: 要计算宽度的文本

    Returns:
        显示宽度（以终端列数计）
    """
    width = 0
    for char in text:
        if not char:
            continue
        if unicodedata.combining(char):
            continue
        code = ord(char)
        if code < 128:
            width += 1
            continue
        east = unicodedata.east_asian_width(char)
        if east in {"F", "W"}:
            width += 2
        elif east == "A" and char not in _AMBIGUOUS_NARROW:
            width += 2
        else:
            width += 1
    return width


@functools.lru_cache(maxsize=1024)
def display_width(text: str) -> int:
    """计算文本在终端中的显示宽度

    自动移除 ANSI 转义序列，并正确处理宽字符（CJK 字符等）。
    优先使用 wcwidth 库，回退到内置实现。

    Args:
        text: 要计算宽度的文本（可包含 ANSI 序列）

    Returns:
        显示宽度（以终端列数计）

    Examples:
        >>> display_width("Hello")
        5
        >>> display_width("你好")
        4
        >>> display_width("\x1b[31m红色\x1b[0m")
        4
    """
    cleaned = strip_ansi(text)
    if _wcwidth_wcswidth:
        width = _wcwidth_wcswidth(cleaned)
        if width >= 0:
            return width
    return _fallback_display_width(cleaned)


def pad_display(text: str, width: int, align: str = "left") -> str:
    """填充文本到指定显示宽度

    根据对齐方式在文本两侧添加空格，以达到指定的显示宽度。
    正确处理宽字符和 ANSI 转义序列。

    Args:
        text: 要填充的文本
        width: 目标显示宽度
        align: 对齐方式，可选 "left"（左对齐）、"right"（右对齐）、"center"（居中）

    Returns:
        填充后的文本

    Examples:
        >>> pad_display("Hi", 10, "left")
        'Hi        '
        >>> pad_display("Hi", 10, "right")
        '        Hi'
        >>> pad_display("Hi", 10, "center")
        '    Hi    '
    """
    current = display_width(text)
    delta = max(0, width - current)
    if delta == 0:
        return text
    if align == "right":
        return " " * delta + text
    if align == "center":
        left = delta // 2
        right = delta - left
        return " " * left + text + " " * right
    return text + " " * delta
