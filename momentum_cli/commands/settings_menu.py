"""设置与工具菜单命令"""
from __future__ import annotations

from ..utils.colors import colorize
from ..cli import (
    _show_preset_settings_menu,
    _show_analysis_preset_settings_menu,
    _show_template_settings_menu,
    _configure_cli_theme,
    _configure_plot_style,
    _configure_correlation_threshold,
    _configure_signal_thresholds,
    _configure_stability_settings,
    _install_optional_dependencies,
    _update_data_bundle,
    _cleanup_generated_artifacts,
    _prompt_menu_choice,
)


def run() -> None:
    """设置与工具菜单"""
    while True:
        options = [
            {"key": "1", "label": "券池预设管理"},
            {"key": "2", "label": "分析预设管理"},
            {"key": "3", "label": "模板设置"},
            {"key": "4", "label": "终端主题与色彩"},
            {"key": "5", "label": "配置图表样式"},
            {"key": "6", "label": "设置相关矩阵阈值"},
            {"key": "7", "label": "动量/趋势阈值设置"},
            {"key": "8", "label": "稳定度参数设置"},
            {"key": "9", "label": "安装/修复依赖（Plotly 等）"},
            {"key": "10", "label": "下载/更新 RQAlpha 数据包"},
            {"key": "11", "label": "清理生成文件"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 设置与工具 ─" + "─" * 20,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
        )
        if choice == "1":
            _show_preset_settings_menu()
            continue
        if choice == "2":
            _show_analysis_preset_settings_menu()
            continue
        if choice == "3":
            _show_template_settings_menu()
            continue
        if choice == "4":
            _configure_cli_theme()
            continue
        if choice == "5":
            _configure_plot_style()
            continue
        if choice == "6":
            _configure_correlation_threshold()
            continue
        if choice == "7":
            _configure_signal_thresholds()
            continue
        if choice == "8":
            _configure_stability_settings()
            continue
        if choice == "9":
            _install_optional_dependencies()
            continue
        if choice == "10":
            _update_data_bundle()
            continue
        if choice == "11":
            _cleanup_generated_artifacts()
            continue
        if choice in {"0", "__escape__"}:
            return
        print(colorize("无效指令，请重新输入。", "warning"))

