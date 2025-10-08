"""用户输入处理模块

提供键盘输入读取、菜单选择等交互功能。
"""

from __future__ import annotations

import os
import select
import sys
import time
from typing import Optional

from ..utils.colors import colorize

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - Windows fallback
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

try:  # pragma: no cover - optional Windows support
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None  # type: ignore[assignment]

# 常量定义
_ESC_SEQUENCE_TIMEOUT = 0.3
_ESC_POLL_INTERVAL = 0.05
_MAX_ESC_SEQUENCE = 16


def _read_byte(fd: int) -> Optional[str]:
    """读取单个字节"""
    try:
        data = os.read(fd, 1)
    except OSError:
        return None
    if not data:
        return None
    return data.decode("latin-1")


def _read_escape_sequence(fd: int) -> str:
    """读取转义序列"""
    chars = []
    deadline = time.monotonic() + _ESC_SEQUENCE_TIMEOUT
    while len(chars) < _MAX_ESC_SEQUENCE and time.monotonic() < deadline:
        try:
            rlist, _, _ = select.select([fd], [], [], _ESC_POLL_INTERVAL)
        except (OSError, ValueError):
            break
        if not rlist:
            break
        next_ch = _read_byte(fd)
        if not next_ch:
            break
        chars.append(next_ch)
        if next_ch.isalpha() or next_ch == "~":
            break
    return "".join(chars)


def _translate_escape_sequence(sequence: str) -> Optional[str]:
    """转换转义序列为按键名称"""
    mapping = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}
    if not sequence:
        return "ESC"
    if len(sequence) < 2:
        return "ESC"
    prefix = sequence[0]
    final = sequence[-1]
    if prefix == "[" and final in mapping:
        return mapping[final]
    return "ESC"


def read_keypress() -> Optional[str]:
    """读取单个按键
    
    Returns:
        按键名称，如 "UP", "DOWN", "ENTER", "ESC" 或单个字符
        如果读取失败返回 None
    """
    # Windows 支持
    if msvcrt is not None:
        try:
            ch = msvcrt.getwch()
            if ch in {"\r", "\n"}:
                return "ENTER"
            if ch in {"\x00", "\xe0"}:
                seq = msvcrt.getwch()
                mapping = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
                return mapping.get(seq, "UNKNOWN")
            if ch == "\x1b":
                return "ESC"
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x08":
                return "BACKSPACE"
            return ch
        except Exception:
            return None
    
    # Unix-like 系统支持
    if termios is None or tty is None:
        return None
    
    try:
        fd = sys.stdin.fileno()
    except (AttributeError, OSError):
        return None
    
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = _read_byte(fd)
        if ch is None:
            return None
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch in {"\r", "\n"}:
            return "ENTER"
        if ch == "\x1b":
            sequence = _read_escape_sequence(fd)
            translated = _translate_escape_sequence(sequence)
            return translated
        if ch in {"\x7f", "\b"}:
            return "BACKSPACE"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """提示用户输入是/否
    
    Args:
        question: 问题文本
        default: 默认值
        
    Returns:
        用户选择的布尔值
    """
    default_label = "是" if default else "否"
    prompt_text = f"{question} 默认{default_label}，按 y/n 或回车确认: "
    
    while True:
        try:
            raw = input(colorize(prompt_text, "prompt")).strip().lower()
            if not raw:
                return default
            if raw in {"y", "yes", "是", "1", "true"}:
                return True
            if raw in {"n", "no", "否", "0", "false"}:
                return False
            print(colorize("请输入 y/n 或直接回车使用默认值。", "warning"))
        except (KeyboardInterrupt, EOFError):
            print()
            return default


def prompt_text(question: str, default: str = "") -> str:
    """提示用户输入文本
    
    Args:
        question: 问题文本
        default: 默认值
        
    Returns:
        用户输入的文本
    """
    if default:
        prompt_text = f"{question} (默认: {default}): "
    else:
        prompt_text = f"{question}: "
    
    try:
        value = input(colorize(prompt_text, "prompt")).strip()
        return value if value else default
    except (KeyboardInterrupt, EOFError):
        print()
        return default


def prompt_positive_int(question: str, default: int) -> int:
    """提示用户输入正整数
    
    Args:
        question: 问题文本
        default: 默认值
        
    Returns:
        用户输入的正整数
    """
    while True:
        try:
            raw = prompt_text(question, str(default))
            if not raw:
                return default
            value = int(raw)
            if value > 0:
                return value
            print(colorize("请输入正整数。", "warning"))
        except ValueError:
            print(colorize("请输入有效的数字。", "warning"))
        except (KeyboardInterrupt, EOFError):
            return default


def prompt_optional_date(question: str, current: Optional[str] = None) -> Optional[str]:
    """提示用户输入可选日期
    
    Args:
        question: 问题文本
        current: 当前值
        
    Returns:
        用户输入的日期字符串或None
    """
    default_text = current or "留空"
    prompt_text = f"{question} (当前: {default_text}): "
    
    try:
        value = input(colorize(prompt_text, "prompt")).strip()
        if not value:
            return current
        if value.lower() in {"none", "null", "空", "留空"}:
            return None
        return value
    except (KeyboardInterrupt, EOFError):
        print()
        return current


def clear_screen() -> None:
    """清屏"""
    print("\033[2J\033[H", end="")


def wait_for_key(prompt: str = "按任意键继续...") -> None:
    """等待用户按键
    
    Args:
        prompt: 提示文本
    """
    try:
        input(colorize(prompt, "prompt"))
    except (KeyboardInterrupt, EOFError):
        print()
