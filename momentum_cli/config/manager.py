"""配置管理器

提供统一的配置管理接口，简化配置操作。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .settings import (
    DEFAULT_SETTINGS,
    load_cli_settings,
    save_cli_settings,
    update_setting,
)
from .validators import (
    validate_corr_threshold,
    validate_float_range_setting,
    validate_positive_int_setting,
    validate_ratio_setting,
)


class ConfigManager:
    """配置管理器类
    
    提供统一的配置访问和修改接口。
    """
    
    def __init__(self):
        """初始化配置管理器"""
        self._settings: Dict[str, Any] = {}
        self._dirty = False
        self.reload()
    
    def reload(self) -> None:
        """重新加载配置"""
        loaded = load_cli_settings()
        self._settings = {**DEFAULT_SETTINGS, **loaded}
        self._dirty = False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any, *, persist: bool = True, validate: bool = True) -> bool:
        """设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            persist: 是否立即持久化
            validate: 是否验证值
            
        Returns:
            是否成功设置
        """
        # 验证值
        if validate:
            if not self._validate_value(key, value):
                return False
        
        # 更新配置
        old_value = self._settings.get(key)
        self._settings[key] = value
        self._dirty = True
        
        # 持久化
        if persist:
            try:
                update_setting(self._settings, key, value)
                self._dirty = False
                return True
            except Exception:
                # 回滚
                if old_value is not None:
                    self._settings[key] = old_value
                else:
                    self._settings.pop(key, None)
                return False
        
        return True
    
    def update(self, updates: Dict[str, Any], *, persist: bool = True) -> bool:
        """批量更新配置
        
        Args:
            updates: 配置更新字典
            persist: 是否持久化
            
        Returns:
            是否成功更新
        """
        old_values = {}
        try:
            for key, value in updates.items():
                old_values[key] = self._settings.get(key)
                self._settings[key] = value
            
            self._dirty = True
            
            if persist:
                save_cli_settings(self._settings)
                self._dirty = False
            
            return True
        except Exception:
            # 回滚
            for key, old_value in old_values.items():
                if old_value is not None:
                    self._settings[key] = old_value
                else:
                    self._settings.pop(key, None)
            return False
    
    def save(self) -> bool:
        """保存配置到文件
        
        Returns:
            是否成功保存
        """
        if not self._dirty:
            return True
        
        try:
            save_cli_settings(self._settings)
            self._dirty = False
            return True
        except Exception:
            return False
    
    def is_dirty(self) -> bool:
        """检查配置是否有未保存的更改"""
        return self._dirty
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return dict(self._settings)
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置
        
        Returns:
            是否成功重置
        """
        try:
            self._settings = dict(DEFAULT_SETTINGS)
            save_cli_settings(self._settings)
            self._dirty = False
            return True
        except Exception:
            return False
    
    def _validate_value(self, key: str, value: Any) -> bool:
        """验证配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否有效
        """
        # 根据键名选择验证器
        if "threshold" in key.lower() or "weight" in key.lower():
            try:
                return validate_ratio_setting(value)
            except Exception:
                return False
        
        if "window" in key.lower() or "span" in key.lower():
            try:
                return validate_positive_int_setting(value)
            except Exception:
                return False
        
        # 默认通过
        return True
    
    # 便捷方法
    def get_theme(self) -> str:
        """获取当前主题"""
        return self.get("cli_theme", DEFAULT_SETTINGS["cli_theme"])
    
    def set_theme(self, theme: str) -> bool:
        """设置主题"""
        return self.set("cli_theme", theme)
    
    def get_plot_template(self) -> str:
        """获取绘图模板"""
        return self.get("plot_template", DEFAULT_SETTINGS["plot_template"])
    
    def set_plot_template(self, template: str) -> bool:
        """设置绘图模板"""
        return self.set("plot_template", template)
    
    def get_correlation_threshold(self) -> float:
        """获取相关性阈值"""
        return float(self.get("correlation_alert_threshold", 0.85))
    
    def set_correlation_threshold(self, value: float) -> bool:
        """设置相关性阈值"""
        return self.set("correlation_alert_threshold", value)
    
    def get_momentum_threshold(self) -> float:
        """获取动量显著性阈值"""
        return float(self.get("momentum_significance_threshold", 0.05))
    
    def set_momentum_threshold(self, value: float) -> bool:
        """设置动量显著性阈值"""
        return self.set("momentum_significance_threshold", value)


# 全局配置管理器实例
config_manager = ConfigManager()
