"""
Market data schemas for API validation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field


class ETFInfoResponse(BaseModel):
    """ETF information response schema"""
    id: int
    code: str
    name: str
    category: str
    style: str
    tracking_index: Optional[str] = None
    fund_company: Optional[str] = None
    inception_date: Optional[date] = None
    aum: Optional[float] = None
    expense_ratio: Optional[float] = None
    exchange: Optional[str] = None
    lot_size: int = 100
    tracking_error: Optional[float] = None
    avg_daily_volume: Optional[float] = None
    avg_spread: Optional[float] = None
    is_active: bool = True
    is_tradeable: bool = True
    has_options: bool = False
    
    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Price history response schema"""
    id: int
    code: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: Optional[float] = None
    iopv: Optional[float] = None
    premium_discount: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma120: Optional[float] = None
    ma200: Optional[float] = None
    atr20: Optional[float] = None
    volatility20: Optional[float] = None
    daily_return: Optional[float] = None
    return_5d: Optional[float] = None
    return_20d: Optional[float] = None
    return_60d: Optional[float] = None
    return_120d: Optional[float] = None
    
    class Config:
        from_attributes = True


class MarketIndicatorsResponse(BaseModel):
    """Market indicators response schema"""
    id: int
    date: date
    hs300_close: float
    hs300_volume: Optional[float] = None
    hs300_turnover: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma120: Optional[float] = None
    ma200: Optional[float] = None
    atr20: Optional[float] = None
    volatility20: Optional[float] = None
    chop_value: Optional[float] = None
    chop_status: Optional[str] = None
    above_yearline: Optional[bool] = None
    yearline_distance: Optional[float] = None
    regime: Optional[str] = None
    regime_days: Optional[int] = None
    
    class Config:
        from_attributes = True


class RealtimeQuoteResponse(BaseModel):
    """Real-time quote response schema"""
    code: str
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    iopv: Optional[float] = None
    premium_discount: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    prev_close: Optional[float] = None
    time: datetime