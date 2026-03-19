from __future__ import annotations
from typing import Optional, List, Dict, Any

from ..utils.colors import colorize
from ..business import get_history, TIMESTAMP_FMT
from ..cli import _display_analysis_summary, _wait_for_ack, _prompt_menu_choice


def run(last_state: Optional[dict]) -> Optional[dict]:
    history_items = list(reversed(get_history()))
    if not history_items:
        if last_state:
            report = last_state.get("report_text")
            if report:
                print(report)
            else:
                _display_analysis_summary(last_state)
            _wait_for_ack()
            return last_state
        print(colorize("暂无分析报告可回顾。", "warning"))
        _wait_for_ack()
        return last_state

    while True:
        options: List[Dict[str, Any]] = []
        for idx, entry in enumerate(history_items, start=1):
            timestamp = entry["timestamp"].strftime(TIMESTAMP_FMT)
            label = f"{timestamp} · {entry['label']}"
            extra_lines = [
                colorize(
                    f"    区间: {entry['timeframe']} · ETF 数量: {entry['etf_count']}",
                    "menu_hint",
                )
            ]
            if entry.get("preset"):
                extra_lines.append(colorize(f"    预设: {entry['preset']}", "dim"))
            options.append({"key": str(idx), "label": label, "extra_lines": extra_lines})
        options.append({"key": "0", "label": "返回上级菜单"})
        choice = _prompt_menu_choice(
            options,
            title="┌─ 报告回顾 ─" + "─" * 22,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
        )
        if choice in {"0", "__escape__"}:
            return last_state
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(history_items):
                selected = history_items[idx - 1]["state"]
                report = selected.get("report_text")
                print("")
                if report:
                    print(report)
                else:
                    _display_analysis_summary(selected)
                _wait_for_ack()
                last_state = selected
                continue
        print(colorize("无效指令，请重新选择。", "warning"))

