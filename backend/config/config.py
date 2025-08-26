"""
Configuration management with adjustable parameters for Momentum Lens ETF trading system.
All parameters can be adjusted from the frontend.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import json
import os

# Provide minimal fallbacks when pydantic is unavailable
try:
    from pydantic import BaseModel, Field, validator
except ModuleNotFoundError:  # pragma: no cover - fallback for limited env
    class BaseModel:  # type: ignore
        """Simple stand-in for pydantic.BaseModel"""

        def __init__(self, **data: Any) -> None:
            for name, value in self.__class__.__dict__.items():
                if (
                    not name.startswith("_")
                    and not callable(value)
                    and not isinstance(value, property)
                ):
                    setattr(self, name, value)
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default=None, description: str | None = None):  # type: ignore
        return default

    def validator(field_name: str):  # type: ignore
        def decorator(func):
            return func
        return decorator


class TradingPreset(str, Enum):
    """Trading strategy presets"""
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class TradingParameters(BaseModel):
    """Trading parameters configuration"""
    stop_loss_min: float = Field(default=-0.15, description="Minimum stop loss threshold")
    stop_loss_max: float = Field(default=-0.10, description="Maximum stop loss threshold")
    buffer_zone_min: float = Field(default=0.02, description="Minimum buffer zone")
    buffer_zone_max: float = Field(default=0.04, description="Maximum buffer zone")
    min_holding_days: int = Field(default=14, description="Minimum holding period in days")
    max_holding_days: int = Field(default=28, description="Maximum holding period in days")
    bandwidth: float = Field(default=0.02, description="Trading bandwidth")
    max_legs_per_day: int = Field(default=3, description="Maximum trading legs per day")
    
    @validator('stop_loss_min')
    def validate_stop_loss_min(cls, v):
        if v > -0.05 or v < -0.30:
            raise ValueError("Stop loss min must be between -30% and -5%")
        return v
    
    @validator('buffer_zone_min')
    def validate_buffer_zone(cls, v):
        if v < 0.01 or v > 0.10:
            raise ValueError("Buffer zone must be between 1% and 10%")
        return v


class MarketThresholds(BaseModel):
    """Market regime detection thresholds"""
    yearline_days: int = Field(default=200, description="Moving average period for yearline")
    chop_upper: float = Field(default=61.8, description="CHOP upper threshold")
    chop_lower: float = Field(default=38.2, description="CHOP lower threshold")
    chop_period: int = Field(default=14, description="CHOP calculation period")
    correlation_limit: float = Field(default=0.8, description="Maximum correlation between ETFs")
    correlation_lookback: int = Field(default=90, description="Correlation lookback period in days")
    momentum_weight_60d: float = Field(default=0.6, description="Weight for 60-day momentum")
    momentum_weight_120d: float = Field(default=0.4, description="Weight for 120-day momentum")


class ETFPool(BaseModel):
    """ETF pool configuration with constraints"""
    code: str
    name: str
    category: str  # Core or Satellite
    style: str  # Style factor, Sector, Theme, Growth, NewEnergy, Cross-border
    tracking_index: Optional[str] = None
    enabled: bool = True
    pool_group: Optional[str] = None  # Constraint group (e.g., growth_line, new_energy)
    priority: Optional[int] = None  # Priority within group (lower is higher priority)
    target_weight: Optional[float] = None  # Fixed target weight for core ETFs


class ExecutionSettings(BaseModel):
    """Trade execution settings"""
    morning_open: str = Field(default="09:30", description="Morning session open time")
    morning_close: str = Field(default="11:30", description="Morning session close time")
    afternoon_open: str = Field(default="13:00", description="Afternoon session open time")
    afternoon_close: str = Field(default="15:00", description="Afternoon session close time")
    iopv_band_lower: float = Field(default=-0.005, description="IOPV lower band")
    iopv_band_upper: float = Field(default=0.005, description="IOPV upper band")
    premium_limit: float = Field(default=0.02, description="Maximum acceptable premium")
    slippage_estimate: float = Field(default=0.001, description="Estimated slippage")
    commission_rate: float = Field(default=0.0003, description="Commission rate")


class PortfolioSettings(BaseModel):
    """Portfolio allocation settings"""
    core_target_weight: float = Field(default=0.6, description="Target weight for core portfolio")
    satellite_target_weight: float = Field(default=0.4, description="Target weight for satellite portfolio")
    max_single_position: float = Field(default=0.15, description="Maximum weight for single position")
    min_single_position: float = Field(default=0.02, description="Minimum weight for single position")
    rebalance_threshold: float = Field(default=0.05, description="Rebalance trigger threshold")
    cash_buffer: float = Field(default=0.02, description="Cash buffer percentage")


class SystemConfig(BaseModel):
    """Complete system configuration"""
    trading_params: TradingParameters = TradingParameters()
    market_thresholds: MarketThresholds = MarketThresholds()
    execution_settings: ExecutionSettings = ExecutionSettings()
    portfolio_settings: PortfolioSettings = PortfolioSettings()
    etf_pools: List[ETFPool] = []
    active_preset: TradingPreset = TradingPreset.BALANCED
    
    class Config:
        use_enum_values = True


class ConfigurationManager:
    """Manager for system configuration with preset support"""
    
    # Preset configurations
    PRESETS = {
        TradingPreset.AGGRESSIVE: {
            "trading_params": {
                "stop_loss_min": -0.20,
                "stop_loss_max": -0.15,
                "buffer_zone_min": 0.01,
                "buffer_zone_max": 0.02,
                "min_holding_days": 7,
                "max_holding_days": 14,
                "max_legs_per_day": 5
            },
            "market_thresholds": {
                "correlation_limit": 0.85,
                "momentum_weight_60d": 0.7,
                "momentum_weight_120d": 0.3
            },
            "portfolio_settings": {
                "core_target_weight": 0.5,
                "satellite_target_weight": 0.5,
                "max_single_position": 0.20,
                "rebalance_threshold": 0.07
            }
        },
        TradingPreset.BALANCED: {
            "trading_params": {
                "stop_loss_min": -0.15,
                "stop_loss_max": -0.10,
                "buffer_zone_min": 0.02,
                "buffer_zone_max": 0.04,
                "min_holding_days": 14,
                "max_holding_days": 28,
                "max_legs_per_day": 3
            },
            "market_thresholds": {
                "correlation_limit": 0.80,
                "momentum_weight_60d": 0.6,
                "momentum_weight_120d": 0.4
            },
            "portfolio_settings": {
                "core_target_weight": 0.6,
                "satellite_target_weight": 0.4,
                "max_single_position": 0.15,
                "rebalance_threshold": 0.05
            }
        },
        TradingPreset.CONSERVATIVE: {
            "trading_params": {
                "stop_loss_min": -0.10,
                "stop_loss_max": -0.07,
                "buffer_zone_min": 0.03,
                "buffer_zone_max": 0.05,
                "min_holding_days": 21,
                "max_holding_days": 42,
                "max_legs_per_day": 2
            },
            "market_thresholds": {
                "correlation_limit": 0.75,
                "momentum_weight_60d": 0.5,
                "momentum_weight_120d": 0.5
            },
            "portfolio_settings": {
                "core_target_weight": 0.7,
                "satellite_target_weight": 0.3,
                "max_single_position": 0.10,
                "rebalance_threshold": 0.03
            }
        }
    }
    
    # Default ETF pools with constraints
    DEFAULT_ETF_POOLS = [
        # Core ETFs - Fixed allocations
        {"code": "510300", "name": "沪深300ETF", "category": "Core", "style": "Style", "tracking_index": "000300", "target_weight": 0.20},
        {"code": "159919", "name": "沪深300ETF(易方达)", "category": "Core", "style": "Style", "tracking_index": "000300", "target_weight": 0.20},
        {"code": "510880", "name": "红利ETF", "category": "Core", "style": "Style", "tracking_index": "000015", "target_weight": 0.15},
        {"code": "511990", "name": "华宝添益", "category": "Core", "style": "Bond", "tracking_index": "BOND", "target_weight": 0.10},
        {"code": "518880", "name": "黄金ETF", "category": "Core", "style": "Commodity", "tracking_index": "AU9999", "target_weight": 0.10},
        {"code": "513500", "name": "标普500ETF", "category": "Core", "style": "Cross-border", "tracking_index": "SPX", "target_weight": 0.05},
        
        # Satellite ETFs - Growth line (Only 1 per period)
        {"code": "588000", "name": "科创50ETF", "category": "Satellite", "style": "Growth", "tracking_index": "000688", "pool_group": "growth_line"},
        {"code": "512760", "name": "芯片ETF", "category": "Satellite", "style": "Growth", "tracking_index": "931743", "pool_group": "growth_line"},
        {"code": "512720", "name": "计算机ETF", "category": "Satellite", "style": "Growth", "tracking_index": "931550", "pool_group": "growth_line"},
        {"code": "516010", "name": "游戏ETF", "category": "Satellite", "style": "Growth", "tracking_index": "CSIH30184", "pool_group": "growth_line", "priority": 1},
        {"code": "159869", "name": "游戏动漫ETF", "category": "Satellite", "style": "Growth", "tracking_index": "CSI930901", "pool_group": "growth_line"},
        
        # Satellite ETFs - New Energy (Only 1 per period)
        {"code": "516160", "name": "新能源ETF", "category": "Satellite", "style": "NewEnergy", "tracking_index": "930997", "pool_group": "new_energy", "priority": 1},
        {"code": "515790", "name": "光伏ETF", "category": "Satellite", "style": "NewEnergy", "tracking_index": "931151", "pool_group": "new_energy"},
        {"code": "515030", "name": "新能源车ETF", "category": "Satellite", "style": "NewEnergy", "tracking_index": "399976", "pool_group": "new_energy"},
        
        # Satellite ETFs - Sectors
        {"code": "512880", "name": "证券ETF", "category": "Satellite", "style": "Sector", "tracking_index": "399975"},
        {"code": "512000", "name": "券商ETF", "category": "Satellite", "style": "Sector", "tracking_index": "399975"},
        {"code": "512660", "name": "军工ETF", "category": "Satellite", "style": "Sector", "tracking_index": "399967"},
        {"code": "512690", "name": "酒ETF", "category": "Satellite", "style": "Sector", "tracking_index": "399997"},
        {"code": "515880", "name": "通信ETF", "category": "Satellite", "style": "Sector", "tracking_index": "931160"},
        {"code": "512400", "name": "有色金属ETF", "category": "Satellite", "style": "Sector", "tracking_index": "000811"},
        
        # Other Cross-border ETFs
        {"code": "513050", "name": "中概互联ETF", "category": "Satellite", "style": "Cross-border", "tracking_index": "KWEB"},
        {"code": "513100", "name": "纳斯达克ETF", "category": "Satellite", "style": "Cross-border", "tracking_index": "NDX"},
        {"code": "513520", "name": "日经ETF", "category": "Satellite", "style": "Cross-border", "tracking_index": "N225"},
    ]
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_file = config_file or os.getenv("CONFIG_FILE", "config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> SystemConfig:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = SystemConfig(**data)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                config = self._create_default_config()
        else:
            config = self._create_default_config()
        
        # Ensure ETF pools are populated
        if not config.etf_pools:
            config.etf_pools = [ETFPool(**etf) for etf in self.DEFAULT_ETF_POOLS]
        
        return config
    
    def _create_default_config(self) -> SystemConfig:
        """Create default configuration"""
        config = SystemConfig()
        config.etf_pools = [ETFPool(**etf) for etf in self.DEFAULT_ETF_POOLS]
        return config
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {e}")
    
    def apply_preset(self, preset: TradingPreset):
        """Apply a preset configuration"""
        if preset not in self.PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        
        preset_config = self.PRESETS[preset]
        
        # Update configuration with preset values
        for section, values in preset_config.items():
            if hasattr(self.config, section):
                section_obj = getattr(self.config, section)
                for key, value in values.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
        
        self.config.active_preset = preset
        self.save_config()
    
    def update_parameter(self, section: str, key: str, value: Any):
        """Update a specific parameter"""
        if not hasattr(self.config, section):
            raise ValueError(f"Unknown section: {section}")
        
        section_obj = getattr(self.config, section)
        if not hasattr(section_obj, key):
            raise ValueError(f"Unknown parameter: {key} in section {section}")
        
        setattr(section_obj, key, value)
        self.save_config()
    
    def get_config(self) -> SystemConfig:
        """Get current configuration"""
        return self.config
    
    def get_etf_pools(self, category: Optional[str] = None, 
                     pool_group: Optional[str] = None,
                     respect_constraints: bool = True) -> List[ETFPool]:
        """Get ETF pools with constraint handling
        
        Args:
            category: Filter by category (Core/Satellite)
            pool_group: Filter by pool group (growth_line, new_energy)
            respect_constraints: Apply pool constraints (only 1 per group)
            
        Returns:
            List of ETF pools respecting constraints
        """
        pools = self.config.etf_pools
        
        # Filter by category
        if category:
            pools = [p for p in pools if p.category == category and p.enabled]
        
        # Filter by pool group
        if pool_group:
            pools = [p for p in pools if p.pool_group == pool_group and p.enabled]
        
        # Apply constraints if requested
        if respect_constraints:
            constrained_pools = []
            seen_groups = set()
            
            # Sort by priority within groups
            sorted_pools = sorted(pools, key=lambda x: (x.pool_group or '', x.priority or 999))
            
            for pool in sorted_pools:
                if pool.pool_group:
                    # Only one per constraint group
                    if pool.pool_group not in seen_groups:
                        constrained_pools.append(pool)
                        seen_groups.add(pool.pool_group)
                else:
                    # No constraint group, always include
                    constrained_pools.append(pool)
            
            return constrained_pools
        
        return pools
    
    def add_etf(self, etf: ETFPool):
        """Add new ETF to pool"""
        # Check for duplicates
        if any(e.code == etf.code for e in self.config.etf_pools):
            raise ValueError(f"ETF {etf.code} already exists")
        
        self.config.etf_pools.append(etf)
        self.save_config()
    
    def remove_etf(self, code: str):
        """Remove ETF from pool"""
        self.config.etf_pools = [e for e in self.config.etf_pools if e.code != code]
        self.save_config()
    
    def toggle_etf(self, code: str, enabled: bool):
        """Enable or disable an ETF"""
        for etf in self.config.etf_pools:
            if etf.code == code:
                etf.enabled = enabled
                self.save_config()
                return
        raise ValueError(f"ETF {code} not found")


# Singleton instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get singleton configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager