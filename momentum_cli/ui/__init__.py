"""UI模块

提供用户界面相关功能，包括菜单、输入处理、交互式界面等。
"""

from .input import (
    read_keypress,
    prompt_yes_no,
    prompt_text,
    prompt_positive_int,
    prompt_optional_date,
    clear_screen,
    wait_for_key,
)
from .menu import (
    format_menu_item,
    menu_hint,
    supports_interactive_menu,
    render_menu_block,
    erase_menu_block,
    print_menu_static,
    MenuState,
)
from .interactive import (
    prompt_menu_choice,
)

__all__ = [
    # Input utilities
    "read_keypress",
    "prompt_yes_no",
    "prompt_text",
    "prompt_positive_int",
    "prompt_optional_date",
    "clear_screen",
    "wait_for_key",
    # Menu utilities
    "format_menu_item",
    "menu_hint",
    "supports_interactive_menu",
    "render_menu_block",
    "erase_menu_block",
    "print_menu_static",
    "MenuState",
    # Interactive utilities
    "prompt_menu_choice",
]
