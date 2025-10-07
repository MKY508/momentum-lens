from __future__ import annotations

import argparse
import datetime as dt
import functools
import importlib
import io
import json
import os
import re
import select
import subprocess
import sys
import shutil
import textwrap
import time
import webbrowser
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - Windows fallback
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

try:  # pragma: no cover - optional Windows support
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None  # type: ignore[assignment]

import numpy as np
import pandas as pd

from .analysis import AnalysisConfig, analyze
from .analysis_presets import (
    ANALYSIS_PRESETS,
    AnalysisPreset,
    DEFAULT_ANALYSIS_PRESETS,
    delete_analysis_preset,
    has_custom_analysis_override,
    reset_analysis_preset,
    upsert_analysis_preset,
)
from .indicators import MomentumConfig
from .metadata import get_label
from .presets import (
    PRESETS,
    DEFAULT_PRESETS,
    delete_preset,
    has_custom_override,
    reset_preset,
    upsert_preset,
)
from .utils.display import display_width as _display_width
from .utils.display import pad_display as _pad_display
from .utils.display import strip_ansi as _strip_ansi
from .utils.parsers import extract_float as _extract_float
from .utils.parsers import parse_bundle_version as _parse_bundle_version
from .utils.parsers import try_parse_datetime as _try_parse_datetime
# 导入颜色工具（渐进式迁移）
from .utils.colors import (
    colorize as _utils_colorize,
    set_color_enabled as _utils_set_color_enabled,
    apply_theme as _utils_apply_theme,
    get_current_theme as _utils_get_current_theme,
)
# 导入UI工具（渐进式迁移）
from .ui import (
    prompt_menu_choice as _ui_prompt_menu_choice,
    supports_interactive_menu as _ui_supports_interactive_menu,
    format_menu_item as _ui_format_menu_item,
    menu_hint as _ui_menu_hint,
    prompt_yes_no as _ui_prompt_yes_no,
    prompt_text as _ui_prompt_text,
    prompt_positive_int as _ui_prompt_positive_int,
    prompt_optional_date as _ui_prompt_optional_date,
)
# 导入业务逻辑工具（渐进式迁移）
from .business import (
    load_template_store as _business_load_template_store,
    write_template_store as _business_write_template_store,
    get_template as _business_get_template,
    save_template as _business_save_template,
    delete_template as _business_delete_template,
    get_builtin_template_store as _business_get_builtin_template_store,
    template_to_params as _business_template_to_params,
    render_text_report as _business_render_text_report,
    render_markdown_report as _business_render_markdown_report,
)
from .config.settings import (
    DEFAULT_SETTINGS as _DEFAULT_SETTINGS,
    SETTINGS_STORE_PATH,
    load_cli_settings as _load_cli_settings,
    save_cli_settings as _save_cli_settings,
    update_setting as _update_setting,
)
from .config.validators import (
    validate_corr_threshold as _validate_corr_threshold,
    validate_float_range_setting as _validate_float_range_setting,
    validate_positive_int_setting as _validate_positive_int_setting,
    validate_ratio_setting as _validate_ratio_setting,
)
from .config.bundle import (
    BUNDLE_ROOT as _BUNDLE_ROOT,
    BUNDLE_VERSION_FILE as _BUNDLE_VERSION_FILE,
    bundle_status as _bundle_status,
    load_bundle_metadata as _load_bundle_metadata,
)

APP_NAME = "Momentum Lens"
APP_VERSION = "0.9.0"
REPO_URL = "https://github.com/MKY508/momentum-lens"
LAUNCHER_BASENAME = "momentum_lens.sh"
LAUNCHER_COMMAND = f"./{LAUNCHER_BASENAME}"

_KEYLOG_ENABLED = bool(os.environ.get("MOMENTUM_KEY_DEBUG"))
_KEYLOG_PATH = Path(
    os.environ.get("MOMENTUM_KEY_DEBUG_FILE", str(Path.home() / ".momentum_keylog"))
)


# 调试日志函数已移至 utils.debug 模块
from .utils.debug import log_key_event as _log_key_event, log_key_result as _log_key_result


# 主题定义已移至 utils/colors.py
# 为了兼容性，从utils.colors导入
from .utils.colors import CLI_THEMES as _CLI_THEMES

_TERMINAL_SIZE_CACHE = {"columns": 120, "timestamp": 0.0}

_MOMENTUM_ALERT_TOP = 6
_MOMENTUM_ALERT_WEEKS = 3
_MOMENTUM_ALERT_MIN_DROP = 2
_MAX_CORRELATION_ALERTS = 15


# _load_cli_settings, _save_cli_settings, _update_setting 已移至 config.settings
_LOADED_SETTINGS = _load_cli_settings()
_SETTINGS = {**_DEFAULT_SETTINGS, **_LOADED_SETTINGS}


_settings_dirty = False
_STYLE_THEME = _SETTINGS.get("cli_theme", _DEFAULT_SETTINGS["cli_theme"])
if _STYLE_THEME not in _CLI_THEMES:
    _STYLE_THEME = _DEFAULT_SETTINGS["cli_theme"]
    _SETTINGS["cli_theme"] = _STYLE_THEME
    _settings_dirty = True
_STYLE_CODES = dict(_CLI_THEMES[_STYLE_THEME])

# 同步主题到utils.colors模块
_utils_apply_theme(_STYLE_THEME, persist=False)

_PLOT_TEMPLATE = str(_SETTINGS.get("plot_template", _DEFAULT_SETTINGS["plot_template"]))
if not isinstance(_PLOT_TEMPLATE, str):
    _PLOT_TEMPLATE = _DEFAULT_SETTINGS["plot_template"]
    _SETTINGS["plot_template"] = _PLOT_TEMPLATE
    _settings_dirty = True
try:
    _PLOT_LINE_WIDTH = float(
        _SETTINGS.get("plot_line_width", _DEFAULT_SETTINGS["plot_line_width"])
    )
    if _PLOT_LINE_WIDTH <= 0:
        raise ValueError
except (TypeError, ValueError):
    _PLOT_LINE_WIDTH = _DEFAULT_SETTINGS["plot_line_width"]
    _SETTINGS["plot_line_width"] = _PLOT_LINE_WIDTH
    _settings_dirty = True


# _validate_* 函数已移至 config.validators


_CORRELATION_ALERT_THRESHOLD = _validate_corr_threshold(
    _SETTINGS.get("correlation_alert_threshold"), _DEFAULT_SETTINGS["correlation_alert_threshold"]
)
if _CORRELATION_ALERT_THRESHOLD != _SETTINGS.get("correlation_alert_threshold"):
    _SETTINGS["correlation_alert_threshold"] = _CORRELATION_ALERT_THRESHOLD
    _settings_dirty = True

_MOMENTUM_SIGNIFICANCE_THRESHOLD = _validate_ratio_setting(
    _SETTINGS.get("momentum_significance_threshold"),
    _DEFAULT_SETTINGS["momentum_significance_threshold"],
    min_value=0.0,
    max_value=0.99,
)
if _MOMENTUM_SIGNIFICANCE_THRESHOLD != _SETTINGS.get("momentum_significance_threshold"):
    _SETTINGS["momentum_significance_threshold"] = _MOMENTUM_SIGNIFICANCE_THRESHOLD
    _settings_dirty = True

_MOMENTUM_SIGNIFICANCE_LOOKBACK = _validate_positive_int_setting(
    _SETTINGS.get("momentum_significance_lookback"),
    _DEFAULT_SETTINGS["momentum_significance_lookback"],
    minimum=120,
    maximum=2000,
)
if _MOMENTUM_SIGNIFICANCE_LOOKBACK != _SETTINGS.get("momentum_significance_lookback"):
    _SETTINGS["momentum_significance_lookback"] = _MOMENTUM_SIGNIFICANCE_LOOKBACK
    _settings_dirty = True

_TREND_CONSISTENCY_ADX = _validate_float_range_setting(
    _SETTINGS.get("trend_consistency_adx"),
    _DEFAULT_SETTINGS["trend_consistency_adx"],
    minimum=0.0,
    maximum=100.0,
)
if _TREND_CONSISTENCY_ADX != _SETTINGS.get("trend_consistency_adx"):
    _SETTINGS["trend_consistency_adx"] = _TREND_CONSISTENCY_ADX
    _settings_dirty = True

_TREND_CONSISTENCY_CHOP = _validate_float_range_setting(
    _SETTINGS.get("trend_consistency_chop"),
    _DEFAULT_SETTINGS["trend_consistency_chop"],
    minimum=0.0,
    maximum=100.0,
)
if _TREND_CONSISTENCY_CHOP != _SETTINGS.get("trend_consistency_chop"):
    _SETTINGS["trend_consistency_chop"] = _TREND_CONSISTENCY_CHOP
    _settings_dirty = True

_TREND_FAST_SPAN = _validate_positive_int_setting(
    _SETTINGS.get("trend_consistency_fast_span"),
    _DEFAULT_SETTINGS["trend_consistency_fast_span"],
    minimum=2,
    maximum=250,
)
if _TREND_FAST_SPAN != _SETTINGS.get("trend_consistency_fast_span"):
    _SETTINGS["trend_consistency_fast_span"] = _TREND_FAST_SPAN
    _settings_dirty = True

_TREND_SLOW_SPAN = _validate_positive_int_setting(
    _SETTINGS.get("trend_consistency_slow_span"),
    _DEFAULT_SETTINGS["trend_consistency_slow_span"],
    minimum=5,
    maximum=500,
)
if _TREND_SLOW_SPAN != _SETTINGS.get("trend_consistency_slow_span"):
    _SETTINGS["trend_consistency_slow_span"] = _TREND_SLOW_SPAN
    _settings_dirty = True

if _TREND_SLOW_SPAN <= _TREND_FAST_SPAN:
    _TREND_SLOW_SPAN = min(500, _TREND_FAST_SPAN + 5)
    _SETTINGS["trend_consistency_slow_span"] = _TREND_SLOW_SPAN
    _settings_dirty = True

_STABILITY_METHOD = str(
    _SETTINGS.get("stability_method", _DEFAULT_SETTINGS["stability_method"])
).strip().lower()
if _STABILITY_METHOD not in {"presence_ratio", "kendall"}:
    _STABILITY_METHOD = _DEFAULT_SETTINGS["stability_method"]
    _SETTINGS["stability_method"] = _STABILITY_METHOD
    _settings_dirty = True

_STABILITY_WINDOW = _validate_positive_int_setting(
    _SETTINGS.get("stability_window"),
    _DEFAULT_SETTINGS["stability_window"],
    minimum=2,
    maximum=250,
)
if _STABILITY_WINDOW != _SETTINGS.get("stability_window"):
    _SETTINGS["stability_window"] = _STABILITY_WINDOW
    _settings_dirty = True

_STABILITY_TOP_N = _validate_positive_int_setting(
    _SETTINGS.get("stability_top_n"),
    _DEFAULT_SETTINGS["stability_top_n"],
    minimum=1,
    maximum=100,
)
if _STABILITY_TOP_N != _SETTINGS.get("stability_top_n"):
    _SETTINGS["stability_top_n"] = _STABILITY_TOP_N
    _settings_dirty = True

_STABILITY_WEIGHT = _validate_ratio_setting(
    _SETTINGS.get("stability_weight"),
    _DEFAULT_SETTINGS["stability_weight"],
    min_value=0.0,
    max_value=1.0,
)
if _STABILITY_WEIGHT != _SETTINGS.get("stability_weight"):
    _SETTINGS["stability_weight"] = _STABILITY_WEIGHT
    _settings_dirty = True

if _settings_dirty:
    _save_cli_settings(_SETTINGS)


def _build_builtin_template(
    preset_keys: Sequence[str],
    analysis_key: str,
    *,
    start: str = "2018-01-01",
    end: Optional[str] = None,
) -> Optional[dict]:
    preset = ANALYSIS_PRESETS.get(analysis_key)
    if not preset:
        return None
    windows = [int(win) for win in preset.momentum_windows]
    weights = (
        [float(weight) for weight in preset.momentum_weights]
        if preset.momentum_weights is not None
        else None
    )
    skip_windows = (
        [int(value) for value in preset.momentum_skip_windows]
        if preset.momentum_skip_windows is not None
        else None
    )
    return {
        "etfs": [],
        "exclude": [],
        "presets": list(preset_keys),
        "start": start,
        "end": end,
        "momentum_windows": windows,
        "momentum_weights": weights,
        "momentum_skip_windows": skip_windows,
        "corr_window": preset.corr_window,
        "chop_window": preset.chop_window,
        "trend_window": preset.trend_window,
        "rank_lookback": preset.rank_lookback,
        "make_plots": True,
        "export_csv": False,
        "output_dir": "results",
        "analysis_preset": analysis_key,
        "stability_method": _STABILITY_METHOD,
        "stability_window": _STABILITY_WINDOW,
        "stability_top_n": _STABILITY_TOP_N,
        "stability_weight": _STABILITY_WEIGHT,
    }


_BUILTIN_TEMPLATE_DEFINITIONS: Sequence[tuple[str, Sequence[str], str]] = (
    ("core-slow-core", ("core",), "slow-core"),
    ("core-satellite-dual", ("core", "satellite"), "blend-dual"),
    ("longwave-12m1m", ("core", "satellite"), "twelve-minus-one"),
    ("fast-rotation", ("satellite",), "fast-rotation"),
)


def _builtin_template_store() -> Dict[str, dict]:
    """获取内置模板存储（兼容层）"""
    return _business_get_builtin_template_store()


TEMPLATE_STORE_PATH = Path(__file__).resolve().parent / "templates.json"
MAX_SERIES_EXPORT = 200


_COLOR_ENABLED = sys.stdout.isatty()
# 同步颜色状态到utils.colors模块
_utils_set_color_enabled(_COLOR_ENABLED)
_INTERACTIVE_MODE = False
_LAST_BUNDLE_REFRESH: dt.datetime | None = None
_LAST_BACKTEST_CONTEXT: dict | None = None
# 报告历史改由 business.history 管理

# Bundle 相关已移至 config.bundle
_BUNDLE_STATUS_CACHE: dict | None = None
_BUNDLE_UPDATE_PROMPTED = False
_BUNDLE_WARNING_EMITTED = False


def _set_color_enabled(flag: bool) -> None:
    global _COLOR_ENABLED
    _COLOR_ENABLED = bool(flag)


def _maybe_prompt_bundle_refresh(interactive: bool, reason: str, *, force: bool = False) -> None:
    global _BUNDLE_UPDATE_PROMPTED, _BUNDLE_WARNING_EMITTED, _BUNDLE_STATUS_CACHE

    # 初始化缓存如果为None
    if _BUNDLE_STATUS_CACHE is None:
        _BUNDLE_STATUS_CACHE = {}

    status = _bundle_status(cache=_BUNDLE_STATUS_CACHE)
    state = status.get("state")
    if state == "fresh" and not force:
        return
    if interactive:
        if state == "fresh" and not force:
            return
        if state == "missing":
            message = "检测到本地 RQAlpha 数据包缺失，分析前需先完成下载。"
            print(colorize(message, "warning"))
            if _prompt_yes_no("是否立即下载最新数据包？", True):
                _update_data_bundle()
                _BUNDLE_STATUS_CACHE = None
                _BUNDLE_UPDATE_PROMPTED = False
            return
        if not force and _BUNDLE_UPDATE_PROMPTED:
            return
        version_display = status.get("version") or status.get("version_raw") or "未知版本"
        prompt_lines = [
            f"分析场景【{reason}】检测到 bundle 版本 {version_display} 可能已过期。",
        ]
        months_behind = status.get("months_behind")
        if isinstance(months_behind, int) and months_behind > 0:
            prompt_lines.append(f"当前版本滞后 {months_behind} 个月。")
        elif status.get("updated_at") is None and status.get("has_files"):
            prompt_lines.append("检测到本地缺少版本记录，建议更新以确保使用最新数据。")
        days_since = status.get("days_since_update")
        if isinstance(days_since, int) and days_since > 14:
            prompt_lines.append(f"距离上次更新已有 {days_since} 天。")
        prompt_text = "".join(prompt_lines) + " 是否立即更新？"
        if _prompt_yes_no(prompt_text, True):
            _update_data_bundle()
            _BUNDLE_STATUS_CACHE = None
            _BUNDLE_UPDATE_PROMPTED = False
        else:
            _BUNDLE_UPDATE_PROMPTED = True
        return
    # non-interactive
    if _BUNDLE_WARNING_EMITTED and not force:
        return
    if state in {"stale", "missing"}:
        version_display = status.get("version") or status.get("version_raw") or "未知版本"
        print(
            colorize(
                f"提示：检测到 RQAlpha 数据包 {version_display} 可能过期，建议运行 {LAUNCHER_COMMAND} bundle-update 以获取最新数据。",
                "warning",
            )
        )
        _BUNDLE_WARNING_EMITTED = True


def _set_correlation_alert_threshold(value: float, *, persist: bool = True) -> float:
    global _CORRELATION_ALERT_THRESHOLD
    numeric = _validate_corr_threshold(value)
    _CORRELATION_ALERT_THRESHOLD = numeric
    if persist:
        _update_setting(_SETTINGS,_SETTINGS, "correlation_alert_threshold", numeric)
    return numeric


def _set_momentum_significance_threshold(value: float, *, persist: bool = True) -> float:
    global _MOMENTUM_SIGNIFICANCE_THRESHOLD
    numeric = _validate_ratio_setting(
        value,
        _DEFAULT_SETTINGS["momentum_significance_threshold"],
        min_value=0.0,
        max_value=0.99,
    )
    _MOMENTUM_SIGNIFICANCE_THRESHOLD = numeric
    if persist:
        _update_setting(_SETTINGS,"momentum_significance_threshold", numeric)
    return numeric


def _set_momentum_significance_lookback(value: int, *, persist: bool = True) -> int:
    global _MOMENTUM_SIGNIFICANCE_LOOKBACK
    numeric = _validate_positive_int_setting(
        value,
        _DEFAULT_SETTINGS["momentum_significance_lookback"],
        minimum=120,
        maximum=2000,
    )
    _MOMENTUM_SIGNIFICANCE_LOOKBACK = numeric
    if persist:
        _update_setting(_SETTINGS,"momentum_significance_lookback", numeric)
    return numeric


def _set_trend_consistency_adx(value: float, *, persist: bool = True) -> float:
    global _TREND_CONSISTENCY_ADX
    numeric = _validate_float_range_setting(
        value,
        _DEFAULT_SETTINGS["trend_consistency_adx"],
        minimum=0.0,
        maximum=100.0,
    )
    _TREND_CONSISTENCY_ADX = numeric
    if persist:
        _update_setting(_SETTINGS,"trend_consistency_adx", numeric)
    return numeric


def _set_trend_consistency_chop(value: float, *, persist: bool = True) -> float:
    global _TREND_CONSISTENCY_CHOP
    numeric = _validate_float_range_setting(
        value,
        _DEFAULT_SETTINGS["trend_consistency_chop"],
        minimum=0.0,
        maximum=100.0,
    )
    _TREND_CONSISTENCY_CHOP = numeric
    if persist:
        _update_setting(_SETTINGS,"trend_consistency_chop", numeric)
    return numeric


def _set_trend_fast_span(value: int, *, persist: bool = True) -> int:
    global _TREND_FAST_SPAN, _TREND_SLOW_SPAN
    numeric = _validate_positive_int_setting(
        value,
        _DEFAULT_SETTINGS["trend_consistency_fast_span"],
        minimum=2,
        maximum=250,
    )
    _TREND_FAST_SPAN = numeric
    if _TREND_SLOW_SPAN <= _TREND_FAST_SPAN:
        _TREND_SLOW_SPAN = min(500, _TREND_FAST_SPAN + 5)
        if persist:
            _update_setting(_SETTINGS,"trend_consistency_slow_span", _TREND_SLOW_SPAN)
    if persist:
        _update_setting(_SETTINGS,"trend_consistency_fast_span", numeric)
    return numeric


def _set_trend_slow_span(value: int, *, persist: bool = True) -> int:
    global _TREND_SLOW_SPAN
    numeric = _validate_positive_int_setting(
        value,
        _DEFAULT_SETTINGS["trend_consistency_slow_span"],
        minimum=max(5, _TREND_FAST_SPAN + 1),
        maximum=500,
    )
    if numeric <= _TREND_FAST_SPAN:
        numeric = min(500, _TREND_FAST_SPAN + 5)
    _TREND_SLOW_SPAN = numeric
    if persist:
        _update_setting(_SETTINGS,"trend_consistency_slow_span", numeric)
    return numeric


def _set_stability_method(value: str, *, persist: bool = True) -> str:
    global _STABILITY_METHOD
    normalized = str(value).strip().lower()
    if normalized not in {"presence_ratio", "kendall"}:
        return _STABILITY_METHOD
    _STABILITY_METHOD = normalized
    if persist:
        _update_setting(_SETTINGS,"stability_method", normalized)
    return normalized


def _set_stability_window(value: int, *, persist: bool = True) -> int:
    global _STABILITY_WINDOW
    numeric = _validate_positive_int_setting(
        value,
        _DEFAULT_SETTINGS["stability_window"],
        minimum=2,
        maximum=250,
    )
    _STABILITY_WINDOW = numeric
    if persist:
        _update_setting(_SETTINGS,"stability_window", numeric)
    return numeric


