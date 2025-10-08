"""分析预设显示和管理"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.colors import colorize

if TYPE_CHECKING:
    from ..analysis_presets import AnalysisPreset


def print_analysis_presets(presets: dict, status_label_func=None) -> None:
    """打印分析预设列表
    
    Args:
        presets: 预设字典
        status_label_func: 状态标签函数
    """
    print(colorize("可用分析预设：", "heading"))
    for idx, preset in enumerate(presets.values(), start=1):
        notes = f"（{preset.notes}）" if preset.notes else ""
        title = colorize(
            f" {idx:>2}. {preset.name} [{preset.key}] - {preset.description}{notes}",
            "menu_text",
        )
        win_str = ",".join(str(w) for w in preset.momentum_windows)
        weight_str = (
            ",".join(f"{w:.2f}" for w in preset.momentum_weights)
            if preset.momentum_weights
            else "等权"
        )
        skip_str = (
            ",".join(str(s) for s in preset.momentum_skip_windows)
            if preset.momentum_skip_windows
            else "0"
        )
        detail = colorize(
            "    "
            + f"窗口 {win_str} | 剔除 {skip_str} | 权重 {weight_str} | Corr {preset.corr_window} | "
            + f"Chop {preset.chop_window} | 趋势 {preset.trend_window} | 排名回溯 {preset.rank_lookback}",
            "menu_hint",
        )
        print(title)
        print(detail)


def print_analysis_preset_details(key: str, preset, status_label_func=None) -> None:
    """打印分析预设详情
    
    Args:
        key: 预设键
        preset: 预设对象
        status_label_func: 状态标签函数
    """
    win_str = ",".join(str(w) for w in preset.momentum_windows)
    weight_str = (
        ",".join(f"{w:.2f}" for w in preset.momentum_weights)
        if preset.momentum_weights
        else "等权"
    )
    skip_str = (
        ",".join(str(s) for s in preset.momentum_skip_windows)
        if preset.momentum_skip_windows
        else "0"
    )
    notes = preset.notes or "-"
    
    # 使用状态标签函数（如果提供）
    status = status_label_func(key) if status_label_func else ""
    status_text = f"（{status}）" if status else ""
    
    print(colorize(f"预设：{preset.name} [{key}]{status_text}", "heading"))
    print(colorize(f"  描述: {preset.description}", "menu_text"))
    print(
        colorize(
            f"  窗口: {win_str} | 剔除: {skip_str} | 权重: {weight_str} | Corr {preset.corr_window} | "
            f"Chop {preset.chop_window} | 趋势 {preset.trend_window} | 回溯 {preset.rank_lookback}",
            "menu_hint",
        )
    )
    print(colorize(f"  备注: {notes}", "menu_hint"))

