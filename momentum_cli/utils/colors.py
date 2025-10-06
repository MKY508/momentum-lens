"""颜色和主题处理工具

提供终端颜色输出和主题管理功能。
"""

from __future__ import annotations

from typing import Dict, Any

# 主题定义
CLI_THEMES = {
    "aurora": {
        "reset": "\033[0m",
        "title": "\033[1;96m",
        "heading": "\033[1;94m",
        "menu_number": "\033[1;36m",
        "menu_text": "\033[36m",
        "menu_disabled": "\033[90m",
        "menu_bullet": "\033[1;94m",
        "menu_hint": "\033[96m",
        "prompt": "\033[1;35m",
        "border": "\033[94m",
        "divider": "\033[90m",
        "info": "\033[36m",
        "warning": "\033[1;33m",
        "danger": "\033[31m",
        "accent": "\033[32m",
        "dim": "\033[2;37m",
        "value_positive": "\033[32m",
        "value_negative": "\033[31m",
        "value_neutral": "\033[90m",
        "rank_gold": "\033[1;33m",
        "rank_silver": "\033[1;36m",
        "rank_bronze": "\033[1;35m",
        "header": "\033[1;96m",
    },
    "ember": {
        "reset": "\033[0m",
        "title": "\033[1;91m",
        "heading": "\033[1;33m",
        "menu_number": "\033[1;31m",
        "menu_text": "\033[31m",
        "menu_disabled": "\033[90m",
        "menu_bullet": "\033[1;33m",
        "menu_hint": "\033[95m",
        "prompt": "\033[1;33m",
        "border": "\033[33m",
        "divider": "\033[90m",
        "info": "\033[95m",
        "warning": "\033[1;33m",
        "danger": "\033[31m",
        "accent": "\033[32m",
        "dim": "\033[2;37m",
        "value_positive": "\033[32m",
        "value_negative": "\033[31m",
        "value_neutral": "\033[90m",
        "rank_gold": "\033[1;33m",
        "rank_silver": "\033[1;36m",
        "rank_bronze": "\033[1;35m",
        "header": "\033[1;91m",
    },
    "evergreen": {
        "reset": "\033[0m",
        "title": "\033[1;92m",
        "heading": "\033[1;32m",
        "menu_number": "\033[1;36m",
        "menu_text": "\033[32m",
        "menu_disabled": "\033[90m",
        "menu_bullet": "\033[1;32m",
        "menu_hint": "\033[96m",
        "prompt": "\033[1;35m",
        "border": "\033[32m",
        "divider": "\033[90m",
        "info": "\033[36m",
        "warning": "\033[1;33m",
        "danger": "\033[31m",
        "accent": "\033[32m",
        "dim": "\033[2;37m",
        "value_positive": "\033[32m",
        "value_negative": "\033[31m",
        "value_neutral": "\033[90m",
        "rank_gold": "\033[1;33m",
        "rank_silver": "\033[1;36m",
        "rank_bronze": "\033[1;35m",
        "header": "\033[1;92m",
    },
}

# 主题顺序
THEME_ORDER = ["aurora", "ember", "evergreen", "monet", "bauhaus", "hokusai", "noir", "rothko"]

# 全局状态
_color_enabled = True
_current_theme = "aurora"
_style_codes = dict(CLI_THEMES[_current_theme])
_theme_sample_cache: Dict[str, str] = {}


def set_color_enabled(enabled: bool) -> None:
    """设置颜色输出开关"""
    global _color_enabled
    _color_enabled = enabled


def is_color_enabled() -> bool:
    """检查颜色输出是否启用"""
    return _color_enabled


def get_current_theme() -> str:
    """获取当前主题"""
    return _current_theme


def get_style_codes() -> Dict[str, str]:
    """获取当前样式代码"""
    return dict(_style_codes)


def colorize(text: str, style: str, fallback: str | None = None) -> str:
    """给文本添加颜色
    
    Args:
        text: 要着色的文本
        style: 样式名称
        fallback: 备用样式名称
        
    Returns:
        着色后的文本
    """
    if not _color_enabled:
        return text
    code = _style_codes.get(style) or (fallback and _style_codes.get(fallback))
    if not code:
        return text
    return f"{code}{text}{_style_codes['reset']}"


def apply_theme(theme_key: str, *, persist: bool = True) -> bool:
    """应用主题
    
    Args:
        theme_key: 主题名称
        persist: 是否持久化保存（暂未实现）
        
    Returns:
        是否成功应用
    """
    global _current_theme, _style_codes
    
    if theme_key not in CLI_THEMES:
        return False
    
    _current_theme = theme_key
    _style_codes = dict(CLI_THEMES[theme_key])
    
    # 清除缓存
    _theme_sample_cache.clear()
    
    # TODO: 如果需要持久化，这里可以调用配置保存函数
    
    return True


def render_theme_sample(theme_key: str) -> str:
    """渲染主题样例
    
    Args:
        theme_key: 主题名称
        
    Returns:
        主题样例文本
    """
    cached = _theme_sample_cache.get(theme_key)
    if cached is not None:
        return cached
    
    if theme_key not in CLI_THEMES:
        return f"未知主题: {theme_key}"
    
    codes = CLI_THEMES[theme_key]
    sample = (
        f"     {codes['title']}标题{codes['reset']} "
        f"{codes['menu_text']}菜单{codes['reset']} "
        f"{codes['prompt']}输入{codes['reset']} "
        f"{codes['value_positive']}+1.20%{codes['reset']} "
        f"{codes['value_negative']}-0.85%{codes['reset']}"
    )
    _theme_sample_cache[theme_key] = sample
    return sample


def get_rank_style(rank: int) -> str | None:
    """获取排名样式
    
    Args:
        rank: 排名（1-based）
        
    Returns:
        样式名称或None
    """
    if rank == 1:
        return "rank_gold"
    elif rank == 2:
        return "rank_silver"
    elif rank == 3:
        return "rank_bronze"
    return None


def get_available_themes() -> list[str]:
    """获取可用主题列表"""
    return list(CLI_THEMES.keys())
