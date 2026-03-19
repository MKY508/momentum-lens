"""通用辅助函数模块"""
from __future__ import annotations

from typing import Iterable, List


def dedup_codes(codes: Iterable[str]) -> List[str]:
    """去重并规范化代码列表
    
    Args:
        codes: 代码列表
        
    Returns:
        去重后的大写代码列表
    """
    seen = set()
    result: List[str] = []
    for code in codes:
        if not code:
            continue
        upper = code.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


def format_code_label(code: str, get_label_func) -> str:
    """格式化代码标签
    
    Args:
        code: 代码
        get_label_func: 获取标签的函数
        
    Returns:
        格式化后的标签，如 "沪深300 (000300.XSHG)"
    """
    label = get_label_func(code)
    return f"{label} ({code})" if label else code