def _set_stability_top_n(value: int, *, persist: bool = True) -> int:
    global _STABILITY_TOP_N
    numeric = _validate_positive_int_setting(
        value,
        _DEFAULT_SETTINGS["stability_top_n"],
        minimum=1,
        maximum=100,
    )
    _STABILITY_TOP_N = numeric
    if persist:
        _update_setting(_SETTINGS,"stability_top_n", numeric)
    return numeric


def _set_stability_weight(value: float, *, persist: bool = True) -> float:
    global _STABILITY_WEIGHT
    numeric = _validate_ratio_setting(
        value,
        _DEFAULT_SETTINGS["stability_weight"],
        min_value=0.0,
        max_value=1.0,
    )
    _STABILITY_WEIGHT = numeric
    if persist:
        _update_setting(_SETTINGS,"stability_weight", numeric)
    return numeric


def colorize(text: str, style: str, fallback: str | None = None) -> str:
    """颜色化文本（兼容层，逐步迁移到utils.colors）"""
    # 使用新的utils.colors模块
    return _utils_colorize(text, style, fallback)


def _apply_cli_theme(theme_key: str, *, persist: bool = True) -> bool:
    global _STYLE_THEME, _STYLE_CODES
    if theme_key not in _CLI_THEMES:
        return False
    _STYLE_THEME = theme_key
    _STYLE_CODES = dict(_CLI_THEMES[theme_key])
    if hasattr(_strip_ansi, "cache_clear"):
        _strip_ansi.cache_clear()  # 清除缓存，防止旧主题残留
    if hasattr(_display_width, "cache_clear"):
        _display_width.cache_clear()
    _THEME_SAMPLE_CACHE.clear()
    if persist:
        _update_setting(_SETTINGS,"cli_theme", theme_key)
    return True


def _render_theme_sample(theme_key: str) -> str:
    cached = _THEME_SAMPLE_CACHE.get(theme_key)
    if cached is not None:
        return cached
    codes = _CLI_THEMES[theme_key]
    sample = (
        f"     {codes['title']}标题{codes['reset']} "
        f"{codes['menu_text']}菜单{codes['reset']} "
        f"{codes['prompt']}输入{codes['reset']} "
        f"{codes['value_positive']}+1.20%{codes['reset']} "
        f"{codes['value_negative']}-0.85%{codes['reset']}"
    )
    _THEME_SAMPLE_CACHE[theme_key] = sample
    return sample


def _rank_style(rank: int) -> str | None:
    if rank == 1:
        return "rank_gold"
    if rank == 2:
        return "rank_silver"
    if rank == 3:
        return "rank_bronze"
    return None


def _detect_rank_drop_alerts(result, weeks: int = _MOMENTUM_ALERT_WEEKS, min_drop: int = _MOMENTUM_ALERT_MIN_DROP, top_n: int = _MOMENTUM_ALERT_TOP) -> List[dict]:
    summary = result.summary
    rank_history = result.rank_history
    if summary.empty or rank_history.empty:
        return []
    summary_sorted = summary.sort_values("momentum_rank")
    codes = [str(code) for code in summary_sorted["etf"].head(top_n) if isinstance(code, str)]
    if not codes:
        return []
    weekly = rank_history.sort_index().resample("W-FRI").last().ffill()
    alerts: List[dict] = []
    for code in codes:
        if code not in weekly.columns:
            continue
        series = weekly[code].dropna()
        if len(series) < weeks + 1:
            continue
        recent_diff = series.diff().iloc[-weeks:]
        if recent_diff.isna().any():
            continue
        if not (recent_diff > 0).all():
            continue
        start_rank = float(series.iloc[-(weeks + 1)])
        end_rank = float(series.iloc[-1])
        total_drop = end_rank - start_rank
        if total_drop < min_drop:
            continue
        alerts.append(
            {
                "code": code,
                "label": _format_label(code),
                "start_rank": int(round(start_rank)),
                "end_rank": int(round(end_rank)),
                "weeks": weeks,
                "drop": round(total_drop, 2),
            }
        )
    return alerts


# Moved to business.alerts
from .business import detect_high_correlation_pairs as _business_detect_high_correlation_pairs
from .business import collect_alerts as _business_collect_alerts

def _detect_high_correlation_pairs(
    corr: pd.DataFrame,
    threshold: float | None = None,
    max_pairs: int = _MAX_CORRELATION_ALERTS,
) -> List[dict]:
    if threshold is None:
        threshold = _CORRELATION_ALERT_THRESHOLD
    return _business_detect_high_correlation_pairs(
        corr, threshold=threshold, max_pairs=max_pairs, format_label_func=_format_label
    )


def _collect_alerts(result) -> dict:
    return _business_collect_alerts(
        result,
        correlation_threshold=_CORRELATION_ALERT_THRESHOLD,
        max_correlation_pairs=_MAX_CORRELATION_ALERTS,
        format_label_func=_format_label,
    )


# 迁移至 utils.formatters
from .utils import chop_state_label as _chop_state_label


# Moved to business.reports (268 lines) - old implementation removed
from .business import build_strategy_gate_entries as _business_build_strategy_gate_entries

def _build_strategy_gate_entries(result, lang: str) -> List[tuple[str, str]]:
    return _business_build_strategy_gate_entries(result, lang, format_label_func=_format_label)

# Old implementation removed (268 lines)

# New wrapper function
def _build_strategy_gate_entries(result, lang: str) -> List[tuple[str, str]]:
    return _business_build_strategy_gate_entries(result, lang, format_label_func=_format_label)


# 显示和解析相关函数已移至 utils 模块


# 移至 utils.formatters
from .utils import adx_state_label as _adx_state_label


def _style_summary_value(label: str, value: str, row: dict) -> str:
    if not _COLOR_ENABLED:
        return value
    style: str | None = None
    if label in {"动量", "Momentum"}:
        number = _extract_float(value)
        if number is not None:
            if number > 0:
                style = "value_positive"
            elif number < 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label in {"变动", "ΔRank"}:
        number = _extract_float(value)
        if number is not None:
            if number < 0:
                style = "value_positive"
            elif number > 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label in {"趋势", "Trend"}:
        number = _extract_float(value)
        if number is not None:
            if number > 0:
                style = "value_positive"
            elif number < 0:
                style = "value_negative"
            else:
                style = "value_neutral"
    elif label == "200MA" or label == "MA200":
        if value.endswith("上") or value.endswith("UP"):
            style = "value_positive"
        elif value.endswith("下") or value.endswith("DN"):
            style = "value_negative"
    elif label in {"排名", "Rank"}:
        try:
            rank = int(row.get("rank_fmt", "0"))
        except ValueError:
            rank = 0
        rank_style = _rank_style(rank)
        if rank_style:
            style = rank_style
    elif label in {"Chop"}:
        state = row.get("__chop_state") if isinstance(row, dict) else None
        if state == "trend":
            style = "value_positive"
        elif state == "range":
            style = "value_negative"
        elif state == "neutral":
            style = "value_neutral"
        else:
            number = _extract_float(value)
            if number is not None:
                if number >= 60:
                    style = "value_negative"
                elif number <= 40:
                    style = "value_positive"
                else:
                    style = "value_neutral"
    elif label in {"ADX"}:
        adx_state = row.get("__adx_state") if isinstance(row, dict) else None
        if adx_state == "strong":
            style = "value_positive"
        elif adx_state == "weak":
            style = "value_negative"
        elif adx_state == "setup":
            style = "accent"
        else:
            number = _extract_float(value)
            if number is not None:
                if number >= 25:
                    style = "value_positive"
                elif number < 20:
                    style = "value_negative"
                else:
                    style = "accent"
    elif label in {"动量分位", "Mom%"}:
        flag = row.get("__mom_significant") if isinstance(row, dict) else None
        if flag is True:
            style = "value_positive"
        elif flag is False:
            style = "value_negative"
        else:
            style = "value_neutral"
    elif label in {"稳定度", "Stability"}:
        number = _extract_float(value)
        if number is not None:
            if number >= 70:
                style = "value_positive"
            elif number <= 30:
                style = "value_negative"
            else:
                style = "menu_hint"
        else:
            stability_raw = row.get("__stability") if isinstance(row, dict) else None
            if isinstance(stability_raw, (int, float)) and np.isfinite(stability_raw):
                if stability_raw >= 0.7:
                    style = "value_positive"
                elif stability_raw <= 0.3:
                    style = "value_negative"
                else:
                    style = "menu_hint"
            else:
                style = "value_neutral"
    elif label in {"趋势一致", "TrendOK"}:
        flag = row.get("__trend_ok") if isinstance(row, dict) else None
        if flag is True:
            style = "value_positive"
        elif flag is False:
            style = "value_negative"
        else:
            style = "value_neutral"
    if style:
        return colorize(value, style)
    return value


# 迁移至 utils.formatters，保留兼容层
def _style_rank_header(rank: int, text: str) -> str:
    from .utils import style_rank_header
    return style_rank_header(rank, text, enable_color=_COLOR_ENABLED)


def _format_menu_item(
    index: int | str,
    label: str,
    enabled: bool = True,
    *,
    selected: bool = False,
) -> str:
    """格式化菜单项（兼容层，使用ui.menu模块）"""
    return _ui_format_menu_item(index, label, enabled, selected=selected)


def _menu_hint(text: str) -> str:
    """菜单提示（兼容层，使用ui.menu模块）"""
    return _ui_menu_hint(text)


def _supports_interactive_menu() -> bool:
    """检查是否支持交互式菜单（兼容层，使用ui.menu模块）"""
    return _ui_supports_interactive_menu()


_ESC_SEQUENCE_TIMEOUT = 0.3
_ESC_POLL_INTERVAL = 0.05
_MAX_ESC_SEQUENCE = 16


# 键盘读取和菜单辅助函数已移至 ui 模块
# 为了兼容性，从ui模块导入
from .ui.input import read_keypress as _read_keypress


def _get_terminal_columns() -> int:
    now = time.monotonic()
    cached = _TERMINAL_SIZE_CACHE["columns"]
    if cached and now - _TERMINAL_SIZE_CACHE["timestamp"] <= 1.0:
        return cached
    try:
        columns = shutil.get_terminal_size(fallback=(120, 30)).columns
    except OSError:
        columns = cached or 120
    columns = max(int(columns or 0), 10)
    _TERMINAL_SIZE_CACHE["columns"] = columns
    _TERMINAL_SIZE_CACHE["timestamp"] = now
    return columns


def _estimate_physical_lines(lines: Sequence[str]) -> int:
    columns = _get_terminal_columns()
    total = 0
    for raw_line in lines:
        segments = str(raw_line).split("\n") if raw_line else [""]
        for segment in segments:
            width = _display_width(segment)
            if width <= 0:
                total += 1
            else:
                total += max(1, (width + columns - 1) // columns)
    return total


# 菜单渲染函数已移至 ui 模块


def _prompt_menu_choice(
    options: Sequence[Dict[str, Any]],
    *,
    title: Optional[str] = None,
    header_lines: Sequence[str] | None = None,
    hint: Optional[str] = None,
    footer_lines: Sequence[str] | None = None,
    prompt_text: str = "请输入编号: ",
    default_key: Optional[str] = None,
    allow_escape: bool = True,
    instant_numeric: bool = True,
    escape_prompt: Optional[str] = None,
    clear_screen: bool = False,
) -> str:
    """菜单选择（兼容层，使用ui.interactive模块）"""
    return _ui_prompt_menu_choice(
        options,
        title=title,
        header_lines=header_lines,
        hint=hint,
        footer_lines=footer_lines,
        prompt_text=prompt_text,
        default_key=default_key,
        allow_escape=allow_escape,
        instant_numeric=instant_numeric,
        escape_prompt=escape_prompt,
        clear_screen_first=clear_screen,
    )



# 模板管理函数已移至 business.templates 模块
def _load_template_store() -> Dict[str, dict]:
    """加载模板存储（兼容层）"""
    return _business_load_template_store()


def _write_template_store(store: Dict[str, dict]) -> None:
    """写入模板存储（兼容层）"""
    _business_write_template_store(store)


def _get_template_entry(name: str) -> Optional[dict]:
    """获取模板条目（兼容层）"""
    return _business_get_template(name)


def _save_template_entry(name: str, payload: dict, overwrite: bool = False) -> bool:
    """保存模板条目（兼容层）"""
    return _business_save_template(name, payload, overwrite)


def _delete_template_entry(name: str) -> bool:
    """删除模板条目（兼容层）"""
    return _business_delete_template(name)


# Moved to business.templates
from .business import print_template_list as _business_print_template_list

def _print_template_list() -> None:
    store = _load_template_store()
    _business_print_template_list(store)


# Moved to business.templates
from .business import build_template_payload as _business_build_template_payload

def _build_template_payload(
    config: AnalysisConfig,
    momentum_config: MomentumConfig,
    preset_keys: Sequence[str],
    analysis_preset: AnalysisPreset | None,
    export_csv: bool = False,
) -> dict:
    return _business_build_template_payload(config, momentum_config, preset_keys, analysis_preset, export_csv)


def _template_to_params(template: dict) -> dict:
    return {
        "codes": template.get("etfs", []),
        "start": template.get("start"),
        "end": template.get("end"),
        "windows": template.get("momentum_windows", ()),
        "weights": template.get("momentum_weights"),
        "skip_windows": template.get("momentum_skip_windows"),
        "corr_window": template.get("corr_window"),
        "chop_window": template.get("chop_window"),
        "trend_window": template.get("trend_window"),
        "rank_lookback": template.get("rank_lookback"),
        "output_dir": template.get("output_dir", "results"),
        "make_plots": template.get("make_plots", True),
        "export_csv": template.get("export_csv", False),
        "analysis_preset": template.get("analysis_preset"),
        "presets": template.get("presets", []),
        "stability_method": template.get("stability_method"),
        "stability_window": template.get("stability_window"),
        "stability_top_n": template.get("stability_top_n"),
        "stability_weight": template.get("stability_weight"),
    }


def _prompt_text_default(question: str, current: str | None) -> str:
    current_display = current if current else "未设置"
    raw = input(colorize(f"{question}（当前 {current_display}，回车保持）: ", "prompt")).strip()
    return raw if raw else (current or "")


def _prompt_optional_date(question: str, current: Optional[str]) -> Optional[str]:
    current_display = current if current else "未设置"
    while True:
        raw = input(
            colorize(
                f"{question}（当前 {current_display}，输入 none 清除）: ",
                "prompt",
            )
        ).strip()
        if not raw:
            return current
        lowered = raw.lower()
        if lowered in {"none", "null", "clear", "无"}:
            return None
        try:
            dt.datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print(colorize("日期格式不正确，请输入 YYYY-MM-DD。", "warning"))


def _prompt_positive_int_default(question: str, current: int) -> int:
    while True:
        raw = input(colorize(f"{question}（当前 {current}）: ", "prompt")).strip()
        if not raw:
            return current
        if raw.isdigit():
            value = int(raw)
            if value > 0:
                return value
        print(colorize("请输入正整数。", "warning"))


def _prompt_windows_with_default(current: Sequence[int]) -> List[int]:
    defaults = tuple(int(win) for win in current) if current else (60, 120)
    windows = _prompt_windows(defaults)
    return [int(win) for win in windows]


def _prompt_weights_for_windows(
    current_weights: Sequence[float] | None, window_count: int
) -> Optional[List[float]]:
    if window_count <= 0:
        return None
    default_text = (
        ",".join(f"{weight:.2f}" for weight in current_weights)
        if current_weights
        else "等权"
    )
    while True:
        raw = input(
            colorize(
                f"动量权重（数量需与窗口一致，当前 {default_text}，输入 auto/均匀 使用等权）: ",
                "prompt",
            )
        ).strip()
        if not raw:
            return list(current_weights) if current_weights else None
        lowered = raw.lower()
        if lowered in {"auto", "均匀", "等权", "equal", "none"}:
            return None
        tokens = [token for token in re.split(r"[ ,，、]+", raw) if token]
        try:
            weights = [float(token) for token in tokens]
        except ValueError:
            print(colorize("请输入数值，例如 0.6 0.4。", "warning"))
            continue
        if len(weights) != window_count:
            print(colorize("权重数量需要和窗口数量一致。", "warning"))
            continue
        return weights


def _prompt_preset_keys_with_default(current: Sequence[str]) -> List[str]:
    display = ",".join(current) if current else "无"
    raw = input(
        colorize(
            f"关联券池预设（逗号分隔，当前 {display}，输入 - 清空）: ",
            "prompt",
        )
    ).strip()
    if not raw:
        return list(current)
    lowered = raw.lower()
    if lowered in {"-", "none", "无"}:
        return []
    tokens = [token for token in re.split(r"[ ,，、]+", raw) if token]
    result: List[str] = []
    seen = set()
    for token in tokens:
        key = token.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float_sequence(value: Sequence[float | int | str] | None) -> Optional[List[float]]:
    if value is None:
        return None
    result: List[float] = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return None
    return result


def _coerce_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "是"}:
            return True
        if lowered in {"0", "false", "no", "n", "否"}:
            return False
    return default


