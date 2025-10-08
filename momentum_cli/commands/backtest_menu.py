from __future__ import annotations
from typing import Optional, List

from ..utils.colors import colorize
from ..analysis_presets import AnalysisPreset
from ..cli import (
    _maybe_prompt_bundle_refresh,
    _ensure_analysis_state,
    _interactive_backtest,
    _run_core_satellite_multi_backtest,
    _interactive_generate_interactive_chart,
    _interactive_export_strategy,
    _run_quick_analysis,
    _wait_for_ack,
    _prompt_menu_choice,
)


def run(last_state: Optional[dict]) -> Optional[dict]:
    """Backtest/tools menu dispatcher.
    Returns updated state or original state.
    """
    _maybe_prompt_bundle_refresh(True, "回测工具")
    current_state = _ensure_analysis_state(last_state, context="回测工具")
    if not current_state:
        return last_state
    while True:
        options = [
            {"key": "1", "label": "简易动量回测（当前参数）"},
            {"key": "2", "label": "核心-卫星多区间回测"},
            {"key": "3", "label": "动量回溯 / 图表"},
            {"key": "4", "label": "导出策略脚本（当前参数）"},
            {"key": "5", "label": "运行策略回测（慢腿/快腿/宏观驱动）"},
            {"key": "6", "label": "刷新数据（运行快速分析）"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 回测与动量工具 ─" + "─" * 14,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
        )
        if choice == "1":
            _interactive_backtest(current_state)
            continue
        if choice == "2":
            _run_core_satellite_multi_backtest(current_state)
            continue
        if choice == "3":
            # 复用 CLI 内部菜单
            from ..cli import _show_history_menu as _cli_history
            new_state = _cli_history(current_state)
            if new_state:
                current_state = new_state
            continue
        if choice == "4":
            _interactive_export_strategy(current_state)
            continue
        if choice == "5":
            from ..cli import _run_strategy_backtest_menu as _cli_strategy
            _cli_strategy()
            continue
        if choice == "6":
            refreshed = _run_quick_analysis(post_actions=False)
            if refreshed:
                current_state = refreshed
                print(colorize("已使用最新数据完成快速分析。", "value_positive"))
            else:
                print(colorize("刷新失败，请稍后再试或运行自定义分析。", "danger"))
            _wait_for_ack()
            continue
        if choice in {"0", "__escape__"}:
            return current_state
        print(colorize("无效指令，请重新输入。", "warning"))

