"""配置管理模块

处理 CLI 配置的加载、保存和更新。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 默认配置
DEFAULT_SETTINGS = {
    "cli_theme": "aurora",
    "plot_template": "plotly_white",
    "plot_line_width": 2.2,
    "correlation_alert_threshold": 0.8,
    "momentum_significance_threshold": 0.6,
    "momentum_significance_lookback": 756,
    "trend_consistency_adx": 25.0,
    "trend_consistency_chop": 38.0,
    "trend_consistency_fast_span": 20,
    "trend_consistency_slow_span": 60,
    "stability_method": "presence_ratio",
    "stability_window": 30,  # 从15改为30，更长的稳定度观察窗口
    "stability_top_n": 10,
    "stability_weight": 0.2,  # 从0.0改为0.2，启用稳定度权重降低追高风险
}

# 配置文件路径
SETTINGS_STORE_PATH = Path(__file__).resolve().parent.parent / "cli_settings.json"


def load_cli_settings() -> dict[str, Any]:
    """加载 CLI 配置

    从 JSON 文件读取用户配置。如果文件不存在或格式错误，返回空字典。

    Returns:
        配置字典，失败返回空字典

    Examples:
        >>> settings = load_cli_settings()
        >>> isinstance(settings, dict)
        True
    """
    if not SETTINGS_STORE_PATH.exists():
        return {}
    try:
        raw = json.loads(SETTINGS_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def save_cli_settings(settings: dict[str, Any]) -> None:
    """保存 CLI 配置

    将配置字典保存到 JSON 文件，自动创建父目录。

    Args:
        settings: 要保存的配置字典

    Examples:
        >>> settings = {"cli_theme": "aurora"}
        >>> save_cli_settings(settings)  # doctest: +SKIP
    """
    SETTINGS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_STORE_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def update_setting(settings: dict[str, Any], key: str, value: Any) -> None:
    """更新单个配置项并保存

    Args:
        settings: 配置字典（会被就地修改）
        key: 配置键
        value: 配置值

    Examples:
        >>> settings = {"cli_theme": "aurora"}
        >>> update_setting(settings, "plot_template", "plotly_dark")  # doctest: +SKIP
        >>> settings["plot_template"]
        'plotly_dark'
    """
    settings[key] = value
    save_cli_settings(settings)
