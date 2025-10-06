"""调试工具模块

提供日志记录、调试输出等功能。
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

# 键盘日志配置
_KEYLOG_ENABLED = os.getenv("MOMENTUM_KEYLOG") == "1"
_KEYLOG_PATH = Path.home() / ".momentum_lens_keylog.txt"


def log_key_event(label: str, payload: str) -> None:
    """记录键盘事件
    
    Args:
        label: 事件标签
        payload: 事件内容
    """
    if not _KEYLOG_ENABLED:
        return
    
    try:
        escaped = payload.encode("unicode_escape", errors="backslashreplace").decode("ascii")
        with _KEYLOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.time():.6f} {label}: {escaped}\n")
    except OSError:
        pass


def log_key_result(value: Optional[str]) -> Optional[str]:
    """记录键盘结果
    
    Args:
        value: 键值
        
    Returns:
        原样返回键值
    """
    if value is None:
        log_key_event("key", "<None>")
    else:
        log_key_event("key", value)
    return value


def is_keylog_enabled() -> bool:
    """检查键盘日志是否启用"""
    return _KEYLOG_ENABLED


def get_keylog_path() -> Path:
    """获取键盘日志路径"""
    return _KEYLOG_PATH
