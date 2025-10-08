from __future__ import annotations
from typing import Optional, List

from ..utils.colors import colorize
from ..analysis_presets import AnalysisPreset
from ..ui.input import prompt_text
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
    _obtain_backtest_context,
    _get_core_satellite_codes,
    _format_label,
    _render_backtest_table,
)


def _show_best_strategy_guide():
    """显示最优策略分析与调仓指南"""
    import subprocess
    import sys
    from pathlib import Path

    guide_path = Path(__file__).parent.parent.parent / "docs" / "BEST_STRATEGY_GUIDE.md"

    if not guide_path.exists():
        print(colorize("❌ 指南文件不存在，请检查安装。", "danger"))
        _wait_for_ack()
        return

    # 尝试用less/more打开，如果失败则直接打印
    try:
        if sys.platform != "win32":
            subprocess.run(["less", str(guide_path)])
        else:
            subprocess.run(["more", str(guide_path)], shell=True)
    except Exception:
        # 回退：直接打印内容
        with open(guide_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(content)
        _wait_for_ack()


def _run_core_satellite_enhanced(current_state: dict):
    """运行核心-卫星增强回测（含止损/再平衡/防御）"""

    print(colorize("\n=== 核心-卫星增强回测配置 ===", "heading"))
    print(colorize("包含止损、再平衡、防御机制的完整回测", "menu_hint"))
    print()

    # 核心配置
    print(colorize("📊 核心配置:", "heading"))
    try:
        core_alloc = float(prompt_text("核心仓配置（默认0.6=60%）", "0.6") or 0.6)
    except Exception:
        core_alloc = 0.6

    try:
        sat_alloc = float(prompt_text("卫星仓配置（默认0.4=40%）", "0.4") or 0.4)
    except Exception:
        sat_alloc = 0.4

    try:
        top_n = int(prompt_text("卫星仓持仓数（默认2）", "2") or 2)
    except Exception:
        top_n = 2

    # 止损配置
    print(colorize("\n🛡️  止损配置:", "heading"))
    enable_stop_loss = prompt_text("启用止损？(y/n，默认y)", "y").strip().lower() != "n"

    if enable_stop_loss:
        try:
            stop_loss_pct = float(prompt_text("止损阈值（从最高点回撤%，默认15）", "15") or 15) / 100
        except Exception:
            stop_loss_pct = 0.15
    else:
        stop_loss_pct = 0.15

    # 再平衡配置
    print(colorize("\n⚖️  再平衡配置:", "heading"))
    enable_rebalance = prompt_text("启用再平衡？(y/n，默认y)", "y").strip().lower() != "n"

    if enable_rebalance:
        try:
            rebalance_threshold = float(prompt_text("再平衡阈值（偏离%，默认5）", "5") or 5) / 100
        except Exception:
            rebalance_threshold = 0.05
    else:
        rebalance_threshold = 0.05

    # 防御配置
    print(colorize("\n🛡️  防御配置:", "heading"))
    enable_defense = prompt_text("启用防御机制？(y/n，默认y)", "y").strip().lower() != "n"

    if enable_defense:
        try:
            defense_ma = int(prompt_text("防御MA窗口（默认200）", "200") or 200)
        except Exception:
            defense_ma = 200

        try:
            defense_sat_alloc = float(prompt_text("防御时卫星仓配置（默认0.2=20%）", "0.2") or 0.2)
        except Exception:
            defense_sat_alloc = 0.2
    else:
        defense_ma = 200
        defense_sat_alloc = 0.2

    print(colorize("\n正在运行增强回测，请稍候...", "accent"))

    from ..business.backtest import run_core_satellite_enhanced_backtest

    run_core_satellite_enhanced_backtest(
        obtain_context_func=_obtain_backtest_context,
        get_core_satellite_codes_func=_get_core_satellite_codes,
        format_label_func=_format_label,
        colorize_func=colorize,
        render_table_func=_render_backtest_table,
        wait_for_ack_func=_wait_for_ack,
        last_state=current_state,
        core_allocation=core_alloc,
        satellite_allocation=sat_alloc,
        top_n=top_n,
        enable_stop_loss=enable_stop_loss,
        stop_loss_pct=stop_loss_pct,
        enable_rebalance=enable_rebalance,
        rebalance_threshold=rebalance_threshold,
        enable_defense=enable_defense,
        defense_ma_window=defense_ma,
        defense_satellite_allocation=defense_sat_alloc,
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
            {"key": "7", "label": "自定义核心-卫星回测（可配置防守/腿数）"},
            {"key": "10", "label": "🔬 核心-卫星增强回测（含止损/再平衡/防御）"},
            {"key": "3", "label": "动量回溯 / 图表"},
            {"key": "4", "label": "导出策略脚本（当前参数）"},
            {"key": "5", "label": "运行策略回测（慢腿/快腿/宏观驱动）"},
            {"key": "6", "label": "刷新数据（运行快速分析）"},
            {"key": "8", "label": "实验性：科学动量回测"},
            {"key": "9", "label": "📊 最优策略分析与调仓指南"},
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
        if choice == "7":
            from ..cli import _run_core_satellite_custom_backtest as _cli_core_sat_custom
            _cli_core_sat_custom(current_state)
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
        if choice == "8":
            from ..cli import _run_experimental_scientific_momentum as _cli_exp
            _cli_exp(current_state)
            continue
        if choice == "9":
            _show_best_strategy_guide()
            continue
        if choice == "10":
            _run_core_satellite_enhanced(current_state)
            continue
        if choice in {"0", "__escape__"}:
            return current_state
        print(colorize("无效指令，请重新输入。", "warning"))

