"""交互式界面模块

提供完整的交互式菜单系统，包括菜单选择、导航等功能。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Sequence

from ..utils.colors import colorize
from .input import read_keypress, clear_screen
from .menu import MenuState, supports_interactive_menu, print_menu_static

# 环境变量控制：是否保留输出（不擦除之前的菜单）
_PRESERVE_OUTPUT = os.environ.get("MOMENTUM_CLI_PRESERVE_OUTPUT", "").lower() in {"1", "true", "yes"}


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
    previous_lines = 0

    # 打印头部（只打印一次）
    header_line_count = 0
    if header_lines:
        for line in header_lines:
            print(line)
            header_line_count += 1

    while True:
        # 清除上一次渲染的内容（除非保留输出模式）
        if previous_lines > 0 and not _PRESERVE_OUTPUT:
            sys.stdout.write(f"\033[{previous_lines}A")
            sys.stdout.write("\033[J")
            sys.stdout.flush()

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

        # 打印输入提示（已移除，footer已包含操作提示）
        # sys.stdout.write(colorize(prompt_text, "prompt"))
        # sys.stdout.flush()

        # 记录本次渲染的总行数（保留输出模式下不记录，避免重复擦除）
        # 注意：提示符(prompt_text)使用 sys.stdout.write 不换行，不计入行数
        current_lines = len(menu_lines) + footer_line_count
        previous_lines = current_lines if not _PRESERVE_OUTPUT else 0

        # 读取按键
        key = read_keypress()
        if key is None:
            # 回退到非交互模式
            if previous_lines > 0:
                sys.stdout.write(f"\033[{previous_lines}A\033[J")
                sys.stdout.flush()
            if header_line_count > 0:
                sys.stdout.write(f"\033[{header_line_count}A\033[J")
                sys.stdout.flush()

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
            # 清除渲染（除非保留输出模式）
            if not _PRESERVE_OUTPUT:
                # 清除菜单和footer
                if previous_lines > 0:
                    sys.stdout.write(f"[{previous_lines}A[J")
                    sys.stdout.flush()
                # 清除header
                if header_line_count > 0:
                    sys.stdout.write(f"[{header_line_count}A[J")
                    sys.stdout.flush()
            elif _PRESERVE_OUTPUT:
                # 保留输出模式：打印选择结果
                print(f"\n{colorize('选择:', 'prompt')} {result}")
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
