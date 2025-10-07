"""分析业务逻辑模块扩展：分析编排"""


def run_analysis_and_build_outputs(
    params: dict,
    build_payload_func,
    render_text_report_func,
    default_settings: dict,
) -> dict:
    """
    运行分析并构建输出（payload + text report）。

    Args:
        params: 分析参数字典
        build_payload_func: 构建结果载荷的函数
        render_text_report_func: 渲染文本报告的函数
        default_settings: 默认设置字典（用于填充缺失参数）

    Returns:
        包含 result/config/momentum_config/preset/payload/report_text/title 的状态字典
    """
    from .analysis import build_configs_from_params, run_analysis_only

    # 合并默认参数
    params = dict(params)
    params.setdefault("presets", [])
    params.setdefault("stability_method", default_settings.get("stability_method"))
    params.setdefault("stability_window", default_settings.get("stability_window"))
    params.setdefault("stability_top_n", default_settings.get("stability_top_n"))
    params.setdefault("stability_weight", default_settings.get("stability_weight"))
    params.setdefault("momentum_percentile_lookback", default_settings.get("momentum_percentile_lookback"))
    params.setdefault("momentum_significance_threshold", default_settings.get("momentum_significance_threshold"))
    params.setdefault("trend_consistency_adx_threshold", default_settings.get("trend_consistency_adx_threshold"))
    params.setdefault("trend_consistency_chop_threshold", default_settings.get("trend_consistency_chop_threshold"))
    params.setdefault("trend_consistency_fast_span", default_settings.get("trend_consistency_fast_span"))
    params.setdefault("trend_consistency_slow_span", default_settings.get("trend_consistency_slow_span"))

    preset = params.get("analysis_preset")
    lang = params.get("lang", "zh")

    # 构建配置并运行分析
    config, momentum_config = build_configs_from_params(params)
    result = run_analysis_only(config)

    # 构建输出
    payload = build_payload_func(result, config, momentum_config, preset, lang)
    report_text = render_text_report_func(result, config, momentum_config, preset, lang)

    # 确定分析标签
    analysis_label = params.get("analysis_name")
    if not analysis_label:
        bundle_context = params.get("_bundle_context")
        if preset:
            analysis_label = f"{preset.name} [{preset.key}]"
        elif bundle_context:
            analysis_label = bundle_context
        else:
            analysis_label = "自定义分析"
    params.setdefault("analysis_name", analysis_label)

    return {
        "result": result,
        "config": config,
        "momentum_config": momentum_config,
        "preset": preset,
        "params": params,
        "payload": payload,
        "report_text": report_text,
        "title": analysis_label,
    }
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




import datetime as dt
from typing import Any, Callable, Dict, List, Optional


def run_quick_analysis(
    analysis_presets: Dict[str, Any],
    code_presets: Dict[str, Any],
    dedup_codes_func: Callable[[List[str]], List[str]],
    run_analysis_func: Callable[[Dict[str, Any], bool, str, bool], Optional[Dict]],
    colorize_func: Callable,
) -> Optional[Dict]:
    """执行快速分析

    Args:
        analysis_presets: 分析预设字典
        code_presets: 代码预设字典
        dedup_codes_func: 去重代码函数
        run_analysis_func: 运行分析函数
        colorize_func: 着色函数

    Returns:
        分析状态字典或None
    """
    preset = analysis_presets.get("slow-core")
    if not preset:
        print(colorize_func("未找到 slow-core 分析预设，无法执行快速分析。", "warning"))
        return None

    core_pool = code_presets.get("core")
    satellite_pool = code_presets.get("satellite")
    if not core_pool and not satellite_pool:
        print(colorize_func("未定义核心或卫星券池，无法执行快速分析。", "warning"))
        return None

    combined_codes: List[str] = []
    preset_tags: List[str] = []
    if core_pool:
        combined_codes.extend(core_pool.tickers)
        preset_tags.append("core")
    if satellite_pool:
        combined_codes.extend(satellite_pool.tickers)
        preset_tags.append("satellite")

    today = dt.date.today()
    lookback_days = max(365 * 5, max(preset.momentum_windows) * 4, 750)
    start_date = (today - dt.timedelta(days=lookback_days)).isoformat()

    params = {
        "codes": dedup_codes_func(combined_codes),
        "start": start_date,
        "end": today.isoformat(),
        "windows": tuple(preset.momentum_windows),
        "corr_window": preset.corr_window,
        "make_plots": False,
        "export_csv": False,
        "chop_window": preset.chop_window,
        "trend_window": preset.trend_window,
        "rank_lookback": preset.rank_lookback,
        "output_dir": "results",
        "weights": (
            tuple(preset.momentum_weights)
            if preset.momentum_weights is not None
            else None
        ),
        "skip_windows": (
            tuple(preset.momentum_skip_windows)
            if preset.momentum_skip_windows is not None
            else None
        ),
        "analysis_preset": preset,
        "presets": preset_tags,
        "lang": "zh",
        "analysis_name": f"快速分析 · {preset.name}",
    }

    return run_analysis_func(
        params,
        post_actions=False,
        bundle_context="快速分析",
        bundle_interactive=True,
    )
