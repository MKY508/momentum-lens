"""工具函数模块

包含显示、解析、颜色、调试等通用工具函数。
"""

from .colors import (
    colorize,
    set_color_enabled,
    is_color_enabled,
    get_current_theme,
    apply_theme,
    render_theme_sample,
    get_rank_style,
    get_available_themes,
)
from .debug import (
    log_key_event,
    log_key_result,
    is_keylog_enabled,
    get_keylog_path,
)
from .display import (
    display_width,
    pad_display,
    strip_ansi,
)
from .parsers import (
    extract_float,
    parse_bundle_version,
    try_parse_datetime,
)
from .formatters import (
    chop_state_label,
    adx_state_label,
    style_rank_header,
    style_summary_value,
    prepare_summary_table,
    summary_to_markdown,
)

__all__ = [
    # Color utilities
    "colorize",
    "set_color_enabled",
    "is_color_enabled",
    "get_current_theme",
    "apply_theme",
    "render_theme_sample",
    "get_rank_style",
    "get_available_themes",
    # Debug utilities
    "log_key_event",
    "log_key_result",
    "is_keylog_enabled",
    "get_keylog_path",
    # Display utilities
    "display_width",
    "pad_display",
    "strip_ansi",
    # Parser utilities
    "extract_float",
    "parse_bundle_version",
    "try_parse_datetime",
    # Formatting utilities
    "chop_state_label",
    "adx_state_label",
    "style_rank_header",
    "style_summary_value",
    "prepare_summary_table",
    "summary_to_markdown",
]
