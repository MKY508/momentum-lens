"""
分析流程编排（不含渲染）

- 将参数组装与 AnalysisConfig 构建放在业务层，CLI 仅负责交互与显示
- 运行 analyze 并返回结果对象；报告渲染/载荷拼装仍由 CLI 处理
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Tuple

from ..analysis import AnalysisConfig, analyze
from ..indicators import MomentumConfig


def build_configs_from_params(params: dict) -> Tuple[AnalysisConfig, MomentumConfig]:
    momentum_config = MomentumConfig(
        windows=tuple(params["windows"]),
        weights=params.get("weights"),
        skip_windows=params.get("skip_windows"),
    )
    config = AnalysisConfig(
        start_date=params["start"],
        end_date=params["end"],
        etfs=params["codes"],
        exclude=(),
        momentum=momentum_config,
        chop_window=params["chop_window"],
        trend_window=params["trend_window"],
        corr_window=params["corr_window"],
        rank_change_lookback=params["rank_lookback"],
        output_dir=Path(params["output_dir"]),
        make_plots=params["make_plots"],
        momentum_percentile_lookback=params.get("momentum_percentile_lookback"),
        momentum_significance_threshold=params.get("momentum_significance_threshold"),
        trend_consistency_adx_threshold=params.get("trend_consistency_adx_threshold"),
        trend_consistency_chop_threshold=params.get("trend_consistency_chop_threshold"),
        trend_consistency_fast_span=params.get("trend_consistency_fast_span"),
        trend_consistency_slow_span=params.get("trend_consistency_slow_span"),
        stability_method=params.get("stability_method"),
        stability_window=params.get("stability_window"),
        stability_top_n=params.get("stability_top_n"),
        stability_weight=params.get("stability_weight"),
    )
    return config, momentum_config


def run_analysis_only(config: AnalysisConfig):
    """仅运行分析，返回结果对象。"""
    return analyze(config)