def _edit_code_list_interactively(existing: Sequence[str]) -> List[str]:
    current = _dedup_codes(existing)
    while True:
        if current:
            print(colorize("\n当前券池：", "heading"))
            _show_codes(current)
        else:
            print(colorize("\n当前券池为空。", "warning"))
        options = [
            {"key": "1", "label": "追加 ETF"},
            {"key": "2", "label": "剔除 ETF"},
            {"key": "3", "label": "手动重新录入"},
            {"key": "0", "label": "完成编辑"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 券池编辑 ─" + "─" * 18,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice in {"0", "__escape__"}:
            break
        if choice == "1":
            current = _interactive_add_codes(current)
            continue
        if choice == "2":
            current = _interactive_remove_codes(current)
            continue
        if choice == "3":
            manual = _prompt_codes_input("请输入 ETF 代码（逗号或空格分隔）")
            if manual:
                current = manual
            else:
                print(colorize("未输入任何代码，已保留原列表。", "warning"))
            continue
        print(colorize("指令无效，请输入 0-3。", "warning"))
    deduped = _dedup_codes(current)
    if not deduped:
        print(colorize("券池不能为空，将保留原始列表。", "warning"))
        return _dedup_codes(existing)
    return deduped


def _parse_list(value: str | None) -> Sequence[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int_list(value: str | None) -> Sequence[int]:
    return [int(item) for item in _parse_list(value)] if value else []


def _parse_float_list(value: str | None) -> Sequence[float]:
    return [float(item) for item in _parse_list(value)] if value else []


def build_parser() -> argparse.ArgumentParser:
    class RichHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
    ):
        pass

    parser = argparse.ArgumentParser(
        description=(
            "ETF momentum analytics toolkit leveraging the local RQAlpha bundle.\n"
            f"默认行为等同于 `{LAUNCHER_BASENAME} analyze ...`。"
        ),
        formatter_class=RichHelpFormatter,
        epilog=(
            "示例:\n"
            f"  {LAUNCHER_COMMAND} analyze --preset core --run-backtest\n"
            f"  {LAUNCHER_COMMAND} analyze --preset core --export-strategy strategies/momentum_strategy.py\n"
            f"  {LAUNCHER_COMMAND} presets\n"
        ),
    )

    universe_group = parser.add_argument_group("券池选择")
    universe_group.add_argument(
        "--etfs",
        help="自定义 ETF order_book_id 列表，逗号分隔（示例：510300.XSHG,159915.XSHE）。",
    )
    universe_group.add_argument(
        "--preset",
        help="使用预设券池（core,satellite，可用英文逗号分隔）。",
    )
    universe_group.add_argument(
        "--exclude",
        help="需要剔除的 ETF 代码，逗号分隔。",
    )
    universe_group.add_argument("--start", help="开始日期 (YYYY-MM-DD)。")
    universe_group.add_argument(
        "--end",
        help="结束日期 (YYYY-MM-DD)。默认读取至可用的最新交易日。",
    )

    analysis_group = parser.add_argument_group("分析参数")
    analysis_group.add_argument(
        "--analysis-preset",
        choices=list(ANALYSIS_PRESETS.keys()),
        help="选择分析预设（如 slow-core, blend-dual, twelve-minus-one 等）。",
    )
    analysis_group.add_argument(
        "--momentum-windows",
        help="动量观测窗口（日），逗号分隔，例如 20,60,120。",
    )
    analysis_group.add_argument(
        "--momentum-weights",
        help="动量窗口对应权重，需与窗口数量一致。",
    )
    analysis_group.add_argument(
        "--corr-window",
        type=int,
        help="滚动相关系数窗口（日）。",
    )
    analysis_group.add_argument(
        "--chop-window",
        type=int,
        help="Choppiness 指数窗口（日）。",
    )
    analysis_group.add_argument(
        "--trend-window",
        type=int,
        help="线性趋势斜率窗口（日）。",
    )
    analysis_group.add_argument(
        "--rank-lookback",
        type=int,
        help="动量排名变动回溯天数。",
    )
    analysis_group.add_argument(
        "--bundle-path",
        type=Path,
        help="自定义 RQAlpha bundle 路径（默认使用 ~/.rqalpha/bundle）。",
    )

    output_group = parser.add_argument_group("输出")
    output_group.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="图表及导出数据的输出目录。",
    )
    output_group.add_argument(
        "--no-plot",
        action="store_true",
        help="仅输出文本，不生成图表。",
    )
    output_group.add_argument(
        "--export-csv",
        action="store_true",
        help="将动量汇总和相关系数矩阵导出为 CSV。",
    )
    output_group.add_argument(
        "--run-backtest",
        action="store_true",
        help="分析完成后运行内置的简易动量回测。",
    )
    output_group.add_argument(
        "--lang",
        choices=["zh", "en"],
        default="zh",
        help="输出语言。",
    )

    strategy_group = parser.add_argument_group("RQAlpha 策略导出")
    strategy_group.add_argument(
        "--export-strategy",
        type=Path,
        help="将当前参数导出为 RQAlpha 策略脚本。",
    )
    strategy_group.add_argument(
        "--strategy-top",
        type=int,
        default=2,
        help="策略调仓时的最大持仓数量（导出策略时使用）。",
    )
    strategy_group.add_argument(
        "--strategy-frequency",
        choices=["monthly", "weekly", "daily"],
        default="monthly",
        help="导出策略的调仓频率。",
    )

    template_group = parser.add_argument_group("分析模板")
    template_group.add_argument("--save-template", help="将当前参数保存为模板名称。")
    template_group.add_argument("--load-template", help="加载指定模板作为默认参数。")
    template_group.add_argument(
        "--list-templates",
        action="store_true",
        help="列出所有保存的分析模板并退出。",
    )
    template_group.add_argument("--delete-template", help="删除指定名称的模板后退出。")

    automation_group = parser.add_argument_group("自动化 / MCP 适配")
    automation_group.add_argument(
        "--output-format",
        choices=["text", "json", "markdown"],
        default="text",
        help="选择输出格式，便于 MCP / 自动化流程消费。",
    )
    automation_group.add_argument(
        "--output-file",
        type=Path,
        help="将主输出写入文件。",
    )
    automation_group.add_argument(
        "--save-state",
        type=Path,
        help="将完整分析结果（JSON）写入文件，便于二次处理。",
    )
    automation_group.add_argument(
        "--print-config",
        action="store_true",
        help="输出生效的参数配置（JSON），便于记录。",
    )
    automation_group.add_argument(
        "--quiet",
        action="store_true",
        help="抑制标准输出，仅在必要时打印提示。",
    )
    automation_group.add_argument(
        "--color",
        action="store_true",
        help="强制启用彩色输出（默认仅在终端支持时启用）。",
    )
    automation_group.add_argument(
        "--no-color",
        action="store_true",
        help="禁用彩色输出。",
    )

    utility_group = parser.add_argument_group("工具")
    utility_group.add_argument(
        "--interactive",
        action="store_true",
        help=f"进入交互式菜单，适合 {LAUNCHER_COMMAND} 不带参数的场景。",
    )
    utility_group.add_argument(
        "--list-presets",
        action="store_true",
        help="列出所有预设券池并退出。",
    )
    utility_group.add_argument(
        "--list-analysis-presets",
        action="store_true",
        help="列出所有分析预设并退出。",
    )
    utility_group.add_argument(
        "--update-bundle",
        action="store_true",
        help="调用 rqalpha update-bundle 更新本地数据。",
    )

    return parser


# moved to utils.formatters
from .utils import formatters as _fmt_utils

def _prepare_summary_table(
    frame: pd.DataFrame, lang: str
) -> tuple[List[tuple[str, str, str]], List[dict[str, str]]]:
    return _fmt_utils.prepare_summary_table(frame, lang)
    ordered = (
        frame.copy()
        .sort_values(["momentum_rank", "momentum_score"], ascending=[True, False])
        .reset_index(drop=True)
    )

    def compose_symbol(row: pd.Series) -> str:
        name = str(row.get("name", "") or "").strip()
        code = str(row.get("etf", "") or "").strip()
        if name and code:
            return f"{name} ({code})"
        return name or code or "-"

    ordered["symbol"] = ordered.apply(compose_symbol, axis=1)

    def fmt_number(value: Optional[float], digits: int = 4) -> str:
        if value is None or pd.isna(value):
            return "-"
        return f"{value:.{digits}f}"

    def fmt_rank(value: Optional[float]) -> str:
        if value is None or pd.isna(value):
            return "--"
        return f"{int(value):02d}"

    def fmt_change(value: Optional[float]) -> str:
        if value is None or pd.isna(value):
            return "-"
        return f"{value:+.0f}"

    def fmt_ma(row: pd.Series) -> str:
        ma = row.get("ma200")
        if ma is None or pd.isna(ma):
            return "-"
        above = bool(row.get("above_ma200"))
        status = "上" if lang == "zh" else "UP"
        alt = "下" if lang == "zh" else "DN"
        suffix = status if above else alt
        return f"{ma:.4f}{suffix}"

    ordered["momentum_fmt"] = ordered["momentum_score"].apply(fmt_number)
    ordered["rank_fmt"] = ordered["momentum_rank"].apply(fmt_rank)
    ordered["delta_fmt"] = ordered["rank_change"].apply(fmt_change)
    ordered["close_fmt"] = ordered["close"].apply(fmt_number)
    ordered["vwap_fmt"] = ordered["vwap"].apply(fmt_number)
    ordered["ma_fmt"] = [fmt_ma(row) for _, row in ordered.iterrows()]

    def fmt_chop_display(row: pd.Series) -> str:
        base = fmt_number(row.get("chop"), 2)
        state_label = _chop_state_label(row.get("chop_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    def fmt_adx_display(row: pd.Series) -> str:
        base = fmt_number(row.get("adx"), 2)
        state_label = _adx_state_label(row.get("adx_state"), lang)
        if state_label:
            suffix = f"（{state_label}）" if lang == "zh" else f" ({state_label})"
            return f"{base}{suffix}"
        return base

    ordered["chop_fmt"] = [fmt_chop_display(row) for _, row in ordered.iterrows()]
    ordered["trend_fmt"] = ordered["trend_slope"].apply(fmt_number)
    ordered["atr_fmt"] = ordered["atr"].apply(fmt_number)
    ordered["adx_fmt"] = [fmt_adx_display(row) for _, row in ordered.iterrows()]

    def fmt_momentum_percentile(row: pd.Series) -> str:
        value = row.get("momentum_percentile")
        if value is None or pd.isna(value):
            return "--"
        flag = row.get("momentum_significant")
        if flag is None or (isinstance(flag, float) and pd.isna(flag)):
            return "--"
        mark = "✅" if bool(flag) else "❌"
        return f"{mark}{value * 100:.1f}%"

    def fmt_stability_display(row: pd.Series) -> str:
        value = row.get("stability")
        if value is None or pd.isna(value):
            return "--"
        return f"{float(value) * 100:.0f}%"

    ordered["stability_fmt"] = [fmt_stability_display(row) for _, row in ordered.iterrows()]

    def fmt_trend_ok(row: pd.Series) -> str:
        flag = row.get("trend_ok")
        if flag is None or (isinstance(flag, float) and pd.isna(flag)):
            return "--"
        return "✅" if bool(flag) else "❌"

    ordered["mom_pct_fmt"] = [fmt_momentum_percentile(row) for _, row in ordered.iterrows()]
    ordered["trend_ok_fmt"] = [fmt_trend_ok(row) for _, row in ordered.iterrows()]

    def truncate(value: str, limit: int) -> str:
        text = str(value).strip()
        if limit <= 0:
            return ""
        if _display_width(text) <= limit:
            return text
        ellipsis = "..."
        ellipsis_width = _display_width(ellipsis)
        if ellipsis_width >= limit:
            trimmed: List[str] = []
            consumed = 0
            for char in text:
                char_width = _display_width(char)
                if consumed + char_width > limit:
                    break
                trimmed.append(char)
                consumed += char_width
            return "".join(trimmed)
        target_width = limit - ellipsis_width
        trimmed_chars: List[str] = []
        consumed = 0
        for char in text:
            char_width = _display_width(char)
            if consumed + char_width > target_width:
                break
            trimmed_chars.append(char)
            consumed += char_width
        if not trimmed_chars:
            return ellipsis
        return "".join(trimmed_chars) + ellipsis

    rows: List[dict[str, object]] = []
    for _, row in ordered.iterrows():
        rows.append(
            {
                "symbol": truncate(row["symbol"], 26),
                "rank_fmt": str(row["rank_fmt"]),
                "delta_fmt": str(row["delta_fmt"]),
                "momentum_fmt": str(row["momentum_fmt"]),
                "mom_pct_fmt": str(row["mom_pct_fmt"]),
                "stability_fmt": str(row["stability_fmt"]),
                "close_fmt": str(row["close_fmt"]),
                "vwap_fmt": str(row["vwap_fmt"]),
                "ma_fmt": str(row["ma_fmt"]),
                "chop_fmt": str(row["chop_fmt"]),
                "trend_fmt": str(row["trend_fmt"]),
                "trend_ok_fmt": str(row["trend_ok_fmt"]),
                "atr_fmt": str(row["atr_fmt"]),
                "adx_fmt": str(row["adx_fmt"]),
                "__chop_state": row.get("chop_state"),
                "__chop_p30": row.get("chop_p30"),
                "__chop_p70": row.get("chop_p70"),
                "__adx_state": row.get("adx_state"),
                "__mom_significant": row.get("momentum_significant"),
                "__trend_ok": row.get("trend_ok"),
                "__stability": row.get("stability"),
            }
        )

    if lang == "zh":
        columns = [
            ("symbol", "标的", "left", True),
            ("rank_fmt", "排名", "right", True),
            ("delta_fmt", "变动", "right", True),
            ("momentum_fmt", "动量", "right", True),
            ("mom_pct_fmt", "动量分位", "right", True),
            ("stability_fmt", "稳定度", "right", True),
            ("close_fmt", "收盘", "right", True),
            ("vwap_fmt", "VWAP", "right", True),
            ("ma_fmt", "200MA", "right", False),
            ("chop_fmt", "Chop", "right", True),
            ("trend_fmt", "趋势", "right", True),
            ("trend_ok_fmt", "趋势一致", "center", True),
            ("adx_fmt", "ADX", "right", True),
            ("atr_fmt", "ATR", "right", True),
        ]
    else:
        columns = [
            ("symbol", "Symbol", "left"),
            ("rank_fmt", "Rank", "right"),
            ("delta_fmt", "ΔRank", "right"),
            ("momentum_fmt", "Momentum", "right"),
            ("mom_pct_fmt", "Mom%", "right"),
            ("stability_fmt", "Stability", "right"),
            ("close_fmt", "Close", "right"),
            ("vwap_fmt", "VWAP", "right"),
            ("ma_fmt", "MA200", "right"),
            ("chop_fmt", "Chop", "right"),
            ("trend_fmt", "Trend", "right"),
            ("trend_ok_fmt", "TrendOK", "center"),
            ("adx_fmt", "ADX", "right"),
            ("atr_fmt", "ATR", "right"),
        ]

    return _normalize_column_specs(columns), rows

# Overwrite with utils implementation (kept above for reference during transition)
from .utils import prepare_summary_table as _utils_prepare_summary_table

def _prepare_summary_table(frame: pd.DataFrame, lang: str):
    return _utils_prepare_summary_table(frame, lang)



# moved to utils.formatters
from .utils import formatters as _fmt_utils
_normalize_column_specs = _fmt_utils.normalize_column_specs


from .utils import formatters as _fmt_utils

def format_summary_frame(frame: pd.DataFrame, lang: str) -> str:
    return _fmt_utils.format_summary_frame(frame, lang, enable_color=_COLOR_ENABLED)


from .utils import formatters as _fmt_utils

def _summary_to_markdown(frame: pd.DataFrame, lang: str) -> str:
    return _fmt_utils.summary_to_markdown(frame, lang)


# Moved to utils.helpers
from .utils import format_code_label as _utils_format_code_label

def _format_label(code: str) -> str:
    return _utils_format_code_label(code, get_label)


def format_correlation(frame: pd.DataFrame, lang: str) -> str:
    if frame.empty:
        return "(相关矩阵为空)" if lang == "zh" else "(correlation matrix empty)"
    if frame.shape[0] > 15:
        threshold = _CORRELATION_ALERT_THRESHOLD
        alerts = _detect_high_correlation_pairs(
            frame, threshold=threshold, max_pairs=min(_MAX_CORRELATION_ALERTS, 10)
        )
        if alerts:
            return (
                "相关矩阵维度较大（详见预警提示中的高相关性列表）。"
                if lang == "zh"
                else "Correlation matrix omitted (see Alerts section for high-ρ pairs)."
            )
        return (
            "相关矩阵维度较大（已略），且当前未发现超过阈值的高相关性。"
            if lang == "zh"
            else "Correlation matrix omitted (dimension too large); no pairs above threshold."
        )
    display_frame = frame.copy()
    if not display_frame.empty:
        for column in display_frame.columns:
            if column in display_frame.index and pd.isna(display_frame.loc[column, column]):
                display_frame.loc[column, column] = 1.0
        display_frame = display_frame.fillna(0.0)
        column_labels = {code: _format_label(code) for code in display_frame.columns}
        display_frame.columns = [column_labels.get(col, _format_label(col)) for col in display_frame.columns]
        display_frame.index = [column_labels.get(idx, _format_label(idx)) for idx in display_frame.index]
    return display_frame.to_string(float_format=lambda x: f"{x:.2f}")


def _correlation_to_markdown(frame: pd.DataFrame, lang: str) -> str:
    if frame.empty:
        return "*相关矩阵为空*" if lang == "zh" else "*Correlation matrix empty.*"
    if frame.shape[0] > 15:
        threshold = _CORRELATION_ALERT_THRESHOLD
        alerts = _detect_high_correlation_pairs(
            frame, threshold=threshold, max_pairs=min(_MAX_CORRELATION_ALERTS, 10)
        )
        if alerts:
            return (
                "*相关矩阵维度较大，详见预警提示中的高相关性列表。*"
                if lang == "zh"
                else "*Correlation matrix omitted (see Alerts section for high-ρ pairs).*"
            )
        return (
            "*相关矩阵维度较大（已略），且当前未发现超过阈值的高相关性。*"
            if lang == "zh"
            else "*Correlation matrix omitted (dimension too large); no pairs above threshold.*"
        )
    display_frame = frame.copy()
    if not display_frame.empty:
        for column in display_frame.columns:
            if column in display_frame.index and pd.isna(display_frame.loc[column, column]):
                display_frame.loc[column, column] = 1.0
        display_frame = display_frame.fillna(0.0)
    label_map = {code: _format_label(code) for code in display_frame.columns}
    header = "| ETF | " + " | ".join(label_map.values()) + " |"
    divider = "| " + " | ".join(["---"] * (len(label_map) + 1)) + " |"
    body = []
    for index, row in display_frame.iterrows():
        index_label = label_map.get(index, _format_label(index))
        values = [f"{row[col]:.2f}" if pd.notna(row[col]) else "-" for col in display_frame.columns]
        body.append("| " + index_label + " | " + " | ".join(values) + " |")
    return "\n".join([header, divider, *body])


def _ensure_plotly():
    try:
        import plotly.graph_objects as go  # type: ignore
    except ImportError:
        print(
            colorize(
                "缺少 plotly，无法生成交互式图表。请运行 `pip install plotly` 后重试。",
                "warning",
            )
        )
        return None
    return go


def _generate_interactive_plot(
    data: pd.DataFrame,
    title: str,
    yaxis_title: str,
    output_dir: Path,
    filename: str,
    invert_y: bool = False,
    core_codes: Optional[set[str]] = None,
    satellite_codes: Optional[set[str]] = None,
    default_visible_codes: Optional[set[str]] = None,
) -> Optional[Path]:
    if data.empty:
        print(colorize("数据为空，无法生成图表。", "warning"))
        return None
    go = _ensure_plotly()
    if go is None:
        print(colorize("plotly 未安装，可尝试执行 `pip install plotly==5.24.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/`（注意命令不要换行）后重试。若依旧失败，可访问 https://pypi.org/project/plotly/#files 手动下载 whl 安装。", "menu_hint"))
        return None
    figure = go.Figure()
    trace_codes = [str(col).upper() for col in data.columns]
    default_visible = {code.upper() for code in default_visible_codes} if default_visible_codes else None

    start_index: Optional[pd.Timestamp] = data.index.min() if not data.empty else None
    target_start: Optional[pd.Timestamp] = None
    if default_visible and data.index.size:
        col_map = {str(col).upper(): col for col in data.columns}
        first_indices: List[pd.Timestamp] = []
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
        figure.add_trace(
            go.Scatter(
                x=data.index,
                y=data[column],
                mode="lines",
                name=_format_label(column),
                legendgroup=legend_group,
                line={"width": _PLOT_LINE_WIDTH},
                visible=visible_state,
            )
        )
    buttons: List[dict] = []
    all_visible = [True] * len(trace_codes)
    buttons.append(
        {
            "label": "全部",
            "method": "update",
            "args": [{"visible": all_visible}],
        }
    )
    if default_visible:
        default_mask = [code in default_visible for code in trace_codes]
        if any(default_mask) and any(v is False for v in default_mask):
            buttons.append(
                {
                    "label": "前 6",
                    "method": "update",
                    "args": [{"visible": default_mask}],
                }
            )
    if core_codes:
        core_visible = [code in core_codes for code in trace_codes]
        if any(core_visible):
            buttons.append(
                {
                    "label": "仅核心",
                    "method": "update",
                    "args": [{"visible": core_visible}],
                }
            )
    if satellite_codes:
        sat_visible = [code in satellite_codes for code in trace_codes]
        if any(sat_visible):
            buttons.append(
                {
                    "label": "仅卫星",
                    "method": "update",
                    "args": [{"visible": sat_visible}],
                }
            )
    other_visible = [
        code not in (core_codes or set()) and code not in (satellite_codes or set())
        for code in trace_codes
    ]
    if any(other_visible):
        buttons.append(
            {
                "label": "仅其他",
                "method": "update",
                "args": [{"visible": other_visible}],
            }
        )
    legend_height_padding = max(0, len(trace_codes) - 12) * 22
    figure.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        template=_PLOT_TEMPLATE,
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


def _maybe_open_browser(path: Path) -> None:
    if not path.exists():
        return
    if _prompt_yes_no("是否在浏览器中打开该图表？", True):
        try:
            webbrowser.open(path.resolve().as_uri())
        except Exception as exc:  # noqa: BLE001
            print(colorize(f"无法打开浏览器: {exc}", "danger"))


# Moved to business.reports (114 lines)
from .business import build_result_payload as _business_build_result_payload

def _build_result_payload(
    result,
    config: AnalysisConfig,
    momentum_config: MomentumConfig,
    preset: AnalysisPreset | None,
    lang: str,
) -> dict:
    return _business_build_result_payload(
        result,
        config,
        momentum_config,
        preset,
        lang,
        collect_alerts_func=_collect_alerts,
        build_gate_entries_func=_build_strategy_gate_entries,
        max_series_export=MAX_SERIES_EXPORT,
    )

# Old implementation removed (114 lines)

def _render_text_report(
    result,
    config: AnalysisConfig,
    momentum_config: MomentumConfig,
    preset: AnalysisPreset | None,
    lang: str,
) -> str:
    lines: List[str] = []
    use_color = _COLOR_ENABLED

    def add(text: str, style: str | None = None) -> None:
        if style and use_color:
            lines.append(colorize(text, style))
        else:
            lines.append(text)

    start_text = config.start_date or ("最早可用" if lang == "zh" else "Earliest")
    end_text = config.end_date or ("最新交易日" if lang == "zh" else "Latest available")
    etf_count = len(result.summary)

    refresh_text = (
        _LAST_BUNDLE_REFRESH.strftime("%Y-%m-%d %H:%M")
        if _LAST_BUNDLE_REFRESH
        else None
    )

    alerts = _collect_alerts(result)

    def render_alerts_block() -> None:
        if not alerts.get("momentum_rank_drops") and not alerts.get("high_correlation_pairs"):
            return
        if lang == "zh":
            add("=== 预警提示 ===", "warning")
            if alerts.get("momentum_rank_drops"):
                add("动量排名连续走弱：", "warning")
                for item in alerts["momentum_rank_drops"]:
                    text = (
                        f"  • {item['label']}：{item['start_rank']} → {item['end_rank']}，"
                        f"连续 {item['weeks']} 周下滑"
                    )
                    add(text, "value_negative")
            if alerts.get("high_correlation_pairs"):
                threshold_text = f"{_CORRELATION_ALERT_THRESHOLD:.2f}"
                add(f"高相关性提示（ρ ≥ {threshold_text}）:", "warning")
                for item in alerts["high_correlation_pairs"]:
                    text = (
                        f"  • {item['label_a']} ↔ {item['label_b']} : {item['value']:.2f}"
                    )
                    add(text, "menu_hint")
        else:
            add("=== Alerts ===", "warning")
            if alerts.get("momentum_rank_drops"):
                add("Momentum ranks weakening:", "warning")
                for item in alerts["momentum_rank_drops"]:
                    text = (
                        f"  • {item['label']} : {item['start_rank']} → {item['end_rank']} "
                        f"over {item['weeks']} consecutive weeks"
                    )
                    add(text, "value_negative")
            if alerts.get("high_correlation_pairs"):
                threshold_text = f"{_CORRELATION_ALERT_THRESHOLD:.2f}"
                add(f"High correlations (ρ ≥ {threshold_text}):", "warning")
                for item in alerts["high_correlation_pairs"]:
                    text = (
                        f"  • {item['label_a']} ↔ {item['label_b']} : {item['value']:.2f}"
                    )
                    add(text, "menu_hint")
        add("", None)

    def render_strategy_gates() -> None:
        gate_entries = _build_strategy_gate_entries(result, lang)
        if not gate_entries:
            return
        heading_text = "=== 策略闸口 ===" if lang == "zh" else "=== Strategy Gates ==="
        add(heading_text, "heading")
        for text, style in gate_entries:
            add(text, style)
        add("", None)

    if lang == "zh":
        add("=== 动量分析报告 ===", "heading")
        add(f"分析区间: {start_text} → {end_text}", "menu_text")
        if refresh_text:
            add(f"数据包更新时间: {refresh_text}", "menu_hint")
        add(
            f"券池规模: {etf_count} / 动量窗口: {', '.join(str(w) for w in momentum_config.windows)}",
            "menu_text",
        )
        if momentum_config.weights:
            weight_text = ", ".join(f"{w:.2f}" for w in momentum_config.weights)
            add(f"动量权重: {weight_text}", "menu_text")
        if preset:
            add(
                f"分析预设: {preset.name} [{preset.key}] - {preset.description}",
                "menu_text",
            )
        add(
            f"参数: Corr {config.corr_window} / Chop {config.chop_window} / 趋势 {config.trend_window} / 回溯 {config.rank_change_lookback}",
            "menu_hint",
        )
        add("", None)
        render_strategy_gates()
        add("=== 动量汇总 ===", "heading")
    else:
        add("=== Momentum Analysis Report ===", "heading")
        add(f"Range: {start_text} → {end_text}", "menu_text")
        if refresh_text:
            add(f"Bundle refreshed at: {refresh_text}", "menu_hint")
        add(
            f"Universe: {etf_count} ETFs · Momentum windows: {', '.join(str(w) for w in momentum_config.windows)}",
            "menu_text",
        )
        if momentum_config.weights:
            weight_text = ", ".join(f"{w:.2f}" for w in momentum_config.weights)
            add(f"Momentum weights: {weight_text}", "menu_text")
        if preset:
            add(
                f"Preset: {preset.name} [{preset.key}] - {preset.description}",
                "menu_text",
            )
        add(
            f"Params: Corr {config.corr_window} / Chop {config.chop_window} / Trend {config.trend_window} / Rank lookback {config.rank_change_lookback}",
            "menu_hint",
        )
        add("", None)
        render_strategy_gates()
        add("=== Momentum Summary ===", "heading")

    add(format_summary_frame(result.summary, lang))
    add("", None)

    add(format_correlation(result.correlation, lang))

    add("", None)
    render_alerts_block()
    if lang == "zh":
        add(
            f"耗时: {result.runtime_seconds:.2f} 秒，覆盖 {etf_count} 只 ETF",
            "info",
        )
    else:
        add(
            f"Runtime: {result.runtime_seconds:.2f} seconds across {etf_count} ETFs",
            "info",
        )

    if result.plot_paths:
        add("生成的图表:" if lang == "zh" else "Generated plots:", "heading")
        for path in result.plot_paths:
            add(f" - {path}", "menu_hint")

    return "\n".join(lines).strip()


def _render_markdown_report(
    result,
    config: AnalysisConfig,
    momentum_config: MomentumConfig,
    preset: AnalysisPreset | None,
    lang: str,
) -> str:
    lines: List[str] = []
    title = "# 动量分析报告" if lang == "zh" else "# Momentum Analysis Report"
    lines.append(title)

    alerts = _collect_alerts(result)

    start_text = config.start_date or ("最早可用" if lang == "zh" else "Earliest")
    end_text = config.end_date or ("最新交易日" if lang == "zh" else "Latest available")
    lines.append("")
    if lang == "zh":
        lines.append(f"- 分析区间：{start_text} → {end_text}")
        lines.append(f"- 券池数量：{len(result.summary)}")
        lines.append(
            f"- 动量窗口：{', '.join(str(w) for w in momentum_config.windows)}"
        )
        if momentum_config.weights:
            lines.append(
                f"- 动量权重：{', '.join(f'{w:.2f}' for w in momentum_config.weights)}"
            )
        lines.append(
            f"- 参数：Corr {config.corr_window} / Chop {config.chop_window} / 趋势 {config.trend_window} / 回溯 {config.rank_change_lookback}"
        )
        if preset:
            lines.append(
                f"- 分析预设：{preset.name} [{preset.key}] - {preset.description}"
            )
    else:
        lines.append(f"- Range: {start_text} → {end_text}")
        lines.append(f"- Universe size: {len(result.summary)} ETFs")
        lines.append(
            f"- Momentum windows: {', '.join(str(w) for w in momentum_config.windows)}"
        )
        if momentum_config.weights:
            lines.append(
                f"- Momentum weights: {', '.join(f'{w:.2f}' for w in momentum_config.weights)}"
            )
        lines.append(
            f"- Parameters: Corr {config.corr_window} / Chop {config.chop_window} / Trend {config.trend_window} / Rank lookback {config.rank_change_lookback}"
        )
        if preset:
            lines.append(
                f"- Preset: {preset.name} [{preset.key}] - {preset.description}"
            )

    gate_entries = _build_strategy_gate_entries(result, lang)
    if gate_entries:
        icon_map = {
            "warning": "⚠️ ",
            "menu_hint": "ℹ️ ",
            "menu_text": "",
        }
        lines.append("")
        lines.append("## 策略闸口" if lang == "zh" else "## Strategy Gates")
        for text, style in gate_entries:
            prefix = icon_map.get(style, "")
            lines.append(f"- {prefix}{text}")

    lines.append("")
    lines.append("## Summary")
    lines.append(_summary_to_markdown(result.summary, lang))
    lines.append("")
    lines.append("## Correlation")
    lines.append(_correlation_to_markdown(result.correlation.round(2), lang))
    lines.append("")

    if alerts.get("momentum_rank_drops") or alerts.get("high_correlation_pairs"):
        lines.append("## 预警提示" if lang == "zh" else "## Alerts")
        if alerts.get("momentum_rank_drops"):
            if lang == "zh":
                lines.append("- 动量排名连续走弱：")
                for item in alerts["momentum_rank_drops"]:
                    lines.append(
                        f"  - {item['label']}：{item['start_rank']} → {item['end_rank']}，连续 {item['weeks']} 周下滑"
                    )
            else:
                lines.append("- Momentum ranks weakening:")
                for item in alerts["momentum_rank_drops"]:
                    lines.append(
                        f"  - {item['label']} : {item['start_rank']} → {item['end_rank']} over {item['weeks']} consecutive weeks"
                    )
        if alerts.get("high_correlation_pairs"):
            threshold_text = f"{_CORRELATION_ALERT_THRESHOLD:.2f}"
            if lang == "zh":
                lines.append(f"- 高相关性（ρ ≥ {threshold_text}）：")
                for item in alerts["high_correlation_pairs"]:
                    lines.append(
                        f"  - {item['label_a']} ↔ {item['label_b']} : {item['value']:.2f}"
                    )
            else:
                lines.append(f"- High correlations (ρ ≥ {threshold_text}):")
                for item in alerts["high_correlation_pairs"]:
                    lines.append(
                        f"  - {item['label_a']} ↔ {item['label_b']} : {item['value']:.2f}"
                    )
        lines.append("")

    if lang == "zh":
        lines.append(f"运行耗时：{result.runtime_seconds:.2f} 秒")
    else:
        lines.append(f"Runtime: {result.runtime_seconds:.2f} seconds")
    if result.plot_paths:
        lines.append("")
        lines.append("## 图表 / Plots")
        for path in result.plot_paths:
            lines.append(f"- {path}")

    return "\n".join(lines).strip()


def _print_presets() -> None:
    print(colorize("可用券池预设：", "heading"))
    for idx, (key, preset) in enumerate(PRESETS.items(), start=1):
        tickers = ", ".join(f"{get_label(code)}({code})" for code in preset.tickers)
        title = colorize(f" {idx:>2}. {preset.name} [{key}]", "menu_text")
        desc = colorize(f"    {preset.description}", "dim")
        tickers_line = colorize(f"    {tickers}", "menu_hint")
        print(title)
        print(desc)
        print(tickers_line)


def _preset_status_label(key: str) -> str:
    if key in DEFAULT_PRESETS:
        return "覆盖" if has_custom_override(key) else "内置"
    return "自定义"


def _select_preset_key(prompt: str) -> Optional[str]:
    if not PRESETS:
        print(colorize("暂无可用的券池预设。", "warning"))
        return None
    print(colorize(prompt, "heading"))
    keys = sorted(PRESETS.keys())
    for idx, key in enumerate(keys, start=1):
        preset = PRESETS[key]
        marker = _preset_status_label(key)
        line = f" {idx:>2}. {preset.name} [{key}] ({marker})"
        print(colorize(line, "menu_text"))
    choice = input(colorize("请输入名称或编号: ", "prompt")).strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(keys):
            return keys[idx - 1]
    if choice and choice in PRESETS:
        return choice
    print(colorize("未找到对应的预设。", "warning"))
    return None


def _interactive_edit_preset_entry(existing_key: Optional[str] = None) -> None:
    key = existing_key or _select_preset_key("请选择要编辑的券池预设：")
    if not key:
        return
    preset = PRESETS.get(key)
    if not preset:
        print(colorize("未找到该预设。", "warning"))
        return
    print(colorize(
        f"编辑 {preset.name} [{key}]（{_preset_status_label(key)}）", "heading"
    ))
    name = _prompt_text_default("显示名称", preset.name)
    description = _prompt_text_default("描述", preset.description)
    tickers = list(preset.tickers)
    if _prompt_yes_no("是否调整券池 ETF？", False):
        tickers = _edit_code_list_interactively(tickers)
    try:
        updated = upsert_preset(
            key=key,
            name=name,
            description=description,
            tickers=tickers,
        )
    except ValueError as exc:
        print(colorize(f"保存失败: {exc}", "danger"))
        return
    status = _preset_status_label(updated.key)
    print(colorize(f"券池 {updated.name} [{updated.key}] 已保存（{status}）。", "value_positive"))


def _interactive_create_preset_entry() -> None:
    raw_key = input(colorize("请输入新的预设键值（示例 growth_sat）：", "prompt")).strip()
    if not raw_key:
        print(colorize("未输入键值。", "warning"))
        return
    key = raw_key
    if key in PRESETS:
        if not _prompt_yes_no("该键值已存在，是否覆盖？", False):
            print(colorize("已取消新建。", "warning"))
            return
    name = _prompt_text_default("显示名称", key)
    description = _prompt_text_default("描述", "")
    tickers = _edit_code_list_interactively([])
    try:
        created = upsert_preset(
            key=key,
            name=name,
            description=description,
            tickers=tickers,
        )
    except ValueError as exc:
        print(colorize(f"保存失败: {exc}", "danger"))
        return
    status = _preset_status_label(created.key)
    print(colorize(f"新增券池 {created.name} [{created.key}] 已保存（{status}）。", "value_positive"))


def _interactive_reset_preset_entry() -> None:
    key = _select_preset_key("请选择需要恢复默认值的预设：")
    if not key:
        return
    if key not in DEFAULT_PRESETS:
        print(colorize("该预设为自定义条目，可直接删除。", "warning"))
        return
    if not has_custom_override(key):
        print(colorize("当前已是默认定义，无需恢复。", "info"))
        return
    if not _prompt_yes_no("确定恢复为默认券池定义？", True):
        return
    try:
        success = reset_preset(key)
    except ValueError as exc:
        print(colorize(f"恢复失败: {exc}", "danger"))
        return
    if success:
        print(colorize(f"预设 {key} 已恢复默认值。", "value_positive"))
    else:
        print(colorize("恢复失败，请稍后重试。", "danger"))


def _interactive_delete_preset_entry() -> None:
    key = _select_preset_key("请选择需要删除的预设：")
    if not key:
        return
    if key in DEFAULT_PRESETS:
        if has_custom_override(key):
            if _prompt_yes_no("该预设为内置，是否仅删除自定义覆盖？", True):
                try:
                    if reset_preset(key):
                        print(colorize(f"已移除 {key} 的自定义覆盖。", "value_positive"))
                        return
                except ValueError as exc:
                    print(colorize(f"操作失败: {exc}", "danger"))
                    return
        print(colorize("内置预设无法彻底删除，可通过“恢复默认”重置。", "warning"))
        return
    if not _prompt_yes_no(f"确认删除自定义预设 {key}？", False):
        return
    try:
        removed = delete_preset(key)
    except ValueError as exc:
        print(colorize(f"删除失败: {exc}", "danger"))
        return
    if removed:
        print(colorize(f"已删除自定义预设 {key}。", "value_positive"))
    else:
        print(colorize("未找到对应的自定义预设。", "warning"))


def _show_preset_settings_menu() -> None:
    while True:
        options = [
            {"key": "1", "label": "查看预设清单"},
            {"key": "2", "label": "编辑现有预设"},
            {"key": "3", "label": "新增或覆盖预设"},
            {"key": "4", "label": "恢复默认预设"},
            {"key": "5", "label": "删除自定义预设"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 券池预设管理 ─" + "─" * 16,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice == "1":
            _print_presets()
            continue
        if choice == "2":
            _interactive_edit_preset_entry()
            continue
        if choice == "3":
            _interactive_create_preset_entry()
            continue
        if choice == "4":
            _interactive_reset_preset_entry()
            continue
        if choice == "5":
            _interactive_delete_preset_entry()
            continue
        if choice in {"0", "__escape__"}:
            return
        print(colorize("无效指令，请重新输入。", "warning"))


# Moved to business.analysis_presets
from .business import print_analysis_presets as _business_print_analysis_presets

def _print_analysis_presets() -> None:
    _business_print_analysis_presets(ANALYSIS_PRESETS)


from .analysis_presets import preset_status_label as _analysis_preset_status_label


def _select_analysis_preset_key(prompt: str) -> Optional[str]:
    if not ANALYSIS_PRESETS:
        print(colorize("暂无分析预设。", "warning"))
        return None
    print(colorize(prompt, "heading"))
    keys = sorted(ANALYSIS_PRESETS.keys())
    for idx, key in enumerate(keys, start=1):
        preset = ANALYSIS_PRESETS[key]
        marker = _analysis_preset_status_label(key)
        line = f" {idx:>2}. {preset.name} [{key}] ({marker})"
        print(colorize(line, "menu_text"))
    choice = input(colorize("请输入名称或编号: ", "prompt")).strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(keys):
            return keys[idx - 1]
    if choice and choice in ANALYSIS_PRESETS:
        return choice
    print(colorize("未找到对应分析预设。", "warning"))
    return None


# Moved to business.analysis_presets
from .business import print_analysis_preset_details as _business_print_analysis_preset_details

def _print_analysis_preset_details(key: str, preset: AnalysisPreset) -> None:
    _business_print_analysis_preset_details(key, preset, status_label_func=_analysis_preset_status_label)


def _interactive_edit_analysis_preset_entry(existing_key: Optional[str] = None) -> None:
    key = existing_key or _select_analysis_preset_key("请选择要编辑的分析预设：")
    if not key:
        return
    preset = ANALYSIS_PRESETS.get(key)
    if not preset:
        print(colorize("未找到该分析预设。", "warning"))
        return
    _print_analysis_preset_details(key, preset)
    name = _prompt_text_default("显示名称", preset.name)
    description = _prompt_text_default("描述", preset.description)
    windows = _prompt_windows_with_default(preset.momentum_windows)
    current_weights = list(preset.momentum_weights) if preset.momentum_weights else None
    weights = _prompt_weights_for_windows(current_weights, len(windows))
    if preset.momentum_skip_windows and len(preset.momentum_skip_windows) == len(windows):
        skip_values: Optional[List[int]] = list(preset.momentum_skip_windows)
    else:
        skip_values = None
    corr_window = _prompt_positive_int_default("相关系数窗口（日）", preset.corr_window)
    chop_window = _prompt_positive_int_default("Chop 指数窗口", preset.chop_window)
    trend_window = _prompt_positive_int_default("趋势斜率窗口", preset.trend_window)
    rank_lookback = _prompt_positive_int_default("动量排名回溯天数", preset.rank_lookback)
    notes_raw = _prompt_text_default("备注", preset.notes or "")
    notes = notes_raw.strip() or None
    try:
        updated = upsert_analysis_preset(
            key=key,
            name=name,
            description=description,
            momentum_windows=windows,
            momentum_weights=weights,
            momentum_skip_windows=skip_values,
            corr_window=corr_window,
            chop_window=chop_window,
            trend_window=trend_window,
            rank_lookback=rank_lookback,
            notes=notes,
        )
    except ValueError as exc:
        print(colorize(f"保存失败: {exc}", "danger"))
        return
    status = _analysis_preset_status_label(updated.key)
    print(colorize(f"分析预设 {updated.name} [{updated.key}] 已保存（{status}）。", "value_positive"))


def _interactive_create_analysis_preset_entry() -> None:
    raw_key = input(colorize("请输入新的分析预设键值: ", "prompt")).strip()
    if not raw_key:
        print(colorize("未输入键值。", "warning"))
        return
    key = raw_key
    if key in ANALYSIS_PRESETS:
        if not _prompt_yes_no("该键值已存在，是否覆盖？", False):
            print(colorize("已取消新建。", "warning"))
            return
    name = _prompt_text_default("显示名称", key)
    description = _prompt_text_default("描述", "")
    windows = _prompt_windows_with_default([20, 60])
    weights = _prompt_weights_for_windows(None, len(windows))
    corr_window = _prompt_positive_int_default("相关系数窗口（日）", 60)
    chop_window = _prompt_positive_int_default("Chop 指数窗口", 14)
    trend_window = _prompt_positive_int_default("趋势斜率窗口", 90)
    rank_lookback = _prompt_positive_int_default("动量排名回溯天数", 5)
    notes_raw = _prompt_text_default("备注", "")
    notes = notes_raw.strip() or None
    try:
        created = upsert_analysis_preset(
            key=key,
            name=name,
            description=description,
            momentum_windows=windows,
            momentum_weights=weights,
            corr_window=corr_window,
            chop_window=chop_window,
            trend_window=trend_window,
            rank_lookback=rank_lookback,
            notes=notes,
        )
    except ValueError as exc:
        print(colorize(f"保存失败: {exc}", "danger"))
        return
    status = _analysis_preset_status_label(created.key)
    print(colorize(f"新增分析预设 {created.name} [{created.key}] 已保存（{status}）。", "value_positive"))


def _interactive_reset_analysis_preset_entry() -> None:
    key = _select_analysis_preset_key("请选择需要恢复默认值的分析预设：")
    if not key:
        return
    if key not in DEFAULT_ANALYSIS_PRESETS:
        print(colorize("该分析预设为自定义条目，可直接删除。", "warning"))
        return
    if not has_custom_analysis_override(key):
        print(colorize("当前已是默认定义，无需恢复。", "info"))
        return
    if not _prompt_yes_no("确定恢复为默认分析预设？", True):
        return
    try:
        success = reset_analysis_preset(key)
    except ValueError as exc:
        print(colorize(f"恢复失败: {exc}", "danger"))
        return
    if success:
        print(colorize(f"分析预设 {key} 已恢复默认值。", "value_positive"))
    else:
        print(colorize("恢复失败，请稍后重试。", "danger"))


def _interactive_delete_analysis_preset_entry() -> None:
    key = _select_analysis_preset_key("请选择需要删除的分析预设：")
    if not key:
        return
    if key in DEFAULT_ANALYSIS_PRESETS:
        if has_custom_analysis_override(key):
            if _prompt_yes_no("该预设为内置，是否仅删除自定义覆盖？", True):
                try:
                    if reset_analysis_preset(key):
                        print(colorize(f"已移除 {key} 的自定义覆盖。", "value_positive"))
                        return
                except ValueError as exc:
                    print(colorize(f"操作失败: {exc}", "danger"))
                    return
        print(colorize("内置分析预设无法彻底删除，可通过“恢复默认”重置。", "warning"))
        return
    if not _prompt_yes_no(f"确认删除自定义分析预设 {key}？", False):
        return
    try:
        removed = delete_analysis_preset(key)
    except ValueError as exc:
        print(colorize(f"删除失败: {exc}", "danger"))
        return
    if removed:
        print(colorize(f"已删除自定义分析预设 {key}。", "value_positive"))
    else:
        print(colorize("未找到对应的自定义分析预设。", "warning"))


def _show_analysis_preset_settings_menu() -> None:
    while True:
        options = [
            {"key": "1", "label": "查看分析预设"},
            {"key": "2", "label": "编辑现有预设"},
            {"key": "3", "label": "新增或覆盖预设"},
            {"key": "4", "label": "恢复默认预设"},
            {"key": "5", "label": "删除自定义预设"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 分析预设管理 ─" + "─" * 16,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice == "1":
            _print_analysis_presets()
            continue
        if choice == "2":
            _interactive_edit_analysis_preset_entry()
            continue
        if choice == "3":
            _interactive_create_analysis_preset_entry()
            continue
        if choice == "4":
            _interactive_reset_analysis_preset_entry()
            continue
        if choice == "5":
            _interactive_delete_analysis_preset_entry()
            continue
        if choice in {"0", "__escape__"}:
            return
        print(colorize("无效指令，请重新输入。", "warning"))


def _find_rqalpha_command() -> Optional[List[str]]:
    venv_cli = Path.home() / "rqalpha_env" / "bin" / "rqalpha"
    if venv_cli.exists():
        return [str(venv_cli)]
    which_cli = shutil.which("rqalpha")
    if which_cli:
        return [which_cli]
    python_candidates = [
        Path.home() / "rqalpha_env" / "bin" / "python",
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for candidate in python_candidates:
        if not candidate:
            continue
        path_obj = Path(candidate) if not isinstance(candidate, Path) else candidate
        if path_obj.exists():
            return [str(path_obj), "-m", "rqalpha"]
    return None


def _run_pip_install(args: List[str], *, index_url: str | None = None) -> bool:
    command = [sys.executable, "-m", "pip", "install", *args]
    if index_url:
        command.extend(["--index-url", index_url])
    printable = " ".join(command)
    print(colorize(f"执行: {printable}", "menu_hint"))
    try:
        result = subprocess.run(command, check=False)
    except Exception as exc:  # noqa: BLE001
        print(colorize(f"pip 调用失败: {exc}", "danger"))
        return False
    if result.returncode == 0:
        print(colorize("安装成功。", "value_positive"))
        return True
    print(colorize(f"命令执行失败（退出码 {result.returncode}）。", "danger"))
    return False


def _ensure_dependency(
    import_name: str,
    *,
    spec: str,
    description: str,
    try_mirror: bool = True,
    success_hint: str | None = None,
) -> bool:
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(colorize(f"缺少 {description}，准备安装 {spec}……", "info"))
    else:
        print(colorize(f"{description} 已安装，无需重复安装。", "info"))
        return True

    installed = _run_pip_install([spec], index_url="https://pypi.org/simple")
    if not installed and try_mirror:
        print(colorize("尝试官方 PyPI 失败，改用清华镜像。", "warning"))
        installed = _run_pip_install([spec], index_url="https://pypi.tuna.tsinghua.edu.cn/simple")
    if not installed:
        print(colorize(f"{description} 安装失败，请手动执行 `pip install {spec}` 后重试。", "danger"))
        return False

    try:
        importlib.import_module(import_name)
    except ImportError as exc:  # noqa: BLE001
        print(colorize(f"{description} 安装完成但导入失败: {exc}", "danger"))
        return False

    if success_hint:
        print(colorize(success_hint, "value_positive"))
    else:
        print(colorize(f"{description} 安装完成。", "value_positive"))
    return True


def _install_optional_dependencies() -> None:
    wcwidth_ok = _ensure_dependency(
        "wcwidth",
        spec="wcwidth>=0.2.13",
        description="终端宽度对齐支持（wcwidth）",
        success_hint="wcwidth 安装完成，表格会按宽字符正确对齐。",
    )

    plotly_ok = _ensure_dependency(
        "plotly",
        spec="plotly==5.24.0",
        description="交互式图表（plotly）",
        success_hint="plotly 安装完成，可在“动量回溯 / 图表”菜单生成交互式图表。",
    )

    if not wcwidth_ok:
        print(
            colorize(
                "若终端排版仍存在错位，请手动执行 `pip install wcwidth>=0.2.13` 后重新运行。",
                "warning",
            )
        )
    if not plotly_ok:
        print(
            colorize(
                "若仍需生成交互式图表，可访问 https://pypi.org/project/plotly/#files 手动下载 whl 后执行 `pip install <文件路径>`。",
                "warning",
            )
        )


# Moved to business.config (57 lines)
from .business import configure_cli_theme_interactive as _biz_config_cli_theme

def _configure_cli_theme() -> None:
    _biz_config_cli_theme(
        current_theme=_STYLE_THEME,
        theme_order=_CLI_THEME_ORDER,
        theme_info=_CLI_THEME_INFO,
        available_themes=_CLI_THEMES,
        apply_theme_func=_apply_cli_theme,
        render_sample_func=_render_theme_sample,
        prompt_menu_choice_func=_prompt_menu_choice,
        colorize_func=colorize,
    )


# Moved to business.config (72 lines)
from .business import configure_plot_style_interactive as _biz_config_plot_style

def _configure_plot_style() -> None:
    global _PLOT_TEMPLATE, _PLOT_LINE_WIDTH

    def set_template(template: str) -> None:
        global _PLOT_TEMPLATE
        _PLOT_TEMPLATE = template
        _update_setting(_SETTINGS, "plot_template", _PLOT_TEMPLATE)

    def set_line_width(width: float) -> None:
        global _PLOT_LINE_WIDTH
        _PLOT_LINE_WIDTH = width
        _update_setting(_SETTINGS, "plot_line_width", _PLOT_LINE_WIDTH)

    _biz_config_plot_style(
        current_template=_PLOT_TEMPLATE,
        current_line_width=_PLOT_LINE_WIDTH,
        current_cli_theme=_STYLE_THEME,
        cli_theme_info=_CLI_THEME_INFO,
        set_template_func=set_template,
        set_line_width_func=set_line_width,
        prompt_menu_choice_func=_prompt_menu_choice,
        colorize_func=colorize,
        prompt_input_func=input,
    )


# Moved to business.config (44 lines)
from .business import configure_correlation_threshold_interactive as _biz_config_corr_threshold

def _configure_correlation_threshold() -> None:
    _biz_config_corr_threshold(
        current_threshold=_CORRELATION_ALERT_THRESHOLD,
        validate_func=_validate_corr_threshold,
        set_threshold_func=_set_correlation_alert_threshold,
        prompt_menu_choice_func=_prompt_menu_choice,
        colorize_func=colorize,
        prompt_input_func=input,
    )


# Moved to business.config (63 lines)
from .business import configure_signal_thresholds_interactive as _biz_config_signal_thresholds

def _configure_signal_thresholds() -> None:
    _biz_config_signal_thresholds(
        momentum_lookback=_MOMENTUM_SIGNIFICANCE_LOOKBACK,
        momentum_threshold=_MOMENTUM_SIGNIFICANCE_THRESHOLD,
        trend_adx=_TREND_CONSISTENCY_ADX,
        trend_chop=_TREND_CONSISTENCY_CHOP,
        trend_fast_span=_TREND_FAST_SPAN,
        trend_slow_span=_TREND_SLOW_SPAN,
        set_momentum_lookback_func=_set_momentum_significance_lookback,
        set_momentum_threshold_func=_set_momentum_significance_threshold,
        set_trend_adx_func=_set_trend_consistency_adx,
        set_trend_chop_func=_set_trend_consistency_chop,
        set_trend_fast_span_func=_set_trend_fast_span,
        set_trend_slow_span_func=_set_trend_slow_span,
        colorize_func=colorize,
        prompt_input_func=input,
    )


# Moved to business.config (103 lines)
from .business import configure_stability_settings_interactive as _biz_config_stability

def _configure_stability_settings() -> None:
    _biz_config_stability(
        current_method=_STABILITY_METHOD,
        current_window=_STABILITY_WINDOW,
        current_top_n=_STABILITY_TOP_N,
        current_weight=_STABILITY_WEIGHT,
        set_method_func=_set_stability_method,
        set_window_func=_set_stability_window,
        set_top_n_func=_set_stability_top_n,
        set_weight_func=_set_stability_weight,
        prompt_menu_choice_func=_prompt_menu_choice,
        colorize_func=colorize,
        prompt_input_func=input,
    )


# Moved to business.bundle (72 lines)
from .business import update_data_bundle_interactive as _biz_update_bundle

def _update_data_bundle() -> None:
    global _LAST_BUNDLE_REFRESH, _LAST_BACKTEST_CONTEXT, _BUNDLE_STATUS_CACHE, _BUNDLE_UPDATE_PROMPTED

    if _BUNDLE_STATUS_CACHE is None:
        _BUNDLE_STATUS_CACHE = {}

    def on_refresh():
        global _LAST_BUNDLE_REFRESH, _LAST_BACKTEST_CONTEXT, _BUNDLE_STATUS_CACHE, _BUNDLE_UPDATE_PROMPTED
        _LAST_BUNDLE_REFRESH = dt.datetime.now()
        _LAST_BACKTEST_CONTEXT = None
        _BUNDLE_STATUS_CACHE = None
        _BUNDLE_UPDATE_PROMPTED = False

    _biz_update_bundle(
        bundle_status_func=lambda force, cache: _bundle_status(force_refresh=force, cache=cache or _BUNDLE_STATUS_CACHE),
        find_rqalpha_func=_find_rqalpha_command,
        on_refresh_callback=on_refresh,
        wait_for_ack_func=_wait_for_ack,
        colorize_func=colorize,
    )


def _normalize_momentum_weights(
    windows: Sequence[int], weights: Sequence[float] | None
) -> List[float]:
    if not windows:
        raise ValueError("动量窗口不能为空。")
    window_list = [int(win) for win in windows]
    if weights and len(weights) == len(window_list):
        normalized = [float(weight) for weight in weights]
        total = sum(normalized)
        if not total:
            normalized = [1.0 / len(window_list) for _ in window_list]
        else:
            normalized = [weight / total for weight in normalized]
    else:
        normalized = [1.0 / len(window_list) for _ in window_list]
    return [round(weight, 6) for weight in normalized]


def _export_rqalpha_strategy(
    destination: Path,
    universe: Sequence[str],
    windows: Sequence[int],
    weights: Sequence[float] | None,
    top_n: int,
    frequency: str,
    start_date: Optional[str],
    end_date: Optional[str],
    label: str,
) -> Path:
    clean_universe = sorted({code.upper() for code in universe if code})
    if not clean_universe:
        raise ValueError("策略导出失败：无可用的 ETF 列表。")
    window_list = [int(win) for win in windows]
    if not window_list:
        raise ValueError("策略导出失败：动量窗口未设置。")
    normalized_weights = _normalize_momentum_weights(window_list, weights)
    max_window = max(window_list)
    capped_top = max(1, min(int(top_n), len(clean_universe)))

    destination = destination.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if frequency == "weekly":
        schedule_line = "scheduler.run_weekly(rebalance, weekday=0)"
        schedule_comment = "# 每周周一开盘重新评估持仓"
    elif frequency == "daily":
        schedule_line = "scheduler.run_daily(rebalance)"
        schedule_comment = "# 每个交易日开盘检查持仓"
    else:
        schedule_line = "scheduler.run_monthly(rebalance, tradingday=1)"
        schedule_comment = "# 每月首个交易日开盘重新评估持仓"

    today = dt.date.today()
    default_start = start_date or (today - dt.timedelta(days=365 * 3)).isoformat()
    default_end = end_date or today.isoformat()
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    universe_repr = "[" + ", ".join(f"\"{code}\"" for code in clean_universe) + "]"
    windows_repr = "[" + ", ".join(str(win) for win in window_list) + "]"
    weights_repr = "[" + ", ".join(f"{weight:.6f}" for weight in normalized_weights) + "]"

    summary_label = label or "自定义参数"

    content = f'''# -*- coding: utf-8 -*-
"""Auto-generated RQAlpha momentum rotation strategy.

Generated by momentum_cli on {timestamp}.
Preset: {summary_label}
Universe size: {len(clean_universe)}
"""

import numpy as np
from rqalpha.api import history_bars, order_target_percent, scheduler, update_universe, logger

UNIVERSE = {universe_repr}
MOMENTUM_WINDOWS = {windows_repr}
MOMENTUM_WEIGHTS = {weights_repr}
TOP_N = {capped_top}
MAX_WINDOW = {max_window}

__config__ = {{
    "base": {{
        "start_date": "{default_start}",
        "end_date": "{default_end}",
        "benchmark": "000300.XSHG",
        "accounts": {{"stock": 100000}},
    }},
    "extra": {{
        "log_level": "info",
    }},
}}


{schedule_comment}
def init(context):
    context.etfs = list(UNIVERSE)
    context.windows = list(MOMENTUM_WINDOWS)
    context.weights = list(MOMENTUM_WEIGHTS)
    context.top_n = TOP_N
    context.max_window = MAX_WINDOW
    update_universe(context.etfs)
    {schedule_line}
    logger.info("Initialized with %d ETFs and top_n=%d", len(context.etfs), context.top_n)


def _compute_momentum(context, code):
    bars = history_bars(code, context.max_window + 1, "1d", "close")
    if bars is None or len(bars) < context.max_window + 1:
        return None
    prices = np.array(bars, dtype=float)
    latest = prices[-1]
    score = 0.0
    for window, weight in zip(context.windows, context.weights):
        past = prices[-window]
        if past <= 0:
            continue
        score += weight * (latest / past - 1.0)
    return float(score)


def rebalance(context, bar_dict):
    scored = []
    for code in context.etfs:
        score = _compute_momentum(context, code)
        if score is not None:
            scored.append((code, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    targets = [code for code, _ in scored[: context.top_n]]
    current = set(context.portfolio.positions.keys())
    target_set = set(targets)

    for code in current - target_set:
        order_target_percent(code, 0)

    if not targets:
        logger.warning("Momentum screen empty; no positions taken.")
        return

    weight = 1.0 / len(targets)
    for code in targets:
        order_target_percent(code, weight)
    logger.info("Rebalanced into %s", ", ".join(targets))
'''

    destination.write_text(content, encoding="utf-8")
    return destination


# Moved to utils.helpers
from .utils import dedup_codes as _utils_dedup_codes

def _dedup_codes(codes: Iterable[str]) -> List[str]:
    return _utils_dedup_codes(codes)


def _show_codes(codes: Sequence[str]) -> None:
    for idx, code in enumerate(codes, start=1):
        label = get_label(code)
        if label:
            display = f"{label} ({code})"
        else:
            display = code
        print(colorize(f" {idx:>2}. {display}", "menu_text"))


def _available_preset_codes(preset_key: str, existing: Sequence[str]) -> List[str]:
    preset = PRESETS.get(preset_key.lower())
    if not preset:
        return []
    existing_set = {code.upper() for code in existing}
    return [code for code in preset.tickers if code.upper() not in existing_set]


def _prompt_select_from_preset(preset_key: str, existing: Sequence[str]) -> List[str]:
    available = _available_preset_codes(preset_key, existing)
    if not available:
        preset = PRESETS.get(preset_key.lower())
        name = preset.name if preset else preset_key
        print(colorize(f"预设 {name} 中的 ETF 已全部包含。", "warning"))
        return []
    preset = PRESETS[preset_key.lower()]
    print(colorize(f"可添加的 {preset.name} ETF：", "heading"))
    for idx, code in enumerate(available, start=1):
        label = get_label(code)
        print(colorize(f" {idx}. {label} ({code})", "menu_text"))
    while True:
        raw = input(colorize("输入需要添加的序号（支持逗号/空格分隔，直接回车取消）: ", "prompt")).strip()
        if not raw:
            return []
        indices = _parse_index_list(raw, len(available))
        if indices is None:
            print(colorize("输入无效，请输入列表中的数字序号。", "warning"))
            continue
        return [available[idx - 1] for idx in indices]


def _parse_index_list(raw: str, upper_bound: int) -> Optional[List[int]]:
    tokens = [token for token in re.split(r"[ ,，、]+", raw) if token]
    indices: List[int] = []
    for token in tokens:
        if not token.isdigit():
            return None
        value = int(token)
        if value < 1 or value > upper_bound:
            return None
        indices.append(value)
    return sorted(set(indices))


def _prompt_yes_no(question: str, default: bool = True) -> bool:
    default_label = "是" if default else "否"
    prompt_text = f"{question} 默认{default_label}，按 y/n 或回车确认: "

    if _supports_interactive_menu():
        while True:
            sys.stdout.write(colorize(prompt_text, "prompt"))
            sys.stdout.flush()
            key = _read_keypress()
            if key is None:
                sys.stdout.write("\n")
                break
            if key == "ENTER":
                sys.stdout.write("\n")
                return default
            if len(key) == 1:
                lower = key.lower()
                if lower in {"y", "yes", "是"}:
                    sys.stdout.write(f"{key}\n")
                    return True
                if lower in {"n", "no", "否"}:
                    sys.stdout.write(f"{key}\n")
                    return False
            if key == "ESC":
                sys.stdout.write("\n")
                return default
            sys.stdout.write("\a")
            sys.stdout.flush()
    # Fallback: standard input
    while True:
        raw = input(colorize(prompt_text, "prompt")).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "是"}:
            return True
        if raw in {"n", "no", "否"}:
            return False
        print(colorize("请输入 y 或 n。", "warning"))


# Moved to ui.input.wait_for_key
from .ui import wait_for_key as _ui_wait_for_key

def _wait_for_ack(message: str = "按任意键继续...") -> None:
    if not _INTERACTIVE_MODE:
        return
    _ui_wait_for_key(message)


def _prompt_date(question: str, default: Optional[str] = None) -> Optional[str]:
    hint = f"默认 {default}" if default else "按回车跳过"
    while True:
        raw = input(colorize(f"{question}（YYYY-MM-DD，{hint}）: ", "prompt")).strip()
        if not raw:
            return default
        try:
            dt.datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print(colorize("日期格式不正确，请重新输入。", "warning"))


def _prompt_int(question: str, default: int) -> int:
    while True:
        raw = input(colorize(f"{question}（默认 {default}）: ", "prompt")).strip()
        if not raw:
            return default
        if raw.isdigit():
            return int(raw)
        print(colorize("请输入正整数。", "warning"))


def _prompt_windows(default_windows: Sequence[int]) -> Sequence[int]:
    default_text = ",".join(str(win) for win in default_windows)
    raw = input(
        colorize(
            f"动量窗口（逗号分隔，默认 {default_text}）: ", "prompt"
        )
    ).strip()
    if not raw:
        return tuple(default_windows)
    tokens = [token for token in re.split(r"[ ,，、]+", raw) if token]
    try:
        windows = [int(token) for token in tokens]
    except ValueError:
        print(colorize("动量窗口需为整数，已回退到默认值。", "warning"))
        return tuple(default_windows)
    windows = [win for win in windows if win > 0]
    return tuple(windows) if windows else tuple(default_windows)


def _prompt_codes_input(question: str) -> List[str]:
    raw = input(colorize(f"{question}: ", "prompt")).strip()
    tokens = [token for token in re.split(r"[ ,，、]+", raw) if token]
    return _dedup_codes(tokens)


def _interactive_remove_codes(codes: List[str]) -> List[str]:
    core_preset = PRESETS.get("core")
    satellite_preset = PRESETS.get("satellite")
    core_set = {code.upper() for code in core_preset.tickers} if core_preset else set()
    satellite_set = {code.upper() for code in satellite_preset.tickers} if satellite_preset else set()
    updated = list(codes)
    while True:
        if not updated:
            print(colorize("券池不能为空，已恢复上一次的选择。", "danger"))
            return list(codes)
        print(colorize("\n当前券池：", "heading"))
        _show_codes(updated)
        options = [
            {"key": "1", "label": "按序号剔除"},
            {"key": "2", "label": "一键剔除核心仓 ETF"},
            {"key": "3", "label": "一键剔除卫星仓 ETF"},
            {"key": "0", "label": "完成剔除"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 券池剔除 ─" + "─" * 18,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice in {"0", "__escape__"}:
            break
        if choice == "1":
            while True:
                raw = input(
                    colorize(
                        "输入需要剔除的序号（逗号/空格分隔，直接回车取消）: ",
                        "prompt",
                    )
                ).strip()
                if not raw:
                    break
                indices = _parse_index_list(raw, len(updated))
                if indices is None:
                    print(colorize("输入有误，请重新选择。", "warning"))
                    continue
                remaining = [
                    code
                    for idx, code in enumerate(updated, start=1)
                    if idx not in set(indices)
                ]
                if not remaining:
                    print(colorize("券池不能为空，请保留至少 1 只 ETF。", "danger"))
                    continue
                updated = remaining
                print(colorize("剔除后券池：", "heading"))
                _show_codes(updated)
                break
            continue
        if choice == "2":
            filtered = [code for code in updated if code.upper() not in core_set]
            if len(filtered) == len(updated):
                print(colorize("当前券池中无核心仓可剔除。", "info"))
                continue
            if not filtered:
                print(colorize("券池不能为空，请至少保留 1 只 ETF。", "danger"))
                continue
            updated = filtered
            print(colorize("已剔除核心仓 ETF：", "heading"))
            _show_codes(updated)
            continue
        if choice == "3":
            filtered = [code for code in updated if code.upper() not in satellite_set]
            if len(filtered) == len(updated):
                print(colorize("当前券池中无卫星仓可剔除。", "info"))
                continue
            if not filtered:
                print(colorize("券池不能为空，请至少保留 1 只 ETF。", "danger"))
                continue
            updated = filtered
            print(colorize("已剔除卫星仓 ETF：", "heading"))
            _show_codes(updated)
            continue
        print(colorize("指令无效，请输入 0-3。", "warning"))
    return _dedup_codes(updated)


def _interactive_add_codes(codes: List[str]) -> List[str]:
    updated = list(codes)
    while True:
        print(colorize("\n当前券池：", "heading"))
        _show_codes(updated)
        options = [
            {"key": "1", "label": "从核心仓预设添加"},
            {"key": "2", "label": "从卫星仓预设添加"},
            {"key": "3", "label": "手动输入代码"},
            {"key": "0", "label": "完成新增"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 券池扩充 ─" + "─" * 18,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice in {"0", "__escape__"}:
            break
        if choice == "1":
            additions = _prompt_select_from_preset("core", updated)
        elif choice == "2":
            additions = _prompt_select_from_preset("satellite", updated)
        elif choice == "3":
            additions = _prompt_codes_input("请输入要新增的代码（逗号或空格分隔）")
        else:
            print(colorize("指令无效，请输入 0-3。", "warning"))
            continue
        if not additions:
            continue
        updated.extend(additions)
        updated = _dedup_codes(updated)
        print(colorize("加入新增代码后的券池：", "heading"))
        _show_codes(updated)
    return _dedup_codes(updated)


def _cleanup_generated_artifacts() -> None:
    candidates = [
        (Path("results"), "results 目录（图表与 CSV 导出）", True),
        (Path("strategies") / "momentum_strategy.py", "自动导出的策略脚本 momentum_strategy.py", False),
        (TEMPLATE_STORE_PATH, "templates.json（保存的分析模板）", False),
    ]
    existing = [item for item in candidates if item[0].exists()]
    if not existing:
        print(colorize("暂无可清理的文件或目录。", "info"))
        return
    print(colorize("可清理的项目：", "heading"))
    for idx, (path, desc, _) in enumerate(existing, start=1):
        print(colorize(f" {idx}. {desc} -> {path}", "menu_text"))
    for path, desc, default in existing:
        if not _prompt_yes_no(f"是否删除 {desc}？", default):
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except Exception as exc:  # noqa: BLE001
            print(colorize(f"删除 {path} 失败: {exc}", "danger"))
        else:
            print(colorize(f"已删除 {desc}", "value_positive"))


def _interactive_show_rank_snapshot(state: dict) -> None:
    result = state["result"]
    rank_df = result.rank_history.dropna(how="all")
    if rank_df.empty:
        print(colorize("暂无排名历史数据。", "warning"))
        _wait_for_ack()
        return
    default_date = rank_df.index[-1].date().isoformat()
    date_str = _prompt_date("选择查看动量排名的日期", default_date)
    target_ts = pd.to_datetime(date_str)
    try:
        loc = rank_df.index.get_loc(target_ts, method="pad")
    except KeyError:
        print(colorize("所选日期早于数据起点，无法回溯。", "warning"))
        _wait_for_ack()
        return
    actual_ts = rank_df.index[loc]
    top_default = min(10, len(rank_df.columns))
    top_n = _prompt_int("显示前多少名？", max(1, top_default))
    snapshot = rank_df.iloc[loc].sort_values()
    top_series = snapshot.head(top_n)
    momentum_df = result.momentum_scores
    momentum_row = momentum_df.loc[actual_ts] if actual_ts in momentum_df.index else None
    print(colorize(f"\n{actual_ts.date()} 的动量排名（越小越好）：", "heading"))
    for idx, (code, rank_value) in enumerate(top_series.items(), start=1):
        label = _format_label(code)
        rank_text = f"{int(round(rank_value)) :02d}"
        score_text = "-"
        if momentum_row is not None and code in momentum_row:
            score_text = f"{momentum_row[code]:.4f}"
        close_text = "-"
        ma_text = "-"
        raw = result.raw_data.get(code)
        if raw is not None and actual_ts in raw.index:
            close_val = raw.loc[actual_ts, "close"]
            close_text = f"{close_val:.4f}"
            ma_series = moving_average(raw["close"], 200)
            if actual_ts in ma_series.index and pd.notna(ma_series.loc[actual_ts]):
                ma_text = f"{ma_series.loc[actual_ts]:.4f}"
        line = (
            f" {idx:02d}. {label} | 排名:{rank_text} | 动量:{score_text} | 收盘:{close_text} | MA200:{ma_text}"
        )
        print(colorize(line, "menu_text"))
    if actual_ts != target_ts:
        print(colorize("（提示：未找到精确日期，已展示最近的交易日数据。）", "menu_hint"))
    _wait_for_ack()


def _interactive_generate_interactive_chart(state: dict, kind: str) -> None:
    result = state["result"]
    config = state["config"]
    core_preset = PRESETS.get("core")
    satellite_preset = PRESETS.get("satellite")
    core_set = {code.upper() for code in core_preset.tickers} if core_preset else set()
    sat_set = {code.upper() for code in satellite_preset.tickers} if satellite_preset else set()
    summary_df = result.summary
    if kind == "momentum":
        data = result.momentum_scores.copy()
        title = "动量得分历史"
        y_label = "动量得分"
        filename = "momentum_scores_interactive.html"
        invert = False
        top_codes = summary_df.sort_values("momentum_score", ascending=False)["etf"].head(6)
    elif kind == "rank":
        data = result.rank_history.copy()
        title = "动量排名历史（数值越小越好）"
        y_label = "排名"
        filename = "momentum_ranks_interactive.html"
        invert = True
        top_codes = summary_df.sort_values("momentum_rank", ascending=True)["etf"].head(6)
    else:
        return
    default_visible_codes = {str(code).upper() for code in top_codes if isinstance(code, str) and code}
    if not default_visible_codes:
        default_visible_codes = None
    start = pd.to_datetime(config.start_date) if config.start_date else None
    end = pd.to_datetime(config.end_date) if config.end_date else None
    if start is not None:
        data = data[data.index >= start]
    if end is not None:
        data = data[data.index <= end]
    data = data.dropna(how="all")
    all_columns = list(data.columns)
    if len(all_columns) > 20:
        default_keep = min(12, max(6, len(all_columns) // 3))
        print(colorize(f"当前共有 {len(all_columns)} 条曲线，为避免图表过于杂乱，请选择保留数量。", "menu_hint"))
        keep_n = _prompt_int("图表最多保留多少条曲线？", default_keep)
        keep_n = max(1, min(len(all_columns), keep_n))
        preferred = []
        if not summary_df.empty:
            preferred = [
                str(code)
                for code in summary_df.sort_values("momentum_rank")["etf"].tolist()
                if isinstance(code, str)
            ]
        keep_columns: list[str] = []
        for code in preferred + all_columns:
            if code in data.columns and code not in keep_columns:
                keep_columns.append(code)
            if len(keep_columns) >= keep_n:
                break
        data = data[keep_columns]
        summary_df = summary_df[summary_df["etf"].isin(keep_columns)] if not summary_df.empty else summary_df
        print(colorize(f"已保留 {len(data.columns)} 条曲线，可在图例中进一步隐藏。", "menu_hint"))
    path = _generate_interactive_plot(
        data,
        title=title,
        yaxis_title=y_label,
        output_dir=Path(config.output_dir),
        filename=filename,
        invert_y=invert,
        core_codes=core_set if core_set else None,
        satellite_codes=sat_set if sat_set else None,
        default_visible_codes=default_visible_codes,
    )
    if path is not None:
        print(colorize(f"已生成图表: {path}", "value_positive"))
        _maybe_open_browser(path)
    _wait_for_ack()


def _select_codes_interactively() -> Optional[List[str]]:
    default_choice = "3"
    while True:
        options = [
            {"key": "1", "label": "核心仓 (core)"},
            {"key": "2", "label": "卫星仓 (satellite)"},
            {"key": "3", "label": "核心 + 卫星"},
            {"key": "4", "label": "自定义输入代码"},
            {"key": "5", "label": "查看券池预设说明"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 券池来源选择 ─" + "─" * 16,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · Enter 默认 3",
            default_key=default_choice,
        )
        if choice in {"0", "__escape__"}:
            return None
        if choice == "5":
            _print_presets()
            continue
        if choice == "1":
            preset = PRESETS.get("core")
            if not preset:
                print(colorize("未定义核心仓预设，请先配置。", "warning"))
                continue
            codes = list(preset.tickers)
            break
        if choice == "2":
            preset = PRESETS.get("satellite")
            if not preset:
                print(colorize("未定义卫星仓预设，请先配置。", "warning"))
                continue
            codes = list(preset.tickers)
            break
        if choice == "3":
            core_preset = PRESETS.get("core")
            satellite_preset = PRESETS.get("satellite")
            combined: List[str] = []
            if core_preset:
                combined.extend(core_preset.tickers)
            if satellite_preset:
                combined.extend(satellite_preset.tickers)
            if not combined:
                print(colorize("未找到核心或卫星预设，请先配置。", "warning"))
                continue
            codes = _dedup_codes(combined)
            break
        if choice == "4":
            codes = _prompt_codes_input("请输入 ETF 代码（逗号或空格分隔）")
            if codes:
                break
            print(colorize("未输入任何代码，请重试。", "warning"))
            continue
        print(colorize("指令无效，请输入 0-5。", "warning"))
    codes = _dedup_codes(codes)
    print("\n" + colorize("已选择的券池：", "heading"))
    _show_codes(codes)
    if _prompt_yes_no("是否剔除部分 ETF？", False):
        codes = _interactive_remove_codes(codes)
    if _prompt_yes_no("是否额外添加其他 ETF？", False):
        codes = _interactive_add_codes(codes)
    print("\n" + colorize("最终券池：", "heading"))
    _show_codes(codes)
    return codes


def _choose_analysis_preset_interactively() -> AnalysisPreset:
    presets = list(ANALYSIS_PRESETS.values())
    while True:
        options = []
        for idx, preset in enumerate(presets, start=1):
            label = f"{preset.name} [{preset.key}] - {preset.description}"
            options.append({"key": str(idx), "label": label})
        options.append({"key": "0", "label": "查看预设详情"})
        choice = _prompt_menu_choice(
            options,
            title="┌─ 分析预设选择 ─" + "─" * 16,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
            allow_escape=False,
        )
        if choice == "0":
            _print_analysis_presets()
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(presets):
                return presets[idx - 1]
        print(colorize("编号超出范围，请重新选择。", "warning"))


def _collect_parameters_interactive() -> Optional[dict]:
    codes = _select_codes_interactively()
    if not codes:
        return None
    analysis_preset = _choose_analysis_preset_interactively()
    defaults = AnalysisConfig(
        momentum=analysis_preset.momentum_config(),
        corr_window=analysis_preset.corr_window,
        chop_window=analysis_preset.chop_window,
        trend_window=analysis_preset.trend_window,
        rank_change_lookback=analysis_preset.rank_lookback,
        momentum_percentile_lookback=_MOMENTUM_SIGNIFICANCE_LOOKBACK,
        momentum_significance_threshold=_MOMENTUM_SIGNIFICANCE_THRESHOLD,
        trend_consistency_adx_threshold=_TREND_CONSISTENCY_ADX,
        trend_consistency_chop_threshold=_TREND_CONSISTENCY_CHOP,
        trend_consistency_fast_span=_TREND_FAST_SPAN,
        trend_consistency_slow_span=_TREND_SLOW_SPAN,
    )
    momentum_defaults = defaults.momentum
    today = dt.date.today()
    lookback_days = max(365 * 5, max(momentum_defaults.windows) * 4, 750)
    default_start = (today - dt.timedelta(days=lookback_days)).isoformat()
    default_end = today.isoformat()

    start = _prompt_date("开始日期", default_start)
    end = _prompt_date("结束日期", default_end)

    windows = tuple(momentum_defaults.windows)
    weights = (
        tuple(momentum_defaults.weights) if momentum_defaults.weights else None
    )
    skip_windows = (
        tuple(momentum_defaults.skip_windows)
        if momentum_defaults.skip_windows
        else None
    )
    corr_window = defaults.corr_window
    chop_window = defaults.chop_window
    trend_window = defaults.trend_window
    rank_lookback = defaults.rank_change_lookback
    make_plots = False
    export_csv = False
    output_dir = str(defaults.output_dir)

    if analysis_preset:
        summary = (
            f"已应用预设 [{analysis_preset.key}]：动量窗口 {', '.join(str(win) for win in windows)} · "
            f"Corr {corr_window} · Chop {chop_window} · 趋势 {trend_window} · 回溯 {rank_lookback}"
        )
        print(colorize(summary, "menu_hint"))

    analysis_label = (
        f"{analysis_preset.name} [{analysis_preset.key}]"
        if analysis_preset
        else "自定义分析"
    )

    return {
        "codes": codes,
        "start": start,
        "end": end,
        "windows": windows,
        "corr_window": corr_window,
        "make_plots": make_plots,
        "export_csv": export_csv,
        "chop_window": chop_window,
        "trend_window": trend_window,
        "rank_lookback": rank_lookback,
        "output_dir": output_dir,
        "weights": weights,
        "skip_windows": skip_windows,
        "analysis_preset": analysis_preset,
        "presets": [],
        "lang": "zh",
        "stability_method": _STABILITY_METHOD,
        "stability_window": _STABILITY_WINDOW,
        "stability_top_n": _STABILITY_TOP_N,
        "stability_weight": _STABILITY_WEIGHT,
        "analysis_name": analysis_label,
    }


def _run_analysis_with_params(
    params: dict,
    *,
    post_actions: bool = True,
    bundle_context: str | None = None,
    bundle_interactive: bool = True,
) -> dict:
    if bundle_context:
        _maybe_prompt_bundle_refresh(bundle_interactive, bundle_context)
    params.setdefault("presets", [])
    preset: AnalysisPreset | None = params.get("analysis_preset")
    from .business.analysis import build_configs_from_params
    # merge defaults
    params = dict(params)
    params.setdefault("stability_method", _STABILITY_METHOD)
    params.setdefault("stability_window", _STABILITY_WINDOW)
    params.setdefault("stability_top_n", _STABILITY_TOP_N)
    params.setdefault("stability_weight", _STABILITY_WEIGHT)
    params.setdefault("momentum_percentile_lookback", _MOMENTUM_SIGNIFICANCE_LOOKBACK)
    params.setdefault("momentum_significance_threshold", _MOMENTUM_SIGNIFICANCE_THRESHOLD)
    params.setdefault("trend_consistency_adx_threshold", _TREND_CONSISTENCY_ADX)
    params.setdefault("trend_consistency_chop_threshold", _TREND_CONSISTENCY_CHOP)
    params.setdefault("trend_consistency_fast_span", _TREND_FAST_SPAN)
    params.setdefault("trend_consistency_slow_span", _TREND_SLOW_SPAN)

    config, momentum_config = build_configs_from_params(params)

    lang = params.get("lang", "zh")
    from .business.analysis import run_analysis_only
    result = run_analysis_only(config)
    payload = _build_result_payload(result, config, momentum_config, preset, lang)
    report_text = _render_text_report(result, config, momentum_config, preset, lang)
    print(report_text)
    print("")

    if params.get("make_plots"):
        print(colorize("当前版本已禁用图表生成功能。", "warning"))
    if params.get("export_csv"):
        print(colorize("当前版本已禁用 CSV 导出功能。", "warning"))

    if post_actions and preset and _prompt_yes_no("是否基于该预设运行简易回测？", False):
        _run_simple_backtest(result, preset)

    if post_actions and _prompt_yes_no("是否导出为 RQAlpha 策略脚本？", False):
        default_path = Path("strategies") / "momentum_strategy.py"
        raw_path = input(
            colorize(f"输出文件（默认 {default_path}）: ", "prompt")
        ).strip()
        dest_path = Path(raw_path) if raw_path else default_path
        freq_raw = input(
            colorize("调仓频率（monthly/weekly/daily，默认 monthly）: ", "prompt")
        ).strip().lower()
        freq = freq_raw or "monthly"
        if freq not in {"monthly", "weekly", "daily"}:
            print(colorize("频率输入无效，已回退为 monthly。", "warning"))
            freq = "monthly"
        top_n = _prompt_int("策略持仓数量", 2)
        label = f"{preset.name} [{preset.key}]" if preset else "自定义参数"
        try:
            exported = _export_rqalpha_strategy(
                dest_path,
                universe=sorted(result.raw_data.keys()),
                windows=momentum_config.windows,
                weights=momentum_config.weights,
                top_n=top_n,
                frequency=freq,
                start_date=config.start_date,
                end_date=config.end_date,
                label=label,
            )
        except Exception as exc:  # noqa: BLE001
            print(colorize(f"导出失败: {exc}", "danger"))
        else:
            print(colorize(f"已生成策略文件: {exported}", "value_positive"))
            print(colorize("可通过 rqalpha run -f <文件路径> 进行回测。", "menu_hint"))

    analysis_label = params.get("analysis_name")
    if not analysis_label:
        if preset:
            analysis_label = f"{preset.name} [{preset.key}]"
        elif bundle_context:
            analysis_label = bundle_context
        else:
            analysis_label = "自定义分析"
    params.setdefault("analysis_name", analysis_label)

    state = {
        "result": result,
        "config": config,
        "momentum_config": momentum_config,
        "preset": preset,
        "params": params,
        "payload": payload,
        "report_text": report_text,
        "title": analysis_label,
    }

    _record_report_history(state, analysis_label, preset)

    return state


def _get_core_satellite_codes() -> tuple[List[str], List[str]]:
    core_preset = PRESETS.get("core")
    satellite_preset = PRESETS.get("satellite")
    core_codes = _dedup_codes(core_preset.tickers) if core_preset else []
    satellite_codes = _dedup_codes(satellite_preset.tickers) if satellite_preset else []
    return core_codes, satellite_codes


def _choose_backtest_analysis_preset() -> AnalysisPreset:
    if "slow-core" in ANALYSIS_PRESETS:
        return ANALYSIS_PRESETS["slow-core"]
    if ANALYSIS_PRESETS:
        return next(iter(ANALYSIS_PRESETS.values()))
    return AnalysisPreset(
        key="auto",
        name="自动预设",
        description="自动生成的回测分析参数",
        momentum_windows=(60, 120),
        momentum_weights=(0.6, 0.4),
        corr_window=60,
        chop_window=14,
        trend_window=90,
        rank_lookback=5,
    )


def _obtain_backtest_context(
    last_state: Optional[dict], *, allow_reuse: bool = True
) -> Optional[dict]:
    global _LAST_BACKTEST_CONTEXT
    if _LAST_BACKTEST_CONTEXT:
        if _prompt_yes_no("复用最近一次回测加载的数据？", True):
            return _LAST_BACKTEST_CONTEXT
    if allow_reuse and last_state:
        if {"result", "config", "momentum_config"}.issubset(last_state.keys()):
            if _prompt_yes_no("复用最近一次分析结果用于回测？", True):
                context = {
                    "result": last_state["result"],
                    "config": last_state["config"],
                    "momentum_config": last_state["momentum_config"],
                    "preset": last_state.get("preset"),
                }
                _LAST_BACKTEST_CONTEXT = context
                return context
        else:
            print(colorize("最近一次分析缺少所需数据，无法直接复用。", "warning"))
    core_codes, satellite_codes = _get_core_satellite_codes()
    if not core_codes and not satellite_codes:
        print(colorize("请先在券池预设中配置 core 与 satellite，再运行回测。", "warning"))
        return None
    combined_codes = _dedup_codes([*core_codes, *satellite_codes])
    if not combined_codes:
        print(colorize("核心与卫星券池为空，无法运行回测。", "warning"))
        return None
    today = dt.date.today()
    default_start = (today - dt.timedelta(days=365 * 10)).isoformat()
    start = _prompt_optional_date("回测起始日期", default_start)
    if not start:
        start = default_start
    end = _prompt_optional_date("回测结束日期", today.isoformat())
    if end:
        try:
            if dt.datetime.fromisoformat(end).date() < dt.datetime.fromisoformat(start).date():
                print(colorize("结束日期早于起始日期，已忽略结束日期设置。", "warning"))
                end = None
        except ValueError:
            end = None
    analysis_preset = _choose_backtest_analysis_preset()
    momentum_config = analysis_preset.momentum_config()
    config = AnalysisConfig(
        start_date=start,
        end_date=end,
        etfs=combined_codes,
        exclude=(),
        momentum=momentum_config,
        chop_window=analysis_preset.chop_window,
        trend_window=analysis_preset.trend_window,
        corr_window=analysis_preset.corr_window,
        rank_change_lookback=analysis_preset.rank_lookback,
        output_dir=Path("results"),
        make_plots=False,
        momentum_percentile_lookback=_MOMENTUM_SIGNIFICANCE_LOOKBACK,
        momentum_significance_threshold=_MOMENTUM_SIGNIFICANCE_THRESHOLD,
        trend_consistency_adx_threshold=_TREND_CONSISTENCY_ADX,
        trend_consistency_chop_threshold=_TREND_CONSISTENCY_CHOP,
        trend_consistency_fast_span=_TREND_FAST_SPAN,
        trend_consistency_slow_span=_TREND_SLOW_SPAN,
        stability_method=_STABILITY_METHOD,
        stability_window=_STABILITY_WINDOW,
        stability_top_n=_STABILITY_TOP_N,
        stability_weight=_STABILITY_WEIGHT,
    )
    _maybe_prompt_bundle_refresh(True, "回测数据加载")
    print(colorize("正在加载回测所需数据，请稍候……", "menu_hint"))
    try:
        from .business.analysis import run_analysis_only
        result = run_analysis_only(config)
    except Exception as exc:  # noqa: BLE001
        print(colorize(f"数据加载失败: {exc}", "danger"))
        return None
    context = {
        "result": result,
        "config": config,
        "momentum_config": momentum_config,
        "preset": analysis_preset,
    }
    _LAST_BACKTEST_CONTEXT = context
    print(colorize("数据加载完成，可开始回测。", "value_positive"))
    return context


def _run_simple_backtest(result, preset: AnalysisPreset, top_n: int = 2) -> None:
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize("无法回测：价格数据为空。", "warning"))
        return
    returns_df = close_df.pct_change().fillna(0)

    aligned_scores = result.momentum_scores.reindex(close_df.index).ffill()
    if aligned_scores.dropna(how="all").empty:
        print(colorize("无法回测：动量得分为空。", "warning"))
        return
    momentum_df = aligned_scores

    rebalance_dates = close_df.resample("ME").last().index
    if rebalance_dates.empty:
        rebalance_dates = close_df.index

    weights = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    current_codes: List[str] = []
    for date in close_df.index:
        if date in rebalance_dates:
            scores = momentum_df.loc[date].dropna()
            top_codes = scores.sort_values(ascending=False).head(top_n).index.tolist()
            current_codes = [code for code in top_codes if code in close_df.columns]
        if current_codes:
            weights.loc[date, current_codes] = 1.0 / len(current_codes)

    portfolio_returns = (weights.shift().fillna(0) * returns_df).sum(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()
    total_return = cumulative.iloc[-1] - 1 if not cumulative.empty else 0
    periods_per_year = 252
    ann_return = (
        (1 + total_return) ** (periods_per_year / len(portfolio_returns)) - 1
        if len(portfolio_returns) > 0
        else 0
    )
    drawdown = cumulative / cumulative.cummax() - 1 if not cumulative.empty else pd.Series()
    max_drawdown = drawdown.min() if not drawdown.empty else 0
    sharpe = (
        (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(periods_per_year)
        if portfolio_returns.std() != 0
        else 0
    )

    print(colorize("\n=== 简易回测结果 ===", "heading"))
    preset_line = f"预设: {preset.name} [{preset.key}]，每月调仓，持仓上限 {top_n} 条腿"
    print(colorize(preset_line, "menu_text"))
    print(colorize(f"累计收益: {total_return:.2%}", "value_positive" if total_return >= 0 else "value_negative"))
    print(colorize(f"年化收益: {ann_return:.2%}", "value_positive" if ann_return >= 0 else "value_negative"))
    print(colorize(f"最大回撤: {max_drawdown:.2%}", "danger"))
    print(colorize(f"夏普比率: {sharpe:.2f}", "accent" if sharpe > 0 else "warning"))

    if current_codes:
        last_weights = weights.iloc[-1]
        holding_lines: List[str] = []
        for code in current_codes:
            weight = float(last_weights.get(code, 0.0))
            label = _format_label(code)
            holding_lines.append(f"{label}: {weight:.1%}")
        print(colorize("最新持仓结构:", "heading"))
        print(colorize("; ".join(holding_lines), "menu_text"))


#   business.backtest
from .business.backtest import core_satellite_portfolio_returns as _core_satellite_portfolio_returns


# moved to business.backtest
from .business.backtest import calculate_performance_metrics as _calculate_performance_metrics


def _render_backtest_table(rows: List[dict]) -> str:
    if not rows:
        return "暂无可用回测结果。"
    columns = [
        ("label", "区间", "left"),
        ("start", "起始", "left"),
        ("end", "结束", "left"),
        ("days", "交易日", "right"),
        ("total", "累计收益", "right"),
        ("annual", "年化收益", "right"),
        ("vol", "波动率", "right"),
        ("maxdd", "最大回撤", "right"),
        ("sharpe", "夏普", "right"),
        ("note", "备注", "left"),
    ]
    from .utils import formatters as _fmt
    return _fmt.render_table(columns, rows)


def _run_core_satellite_multi_backtest(last_state: Optional[dict] = None) -> None:
    context = _obtain_backtest_context(last_state, allow_reuse=bool(last_state))
    if not context:
        return
    result = context["result"]
    config = context["config"]
    close_df = pd.DataFrame({code: data["close"] for code, data in result.raw_data.items()})
    close_df = close_df.sort_index().dropna(how="all")
    if close_df.empty:
        print(colorize("无法回测：价格数据为空。", "warning"))
        return
    momentum_df = result.momentum_scores
    if momentum_df.empty:
        print(colorize("无法回测：动量得分为空。", "warning"))
        return

    core_codes, satellite_codes = _get_core_satellite_codes()
    if not core_codes and not satellite_codes:
        print(colorize("缺少核心/卫星券池定义，请先在券池预设中配置 core 与 satellite。", "warning"))
        return
    available_columns = set(close_df.columns)
    core_available = [code for code in core_codes if code in available_columns]
    satellite_available = [code for code in satellite_codes if code in available_columns]

    if not core_available:
        print(colorize("核心券池在当前分析结果中无可用标的，将仅使用卫星仓。", "warning"))
    if not satellite_available:
        print(colorize("卫星券池在当前分析结果中无可用标的，将仅使用核心仓。", "warning"))
    if not core_available and not satellite_available:
        print(colorize("核心与卫星券池均无可用标的，无法执行回测。", "danger"))
        return

    horizons = [
        ("近10年", pd.DateOffset(years=10)),
        ("近5年", pd.DateOffset(years=5)),
        ("近2年", pd.DateOffset(years=2)),
        ("近1年", pd.DateOffset(years=1)),
        ("近6个月", pd.DateOffset(months=6)),
        ("近3个月", pd.DateOffset(months=3)),
    ]

    end_date = close_df.index.max()
    rows_for_table: List[dict] = []
    last_holdings: dict[str, float] = {}
    warnings: List[str] = []

    for label, offset in horizons:
        start_candidate = end_date - offset
        mask = close_df.index >= start_candidate
        close_slice = close_df.loc[mask]
        if close_slice.empty:
            continue
        actual_start = close_slice.index[0]
        momentum_slice = momentum_df.reindex(close_slice.index).ffill()
        portfolio_returns, detail = _core_satellite_portfolio_returns(
            close_slice,
            momentum_slice,
            core_available,
            satellite_available,
            core_allocation=0.6,
            satellite_allocation=0.4,
            top_n=2,
        )
        metrics = _calculate_performance_metrics(portfolio_returns)
        if metrics["days"] == 0:
            continue
        note_text = ""
        if metrics["days"] < 40:
            warnings.append(
                f"{label} 数据量仅 {metrics['days']} 个交易日，结果仅供参考。"
            )
            note_text = "样本偏少"
        total_str = "-" if np.isnan(metrics["total_return"]) else f"{metrics['total_return']:.2%}"
        annual_str = "-" if np.isnan(metrics["annualized"]) else f"{metrics['annualized']:.2%}"
        vol_str = "-" if np.isnan(metrics["volatility"]) else f"{metrics['volatility']:.2%}"
        maxdd_str = "-" if np.isnan(metrics["max_drawdown"]) else f"{metrics['max_drawdown']:.2%}"
        sharpe_str = "-" if np.isnan(metrics["sharpe"]) else f"{metrics['sharpe']:.2f}"
        row = {
            "label": label,
            "start": str(actual_start.date()),
            "end": str(end_date.date()),
            "days": str(metrics["days"]),
            "total": total_str,
            "annual": annual_str,
            "vol": vol_str,
            "maxdd": maxdd_str,
            "sharpe": sharpe_str,
            "note": note_text,
        }
        if not np.isnan(metrics["total_return"]) and metrics["total_return"] >= 0:
            row["style_total"] = "value_positive"
            row["style_annual"] = "value_positive"
        elif not np.isnan(metrics["total_return"]):
            row["style_total"] = "value_negative"
            row["style_annual"] = "value_negative"
        if not np.isnan(metrics["max_drawdown"]):
            row["style_maxdd"] = "value_negative" if metrics["max_drawdown"] < 0 else "value_positive"
        if not np.isnan(metrics["sharpe"]):
            row["style_sharpe"] = "accent" if metrics["sharpe"] > 0 else "warning"
        rows_for_table.append(row)
        last_holdings = detail.get("last_weights", {})

    print(colorize("\n=== 核心-卫星多区间回测 ===", "heading"))
    print(colorize("策略假设：核心仓 60% 等权持有核心券池全部标的；卫星仓 40% 择优持有卫星券池中动量得分排名前二，每月调仓。", "menu_hint"))
    print(colorize(f"核心仓标的数: {len(core_available)} | 卫星仓候选: {len(satellite_available)}", "menu_text"))

    print(_render_backtest_table(rows_for_table))

    if last_holdings:
        sorted_holdings = sorted(last_holdings.items(), key=lambda item: item[1], reverse=True)
        holding_lines = []
        for code, weight in sorted_holdings:
            label = _format_label(code)
            holding_lines.append(f"{label}: {weight:.1%}")
        print(colorize("\n最新权重（所有区间共用）:", "heading"))
        print(colorize("; ".join(holding_lines), "menu_text"))

    if warnings:
        print("")
        for message in warnings:
            print(colorize(f"提示: {message}", "warning"))
    _wait_for_ack()



def _make_backtest_preset(
    preset: AnalysisPreset | None,
    config: AnalysisConfig,
    momentum_config: MomentumConfig,
) -> AnalysisPreset:
    if preset:
        return preset
    weights = (
        tuple(momentum_config.weights)
        if momentum_config.weights is not None
        else None
    )
    return AnalysisPreset(
        key="custom",
        name="自定义窗口",
        description="基于当前参数的简易回测",
        momentum_windows=momentum_config.windows,
        momentum_weights=weights,
        corr_window=config.corr_window,
        chop_window=config.chop_window,
        trend_window=config.trend_window,
        rank_lookback=config.rank_change_lookback,
    )


# Moved to business.reports
from .business import display_analysis_summary as _business_display_analysis_summary

def _display_analysis_summary(state: dict) -> None:
    _business_display_analysis_summary(
        state,
        format_summary_func=lambda s, l: format_summary_frame(s, l),
        format_correlation_func=format_correlation,
        colorize_func=colorize
    )


def _interactive_backtest(last_state: Optional[dict]) -> None:
    context = _obtain_backtest_context(last_state, allow_reuse=bool(last_state))
    if not context:
        return
    result = context["result"]
    config = context["config"]
    preset = _make_backtest_preset(context.get("preset"), config, context["momentum_config"])
    default_top = max(1, min(3, len(result.summary)))
    top_n = _prompt_int("回测持仓数量", default_top)
    _run_simple_backtest(result, preset, top_n=top_n)


def _interactive_export_strategy(state: dict) -> None:
    config = state["config"]
    momentum_config = state["momentum_config"]
    preset = state["preset"]
    result = state["result"]

    default_path = Path("strategies") / "momentum_strategy.py"
    raw_path = input(colorize(f"输出文件（默认 {default_path}）: ", "prompt")).strip()
    dest_path = Path(raw_path) if raw_path else default_path

    freq_raw = input(
        colorize("调仓频率（monthly/weekly/daily，默认 monthly）: ", "prompt")
    ).strip().lower()
    freq = freq_raw or "monthly"
    if freq not in {"monthly", "weekly", "daily"}:
        print(colorize("频率输入无效，已回退为 monthly。", "warning"))
        freq = "monthly"

    default_top = max(1, min(3, len(result.summary)))
    top_n = _prompt_int("策略持仓数量", default_top)

    label = f"{preset.name} [{preset.key}]" if preset else "自定义参数"
    try:
        exported = _export_rqalpha_strategy(
            dest_path,
            universe=sorted(result.raw_data.keys()),
            windows=momentum_config.windows,
            weights=momentum_config.weights,
            top_n=top_n,
            frequency=freq,
            start_date=config.start_date,
            end_date=config.end_date,
            label=label,
        )
    except Exception as exc:  # noqa: BLE001
        print(colorize(f"导出失败: {exc}", "danger"))
    else:
        print(colorize(f"已生成策略文件: {exported}", "value_positive"))
        print(colorize("可通过 rqalpha run -f <文件路径> 进行回测。", "menu_hint"))


def _interactive_list_templates() -> None:
    _print_template_list()
    _wait_for_ack()


def _interactive_run_template() -> dict | None:
    name = input(colorize("请输入模板名称: ", "prompt")).strip()
    if not name:
        print(colorize("未输入模板名称。", "warning"))
        _wait_for_ack()
        return None
    template = _get_template_entry(name)
    if not template:
        print(colorize("未找到同名模板。", "warning"))
        _wait_for_ack()
        return None
    params = _template_to_params(template)
    preset_key = params.get("analysis_preset")
    preset_obj = ANALYSIS_PRESETS.get(preset_key) if preset_key else None
    if preset_key and not preset_obj:
        print(colorize(f"模板引用的分析预设 {preset_key} 不存在，请更新模板后重试。", "warning"))
        _wait_for_ack()
        return None
    params["analysis_preset"] = preset_obj
    if not params.get("codes") and params.get("presets"):
        codes: List[str] = []
        for key in params["presets"]:
            preset_def = PRESETS.get(key.lower())
            if preset_def:
                codes.extend(preset_def.tickers)
        params["codes"] = _dedup_codes(codes)
    if not params.get("codes"):
        print(colorize("模板未包含券池信息，无法运行分析。", "warning"))
        _wait_for_ack()
        return None
    params.setdefault("chop_window", 14)
    params.setdefault("trend_window", 90)
    params.setdefault("rank_lookback", 5)
    params.setdefault("make_plots", False)
    params.setdefault("export_csv", False)
    params.setdefault("windows", (60, 120))
    params.setdefault("weights", None)
    params["lang"] = "zh"
    params.setdefault("analysis_name", f"模板 {name}")
    try:
        result = _run_analysis_with_params(
            params,
            post_actions=False,
            bundle_context=f"模板 {name}",
            bundle_interactive=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(colorize(f"分析失败: {exc}", "danger"))
        _wait_for_ack()
        return None
    _wait_for_ack()
    return result


def _interactive_save_template(state: dict) -> None:
    name = input(colorize("请输入要保存的模板名称: ", "prompt")).strip()
    if not name:
        print(colorize("未输入模板名称。", "warning"))
        _wait_for_ack()
        return
    payload = _build_template_payload(
        state["config"],
        state["momentum_config"],
        state["params"].get("presets", []),
        state["preset"],
        export_csv=state["params"].get("export_csv", False),
    )
    if not _save_template_entry(name, payload):
        if _prompt_yes_no("模板已存在，是否覆盖？", False):
            _save_template_entry(name, payload, overwrite=True)
            print(colorize(f"已覆盖模板 {name}。", "info"))
        else:
            print(colorize("未保存模板。", "warning"))
        _wait_for_ack()
        return
    print(colorize(f"模板 {name} 已保存。", "value_positive"))
    _wait_for_ack()


def _interactive_delete_template() -> None:
    name = input(colorize("请输入要删除的模板名称: ", "prompt")).strip()
    if not name:
        print(colorize("未输入模板名称。", "warning"))
        _wait_for_ack()
        return
    if _delete_template_entry(name):
        print(colorize(f"已删除模板 {name}。", "value_positive"))
    else:
        print(colorize("未找到同名模板。", "warning"))
    _wait_for_ack()


# Moved to business.templates
from .business import print_template_details as _business_print_template_details

def _print_template_details(name: str, payload: dict) -> None:
    _business_print_template_details(name, payload, format_label_func=_format_label)

def _interactive_edit_template_entry() -> None:
    store = _load_template_store()
    if not store:
        print(colorize("暂无模板可编辑。", "warning"))
        _wait_for_ack()
        return
    names = sorted(store.keys())
    print(colorize("可编辑的模板：", "heading"))
    for idx, name in enumerate(names, start=1):
        print(colorize(f" {idx:>2}. {name}", "menu_text"))
    choice = input(colorize("请选择模板名称或编号: ", "prompt")).strip()
    target_name: Optional[str] = None
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(names):
            target_name = names[idx - 1]
    elif choice in store:
        target_name = choice
    if not target_name:
        print(colorize("未找到对应模板。", "warning"))
        _wait_for_ack()
        return
    payload = dict(store[target_name])
    _print_template_details(target_name, payload)

    new_name_raw = _prompt_text_default("模板名称", target_name).strip()
    new_name = new_name_raw or target_name
    start = _prompt_optional_date("开始日期", payload.get("start"))
    end = _prompt_optional_date("结束日期", payload.get("end"))
    windows = _prompt_windows_with_default(payload.get("momentum_windows", []))
    current_weights = _coerce_float_sequence(payload.get("momentum_weights"))
    weights = _prompt_weights_for_windows(current_weights, len(windows))
    skip_payload = payload.get("momentum_skip_windows")
    skip_values = None
    if skip_payload and len(skip_payload) == len(windows):
        try:
            skip_values = [int(value) for value in skip_payload]
        except (TypeError, ValueError):
            skip_values = None
    corr_window = _prompt_positive_int_default(
        "相关系数窗口（日）", _coerce_int(payload.get("corr_window"), 60)
    )
    chop_window = _prompt_positive_int_default(
        "Chop 指数窗口", _coerce_int(payload.get("chop_window"), 14)
    )
    trend_window = _prompt_positive_int_default(
        "趋势斜率窗口", _coerce_int(payload.get("trend_window"), 90)
    )
    rank_lookback = _prompt_positive_int_default(
        "动量排名回溯天数", _coerce_int(payload.get("rank_lookback"), 5)
    )
    preset_keys = _prompt_preset_keys_with_default(payload.get("presets", []))
    codes = payload.get("etfs", [])
    if _prompt_yes_no("是否调整券池 ETF 列表？", False):
        codes = _edit_code_list_interactively(codes)
    codes = _dedup_codes(codes)
    new_payload = {
        "etfs": codes,
        "presets": preset_keys,
        "start": start,
        "end": end,
        "momentum_windows": windows,
        "momentum_weights": weights,
        "momentum_skip_windows": skip_values,
        "corr_window": corr_window,
        "chop_window": chop_window,
        "trend_window": trend_window,
        "rank_lookback": rank_lookback,
        "make_plots": False,
        "output_dir": "results",
        "export_csv": False,
    }
    if new_name != target_name and new_name in store:
        if not _prompt_yes_no("同名模板已存在，是否覆盖？", False):
            print(colorize("已取消编辑。", "warning"))
            _wait_for_ack()
            return
    if target_name in store:
        del store[target_name]
    store[new_name] = new_payload
    _write_template_store(store)
    print(colorize(f"模板 {new_name} 已更新。", "value_positive"))
    _wait_for_ack()


def _interactive_clone_template_entry() -> None:
    store = _load_template_store()
    if not store:
        print(colorize("暂无模板可复制。", "warning"))
        _wait_for_ack()
        return
    names = sorted(store.keys())
    print(colorize("请选择要复制的模板：", "heading"))
    for idx, name in enumerate(names, start=1):
        print(colorize(f" {idx:>2}. {name}", "menu_text"))
    choice = input(colorize("输入名称或编号: ", "prompt")).strip()
    source_name: Optional[str] = None
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(names):
            source_name = names[idx - 1]
    elif choice in store:
        source_name = choice
    if not source_name:
        print(colorize("未找到对应模板。", "warning"))
        _wait_for_ack()
        return
    new_name_raw = input(colorize("请输入新模板名称: ", "prompt")).strip()
    if not new_name_raw:
        print(colorize("未输入新模板名称。", "warning"))
        _wait_for_ack()
        return
    new_name = new_name_raw
    if new_name in store and not _prompt_yes_no("同名模板已存在，是否覆盖？", False):
        print(colorize("已取消复制。", "warning"))
        _wait_for_ack()
        return
    payload = json.loads(json.dumps(store[source_name], ensure_ascii=False))
    store[new_name] = payload
    _write_template_store(store)
    print(colorize(f"已复制模板 {source_name} → {new_name}。", "value_positive"))
    _wait_for_ack()


def _show_template_settings_menu() -> None:
    while True:
        options = [
            {"key": "1", "label": "查看模板清单"},
            {"key": "2", "label": "编辑模板参数"},
            {"key": "3", "label": "复制模板"},
            {"key": "4", "label": "删除模板"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 模板设置 ─" + "─" * 22,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="0",
        )
        if choice == "1":
            _interactive_list_templates()
            continue
        if choice == "2":
            _interactive_edit_template_entry()
            continue
        if choice == "3":
            _interactive_clone_template_entry()
            continue
        if choice == "4":
            _interactive_delete_template()
            continue
        if choice in {"0", "__escape__"}:
            return
        print(colorize("无效指令，请重新输入。", "warning"))


def _show_history_menu(last_state: Optional[dict]) -> Optional[dict]:
    global _LAST_BACKTEST_CONTEXT
    _maybe_prompt_bundle_refresh(True, "动量回溯 / 图表")
    current_state = _ensure_analysis_state(last_state, context="动量回溯 / 图表")
    if not current_state:
        return last_state
    while True:
        options = [
            {"key": "1", "label": "查看指定日期的动量排名"},
            {"key": "2", "label": "生成/查看动量得分交互图"},
            {"key": "3", "label": "生成/查看动量排名交互图"},
            {"key": "4", "label": "查看当前分析摘要"},
            {"key": "5", "label": "刷新数据（运行快速分析）"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 动量回溯 / 图表 ─" + "─" * 16,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
        )
        if choice == "1":
            _interactive_show_rank_snapshot(current_state)
            continue
        if choice == "2":
            _interactive_generate_interactive_chart(current_state, "momentum")
            continue
        if choice == "3":
            _interactive_generate_interactive_chart(current_state, "rank")
            continue
        if choice == "4":
            _display_analysis_summary(current_state)
            _wait_for_ack()
            continue
        if choice == "5":
            refreshed = _run_quick_analysis(post_actions=False)
            if refreshed:
                current_state = refreshed
                _LAST_BACKTEST_CONTEXT = None
                print(colorize("已使用最新数据完成快速分析。", "value_positive"))
            else:
                print(colorize("刷新失败，请稍后再试或运行自定义分析。", "danger"))
            _wait_for_ack()
            continue
        if choice in {"0", "__escape__"}:
            return current_state
        print(colorize("无效指令，请重新输入。", "warning"))


def _show_backtest_menu(last_state: Optional[dict]) -> Optional[dict]:
    from .commands.backtest_menu import run as _run
    return _run(last_state)


def _show_templates_menu(last_state: Optional[dict]) -> Optional[dict]:
    # Routed to commands.templates_menu
    from .commands.templates_menu import run as _run_templates
    return _run_templates(last_state)


def _show_settings_menu() -> None:
    # Routed to commands.settings_menu
    from .commands.settings_menu import run as _run_settings
    _run_settings()


# Moved to business.analysis (54 lines)
from .business import run_quick_analysis as _biz_run_quick_analysis

def _run_quick_analysis(post_actions: bool = False) -> dict | None:
    return _biz_run_quick_analysis(
        analysis_presets=ANALYSIS_PRESETS,
        code_presets=PRESETS,
        dedup_codes_func=_dedup_codes,
        run_analysis_func=_run_analysis_with_params,
        colorize_func=colorize,
    )


def _ensure_analysis_state(
    state: Optional[dict],
    *,
    context: str,
) -> Optional[dict]:
    if state:
        return state
    print(
        colorize(
            f"尚无现成的分析结果，将自动运行“快速分析”以用于 {context}。",
            "menu_hint",
        )
    )
    try:
        refreshed = _run_quick_analysis(post_actions=False)
    except Exception as exc:  # noqa: BLE001
        print(colorize(f"自动分析失败: {exc}", "danger"))
        _wait_for_ack()
        return None
    _wait_for_ack()
    if refreshed:
        return refreshed
    print(colorize("快速分析未返回有效结果，请先运行一次自定义分析。", "danger"))
    _wait_for_ack()
    return None


def _show_about() -> None:
    # Routed to commands.about
    from .commands import show_about as _cmd_show_about
    _cmd_show_about(APP_NAME, APP_VERSION, REPO_URL)


def _record_report_history(state: dict, label: str, preset: AnalysisPreset | None) -> None:
    # 	2024														 迁移至 business.history
    from .business import record_history
    preset_label = f"{preset.name} [{preset.key}]" if preset else None
    record_history(state, label, preset_label, interactive=_INTERACTIVE_MODE)


def _show_report_history(last_state: Optional[dict]) -> Optional[dict]:
    # Routed to commands.history_menu
    from .commands.history_menu import run as _history_run
    return _history_run(last_state)


def run_interactive() -> int:
    global _INTERACTIVE_MODE
    _INTERACTIVE_MODE = True
    try:
        _set_color_enabled(sys.stdout.isatty())
        banner_top = colorize("╔" + "═" * 34 + "╗", "border")
        mid_content = f" {APP_NAME} 交互模式 "
        banner_mid = colorize("║" + mid_content.center(34) + "║", "title")
        banner_bot = colorize("╚" + "═" * 34 + "╝", "border")
        banner_lines = ["", banner_top, banner_mid, banner_bot, ""]
        last_state: dict | None = None
        while True:
            options = [
                {"key": "1", "label": "快速分析（核心+卫星 · slow-core）"},
                {"key": "2", "label": "自定义运行动量分析"},
                {"key": "3", "label": "回测与动量工具"},
                {"key": "4", "label": "模板管理"},
                {"key": "5", "label": "报告回顾"},
                {"key": "6", "label": "更新数据（rqalpha bundle）"},
                {"key": "7", "label": "设置与工具"},
                {"key": "8", "label": "关于 Momentum Lens"},
                {"key": "0", "label": "退出"},
            ]
            choice = _prompt_menu_choice(
                options,
                title="┌─ 功能清单 ─" + "─" * 24,
                header_lines=banner_lines,
                hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC 退出",
                default_key="1",
            )
            if choice in {"0", "__escape__"}:
                print(colorize("再见，祝投资顺利！", "info"))
                return 0
            if choice == "1":
                try:
                    state = _run_quick_analysis(post_actions=False)
                except Exception as exc:  # noqa: BLE001
                    print(colorize(f"分析失败: {exc}", "danger"))
                    _wait_for_ack()
                    continue
                if state:
                    last_state = state
                _wait_for_ack()
                continue
            if choice == "2":
                params = _collect_parameters_interactive()
                if not params:
                    continue
                try:
                    last_state = _run_analysis_with_params(
                        params,
                        post_actions=False,
                        bundle_context="自定义分析",
                        bundle_interactive=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    print(colorize(f"分析失败: {exc}", "danger"))
                    _wait_for_ack()
                else:
                    _wait_for_ack()
                continue
            if choice == "3":
                new_state = _show_backtest_menu(last_state)
                if new_state:
                    last_state = new_state
                continue
            if choice == "4":
                new_state = _show_templates_menu(last_state)
                if new_state is not None:
                    last_state = new_state
                continue
            if choice == "5":
                last_state = _show_report_history(last_state)
                continue
            if choice == "6":
                _update_data_bundle()
                continue
            if choice == "7":
                _show_settings_menu()
                continue
            if choice == "8":
                _show_about()
                _wait_for_ack()
                continue
            print(colorize("无效指令，请重新选择。", "warning"))
    finally:
        _INTERACTIVE_MODE = False


def _run_strategy_backtest_menu() -> None:
    """运行策略回测菜单"""
    from .backtest import run_slow_leg_strategy, run_fast_leg_strategy, run_macro_driven_strategy
    from .analysis_presets import ANALYSIS_PRESETS

    print(colorize("\n" + "═" * 60, "border"))
    print(colorize("策略回测选择", "title"))
    print(colorize("═" * 60 + "\n", "border"))

    options = [
        {"key": "1", "label": "核心 + 慢腿轮动 (月度, 含风控)"},
        {"key": "2", "label": "核心 + 快腿轮动 (周度, 20日动量)"},
        {"key": "3", "label": "核心 + 宏观驱动 (12M-1M 长波)"},
        {"key": "0", "label": "返回上级菜单"},
    ]

    choice = _prompt_menu_choice(
        options,
        title="选择要回测的策略",
        hint="↑/↓ 选择策略 · 回车确认 · 0 返回"
    )

    if choice in {"0", "__escape__"}:
        return

    # 选择券池
    print(colorize("\n选择回测券池:", "heading"))
    preset_options = [
        {"key": key, "label": f"{preset.name} - {preset.description}"}
        for key, preset in PRESETS.items()
    ]
    preset_options.append({"key": "0", "label": "取消"})

    preset_choice = _prompt_menu_choice(preset_options, title="选择券池预设")

    if preset_choice in {"0", "__escape__"}:
        return

    # 获取选中的preset
    selected_preset = PRESETS.get(preset_choice)
    if not selected_preset:
        print(colorize("未找到选中的券池", "danger"))
        _wait_for_ack()
        return

    # 获取ETF代码列表
    etf_codes = list(selected_preset.etfs)

    # 设置回测时间范围
    print(colorize("\n设置回测时间范围:", "heading"))
    start_date = input(colorize("开始日期 (YYYY-MM-DD, 默认: 2020-01-01): ", "prompt")).strip() or "2020-01-01"
    end_date = input(colorize("结束日期 (YYYY-MM-DD, 默认: 今天): ", "prompt")).strip() or dt.date.today().isoformat()

    # 根据选择的策略运行回测
    strategy_map = {
        "1": ("slow-core", run_slow_leg_strategy, "慢腿轮动"),
        "2": ("fast-rotation", run_fast_leg_strategy, "快腿轮动"),
        "3": ("twelve-minus-one", run_macro_driven_strategy, "宏观驱动")
    }

    if choice not in strategy_map:
        print(colorize("无效的策略选择", "danger"))
        _wait_for_ack()
        return

    analysis_preset_key, strategy_func, strategy_name = strategy_map[choice]

    # 获取对应的分析预设参数
    analysis_preset = ANALYSIS_PRESETS.get(analysis_preset_key)
    if not analysis_preset:
        print(colorize(f"未找到分析预设: {analysis_preset_key}", "danger"))
        _wait_for_ack()
        return

    momentum_params = {
        'momentum_windows': list(analysis_preset.momentum_windows),
        'momentum_weights': list(analysis_preset.momentum_weights) if analysis_preset.momentum_weights else None,
        'momentum_skip_windows': list(analysis_preset.momentum_skip_windows) if analysis_preset.momentum_skip_windows else None
    }

    print(colorize(f"\n开始运行 {strategy_name} 策略回测...", "info"))
    print(colorize(f"券池: {selected_preset.name}", "dim"))
    print(colorize(f"ETF数量: {len(etf_codes)}", "dim"))
    print(colorize(f"时间范围: {start_date} 至 {end_date}", "dim"))

    try:
        result = strategy_func(
            etf_codes=etf_codes,
            start_date=start_date,
            end_date=end_date,
            momentum_params=momentum_params
        )

        # 显示回测结果
        print(colorize("\n" + "═" * 60, "border"))
        print(colorize(f"回测结果 - {result.strategy_name}", "title"))
        print(colorize("═" * 60, "border"))

        print(colorize(f"\n总收益率: ", "heading") + colorize(f"{result.total_return:.2f}%",
              "value_positive" if result.total_return > 0 else "value_negative"))
        print(colorize(f"年化收益率: ", "heading") + colorize(f"{result.annual_return:.2f}%",
              "value_positive" if result.annual_return > 0 else "value_negative"))
        print(colorize(f"夏普比率: ", "heading") + colorize(f"{result.sharpe_ratio:.2f}", "accent"))
        print(colorize(f"最大回撤: ", "heading") + colorize(f"{result.max_drawdown:.2f}%", "value_negative"))
        print(colorize(f"交易次数: ", "heading") + colorize(f"{len(result.trades)}", "info"))

        # 显示最近几笔交易
        if result.trades:
            print(colorize("\n最近5笔交易:", "heading"))
            for trade in result.trades[-5:]:
                action_color = "value_positive" if trade.action == "BUY" else "value_negative"
                print(f"  {trade.date} | {colorize(trade.action, action_color)} {trade.code} | "
                      f"价格: {trade.price:.2f} | 原因: {trade.reason}")

        print(colorize("\n" + "═" * 60 + "\n", "border"))

    except Exception as e:
        print(colorize(f"\n回测失败: {e}", "danger"))
        import traceback
        traceback.print_exc()

    _wait_for_ack()


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "no_color", False):
        _set_color_enabled(False)
    elif getattr(args, "color", False):
        _set_color_enabled(True)
    else:
        _set_color_enabled(sys.stdout.isatty())

    if args.interactive:
        return run_interactive()

    if args.list_templates:
        _print_template_list()
        return 0

    if args.delete_template:
        if _delete_template_entry(args.delete_template):
            if not args.quiet:
                print(colorize(f"已删除模板 {args.delete_template}。", "value_positive"))
            return 0
        print(
            colorize(f"未找到模板 {args.delete_template}。", "warning"),
            file=sys.stderr,
        )
        return 1

    if args.update_bundle:
        _update_data_bundle()
        return 0

    if args.list_presets:
        _print_presets()
        return 0

    if args.list_analysis_presets:
        _print_analysis_presets()
        return 0

    template_data: dict = {}
    if args.load_template:
        template_data = _get_template_entry(args.load_template)
        if not template_data:
            print(
                colorize(f"模板 {args.load_template} 不存在。", "warning"),
                file=sys.stderr,
            )
            return 1
        if not args.quiet:
            print(colorize(f"已加载模板 {args.load_template}。", "info"))

    etfs = list(template_data.get("etfs", []))
    etfs.extend(_parse_list(args.etfs))
    exclude = list(template_data.get("exclude", []))
    exclude.extend(_parse_list(args.exclude))

    preset_keys = [key.lower() for key in template_data.get("presets", [])]
    preset_keys.extend(key.lower() for key in _parse_list(args.preset))
    preset_keys = list(dict.fromkeys(preset_keys))

    for key in preset_keys:
        if key not in PRESETS:
            parser.error(f"预设券池 {key} 未定义，可使用 --list-presets 查看。")
        etfs.extend(PRESETS[key].tickers)

    etfs = list(_dedup_codes(etfs))
    exclude = list(_dedup_codes(exclude))

    analysis_preset_key = args.analysis_preset or template_data.get("analysis_preset")
    analysis_preset: AnalysisPreset | None = None
    if analysis_preset_key:
        if analysis_preset_key not in ANALYSIS_PRESETS:
            parser.error(f"分析预设 {analysis_preset_key} 未定义。")
        analysis_preset = ANALYSIS_PRESETS[analysis_preset_key]

    if analysis_preset:
        default_momentum = analysis_preset.momentum_config()
        default_corr_window = analysis_preset.corr_window
        default_chop_window = analysis_preset.chop_window
        default_trend_window = analysis_preset.trend_window
        default_rank_lookback = analysis_preset.rank_lookback
    else:
        default_momentum = MomentumConfig()
        default_corr_window = 60
        default_chop_window = 14
        default_trend_window = 90
        default_rank_lookback = 5

    momentum_windows_cli = _parse_int_list(args.momentum_windows)
    momentum_windows_tpl = template_data.get("momentum_windows")
    if momentum_windows_cli:
        momentum_windows = momentum_windows_cli
    elif momentum_windows_tpl:
        momentum_windows = [int(win) for win in momentum_windows_tpl]
    else:
        momentum_windows = None

    momentum_weights_cli = _parse_float_list(args.momentum_weights)
    momentum_weights_tpl = template_data.get("momentum_weights")
    if momentum_weights_cli:
        momentum_weights = momentum_weights_cli
    elif momentum_weights_tpl is not None:
        momentum_weights = [float(weight) for weight in momentum_weights_tpl]
    else:
        momentum_weights = None

    momentum_skip_tpl = template_data.get("momentum_skip_windows")
    if momentum_skip_tpl is not None:
        momentum_skip = [int(value) for value in momentum_skip_tpl]
    else:
        momentum_skip = None

    start_date = args.start or template_data.get("start")
    end_date = args.end or template_data.get("end")

    corr_window = (
        args.corr_window
        if args.corr_window is not None
        else template_data.get("corr_window")
    )
    chop_window = (
        args.chop_window
        if args.chop_window is not None
        else template_data.get("chop_window")
    )
    trend_window = (
        args.trend_window
        if args.trend_window is not None
        else template_data.get("trend_window")
    )
    rank_lookback = (
        args.rank_lookback
        if args.rank_lookback is not None
        else template_data.get("rank_lookback")
    )

    if momentum_windows:
        windows = tuple(momentum_windows)
        weights = tuple(momentum_weights) if momentum_weights else None
        skip_windows = (
            tuple(momentum_skip)
            if momentum_skip is not None and len(momentum_skip) == len(momentum_windows)
            else None
        )
    else:
        windows = default_momentum.windows
        weights = (
            tuple(momentum_weights)
            if momentum_weights is not None
            else default_momentum.weights
        )
        skip_windows = (
            tuple(momentum_skip)
            if momentum_skip is not None and len(momentum_skip) == len(windows)
            else default_momentum.skip_windows
        )

    corr_window = corr_window if corr_window is not None else default_corr_window
    chop_window = chop_window if chop_window is not None else default_chop_window
    trend_window = trend_window if trend_window is not None else default_trend_window
    rank_lookback = (
        rank_lookback if rank_lookback is not None else default_rank_lookback
    )

    make_plots = False
    if (not args.no_plot) and template_data.get("make_plots"):
        if not args.quiet:
            print("[warning] 图表生成功能已禁用。")

    export_csv = args.export_csv or template_data.get("export_csv", False)
    if export_csv and not args.quiet:
        print("[warning] CSV 导出功能已禁用。")
    export_csv = False

    output_dir = args.output_dir
    tpl_output_dir = template_data.get("output_dir")
    if tpl_output_dir and args.output_dir == Path("results"):
        output_dir = Path(tpl_output_dir)

    stability_method_tpl = template_data.get("stability_method")
    stability_method = stability_method_tpl if stability_method_tpl in {"presence_ratio", "kendall"} else _STABILITY_METHOD

    stability_window_tpl = template_data.get("stability_window")
    try:
        stability_window_val = int(stability_window_tpl)
    except (TypeError, ValueError):
        stability_window_val = _STABILITY_WINDOW
    stability_window_val = max(2, min(250, stability_window_val))

    stability_top_n_tpl = template_data.get("stability_top_n")
    try:
        stability_top_n_val = int(stability_top_n_tpl)
    except (TypeError, ValueError):
        stability_top_n_val = _STABILITY_TOP_N
    stability_top_n_val = max(1, min(100, stability_top_n_val))

    stability_weight_tpl = template_data.get("stability_weight")
    try:
        stability_weight_val = float(stability_weight_tpl)
    except (TypeError, ValueError):
        stability_weight_val = _STABILITY_WEIGHT
    stability_weight_val = float(np.clip(stability_weight_val, 0.0, 1.0))

    momentum_config = MomentumConfig(windows=windows, weights=weights, skip_windows=skip_windows)

    config = AnalysisConfig(
        start_date=start_date,
        end_date=end_date,
        etfs=etfs,
        exclude=exclude,
        momentum=momentum_config,
        chop_window=chop_window,
        trend_window=trend_window,
        corr_window=corr_window,
        rank_change_lookback=rank_lookback,
        bundle_path=args.bundle_path,
        output_dir=output_dir,
        make_plots=False,
        momentum_percentile_lookback=_MOMENTUM_SIGNIFICANCE_LOOKBACK,
        momentum_significance_threshold=_MOMENTUM_SIGNIFICANCE_THRESHOLD,
        trend_consistency_adx_threshold=_TREND_CONSISTENCY_ADX,
        trend_consistency_chop_threshold=_TREND_CONSISTENCY_CHOP,
        trend_consistency_fast_span=_TREND_FAST_SPAN,
        trend_consistency_slow_span=_TREND_SLOW_SPAN,
        stability_method=stability_method,
        stability_window=stability_window_val,
        stability_top_n=stability_top_n_val,
        stability_weight=stability_weight_val,
    )

    _maybe_prompt_bundle_refresh(False, "命令行分析")

    try:
        from .business.analysis import run_analysis_only
        result = run_analysis_only(config)
    except Exception as exc:  # noqa: BLE001
        parser.error(str(exc))
        return 1

    payload = _build_result_payload(result, config, momentum_config, analysis_preset, args.lang)

    if args.output_format == "json":
        rendered_output = json.dumps(payload, ensure_ascii=False, indent=2)
    elif args.output_format == "markdown":
        rendered_output = _render_markdown_report(
            result, config, momentum_config, analysis_preset, args.lang
        )
    else:
        rendered_output = _render_text_report(
            result, config, momentum_config, analysis_preset, args.lang
        )

    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(rendered_output, encoding="utf-8")
        if not args.quiet:
            print(colorize(f"输出已写入 {args.output_file}", "info"))
    elif not args.quiet:
        print(rendered_output)

    if args.print_config:
        print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))

    if args.save_state:
        args.save_state.parent.mkdir(parents=True, exist_ok=True)
        args.save_state.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not args.quiet:
            print(colorize(f"分析结果已保存到 {args.save_state}", "info"))

    if args.run_backtest:
        preset_for_bt = _make_backtest_preset(analysis_preset, config, momentum_config)
        _run_simple_backtest(result, preset_for_bt)

    if args.export_strategy:
        label = (
            f"{analysis_preset.name} [{analysis_preset.key}]"
            if analysis_preset
            else "自定义参数"
        )
        try:
            exported_path = _export_rqalpha_strategy(
                args.export_strategy,
                universe=sorted(result.raw_data.keys()),
                windows=momentum_config.windows,
                weights=momentum_config.weights,
                top_n=args.strategy_top,
                frequency=args.strategy_frequency,
                start_date=config.start_date,
                end_date=config.end_date,
                label=label,
            )
        except Exception as exc:  # noqa: BLE001
            message = (
                f"导出策略失败: {exc}"
                if args.lang == "zh"
                else f"Failed to export strategy: {exc}"
            )
            print(message, file=sys.stderr)
            return 1
        else:
            if not args.quiet:
                if args.lang == "zh":
                    print(colorize(f"已导出 RQAlpha 策略脚本: {exported_path}", "value_positive"))
                    print(colorize(f"示例：rqalpha run -f {exported_path}", "menu_hint"))
                else:
                    print(colorize(f"Exported RQAlpha strategy script to {exported_path}", "value_positive"))
                    print(colorize(f"Example: rqalpha run -f {exported_path}", "menu_hint"))

    if args.save_template:
        template_payload = _build_template_payload(
            config,
            momentum_config,
            preset_keys,
            analysis_preset,
            export_csv=export_csv,
        )
        if not _save_template_entry(args.save_template, template_payload):
            print(
                colorize(
                    f"模板 {args.save_template} 已存在，请先使用 --delete-template 删除或更换名称。",
                    "warning",
                ),
                file=sys.stderr,
            )
            return 1
        if not args.quiet:
            print(colorize(f"模板 {args.save_template} 已保存。", "value_positive"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
