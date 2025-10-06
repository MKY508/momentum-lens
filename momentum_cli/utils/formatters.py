"""
通用格式化与标签工具

提供对值着色、状态标签、人类友好文本等功能，供 CLI 与业务模块复用。
"""
from __future__ import annotations

from typing import Optional, Dict, Any

from .colors import colorize, get_rank_style
from .parsers import extract_float


def chop_state_label(state: Optional[str], lang: str) -> Optional[str]:
    mapping = {
        "strong_trend": {"zh": "强趋势", "en": "Strong Trend"},
        "trend_breakout": {"zh": "趋势启动", "en": "Trend Breakout"},
        "trend": {"zh": "趋势", "en": "Trend"},
        "range": {"zh": "盘整", "en": "Range"},
        "range_watch": {"zh": "盘整观察", "en": "Range Watch"},
        "neutral": {"zh": "中性", "en": "Neutral"},
    }
    if not state:
        return None
    record = mapping.get(state)
    if not record:
        return None
    return record.get(lang, record.get("en"))


def adx_state_label(state: Optional[str], lang: str) -> Optional[str]:
    mapping = {
        "weak": {"zh": "趋势弱", "en": "Weak"},
        "setup": {"zh": "趋势初现", "en": "Emerging"},
        "strong": {"zh": "趋势强", "en": "Strong"},
    }
    if not state:
        return None
    record = mapping.get(state)
    if not record:
        return None
    return record.get(lang, record.get("en"))


def style_rank_header(rank: int, text: str, *, enable_color: bool = True) -> str:
    if not enable_color:
        return text
    style = get_rank_style(rank)
    if style:
        return colorize(text, style)
    return text


def style_summary_value(label: str, value: str, row: Dict[str, Any], *, enable_color: bool = True) -> str:
    if not enable_color:
        return value
    style: str | None = None
    if label in {"动量", "Momentum"}:
        number = extract_float(value)
        if number is not None:
            if number > 0:
                style = "value_positive"
            elif number < 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label in {"变动", "ΔRank"}:
        number = extract_float(value)
        if number is not None:
            if number < 0:
                style = "value_positive"
            elif number > 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label in {"趋势", "Trend"}:
        number = extract_float(value)
        if number is not None:
            if number > 0:
                style = "value_positive"
            elif number < 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label in {"200MA", "MA200"}:
        if value.endswith("上") or value.endswith("UP"):
            style = "value_positive"
        elif value.endswith("下") or value.endswith("DN"):
            style = "value_negative"
        else:
            style = "value_neutral"
    elif label in {"趋势一致", "TrendOK"}:
        flag = row.get("__trend_ok") if isinstance(row, dict) else None
        if flag is True:
            style = "value_positive"
        elif flag is False:
            style = "value_negative"
        else:
            style = "value_neutral"
    if style:
        return colorize(value, style)
    return value

from .display import display_width as _display_width, pad_display as _pad_display


def render_table(columns: list[tuple[str, str, str]], rows: list[dict]) -> str:
    if not rows:
        return ""
    col_widths: dict[str, int] = {}
    for key, header, _ in columns:
        width = _display_width(header)
        for row in rows:
            width = max(width, _display_width(str(row.get(key, ""))))
        col_widths[key] = width

    def fmt_cell(key: str, text: str, align: str, style: str | None = None) -> str:
        padded = _pad_display(str(text), col_widths[key], align)
        if style:
            return colorize(padded, style)
        return padded

    header_line = " | ".join(
        fmt_cell(key, header, align, style="header") for key, header, align in columns
    )
    separator_line = colorize(
        "-+-".join("-" * col_widths[key] for key, _, _ in columns), "divider"
    )

    body_lines = []
    for row in rows:
        parts: list[str] = []
        for key, _, align in columns:
            value = row.get(key, "")
            style = row.get(f"style_{key}")
            parts.append(fmt_cell(key, value, align, style))
        body_lines.append(" | ".join(parts))

    return "\n".join([header_line, separator_line, *body_lines])

