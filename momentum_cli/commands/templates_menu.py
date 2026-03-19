"""模板管理菜单命令"""
from __future__ import annotations
from typing import Optional

from ..utils.colors import colorize
from ..cli import (
    _interactive_list_templates,
    _interactive_run_template,
    _interactive_save_template,
    _interactive_delete_template,
    _prompt_menu_choice,
)


def run(last_state: Optional[dict]) -> Optional[dict]:
    """模板管理菜单
    
    Returns:
        更新后的状态或原状态
    """
    current_state = last_state
    while True:
        options = [
            {"key": "1", "label": "列出分析模板"},
            {"key": "2", "label": "使用模板运行动量分析"},
            {
                "key": "3",
                "label": "保存最近一次分析为模板" if current_state else "保存最近一次分析为模板（需先运行分析）",
                "enabled": bool(current_state),
            },
            {"key": "4", "label": "删除分析模板"},
            {"key": "0", "label": "返回上级菜单"},
        ]
        choice = _prompt_menu_choice(
            options,
            title="┌─ 模板管理 ─" + "─" * 20,
            header_lines=[""],
            hint="↑/↓ 选择 · 回车确认 · 数字快捷 · ESC/q 返回",
            default_key="1",
        )
        if choice == "1":
            _interactive_list_templates()
            continue
        if choice == "2":
            state = _interactive_run_template()
            if state:
                current_state = state
            continue
        if choice == "3":
            if current_state:
                _interactive_save_template(current_state)
            else:
                print(colorize("暂无分析结果，请先运行动量分析后再保存模板。", "warning"))
            continue
        if choice == "4":
            _interactive_delete_template()
            continue
        if choice in {"0", "__escape__"}:
            return current_state
        print(colorize("无效指令，请重新输入。", "warning"))

