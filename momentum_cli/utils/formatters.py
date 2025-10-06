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



# ===== Summary table preparation and markdown export =====
import pandas as pd
from .display import display_width as _display_width


def _normalize_column_specs(specs):
    normalized = []
    for spec in specs:
        if len(spec) == 3:
            key, label, align = spec
            include_compact = True
        elif len(spec) == 4:
            key, label, align, include_compact = spec
        else:
            raise ValueError("Invalid column specification")
        normalized.append((str(key), str(label), str(align), bool(include_compact)))
    return normalized


def prepare_summary_table(frame: pd.DataFrame, lang: str):
    ordered = (
        frame.copy()
        .sort_values(["momentum_rank", "momentum_score"], ascending=[True, False])
        .reset_index(drop=True)
    )

    def compose_symbol(row: pd.Series) -> str:
        name = str(row.get("name", "") or "").strip()
        code = str(row.get("etf", "") or "").strip()
        if name and code:
            return f"{name} ({code})"
        return name or code or "-"

    ordered["symbol"] = ordered.apply(compose_symbol, axis=1)

    def fmt_number(value, digits: int = 4) -> str:
        import pandas as _pd
        if value is None or _pd.isna(value):
            return "-"
        return f"{value:.{digits}f}"

    def fmt_rank(value) -> str:
        import pandas as _pd
        if value is None or _pd.isna(value):
            return "--"
        return f"{int(value):02d}"

    def fmt_change(value) -> str:
        import pandas as _pd
        if value is None or _pd.isna(value):
            return "-"
        return f"{value:+.0f}"

    def fmt_ma(row: pd.Series) -> str:
        import pandas as _pd
        ma = row.get("ma200")
        if ma is None or _pd.isna(ma):
            return "-"
        above = bool(row.get("above_ma200"))
        status = "上" if lang == "zh" else "UP"
        alt = "下" if lang == "zh" else "DN"
        suffix = status if above else alt
        return f"{ma:.4f}{suffix}"

    ordered["momentum_fmt"] = ordered["momentum_score"].apply(fmt_number)
    ordered["rank_fmt"] = ordered["momentum_rank"].apply(fmt_rank)
    ordered["delta_fmt"] = ordered["rank_change"].apply(fmt_change)
    ordered["close_fmt"] = ordered["close"].apply(fmt_number)
    ordered["vwap_fmt"] = ordered["vwap"].apply(fmt_number)
    ordered["ma_fmt"] = [fmt_ma(row) for _, row in ordered.iterrows()]

    def fmt_chop_display(row: pd.Series) -> str:
        base = fmt_number(row.get("chop"), 2)
        state_label = chop_state_label(row.get("chop_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    def fmt_adx_display(row: pd.Series) -> str:
        base = fmt_number(row.get("adx"), 2)
        state_label = adx_state_label(row.get("adx_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    ordered["chop_fmt"] = [fmt_chop_display(row) for _, row in ordered.iterrows()]
    ordered["trend_fmt"] = ordered["trend_slope"].apply(fmt_number)
    ordered["atr_fmt"] = ordered["atr"].apply(fmt_number)
    ordered["adx_fmt"] = [fmt_adx_display(row) for _, row in ordered.iterrows()]

    def fmt_momentum_percentile(row: pd.Series) -> str:
        import pandas as _pd
        value = row.get("momentum_percentile")
        if value is None or _pd.isna(value):
            return "--"
        flag = row.get("momentum_significant")
        if flag is None or (isinstance(flag, float) and _pd.isna(flag)):
            return "--"
        mark = "✅" if bool(flag) else "❌"
        return f"{mark}{value * 100:.1f}%"

    def fmt_stability_display(row: pd.Series) -> str:
        import pandas as _pd
        value = row.get("stability")
        if value is None or _pd.isna(value):
            return "--"
        return f"{float(value) * 100:.0f}%"

    ordered["stability_fmt"] = [fmt_stability_display(row) for _, row in ordered.iterrows()]

    def truncate(value: str, limit: int) -> str:
        text = str(value).strip()
        if limit <= 0:
            return ""
        if _display_width(text) <= limit:
            return text
        ellipsis = "..."
        ellipsis_width = _display_width(ellipsis)
        if ellipsis_width >= limit:
            # 返回尽可能多的字符
            trimmed: list[str] = []
            consumed = 0
            for char in text:
                char_width = _display_width(char)
                if consumed + char_width > limit:
                    break
                trimmed.append(char)
                consumed += char_width
            return "".join(trimmed)
        target_width = limit - ellipsis_width
        trimmed_chars: list[str] = []
        consumed = 0
        for char in text:
            char_width = _display_width(char)
            if consumed + char_width > target_width:
                break
            trimmed_chars.append(char)
            consumed += char_width
        if not trimmed_chars:
            return ellipsis
        return "".join(trimmed_chars) + ellipsis

    rows: list[dict[str, str]] = []
    for _, row in ordered.iterrows():
        rows.append({
            "symbol": truncate(row["symbol"], 26),
            "rank_fmt": str(row["rank_fmt"]),
            "delta_fmt": str(row["delta_fmt"]),
            "momentum_fmt": str(row["momentum_fmt"]),
            "mom_pct_fmt": str(row["mom_pct_fmt"]) if "mom_pct_fmt" in ordered.columns else str(fmt_momentum_percentile(row)),
            "stability_fmt": str(row["stability_fmt"]),
            "close_fmt": str(row["close_fmt"]),
            "vwap_fmt": str(row["vwap_fmt"]),
            "ma_fmt": str(row["ma_fmt"]),
            "chop_fmt": str(row["chop_fmt"]),
            "trend_fmt": str(row["trend_fmt"]),
            "trend_ok_fmt": str("✅" if row.get("trend_ok") else ("❌" if row.get("trend_ok") is not None else "--")),
            "atr_fmt": str(row["atr_fmt"]),
            "adx_fmt": str(row["adx_fmt"]),
            "__chop_state": row.get("chop_state"),
            "__chop_p30": row.get("chop_p30"),
            "__chop_p70": row.get("chop_p70"),
            "__adx_state": row.get("adx_state"),
            "__mom_significant": row.get("momentum_significant"),
            "__trend_ok": row.get("trend_ok"),
            "__stability": row.get("stability"),
        })

    if lang == "zh":
        columns = [
            ("symbol", "标的", "left", True),
            ("rank_fmt", "排名", "right", True),
            ("delta_fmt", "变动", "right", True),
            ("momentum_fmt", "动量", "right", True),
            ("mom_pct_fmt", "动量分位", "right", True),
            ("stability_fmt", "稳定度", "right", True),
            ("close_fmt", "收盘", "right", True),
            ("vwap_fmt", "VWAP", "right", True),
            ("ma_fmt", "200MA", "right", False),
            ("chop_fmt", "Chop", "right", True),
            ("trend_fmt", "趋势", "right", True),
            ("trend_ok_fmt", "趋势一致", "center", True),
            ("adx_fmt", "ADX", "right", True),
            ("atr_fmt", "ATR", "right", True),
        ]
    else:
        columns = [
            ("symbol", "Symbol", "left", True),
            ("rank_fmt", "Rank", "right", True),
            ("delta_fmt", "ΔRank", "right", True),
            ("momentum_fmt", "Momentum", "right", True),
            ("mom_pct_fmt", "Mom%", "right", True),
            ("stability_fmt", "Stability", "right", True),
            ("close_fmt", "Close", "right", True),
            ("vwap_fmt", "VWAP", "right", True),
            ("ma_fmt", "MA200", "right", True),
            ("chop_fmt", "Chop", "right", True),
            ("trend_fmt", "Trend", "right", True),
            ("trend_ok_fmt", "TrendOK", "center", True),
            ("adx_fmt", "ADX", "right", True),
            ("atr_fmt", "ATR", "right", True),
        ]

    return _normalize_column_specs(columns), rows


def summary_to_markdown(frame: pd.DataFrame, lang: str) -> str:
    if frame.empty:
        return "*暂无可用的动量结果*" if lang == "zh" else "*No momentum results available.*"
    columns, rows = prepare_summary_table(frame, lang)
    if not rows:
        return "*暂无可用的动量结果*" if lang == "zh" else "*No momentum results available.*"

    columns = _normalize_column_specs(columns)

    def escape(text: str) -> str:
        return str(text).replace("|", "\\|")

    header = "| " + " | ".join(header for _, header, _, _ in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(escape(row.get(key, "-")) for key, _, _, _ in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])



import shutil


def format_summary_frame(frame: pd.DataFrame, lang: str, *, enable_color: bool = True) -> str:
    if frame.empty:
        return "暂无可用的动量结果。" if lang == "zh" else "No momentum results available."

    columns, rows = prepare_summary_table(frame, lang)
    if not rows:
        return "暂无可用的动量结果。" if lang == "zh" else "No momentum results available."

    columns = _normalize_column_specs(columns)

    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        terminal_width = 120

    # Compact view for narrow terminals
    if terminal_width < 100:
        compact_columns = [spec for spec in columns if spec[3]] or columns
        lines: list[str] = []
        for row in rows:
            header = f"{row['rank_fmt']}. {row['symbol']}"
            delta = row.get("delta_fmt")
            if delta and delta not in {"-", "0"}:
                header += f" (Δ{delta})"
            try:
                rank_value = int(row.get("rank_fmt", "0"))
            except ValueError:
                rank_value = 0
            styled_header = style_rank_header(rank_value, header, enable_color=enable_color)
            if enable_color:
                lines.append(colorize(styled_header, "menu_text"))
            else:
                lines.append(styled_header)

            field_parts: list[str] = []
            for key, label, _, _ in compact_columns:
                if key == "symbol":
                    continue
                value = row.get(key, "-")
                field_parts.append(f"{label}:{value}")
            body_text = " · ".join(field_parts)
            import textwrap as _tw
            wrapped = _tw.fill(
                body_text,
                width=max(terminal_width, 40),
                initial_indent="    ",
                subsequent_indent="    ",
            )
            lines.append(wrapped)
            lines.append("")
        return "\n".join(lines).strip()

    active_columns = columns
    label_map = {key: label for key, label, _, _ in active_columns}

    col_widths: dict[str, int] = {}
    for key, header, _, _ in columns:
        width_hint = _display_width(header)
        for row in rows:
            width_hint = max(width_hint, _display_width(row[key]))
        col_widths[key] = width_hint

    def _calc_total_width(specs) -> int:
        if not specs:
            return 0
        total = 0
        for idx, (key, _, _, _) in enumerate(specs):
            total += col_widths[key]
            if idx < len(specs) - 1:
                total += 3
        return total

    max_table_width = max(terminal_width - 4, 60)
    removable_priority = [
        "trend_ok_fmt",
        "mom_pct_fmt",
        "atr_fmt",
        "vwap_fmt",
        "trend_fmt",
        "ma_fmt",
        "chop_fmt",
    ]
    while len(active_columns) > 5 and _calc_total_width(active_columns) > max_table_width:
        removed = False
        for key in removable_priority:
            if any(col_key == key for col_key, _, _, _ in active_columns):
                active_columns = [spec for spec in active_columns if spec[0] != key]
                removed = True
                break
        if not removed:
            break

    label_map = {key: label for key, label, _, _ in active_columns}

    def format_cell(key: str, text: str, align: str, row: dict | None = None) -> str:
        width = col_widths[key]
        padded = _pad_display(text, width, align)
        if row is not None:
            return style_summary_value(label_map[key], padded, row, enable_color=enable_color)
        return colorize(padded, "header") if enable_color else padded

    header_line = " | ".join(
        format_cell(key, label, align) for key, label, align, _ in active_columns
    )
    separator_line = colorize(
        "-+-".join("-" * col_widths[key] for key, _, _, _ in active_columns), "divider"
    ) if enable_color else "-+-".join("-" * col_widths[key] for key, _, _, _ in active_columns)

    body_lines: list[str] = []
    for row in rows:
        line_parts: list[str] = []
        for key, _, align, _ in active_columns:
            styled_value = format_cell(key, row[key], align, row=row)
            line_parts.append(styled_value)
        body_lines.append(" | ".join(line_parts))

    return "\n".join([header_line, separator_line, *body_lines])

# ---- Summary table preparation and rendering ----
from .display import display_width as display_width
from .colors import colorize
import shutil
import textwrap
import pandas as pd  # type: ignore
from typing import Sequence, List, Tuple


def normalize_column_specs(
    specs: Sequence[tuple[str, str, str] | tuple[str, str, str, bool]]
) -> List[tuple[str, str, str, bool]]:
    normalized: List[tuple[str, str, str, bool]] = []
    for spec in specs:
        if len(spec) == 3:
            key, label, align = spec
            include_compact = True
        elif len(spec) == 4:
            key, label, align, include_compact = spec
        else:  # defensive
            raise ValueError("Invalid column specification")
        normalized.append((str(key), str(label), str(align), bool(include_compact)))
    return normalized


def prepare_summary_table(
    frame: pd.DataFrame, lang: str
) -> tuple[List[tuple[str, str, str]], List[dict[str, str]]]:
    ordered = (
        frame.copy()
        .sort_values(["momentum_rank", "momentum_score"], ascending=[True, False])
        .reset_index(drop=True)
    )

    def compose_symbol(row: pd.Series) -> str:
        name = str(row.get("name", "") or "").strip()
        code = str(row.get("etf", "") or "").strip()
        if name and code:
            return f"{name} ({code})"
        return name or code or "-"

    ordered["symbol"] = ordered.apply(compose_symbol, axis=1)

    def fmt_number(value, digits: int = 4) -> str:
        if value is None or pd.isna(value):
            return "-"
        return f"{float(value):.{digits}f}"

    def fmt_rank(value) -> str:
        if value is None or pd.isna(value):
            return "--"
        try:
            return f"{int(value):02d}"
        except Exception:
            return "--"

    def fmt_change(value) -> str:
        if value is None or pd.isna(value):
            return "-"
        try:
            return f"{float(value):+0.0f}"
        except Exception:
            return "-"

    def fmt_ma(row: pd.Series) -> str:
        ma = row.get("ma200")
        if ma is None or pd.isna(ma):
            return "-"
        above = bool(row.get("above_ma200"))
        status = "上" if lang == "zh" else "UP"
        alt = "下" if lang == "zh" else "DN"
        suffix = status if above else alt
        return f"{float(ma):.4f}{suffix}"

    ordered["momentum_fmt"] = ordered["momentum_score"].apply(fmt_number)
    ordered["rank_fmt"] = ordered["momentum_rank"].apply(fmt_rank)
    ordered["delta_fmt"] = ordered["rank_change"].apply(fmt_change)
    ordered["close_fmt"] = ordered["close"].apply(fmt_number)
    ordered["vwap_fmt"] = ordered["vwap"].apply(fmt_number)
    ordered["ma_fmt"] = [fmt_ma(row) for _, row in ordered.iterrows()]

    def fmt_chop_display(row: pd.Series) -> str:
        base = fmt_number(row.get("chop"), 2)
        state_label = chop_state_label(row.get("chop_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    def fmt_adx_display(row: pd.Series) -> str:
        base = fmt_number(row.get("adx"), 2)
        state_label = adx_state_label(row.get("adx_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    ordered["chop_fmt"] = [fmt_chop_display(row) for _, row in ordered.iterrows()]
    ordered["trend_fmt"] = ordered["trend_slope"].apply(fmt_number)
    ordered["atr_fmt"] = ordered["atr"].apply(fmt_number)
    ordered["adx_fmt"] = [fmt_adx_display(row) for _, row in ordered.iterrows()]

    def fmt_momentum_percentile(row: pd.Series) -> str:
        value = row.get("momentum_percentile")
        if value is None or pd.isna(value):
            return "--"
        flag = row.get("momentum_significant")
        if flag is None or (isinstance(flag, float) and pd.isna(flag)):
            return "--"
        mark = "✅" if bool(flag) else "❌"
        try:
            return f"{mark}{float(value) * 100:.1f}%"
        except Exception:
            return f"{mark}--"

    def fmt_stability_display(row: pd.Series) -> str:
        value = row.get("stability")
        if value is None or pd.isna(value):
            return "--"
        try:
            return f"{float(value) * 100:.0f}%"
        except Exception:
            return "--"

    ordered["stability_fmt"] = [fmt_stability_display(row) for _, row in ordered.iterrows()]

    def fmt_trend_ok(row: pd.Series) -> str:
        flag = row.get("trend_ok")
        if flag is None or (isinstance(flag, float) and pd.isna(flag)):
            return "--"
        return "✅" if bool(flag) else "❌"

    ordered["mom_pct_fmt"] = [fmt_momentum_percentile(row) for _, row in ordered.iterrows()]
    ordered["trend_ok_fmt"] = [fmt_trend_ok(row) for _, row in ordered.iterrows()]

    def truncate(text: str, limit: int) -> str:
        text = str(text).strip()
        if limit <= 0:
            return ""
        from .display import display_width as _dw
        if _dw(text) <= limit:
            return text
        ellipsis = "..."
        e_width = _dw(ellipsis)
        if e_width >= limit:
            trimmed: List[str] = []
            consumed = 0
            for ch in text:
                cw = _dw(ch)
                if consumed + cw > limit:
                    break
                trimmed.append(ch)
                consumed += cw
            return "".join(trimmed)
        target = limit - e_width
        trimmed_chars: List[str] = []
        consumed = 0
        for ch in text:
            cw = _dw(ch)
            if consumed + cw > target:
                break
            trimmed_chars.append(ch)
            consumed += cw
        if not trimmed_chars:
            return ellipsis
        return "".join(trimmed_chars) + ellipsis

    rows: List[dict[str, str]] = []
    for _, row in ordered.iterrows():
        rows.append(
            {
                "symbol": truncate(row["symbol"], 26),
                "rank_fmt": str(row.get("rank_fmt", "--")),
                "delta_fmt": str(row.get("delta_fmt", "-")),
                "momentum_fmt": str(row.get("momentum_fmt", "-")),
                "mom_pct_fmt": str(row.get("mom_pct_fmt", "--")),
                "stability_fmt": str(row.get("stability_fmt", "--")),
                "close_fmt": str(row.get("close_fmt", "-")),
                "vwap_fmt": str(row.get("vwap_fmt", "-")),
                "ma_fmt": str(row.get("ma_fmt", "-")),
                "chop_fmt": str(row.get("chop_fmt", "-")),
                "trend_fmt": str(row.get("trend_fmt", "-")),
                "trend_ok_fmt": str(row.get("trend_ok_fmt", "--")),
                "atr_fmt": str(row.get("atr_fmt", "-")),
                "adx_fmt": str(row.get("adx_fmt", "-")),
                "__chop_state": row.get("chop_state"),
                "__chop_p30": row.get("chop_p30"),
                "__chop_p70": row.get("chop_p70"),
                "__adx_state": row.get("adx_state"),
                "__mom_significant": row.get("momentum_significant"),
                "__trend_ok": row.get("trend_ok"),
                "__stability": row.get("stability"),
            }
        )

    if lang == "zh":
        columns = [
            ("symbol", "标的", "left"),
            ("rank_fmt", "排名", "right"),
            ("delta_fmt", "变动", "right"),
            ("momentum_fmt", "动量", "right"),
            ("mom_pct_fmt", "动量分位", "right"),
            ("stability_fmt", "稳定度", "right"),
            ("close_fmt", "收盘", "right"),
            ("vwap_fmt", "VWAP", "right"),
            ("ma_fmt", "200MA", "right"),
            ("chop_fmt", "Chop", "right"),
            ("trend_fmt", "趋势", "right"),
            ("trend_ok_fmt", "趋势一致", "center"),
            ("adx_fmt", "ADX", "right"),
            ("atr_fmt", "ATR", "right"),
        ]
    else:
        columns = [
            ("symbol", "Symbol", "left"),
            ("rank_fmt", "Rank", "right"),
            ("delta_fmt", "ΔRank", "right"),
            ("momentum_fmt", "Momentum", "right"),
            ("mom_pct_fmt", "Mom%", "right"),
            ("stability_fmt", "Stability", "right"),
            ("close_fmt", "Close", "right"),
            ("vwap_fmt", "VWAP", "right"),
            ("ma_fmt", "MA200", "right"),
            ("chop_fmt", "Chop", "right"),
            ("trend_fmt", "Trend", "right"),
            ("trend_ok_fmt", "TrendOK", "center"),
            ("adx_fmt", "ADX", "right"),
            ("atr_fmt", "ATR", "right"),
        ]

    return normalize_column_specs(columns), rows


def format_summary_frame(
    frame: pd.DataFrame, lang: str, *, enable_color: bool = True
) -> str:
    if frame.empty:
        return "暂无可用的动量结果。" if lang == "zh" else "No momentum results available."

    columns, rows = prepare_summary_table(frame, lang)
    if not rows:
        return "暂无可用的动量结果。" if lang == "zh" else "No momentum results available."

    columns = normalize_column_specs(columns)

    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        terminal_width = 120

    if terminal_width < 100:
        compact_columns = [spec for spec in columns if spec[3]] or columns
        lines: List[str] = []
        for row in rows:
            header = f"{row['rank_fmt']}. {row['symbol']}"
            delta = row.get("delta_fmt")
            if delta and delta not in {"-", "0"}:
                header += f" (Δ{delta})"
            try:
                rank_value = int(row.get("rank_fmt", "0"))
            except ValueError:
                rank_value = 0
            header = style_rank_header(rank_value, header, enable_color=enable_color)
            if not get_rank_style(rank_value):
                header = colorize(header, "menu_text")
            lines.append(header)
            field_parts: List[str] = []
            for key, label, _, _ in compact_columns:
                if key == "symbol":
                    continue
                value = row.get(key, "-")
                field_parts.append(f"{label}:{value}")
            body_text = " · ".join(field_parts)
            wrapped = textwrap.fill(
                body_text,
                width=max(terminal_width, 40),
                initial_indent="    ",
                subsequent_indent="    ",
            )
            lines.append(wrapped)
            lines.append("")
        return "\n".join(lines).strip()

    active_columns = columns
    label_map = {key: label for key, label, _, _ in active_columns}
    col_widths: dict[str, int] = {}
    for key, header, _, _ in columns:
        width_hint = display_width(header)
        for row in rows:
            width_hint = max(width_hint, display_width(row[key]))
        col_widths[key] = width_hint

    def _calc_total_width(specs: Sequence[tuple[str, str, str, bool]]) -> int:
        if not specs:
            return 0
        total = 0
        for idx, (key, _, _, _) in enumerate(specs):
            total += col_widths[key]
            if idx < len(specs) - 1:
                total += 3
        return total

    max_table_width = max(terminal_width - 4, 60)
    removable_priority = [
        "trend_ok_fmt",
        "mom_pct_fmt",
        "atr_fmt",
        "vwap_fmt",
        "trend_fmt",
        "ma_fmt",
        "chop_fmt",
    ]
    while len(active_columns) > 5 and _calc_total_width(active_columns) > max_table_width:
        removed = False
        for key in removable_priority:
            if any(col_key == key for col_key, _, _, _ in active_columns):
                active_columns = [spec for spec in active_columns if spec[0] != key]
                removed = True
                break
        if not removed:
            break

    label_map = {key: label for key, label, _, _ in active_columns}

    from .display import pad_display as pad_display

    def format_cell(key: str, text: str, align: str, row: dict | None = None) -> str:
        width = col_widths[key]
        padded = pad_display(text, width, align)
        if row is not None:
            return style_summary_value(label_map[key], padded, row, enable_color=enable_color)
        return colorize(padded, "header")

    header_line = " | ".join(
        format_cell(key, label, align) for key, label, align, _ in active_columns
    )
    separator_line = colorize(
        "-+-".join("-" * col_widths[key] for key, _, _, _ in active_columns), "divider"
    )

    body_lines = []
    for row in rows:
        line_parts = []
        for key, _, align, _ in active_columns:
            styled_value = format_cell(key, row[key], align, row=row)
            if key == "symbol" and enable_color:
                try:
                    rank = int(row.get("rank_fmt", "0"))
                except ValueError:
                    rank = 0
                rank_style = get_rank_style(rank)
                if rank_style:
                    styled_value = colorize(styled_value, rank_style)
            line_parts.append(styled_value)
        body_lines.append(" | ".join(line_parts))

    return "\n".join([header_line, separator_line, *body_lines])


def summary_to_markdown(frame: pd.DataFrame, lang: str) -> str:
    if frame.empty:
        return "*暂无可用的动量结果*" if lang == "zh" else "*No momentum results available.*"
    columns, rows = prepare_summary_table(frame, lang)
    if not rows:
        return "*暂无可用的动量结果*" if lang == "zh" else "*No momentum results available.*"
    columns = normalize_column_specs(columns)

    def escape(text: str) -> str:
        return str(text).replace("|", "\\|")

    header = "| " + " | ".join(header for _, header, _, _ in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| "
        + " | ".join(escape(row.get(key, "-")) for key, _, _, _ in columns)
        + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])
