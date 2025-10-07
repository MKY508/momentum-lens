"""业务逻辑模块

提供核心业务功能，包括模板管理、报告生成等。
"""

from .reports import (
    render_text_report,
    render_markdown_report,
    format_summary_table,
    generate_quick_summary,
    display_analysis_summary,
    build_strategy_gate_entries,
    build_result_payload,
)
from .analysis_presets import (
    print_analysis_presets,
    print_analysis_preset_details,
)
from .templates import (
    build_builtin_template,
    get_builtin_template_store,
    load_template_store,
    write_template_store,
    get_template,
    save_template,
    delete_template,
    list_templates,
    template_to_params,
    print_template_details,
    print_template_list,
    build_template_payload,
    TEMPLATE_STORE_PATH,
)
from .history import (
    record_history,
    get_history,
    clear_history,
    MAX_REPORT_HISTORY,
    TIMESTAMP_FMT,
)
from .alerts import (
    detect_high_correlation_pairs,
    detect_rank_drop_alerts,
    collect_alerts,
)
from .config import (
    configure_correlation_threshold_interactive,
    configure_plot_style_interactive,
)

__all__ = [
    # Reports
    "render_text_report",
    "render_markdown_report",
    "format_summary_table",
    "generate_quick_summary",
    "display_analysis_summary",
    "build_strategy_gate_entries",
    "build_result_payload",
    # Analysis Presets
    "print_analysis_presets",
    "print_analysis_preset_details",
    # Templates
    "build_builtin_template",
    "get_builtin_template_store",
    "load_template_store",
    "write_template_store",
    "get_template",
    "save_template",
    "delete_template",
    "list_templates",
    "template_to_params",
    "print_template_details",
    "print_template_list",
    "build_template_payload",
    "TEMPLATE_STORE_PATH",
    # History
    "record_history",
    "get_history",
    "clear_history",
    "MAX_REPORT_HISTORY",
    "TIMESTAMP_FMT",
    # Alerts
    "detect_high_correlation_pairs",
    "detect_rank_drop_alerts",
    "collect_alerts",
    # Config
    "configure_correlation_threshold_interactive",
    "configure_plot_style_interactive",
]
