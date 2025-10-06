"""配置管理模块

包含设置管理、验证和数据包状态检查功能。
"""

from .bundle import (
    BUNDLE_ROOT,
    BUNDLE_VERSION_FILE,
    bundle_status,
    load_bundle_metadata,
)
from .settings import (
    DEFAULT_SETTINGS,
    SETTINGS_STORE_PATH,
    load_cli_settings,
    save_cli_settings,
    update_setting,
)
from .validators import (
    validate_corr_threshold,
    validate_float_range_setting,
    validate_positive_int_setting,
    validate_ratio_setting,
)

__all__ = [
    # Bundle management
    "BUNDLE_ROOT",
    "BUNDLE_VERSION_FILE",
    "bundle_status",
    "load_bundle_metadata",
    # Settings management
    "DEFAULT_SETTINGS",
    "SETTINGS_STORE_PATH",
    "load_cli_settings",
    "save_cli_settings",
    "update_setting",
    # Validators
    "validate_corr_threshold",
    "validate_float_range_setting",
    "validate_positive_int_setting",
    "validate_ratio_setting",
]
