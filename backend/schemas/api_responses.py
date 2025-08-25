"""
API Response Schemas
API响应数据格式定义 - 确保前后端数据一致性
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ========== 动量排名相关 ==========

class ETFMomentumScore(BaseModel):
    """ETF动量得分"""
    code: str = Field(..., description="ETF代码")
    name: str = Field(..., description="ETF名称")
    return_60d: float = Field(..., description="60日收益率(%)")
    return_120d: float = Field(..., description="120日收益率(%)")
    momentum_score: float = Field(..., description="动量得分")
    rank: int = Field(..., description="排名")
    category: str = Field(..., description="分类(growth/new_energy/others)")
    qualified: bool = Field(True, description="是否满足资格条件")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "512760",
                "name": "半导体ETF",
                "return_60d": 15.2,
                "return_120d": 22.5,
                "momentum_score": 18.12,
                "rank": 1,
                "category": "growth",
                "qualified": True
            }
        }


class MomentumRankingsResponse(BaseModel):
    """动量排行响应"""
    rankings: List[ETFMomentumScore]
    calculation_time: datetime
    formula: str = "Score = 0.6 × r60 + 0.4 × r120"
    
    class Config:
        schema_extra = {
            "example": {
                "rankings": [...],
                "calculation_time": "2024-08-25T10:30:00",
                "formula": "Score = 0.6 × r60 + 0.4 × r120"
            }
        }


# ========== 相关性矩阵相关 ==========

class CorrelationData(BaseModel):
    """相关性数据"""
    etf1_code: str
    etf1_name: str
    etf2_code: str
    etf2_name: str
    correlation: float = Field(..., ge=-1, le=1, description="相关系数")
    qualified: bool = Field(..., description="是否满足条件(ρ≤0.8)")
    
    class Config:
        schema_extra = {
            "example": {
                "etf1_code": "512760",
                "etf1_name": "半导体ETF",
                "etf2_code": "512720",
                "etf2_name": "计算机ETF",
                "correlation": 0.75,
                "qualified": True
            }
        }


class CorrelationMatrixResponse(BaseModel):
    """相关性矩阵响应"""
    matrix: List[CorrelationData]
    lookback_days: int = 90
    threshold: float = 0.8
    
    
# ========== 资格状态相关 ==========

class QualificationCondition(BaseModel):
    """资格条件"""
    name: str
    description: str
    met: bool
    value: Optional[Any] = None
    threshold: Optional[Any] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "ma200_above",
                "description": "价格在200日均线上方",
                "met": True,
                "value": 105.2,
                "threshold": 100.0
            }
        }


class QualificationStatusResponse(BaseModel):
    """资格状态响应"""
    etf_code: str
    etf_name: str
    overall_qualified: bool
    conditions: List[QualificationCondition]
    recommendations: List[str]
    

# ========== 市场环境相关 ==========

class MarketIndicator(BaseModel):
    """市场指标"""
    name: str
    value: float
    unit: str = "%"
    status: str = Field(..., description="状态(normal/warning/critical)")
    description: Optional[str] = None
    

class MarketRegimeResponse(BaseModel):
    """市场状态响应"""
    regime: str = Field(..., description="市场状态(TREND/CHOP/BEAR/NEUTRAL)")
    trend_confirmed: bool = Field(..., description="趋势确认(可否双腿)")
    ma200_status: Dict[str, Any]
    chop_conditions: Dict[str, bool]
    indicators: List[MarketIndicator]
    recommendations: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "regime": "TREND",
                "trend_confirmed": True,
                "ma200_status": {
                    "above_ma200": True,
                    "distance_pct": 2.5,
                    "ma200_slope": 0.3
                },
                "chop_conditions": {
                    "band_days": False,
                    "high_atr_flat_ma": False,
                    "momentum_convergence": False
                },
                "indicators": [...],
                "recommendations": ["趋势模式：可启用双腿策略"]
            }
        }


# ========== 决策建议相关 ==========

class TradingDecision(BaseModel):
    """交易决策"""
    action: str = Field(..., description="操作(BUY/SELL/HOLD)")
    etf_code: str
    etf_name: str
    position_size: float = Field(..., description="仓位大小(%)")
    price_band: Dict[str, float] = Field(..., description="限价区间")
    stop_loss: float = Field(..., description="止损价")
    reasons: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "action": "BUY",
                "etf_code": "512760",
                "etf_name": "半导体ETF",
                "position_size": 5.0,
                "price_band": {"lower": 1.234, "upper": 1.246},
                "stop_loss": 1.085,
                "reasons": ["动量得分排名第1", "与现有持仓相关性低"]
            }
        }


class DecisionResponse(BaseModel):
    """决策响应"""
    market_regime: str
    mode: str = Field(..., description="当前模式(aggressive/balanced/conservative/chop)")
    decisions: List[TradingDecision]
    current_parameters: Dict[str, Any]
    execution_window: str
    timestamp: datetime
    

# ========== 持仓状态相关 ==========

class PositionInfo(BaseModel):
    """持仓信息"""
    etf_code: str
    etf_name: str
    entry_price: float
    current_price: float
    shares: int
    weight: float = Field(..., description="当前权重(%)")
    target_weight: float = Field(..., description="目标权重(%)")
    pnl: float = Field(..., description="盈亏(%)")
    days_held: int
    stop_loss_price: float
    
    
class PortfolioStatusResponse(BaseModel):
    """组合状态响应"""
    core_positions: List[PositionInfo]
    satellite_positions: List[PositionInfo]
    total_value: float
    core_weight: float
    satellite_weight: float
    cash_weight: float
    rebalance_needed: bool
    

# ========== 错误响应 ==========

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)