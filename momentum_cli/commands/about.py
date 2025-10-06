"""
关于页命令模块
"""
from __future__ import annotations

from . import typing as _typing  # noqa: F401  # 预留给后续类型导入
from ..utils.colors import colorize


def show_about(app_name: str, app_version: str, repo_url: str) -> None:
    print("")
    print(colorize(f"{app_name} {app_version}", "heading"))
    print(colorize("面向量化复盘的 ETF 动量分析与回测工具。", "menu_text"))
    print(colorize("主要特性:", "menu_hint"))
    for bullet in (
        "快速分析核心/卫星券池并给出动量预警",
        "交互式 Plotly 图表、策略导出与多区间回测",
        "可配置模板、阈值与配色，适合定制流程",
    ):
        print(colorize(f" - {bullet}", "menu_text"))
    print(colorize("项目主页:", "menu_hint"))
    print(colorize(f" {repo_url}", "menu_text"))
    print(colorize("作者: mky508", "menu_hint"))
    print("")

