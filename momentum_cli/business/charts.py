"""
图表相关业务逻辑
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, Set

import pandas as pd


def ensure_plotly(colorize_func):
    try:
        import plotly.graph_objects as go  # type: ignore
    except Exception:
        print(
            colorize_func(
                "缺少 plotly，无法生成交互式图表。请运行 `pip install plotly` 后重试。",
                "warning",
            )
        )
        return None
    return go


def generate_interactive_plot(
    data: pd.DataFrame,
    title: str,
    yaxis_title: str,
    output_dir: Path,
    filename: str,
    *,
    invert_y: bool = False,
    core_codes: Optional[Set[str]] = None,
    satellite_codes: Optional[Set[str]] = None,
    default_visible_codes: Optional[Iterable[str]] = None,
    format_label_func=None,
    plot_template: str = "plotly_white",
    line_width: float = 1.5,
    colorize_func=None,
) -> Optional[Path]:
    if data.empty:
        if colorize_func:
            print(colorize_func("数据为空，无法生成图表。", "warning"))
        return None
    go = ensure_plotly(colorize_func or (lambda x, *_: x))
    if go is None:
        if colorize_func:
            print(colorize_func("plotly 未安装，可尝试执行 `pip install plotly` 后重试。", "menu_hint"))
        return None

    figure = go.Figure()
    default_visible = {str(c).upper() for c in default_visible_codes} if default_visible_codes else None

    start_index: Optional[pd.Timestamp] = data.index.min() if not data.empty else None
    target_start: Optional[pd.Timestamp] = None
    if default_visible and data.index.size:
        col_map = {str(col).upper(): col for col in data.columns}
        first_indices: list[pd.Timestamp] = []
        for code in default_visible:
            column = col_map.get(code)
            if column is None:
                continue
            first_valid = data[column].first_valid_index()
            if first_valid is not None:
                first_indices.append(first_valid)
        if first_indices:
            target_start = min(first_indices)
    if target_start is None and not data.empty:
        non_empty = data.dropna(how="all")
        if not non_empty.empty:
            target_start = non_empty.index.min()
    if target_start is not None and start_index is not None:
        threshold = pd.Timedelta(days=45)
        if target_start - start_index <= threshold:
            data = data[data.index >= target_start]
    data = data.dropna(how="all")

    trace_codes = [str(col).upper() for col in data.columns]
    for column, code_upper in zip(data.columns, trace_codes):
        visible_state: bool | str = True
        if default_visible and code_upper not in default_visible:
            visible_state = "legendonly"
        legend_group = (
            "CORE" if core_codes and code_upper in core_codes else (
                "SAT" if satellite_codes and code_upper in satellite_codes else "OTHER"
            )
        )
        label = format_label_func(column) if format_label_func else str(column)
        figure.add_trace(
            go.Scatter(
                x=data.index,
                y=data[column],
                mode="lines",
                name=label,
                legendgroup=legend_group,
                line={"width": line_width},
                visible=visible_state,
            )
        )

    buttons: list[dict] = []
    all_visible = [True] * len(trace_codes)
    buttons.append({"label": "全部", "method": "update", "args": [{"visible": all_visible}]})
    if default_visible:
        default_mask = [code in default_visible for code in trace_codes]
        if any(default_mask) and any(v is False for v in default_mask):
            buttons.append({"label": "前 6", "method": "update", "args": [{"visible": default_mask}]})
    if core_codes:
        core_visible = [code in core_codes for code in trace_codes]
        if any(core_visible):
            buttons.append({"label": "仅核心", "method": "update", "args": [{"visible": core_visible}]})
    if satellite_codes:
        sat_visible = [code in satellite_codes for code in trace_codes]
        if any(sat_visible):
            buttons.append({"label": "仅卫星", "method": "update", "args": [{"visible": sat_visible}]})
    other_visible = [
        code not in (core_codes or set()) and code not in (satellite_codes or set())
        for code in trace_codes
    ]
    if any(other_visible):
        buttons.append({"label": "仅其他", "method": "update", "args": [{"visible": other_visible}]})

    legend_height_padding = max(0, len(trace_codes) - 12) * 22
    figure.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        template=plot_template,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            itemwidth=110,
            groupclick="toggleitem",
            traceorder="grouped",
        ),
        height=650 + legend_height_padding,
        margin=dict(l=60, r=30, t=80, b=60 + min(legend_height_padding, 120)),
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 0,
                "y": 1.18,
                "showactive": False,
                "buttons": buttons,
            }
        ] if len(buttons) > 1 else None,
    )
    figure.update_layout(legend_title_text="图例 (点击可隐藏/显示单个 ETF)")
    if invert_y:
        figure.update_yaxes(autorange="reversed")

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    figure.write_html(str(path), include_plotlyjs="cdn")
    return path

