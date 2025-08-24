"""
Market data API endpoints.
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models.base import get_db_dependency
from backend.models import ETFInfo, PriceHistory, MarketIndicators
from backend.core.data_fetcher import get_data_fetcher
from backend.schemas.market import (
    ETFInfoResponse,
    PriceHistoryResponse,
    MarketIndicatorsResponse,
    RealtimeQuoteResponse
)

router = APIRouter()

# Request models for data source endpoints
class TestSourceRequest(BaseModel):
    sourceId: str
    apiKey: Optional[str] = None

class FetchDataRequest(BaseModel):
    sourceId: str
    symbol: str
    apiKey: Optional[str] = None

class FetchBatchRequest(BaseModel):
    sourceId: str
    symbols: List[str]
    apiKey: Optional[str] = None


@router.get("/etf/{code}", response_model=ETFInfoResponse)
async def get_etf_info(code: str, db: Session = Depends(get_db_dependency)):
    """Get ETF information by code"""
    etf = db.query(ETFInfo).filter(ETFInfo.code == code).first()
    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF {code} not found")
    return etf


@router.get("/etf", response_model=List[ETFInfoResponse])
async def list_etfs(
    category: Optional[str] = Query(None, description="Filter by category (Core/Satellite)"),
    style: Optional[str] = Query(None, description="Filter by style"),
    active_only: bool = Query(True, description="Only show active ETFs"),
    db: Session = Depends(get_db_dependency)
):
    """List all ETFs with optional filters"""
    query = db.query(ETFInfo)
    
    if category:
        query = query.filter(ETFInfo.category == category)
    if style:
        query = query.filter(ETFInfo.style == style)
    if active_only:
        query = query.filter(ETFInfo.is_active == True)
    
    return query.all()


@router.get("/prices/{code}", response_model=List[PriceHistoryResponse])
async def get_price_history(
    code: str,
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(100, description="Maximum number of records"),
    db: Session = Depends(get_db_dependency)
):
    """Get price history for an ETF"""
    query = db.query(PriceHistory).filter(PriceHistory.code == code)
    
    if start_date:
        query = query.filter(PriceHistory.date >= start_date)
    if end_date:
        query = query.filter(PriceHistory.date <= end_date)
    
    prices = query.order_by(PriceHistory.date.desc()).limit(limit).all()
    
    if not prices:
        # Try to fetch from external source
        data_fetcher = get_data_fetcher()
        df = await data_fetcher.fetch_etf_prices(
            [code],
            start_date or date.today() - timedelta(days=30),
            end_date or date.today()
        )
        
        if code in df and not df[code].empty:
            # Store in database for future use
            for _, row in df[code].iterrows():
                price_record = PriceHistory(
                    code=code,
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                db.add(price_record)
            db.commit()
            
            # Query again
            prices = query.order_by(PriceHistory.date.desc()).limit(limit).all()
    
    return prices


@router.get("/indicators", response_model=MarketIndicatorsResponse)
async def get_market_indicators(
    indicator_date: Optional[date] = Query(None, description="Date for indicators"),
    db: Session = Depends(get_db_dependency)
):
    """Get market indicators for a specific date"""
    if not indicator_date:
        indicator_date = date.today()
    
    indicators = db.query(MarketIndicators).filter(
        MarketIndicators.date == indicator_date
    ).first()
    
    if not indicators:
        # Fetch and calculate indicators
        data_fetcher = get_data_fetcher()
        indicators = await data_fetcher.fetch_market_indicators(indicator_date)
        
        if indicators:
            db.add(indicators)
            db.commit()
    
    if not indicators:
        raise HTTPException(status_code=404, detail="Market indicators not available")
    
    return indicators


@router.get("/quotes", response_model=Dict[str, RealtimeQuoteResponse])
async def get_realtime_quotes(
    codes: List[str] = Query(..., description="List of ETF codes")
):
    """Get real-time quotes for multiple ETFs"""
    data_fetcher = get_data_fetcher()
    quotes = await data_fetcher.get_realtime_quotes(codes)
    
    if not quotes:
        raise HTTPException(status_code=404, detail="No quotes available")
    
    return quotes


@router.get("/iopv", response_model=Dict[str, Dict])
async def get_iopv_data(
    codes: List[str] = Query(..., description="List of ETF codes")
):
    """Get IOPV and premium/discount data"""
    data_fetcher = get_data_fetcher()
    iopv_data = await data_fetcher.get_iopv_premium(codes)
    
    if not iopv_data:
        raise HTTPException(status_code=404, detail="IOPV data not available")
    
    return iopv_data


# Data source management endpoints
@router.post("/test-source")
async def test_data_source(request: TestSourceRequest = Body(...)):
    """Test connection to a specific data source"""
    data_fetcher = get_data_fetcher()
    result = await data_fetcher.test_data_source(request.sourceId, request.apiKey)
    return result


@router.post("/fetch")
async def fetch_from_source(request: FetchDataRequest = Body(...)):
    """Fetch data from a specific data source"""
    data_fetcher = get_data_fetcher()
    data = await data_fetcher.fetch_from_source(
        request.sourceId, 
        request.symbol, 
        request.apiKey
    )
    
    if not data:
        raise HTTPException(
            status_code=404, 
            detail=f"No data available from {request.sourceId} for {request.symbol}"
        )
    
    return {"data": data}


@router.post("/fetch-batch")
async def fetch_batch_from_source(request: FetchBatchRequest = Body(...)):
    """Fetch batch data from a specific data source"""
    data_fetcher = get_data_fetcher()
    results = {}
    
    for symbol in request.symbols:
        data = await data_fetcher.fetch_from_source(
            request.sourceId,
            symbol,
            request.apiKey
        )
        if data:
            results[symbol] = data
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No data available from {request.sourceId}"
        )
    
    return {"data": results}


@router.get("/data-sources")
async def get_data_sources():
    """Get list of available data sources"""
    return {
        "sources": [
            {
                "id": "akshare",
                "name": "AKShare",
                "type": "free",
                "requiresKey": False,
                "available": True
            },
            {
                "id": "sina",
                "name": "Sina Finance",
                "type": "free",
                "requiresKey": False,
                "available": True
            },
            {
                "id": "eastmoney",
                "name": "East Money",
                "type": "free",
                "requiresKey": False,
                "available": True
            },
            {
                "id": "tushare",
                "name": "Tushare",
                "type": "freemium",
                "requiresKey": True,
                "available": True
            },
            {
                "id": "yahoo",
                "name": "Yahoo Finance",
                "type": "free",
                "requiresKey": False,
                "available": True
            }
        ]
    }