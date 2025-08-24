"""
Configuration management API endpoints.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from backend.config.config import get_config_manager, TradingPreset, ETFPool
from backend.utils.validators import validate_parameters

router = APIRouter()


class ParameterUpdate(BaseModel):
    """Parameter update request schema"""
    section: str
    key: str
    value: Any


class ETFAddRequest(BaseModel):
    """ETF addition request schema"""
    code: str
    name: str
    category: str
    style: str
    tracking_index: str = None
    enabled: bool = True


@router.get("/current")
async def get_current_config():
    """Get current system configuration"""
    manager = get_config_manager()
    config = manager.get_config()
    
    return {
        "active_preset": config.active_preset,
        "trading_params": config.trading_params.dict(),
        "market_thresholds": config.market_thresholds.dict(),
        "execution_settings": config.execution_settings.dict(),
        "portfolio_settings": config.portfolio_settings.dict(),
        "etf_pools": [
            {
                "code": etf.code,
                "name": etf.name,
                "category": etf.category,
                "style": etf.style,
                "tracking_index": etf.tracking_index,
                "enabled": etf.enabled
            }
            for etf in config.etf_pools
        ]
    }


@router.post("/preset/{preset_name}")
async def apply_preset(preset_name: str):
    """Apply a configuration preset"""
    manager = get_config_manager()
    
    try:
        preset = TradingPreset(preset_name.lower())
        manager.apply_preset(preset)
        return {
            "status": "success",
            "message": f"Applied {preset_name} preset",
            "active_preset": preset_name
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset: {preset_name}. Valid options: aggressive, balanced, conservative"
        )


@router.post("/parameter")
async def update_parameter(update: ParameterUpdate):
    """Update a specific configuration parameter"""
    manager = get_config_manager()
    
    try:
        # Validate the parameter update
        is_valid, errors = validate_parameters({update.key: update.value})
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Validation errors: {errors}")
        
        manager.update_parameter(update.section, update.key, update.value)
        return {
            "status": "success",
            "message": f"Updated {update.section}.{update.key} to {update.value}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parameters/batch")
async def update_parameters_batch(updates: List[ParameterUpdate]):
    """Update multiple configuration parameters"""
    manager = get_config_manager()
    updated = []
    errors = []
    
    for update in updates:
        try:
            manager.update_parameter(update.section, update.key, update.value)
            updated.append(f"{update.section}.{update.key}")
        except ValueError as e:
            errors.append(f"{update.section}.{update.key}: {str(e)}")
    
    if errors:
        return {
            "status": "partial",
            "updated": updated,
            "errors": errors
        }
    
    return {
        "status": "success",
        "updated": updated
    }


@router.get("/etf-pools")
async def get_etf_pools(category: str = None):
    """Get ETF pools with optional category filter"""
    manager = get_config_manager()
    pools = manager.get_etf_pools(category)
    
    return {
        "etf_pools": [
            {
                "code": etf.code,
                "name": etf.name,
                "category": etf.category,
                "style": etf.style,
                "tracking_index": etf.tracking_index,
                "enabled": etf.enabled
            }
            for etf in pools
        ]
    }


@router.post("/etf-pool/add")
async def add_etf_to_pool(etf: ETFAddRequest):
    """Add new ETF to pool"""
    manager = get_config_manager()
    
    try:
        new_etf = ETFPool(
            code=etf.code,
            name=etf.name,
            category=etf.category,
            style=etf.style,
            tracking_index=etf.tracking_index,
            enabled=etf.enabled
        )
        manager.add_etf(new_etf)
        return {
            "status": "success",
            "message": f"Added ETF {etf.code} to pool"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/etf-pool/{code}")
async def remove_etf_from_pool(code: str):
    """Remove ETF from pool"""
    manager = get_config_manager()
    
    try:
        manager.remove_etf(code)
        return {
            "status": "success",
            "message": f"Removed ETF {code} from pool"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/etf-pool/{code}/toggle")
async def toggle_etf_status(code: str, enabled: bool = Body(...)):
    """Enable or disable an ETF"""
    manager = get_config_manager()
    
    try:
        manager.toggle_etf(code, enabled)
        return {
            "status": "success",
            "message": f"ETF {code} {'enabled' if enabled else 'disabled'}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/presets")
async def list_presets():
    """List available configuration presets"""
    manager = get_config_manager()
    
    presets = []
    for preset_name, preset_config in manager.PRESETS.items():
        presets.append({
            "name": preset_name.value,
            "description": get_preset_description(preset_name),
            "key_parameters": {
                "stop_loss_range": f"{preset_config['trading_params']['stop_loss_min']*100:.0f}% to {preset_config['trading_params']['stop_loss_max']*100:.0f}%",
                "min_holding_days": preset_config['trading_params']['min_holding_days'],
                "core_weight": f"{preset_config['portfolio_settings']['core_target_weight']*100:.0f}%",
                "max_legs_per_day": preset_config['trading_params']['max_legs_per_day']
            }
        })
    
    return {"presets": presets}


def get_preset_description(preset: TradingPreset) -> str:
    """Get description for a preset"""
    descriptions = {
        TradingPreset.AGGRESSIVE: "High risk, high return strategy with frequent trading",
        TradingPreset.BALANCED: "Moderate risk strategy balancing growth and stability",
        TradingPreset.CONSERVATIVE: "Low risk strategy prioritizing capital preservation"
    }
    return descriptions.get(preset, "Custom configuration")