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

