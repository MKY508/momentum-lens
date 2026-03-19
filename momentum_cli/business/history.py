"""
报告历史管理模块

提供报告历史的记录、读取、清理与辅助格式化。
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

# 内存中的报告历史队列（按生成顺序）
_REPORT_HISTORY: List[Dict[str, Any]] = []
MAX_REPORT_HISTORY = 20
TIMESTAMP_FMT = "%Y-%m-%d %H:%M"


def _safe_get_config_info(state: Dict[str, Any]) -> tuple[str, int]:
    """从 state 中提取时间区间与ETF数量（尽量兼容不同结构）。"""
    config = state.get("config")
    # 默认值
    timeframe_start, timeframe_end = "最早可用", "最新"
    etf_count = 0
    if config is not None:
        # 优先按属性访问（对象）
        start = getattr(config, "start_date", None) or getattr(config, "start", None)
        end = getattr(config, "end_date", None) or getattr(config, "end", None)
        etfs = getattr(config, "etfs", None) or getattr(config, "tickers", None)
        if start:
            timeframe_start = str(start)
        if end:
            timeframe_end = str(end)
        if isinstance(etfs, (list, tuple, set)):
            etf_count = len(etfs)
    timeframe = f"{timeframe_start} → {timeframe_end}"
    return timeframe, etf_count


def record_history(state: Dict[str, Any], label: str, preset_label: Optional[str], *, interactive: bool = True) -> None:
    """记录报告历史（仅在交互模式下记录）。"""
    if not interactive:
        return
    timeframe, etf_count = _safe_get_config_info(state)
    timestamp = dt.datetime.now()

    # 如果与上一条引用的是同一个 state，则更新之
    if _REPORT_HISTORY and _REPORT_HISTORY[-1].get("state") is state:
        _REPORT_HISTORY[-1].update(
            {
                "label": label,
                "timeframe": timeframe,
                "timestamp": timestamp,
                "preset": preset_label,
                "etf_count": etf_count,
            }
        )
        return

    entry = {
        "label": label,
        "timeframe": timeframe,
        "timestamp": timestamp,
        "preset": preset_label,
        "etf_count": etf_count,
        "state": state,
    }
    _REPORT_HISTORY.append(entry)
    # 维持最大长度
    while len(_REPORT_HISTORY) > MAX_REPORT_HISTORY:
        _REPORT_HISTORY.pop(0)


def get_history() -> List[Dict[str, Any]]:
    """返回历史列表（按生成顺序，调用方可选择反转）。"""
    return list(_REPORT_HISTORY)


def clear_history() -> None:
    """清空报告历史。"""
    _REPORT_HISTORY.clear()

