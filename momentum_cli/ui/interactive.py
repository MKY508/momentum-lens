"""交互式界面模块

提供完整的交互式菜单系统，包括菜单选择、导航等功能。
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence

from ..utils.colors import colorize
from .input import read_keypress, clear_screen
from .menu import MenuState, supports_interactive_menu, print_menu_static


def prompt_menu_choice(
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
    clear_screen_first: bool = False,
) -> str:
    """提示用户从菜单中选择
    
    Args:
        options: 选项列表，每项包含 'key', 'label', 'enabled' 等字段
        title: 菜单标题
        header_lines: 头部额外行
        hint: 提示文本
        footer_lines: 底部额外行
        prompt_text: 输入提示文本
        default_key: 默认选择的键
        allow_escape: 是否允许ESC退出
        instant_numeric: 是否支持数字键立即响应
        escape_prompt: ESC退出时的提示
        clear_screen_first: 是否先清屏
        
    Returns:
        用户选择的键，或特殊值如 "__escape__"
    """
    # 标准化选项
    normalized = []
    for option in options:
        key = str(option.get("key", ""))
        display = str(option.get("display", key))
        normalized.append({
            "index": display,
            "key": key,
            "label": option.get("label", ""),
            "enabled": bool(option.get("enabled", True)),
            "extra_lines": option.get("extra_lines", []),
        })
    
    if clear_screen_first:
        clear_screen()
    
    # 非交互模式
    if not supports_interactive_menu():
        return _handle_non_interactive_menu(
            normalized, title, header_lines, hint, footer_lines, 
            prompt_text, default_key
        )
    
    # 交互模式
    return _handle_interactive_menu(
        normalized, title, header_lines, hint, footer_lines,
        prompt_text, default_key, allow_escape, instant_numeric, escape_prompt
    )


def _handle_non_interactive_menu(
    options: List[Dict[str, Any]],
    title: Optional[str],
    header_lines: Sequence[str] | None,
    hint: Optional[str],
    footer_lines: Sequence[str] | None,
    prompt_text: str,
    default_key: Optional[str],
) -> str:
    """处理非交互模式的菜单"""
    # 打印头部
    if header_lines:
        for line in header_lines:
            print(line)
    
    # 打印菜单
    print_menu_static(options, title=title, show_hints=False)
    
    # 打印提示和底部
    if hint:
        print(colorize(hint, "menu_hint"))
    if footer_lines:
        for line in footer_lines:
            print(line)
    
    # 获取输入
    try:
        raw = input(colorize(prompt_text, "prompt")).strip()
        if not raw and default_key is not None:
            return default_key
        return raw
    except (KeyboardInterrupt, EOFError):
        return "__escape__"


def _handle_interactive_menu(
    options: List[Dict[str, Any]],
    title: Optional[str],
    header_lines: Sequence[str] | None,
    hint: Optional[str],
    footer_lines: Sequence[str] | None,
    prompt_text: str,
    default_key: Optional[str],
    allow_escape: bool,
    instant_numeric: bool,
    escape_prompt: Optional[str],
) -> str:
    """处理交互模式的菜单"""
    menu_state = MenuState(options)
    pending = ""
    rendered_total_lines = 0

    # 打印头部（只打印一次）
    header_line_count = 0
    if header_lines:
        for line in header_lines:
            print(line)
            header_line_count += 1

    # 在标题后留出一行空行，作为菜单渲染区域的起始行
    print("")

    # 在此处保存“菜单起始位置”的锚点（不再清除其上的内容）
    print("\033[s", end="")  # ANSI Save Cursor Position

    while True:
        # 清空菜单区域（不影响上方 banner/头部）
        print("\033[u\033[J", end="", flush=True)

        # 渲染菜单
        menu_lines = []
        from .menu import render_menu_block
        menu_lines = render_menu_block(
            menu_state.items,
            selected_index=menu_state.selected_index,
            title=title,
            show_hints=False
        )

        for line in menu_lines:
            print(line)

        # 打印提示和底部
        footer_line_count = 0
        if hint:
            print(colorize(hint, "menu_hint"))
            footer_line_count += 1
        if footer_lines:
            for line in footer_lines:
                print(line)
                footer_line_count += 1

        # 打印输入提示
        print(colorize(prompt_text, "prompt"), end="", flush=True)

        rendered_total_lines = len(menu_lines) + footer_line_count + 1

        # 读取按键
        key = read_keypress()
        if key is None:
            # 回退到非交互模式
            # 清除所有渲染（包括头部）
            if rendered_total_lines > 0:
                print(f"\033[{rendered_total_lines}A\r\033[J", end="", flush=True)
            if header_line_count > 0:
                print(f"\033[{header_line_count}A\r\033[J", end="", flush=True)

            return _handle_non_interactive_menu(
                options, title, header_lines, hint, footer_lines,
                prompt_text, default_key
            )

        # 处理按键
        result = _process_menu_key(
            key, menu_state, pending, default_key, allow_escape,
            instant_numeric, escape_prompt
        )

        if isinstance(result, str):
            # 清除渲染
            if rendered_total_lines > 0:
                print(f"\033[{rendered_total_lines}A\r\033[J", end="", flush=True)
            return result
        elif isinstance(result, dict):
            # 更新状态
            pending = result.get("pending", pending)
        # 否则继续循环





def _process_menu_key(
    key: str,
    menu_state: MenuState,
    pending: str,
    default_key: Optional[str],
    allow_escape: bool,
    instant_numeric: bool,
    escape_prompt: Optional[str],
) -> str | Dict[str, Any] | None:
    """处理菜单按键
    
    Returns:
        str: 最终选择的键
        dict: 状态更新信息
        None: 继续处理
    """
    # 方向键导航
    if key in {"UP", "LEFT"}:
        menu_state.move_selection(-1)
        return {"pending": ""}
    
    if key in {"DOWN", "RIGHT"}:
        menu_state.move_selection(1)
        return {"pending": ""}
    
    # 退格键
    if key == "BACKSPACE":
        return {"pending": pending[:-1]}
    
    # 回车键
    if key == "ENTER":
        if pending:
            # 有待处理输入，查找对应项目
            target_idx = menu_state.find_item_by_key(pending)
            if target_idx is not None:
                item = menu_state.items[target_idx]
                if item.get("enabled", True):
                    return item.get("key", "")
            return {"pending": ""}
        else:
            # 选择当前项目
            selected = menu_state.get_selected_item()
            if selected and selected.get("enabled", True):
                return selected.get("key", "")
            return None
    
    # ESC键
    if key == "ESC":
        if allow_escape:
            if escape_prompt:
                print(f"\n{colorize(escape_prompt, 'info')}")
            return "__escape__"
        return None
    
    # 数字键
    if len(key) == 1 and key.isdigit():
        new_pending = pending + key
        exact_match = menu_state.find_item_by_key(new_pending)
        
        if exact_match is not None:
            item = menu_state.items[exact_match]
            if item.get("enabled", True):
                menu_state.selected_index = exact_match
                if instant_numeric:
                    # 立即返回
                    return item.get("key", "")
        
        return {"pending": new_pending}
    
    # 其他键，清空待处理输入
    return {"pending": ""}
