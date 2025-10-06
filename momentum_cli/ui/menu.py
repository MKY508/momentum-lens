"""菜单系统模块

提供交互式菜单的渲染、导航和选择功能。
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence

from ..utils.colors import colorize


def format_menu_item(
    index: int | str,
    label: str,
    enabled: bool = True,
    *,
    selected: bool = False,
) -> str:
    """格式化菜单项
    
    Args:
        index: 菜单项索引或标识
        label: 菜单项标签
        enabled: 是否启用
        selected: 是否选中
        
    Returns:
        格式化后的菜单项字符串
    """
    if isinstance(index, str):
        index_display = index.rjust(2)
    else:
        index_display = f"{index:>2}"
    
    number_style = "menu_number" if enabled else "menu_disabled"
    bullet_style = "menu_bullet" if enabled else "menu_disabled"
    text_style = "menu_text" if enabled else "menu_disabled"
    bullet_char = "›" if enabled else "·"
    
    if selected and enabled:
        number_style = "prompt"
        bullet_style = "prompt"
        text_style = "prompt"
        bullet_char = "▶"
    
    number = colorize(index_display, number_style)
    bullet = colorize(bullet_char, bullet_style)
    text = colorize(label, text_style)
    return f" {number} {bullet} {text}"


def menu_hint(text: str) -> str:
    """格式化菜单提示文本"""
    return colorize(text, "menu_hint")


def supports_interactive_menu() -> bool:
    """检查是否支持交互式菜单"""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    
    try:
        import msvcrt
        return True
    except ImportError:
        pass
    
    try:
        import termios
        import tty
        sys.stdin.fileno()
        return True
    except (ImportError, AttributeError, OSError):
        return False


def render_menu_block(
    items: List[Dict[str, Any]],
    selected_index: int = -1,
    title: Optional[str] = None,
    show_hints: bool = True,
) -> List[str]:
    """渲染菜单块
    
    Args:
        items: 菜单项列表，每项包含 'index', 'label', 'enabled' 等字段
        selected_index: 选中的项目索引
        title: 可选的标题
        show_hints: 是否显示操作提示
        
    Returns:
        渲染后的文本行列表
    """
    lines = []

    if title:
        # 如果title已经包含边框字符，直接使用；否则添加边框
        if title.startswith("┌─"):
            lines.append(colorize(title, "border"))
        else:
            lines.append(colorize(f"┌─ {title} ─────────────────────────", "border"))
    else:
        lines.append(colorize("┌─ 功能清单 ─────────────────────────", "border"))
    
    for i, item in enumerate(items):
        index = item.get("index", i + 1)
        label = item.get("label", "")
        enabled = item.get("enabled", True)
        selected = (i == selected_index)
        
        formatted_item = format_menu_item(index, label, enabled, selected=selected)
        lines.append(formatted_item)
    
    if show_hints:
        lines.append(menu_hint("↑/↓ 选择 · 回车确认 · 数字快捷 · ESC 退出"))
    
    return lines


def erase_menu_block(lines: int) -> None:
    """擦除菜单块
    
    Args:
        lines: 要擦除的行数
    """
    if lines > 0:
        sys.stdout.write("\r")
        if lines > 1:
            sys.stdout.write("\033[F" * (lines - 1))
        sys.stdout.write("\033[J")
        sys.stdout.flush()


def print_menu_static(
    items: List[Dict[str, Any]],
    title: Optional[str] = None,
    show_hints: bool = True,
) -> None:
    """打印静态菜单（非交互模式）
    
    Args:
        items: 菜单项列表
        title: 可选的标题
        show_hints: 是否显示操作提示
    """
    lines = render_menu_block(items, title=title, show_hints=show_hints)
    for line in lines:
        print(line)


class MenuState:
    """菜单状态管理类"""
    
    def __init__(self, items: List[Dict[str, Any]]):
        self.items = items
        self.selected_index = 0
        self.rendered_lines = 0
        
        # 找到第一个启用的项目
        enabled_indices = [i for i, item in enumerate(items) if item.get("enabled", True)]
        if enabled_indices:
            self.selected_index = enabled_indices[0]
    
    def move_selection(self, delta: int) -> None:
        """移动选择
        
        Args:
            delta: 移动方向，正数向下，负数向上
        """
        enabled_indices = [i for i, item in enumerate(self.items) if item.get("enabled", True)]
        if not enabled_indices:
            return
        
        try:
            current_pos = enabled_indices.index(self.selected_index)
        except ValueError:
            self.selected_index = enabled_indices[0]
            return
        
        new_pos = (current_pos + delta) % len(enabled_indices)
        self.selected_index = enabled_indices[new_pos]
    
    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        """获取当前选中的项目"""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None
    
    def find_item_by_key(self, key: str) -> Optional[int]:
        """根据键查找项目索引
        
        Args:
            key: 要查找的键
            
        Returns:
            项目索引，如果未找到返回None
        """
        for i, item in enumerate(self.items):
            if str(item.get("index", i + 1)) == key:
                return i
        return None
    
    def render(self, title: Optional[str] = None, show_hints: bool = True) -> None:
        """渲染菜单"""
        # 擦除之前的渲染
        if self.rendered_lines > 0:
            erase_menu_block(self.rendered_lines)
        
        # 渲染新的菜单
        lines = render_menu_block(
            self.items, 
            selected_index=self.selected_index,
            title=title,
            show_hints=show_hints
        )
        
        for line in lines:
            print(line)
        
        self.rendered_lines = len(lines)
    
    def clear(self) -> None:
        """清除菜单显示"""
        if self.rendered_lines > 0:
            erase_menu_block(self.rendered_lines)
            self.rendered_lines = 0
