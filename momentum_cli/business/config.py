"""配置管理模块

提供CLI配置、主题、样式等设置的业务逻辑。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def configure_correlation_threshold_interactive(
    current_threshold: float,
    validate_func: Callable[[float], float],
    set_threshold_func: Callable[[float], float],
    prompt_menu_choice_func: Callable,
    colorize_func: Callable,
    prompt_input_func: Callable,
) -> None:
    """交互式配置相关矩阵阈值

    Args:
        current_threshold: 当前阈值
        validate_func: 验证阈值的函数
        set_threshold_func: 设置阈值的函数
        prompt_menu_choice_func: 菜单选择函数
        colorize_func: 着色函数
        prompt_input_func: 输入提示函数
    """
    presets = {
        "1": 0.6,
        "2": 0.8,
        "3": 0.85,
    }
    options = [
        {"key": "1", "label": "设为 0.60"},
        {"key": "2", "label": "设为 0.80"},
        {"key": "3", "label": "设为 0.85"},
        {"key": "4", "label": "自定义输入"},
        {"key": "0", "label": "返回上级菜单"},
    ]
    header_lines = [
        "",
        colorize_func(f"当前阈值: {current_threshold:.2f}", "menu_text"),
    ]
    choice = prompt_menu_choice_func(
        options,
        title="┌─ 相关矩阵阈值 ─" + "─" * 18,
        header_lines=header_lines,
        hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
        default_key="0",
    ).strip()

    if not choice or choice in {"0", "__escape__"}:
        return

    if choice in presets:
        new_value = presets[choice]
    elif choice == "4":
        raw = prompt_input_func(colorize_func("请输入 0-1 之间的小数，例如 0.75: ", "prompt")).strip()
        try:
            new_value = float(raw)
        except ValueError:
            print(colorize_func("输入无效，阈值保持不变。", "warning"))
            return
    else:
        print(colorize_func("输入无效，阈值保持不变。", "warning"))
        return

    validated = validate_func(new_value)
    if validated != new_value:
        print(colorize_func("输入超出范围，已自动调整到有效区间。", "warning"))

    updated = set_threshold_func(validated)
    print(colorize_func(f"相关矩阵预警阈值已更新为 {updated:.2f}。", "value_positive"))


def configure_plot_style_interactive(
    current_template: str,
    current_line_width: float,
    current_cli_theme: str,
    cli_theme_info: Dict[str, Any],
    set_template_func: Callable[[str], None],
    set_line_width_func: Callable[[float], None],
    prompt_menu_choice_func: Callable,
    colorize_func: Callable,
    prompt_input_func: Callable,
) -> None:
    """交互式配置图表样式

    Args:
        current_template: 当前图表模板
        current_line_width: 当前线宽
        current_cli_theme: 当前CLI主题
        cli_theme_info: CLI主题信息字典
        set_template_func: 设置模板的函数
        set_line_width_func: 设置线宽的函数
        prompt_menu_choice_func: 菜单选择函数
        colorize_func: 着色函数
        prompt_input_func: 输入提示函数
    """
    templates = [
        "plotly_white",
        "plotly_dark",
        "presentation",
        "ggplot2",
        "seaborn",
        "simple_white",
    ]

    print(colorize_func("当前图表样式：", "heading"))
    print(colorize_func(f"主题: {current_template}", "menu_text"))
    print(colorize_func(f"曲线宽度: {current_line_width}", "menu_text"))
    current_theme = cli_theme_info.get(current_cli_theme, {"label": current_cli_theme})
    print(
        colorize_func(
            f"终端主题: {current_theme.get('label', current_cli_theme)} ({current_cli_theme})",
            "menu_hint",
        )
    )

    # 选择模板
    while True:
        options: List[Dict[str, Any]] = []
        default_key = current_template
        for idx, template in enumerate(templates, start=1):
            marker = "✓" if template == current_template else " "
            options.append(
                {
                    "key": template,
                    "display": str(idx),
                    "label": f"[{marker}] {template}",
                }
            )
        options.append({"key": "0", "label": "返回上级菜单"})
        choice = prompt_menu_choice_func(
            options,
            title="┌─ 图表样式设置 ─" + "─" * 18,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key=default_key,
        )
        if choice in {"0", "__escape__"}:
            break
        if choice in templates:
            set_template_func(choice)
            print(colorize_func(f"已切换到 {choice} 主题。", "value_positive"))
            break
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(templates):
                selected = templates[idx - 1]
                set_template_func(selected)
                print(colorize_func(f"已切换到 {selected} 主题。", "value_positive"))
                break
        print(colorize_func("输入无效，请重新选择。", "warning"))

    # 设置线宽
    while True:
        raw = prompt_input_func(
            colorize_func("设置曲线宽度（示例 1.5，直接回车保持当前值）: ", "prompt")
        ).strip()
        if not raw:
            break
        try:
            width = float(raw)
        except ValueError:
            print(colorize_func("请输入数值，例如 1.5。", "warning"))
            continue
        if width <= 0:
            print(colorize_func("宽度需为正数。", "warning"))
            continue
        set_line_width_func(width)
        print(colorize_func(f"曲线宽度已更新为 {width}。", "value_positive"))
        break




def configure_cli_theme_interactive(
    current_theme: str,
    theme_order: List[str],
    theme_info: Dict[str, Any],
    available_themes: Dict[str, Any],
    apply_theme_func: Callable[[str], bool],
    render_sample_func: Callable[[str], str],
    prompt_menu_choice_func: Callable,
    colorize_func: Callable,
) -> None:
    """交互式配置CLI主题

    Args:
        current_theme: 当前主题键
        theme_order: 主题顺序列表
        theme_info: 主题信息字典
        available_themes: 可用主题字典
        apply_theme_func: 应用主题的函数
        render_sample_func: 渲染主题样本的函数
        prompt_menu_choice_func: 菜单选择函数
        colorize_func: 着色函数
    """
    while True:
        current_info = theme_info.get(current_theme, {"label": current_theme})
        header_lines = [
            "",
            colorize_func(
                f"当前主题: {current_info.get('label', current_theme)} ({current_theme})",
                "menu_text",
            ),
        ]
        if current_info.get("description"):
            header_lines.append(colorize_func(f"说明: {current_info['description']}", "menu_hint"))

        options: List[Dict[str, Any]] = []
        default_key = "1"
        for idx, key in enumerate(theme_order, start=1):
            info = theme_info.get(key, {"label": key})
            marker = "✓" if key == current_theme else " "
            label = info.get("label", key)
            extra_lines: List[str] = []
            if info.get("description"):
                extra_lines.append(colorize_func(f"     {info['description']}", "menu_hint"))
            extra_lines.append(render_sample_func(key))
            option = {
                "key": key,
                "display": str(idx),
                "label": f"[{marker}] {label} ({key})",
                "extra_lines": extra_lines,
            }
            options.append(option)
            if key == current_theme:
                default_key = key
        options.append({"key": "0", "label": "返回上级菜单"})

        choice = prompt_menu_choice_func(
            options,
            title="┌─ 终端主题与色彩 ─" + "─" * 18,
            header_lines=header_lines,
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key=default_key,
        )
        if choice in {"0", "__escape__"}:
            return

        selected: Optional[str] = None
        if choice in available_themes:
            selected = choice
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(theme_order):
                selected = theme_order[idx - 1]

        if not selected:
            print(colorize_func("输入无效，请重新选择。", "warning"))
            continue
        if selected == current_theme:
            print(colorize_func("当前已经是该主题。", "info"))
            continue
        if apply_theme_func(selected):
            info = theme_info.get(selected, {"label": selected})
            print(colorize_func(f"已切换到 {info.get('label', selected)} 主题。", "value_positive"))





def configure_signal_thresholds_interactive(
    momentum_lookback: int,
    momentum_threshold: float,
    trend_adx: float,
    trend_chop: float,
    trend_fast_span: int,
    trend_slow_span: int,
    set_momentum_lookback_func: Callable[[int], int],
    set_momentum_threshold_func: Callable[[float], float],
    set_trend_adx_func: Callable[[float], float],
    set_trend_chop_func: Callable[[float], float],
    set_trend_fast_span_func: Callable[[int], int],
    set_trend_slow_span_func: Callable[[int], int],
    colorize_func: Callable,
    prompt_input_func: Callable,
) -> None:
    """交互式配置信号阈值

    Args:
        momentum_lookback: 动量分位回溯天数
        momentum_threshold: 动量分位阈值
        trend_adx: 趋势ADX阈值
        trend_chop: 趋势Chop阈值
        trend_fast_span: EMA快线跨度
        trend_slow_span: EMA慢线跨度
        set_momentum_lookback_func: 设置动量回溯的函数
        set_momentum_threshold_func: 设置动量阈值的函数
        set_trend_adx_func: 设置ADX阈值的函数
        set_trend_chop_func: 设置Chop阈值的函数
        set_trend_fast_span_func: 设置快线跨度的函数
        set_trend_slow_span_func: 设置慢线跨度的函数
        colorize_func: 着色函数
        prompt_input_func: 输入提示函数
    """
    print("\n" + colorize_func("┌─ 动量与趋势阈值 ─" + "─" * 16, "divider"))
    print(colorize_func(
        f"动量分位回溯天数: {momentum_lookback} · 分位阈值: {momentum_threshold:.2f}",
        "menu_text",
    ))
    print(colorize_func(
        f"趋势一致条件: ADX>{trend_adx:.1f} · Chop<{trend_chop:.1f} · EMA{trend_fast_span}/EMA{trend_slow_span}",
        "menu_hint",
    ))

    def _update_int(prompt: str, setter, current_value: int) -> None:
        raw_local = prompt_input_func(colorize_func(prompt, "prompt")).strip()
        if not raw_local:
            return
        if not raw_local.isdigit():
            print(colorize_func("请输入正整数。", "warning"))
            return
        value_local = int(raw_local)
        updated_value = setter(value_local)
        print(colorize_func(f"已更新为 {updated_value}", "value_positive"))

    def _update_float(prompt: str, setter) -> None:
        raw_local = prompt_input_func(colorize_func(prompt, "prompt")).strip()
        if not raw_local:
            return
        try:
            value_local = float(raw_local)
        except ValueError:
            print(colorize_func("请输入数值。", "warning"))
            return
        updated_value = setter(value_local)
        print(colorize_func(f"已更新为 {updated_value:.2f}", "value_positive"))

    _update_int(
        f"动量分位回溯天数（当前 {momentum_lookback}）: ",
        set_momentum_lookback_func,
        momentum_lookback,
    )
    _update_float(
        f"动量分位阈值 0-0.99（当前 {momentum_threshold:.2f}）: ",
        set_momentum_threshold_func,
    )
    _update_float(
        f"Trend ADX 阈值（当前 {trend_adx:.1f}）: ",
        set_trend_adx_func,
    )
    _update_float(
        f"Trend Chop 阈值（当前 {trend_chop:.1f}）: ",
        set_trend_chop_func,
    )
    _update_int(
        f"EMA 快线跨度（当前 {trend_fast_span}）: ",
        set_trend_fast_span_func,
        trend_fast_span,
    )
    _update_int(
        f"EMA 慢线跨度（当前 {trend_slow_span}）: ",
        set_trend_slow_span_func,
        trend_slow_span,
    )
    print(colorize_func("阈值设置已更新。后续分析将应用新的判定条件。", "menu_hint"))
