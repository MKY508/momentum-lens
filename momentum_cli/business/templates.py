"""模板管理模块

提供分析模板的加载、保存、删除等功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

# 模板存储路径
TEMPLATE_STORE_PATH = Path(__file__).resolve().parent.parent / "templates.json"


def build_builtin_template(
    name: str,
    description: str,
    preset_keys: list[str],
    windows: list[int],
    weights: list[float],
    **kwargs
) -> dict:
    """构建内置模板
    
    Args:
        name: 模板名称
        description: 模板描述
        preset_keys: 预设键列表
        windows: 动量窗口列表
        weights: 动量权重列表
        **kwargs: 其他参数
        
    Returns:
        模板字典
    """
    template = {
        "name": name,
        "description": description,
        "preset_keys": preset_keys,
        "momentum_windows": windows,
        "momentum_weights": weights,
    }
    
    # 添加可选参数
    for key in ["start", "end", "correlation_threshold", "momentum_threshold", 
                "stability_weight", "chop_window", "trend_window", "lookback_days"]:
        if key in kwargs:
            template[key] = kwargs[key]
    
    return template


def get_builtin_template_store() -> Dict[str, dict]:
    """获取内置模板存储
    
    Returns:
        内置模板字典
    """
    return {
        "default": build_builtin_template(
            name="默认配置",
            description="3个月 + 6个月动量，等权重",
            preset_keys=["core", "satellite"],
            windows=[63, 126],
            weights=[0.5, 0.5],
        ),
        "slow-core": build_builtin_template(
            name="慢腿·核心监控",
            description="3M-1M · 6M-1M 加权（60/40），兼顾反转与趋势",
            preset_keys=["core", "satellite"],
            windows=[63, 126],
            weights=[0.6, 0.4],
            correlation_threshold=0.80,
            momentum_threshold=0.05,
            stability_weight=0.15,
            chop_window=14,
            trend_window=90,
            lookback_days=5,
        ),
    }


def load_template_store() -> Dict[str, dict]:
    """加载模板存储
    
    Returns:
        模板字典
    """
    base_store = get_builtin_template_store()
    
    if not TEMPLATE_STORE_PATH.exists():
        return dict(base_store)
    
    try:
        data = json.loads(TEMPLATE_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(base_store)
    
    templates = data.get("templates")
    if not isinstance(templates, dict):
        return dict(base_store)
    
    store = dict(base_store)
    for raw_key, value in templates.items():
        key = str(raw_key)
        if value is None:
            store.pop(key, None)
            continue
        if isinstance(value, dict):
            store[key] = dict(value)
    
    return store


def write_template_store(store: Dict[str, dict]) -> None:
    """写入模板存储
    
    Args:
        store: 模板字典
    """
    base_store = get_builtin_template_store()
    payload_templates: Dict[str, Optional[dict]] = {}
    
    for key, value in store.items():
        base_value = base_store.get(key)
        if value is None:
            payload_templates[key] = None
            continue
        if not isinstance(value, dict):
            continue
        if base_value is not None and base_value == value:
            continue
        payload_templates[key] = value
    
    TEMPLATE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not payload_templates:
        try:
            TEMPLATE_STORE_PATH.unlink()
        except OSError:
            pass
        return
    
    payload = {"templates": payload_templates}
    TEMPLATE_STORE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def get_template(name: str) -> Optional[dict]:
    """获取模板
    
    Args:
        name: 模板名称
        
    Returns:
        模板字典，如果不存在返回None
    """
    return load_template_store().get(name)


def save_template(name: str, payload: dict, overwrite: bool = False) -> bool:
    """保存模板
    
    Args:
        name: 模板名称
        payload: 模板数据
        overwrite: 是否覆盖已存在的模板
        
    Returns:
        是否成功保存
    """
    store = load_template_store()
    existing = store.get(name)
    
    if not overwrite and existing is not None:
        return False
    
    store[name] = dict(payload)
    write_template_store(store)
    return True


def delete_template(name: str) -> bool:
    """删除模板
    
    Args:
        name: 模板名称
        
    Returns:
        是否成功删除
    """
    store = load_template_store()
    base_store = get_builtin_template_store()
    
    existed = name in store or name in base_store
    if not existed:
        return False
    
    if name in store:
        del store[name]
    
    if name in base_store:
        store[name] = None
    
    write_template_store(store)
    return True


def list_templates() -> Dict[str, dict]:
    """列出所有模板
    
    Returns:
        模板字典
    """
    return load_template_store()


def template_to_params(template: dict) -> dict:
    """将模板转换为参数字典
    
    Args:
        template: 模板字典
        
    Returns:
        参数字典
    """
    params = {}
    
    # 基本参数
    if "preset_keys" in template:
        params["preset_keys"] = template["preset_keys"]
    if "momentum_windows" in template:
        params["momentum_windows"] = template["momentum_windows"]
    if "momentum_weights" in template:
        params["momentum_weights"] = template["momentum_weights"]
    
    # 可选参数
    optional_keys = [
        "start", "end", "correlation_threshold", "momentum_threshold",
        "stability_weight", "chop_window", "trend_window", "lookback_days"
    ]
    
    for key in optional_keys:
        if key in template:
            params[key] = template[key]
    
    return params
