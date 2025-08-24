"""
Portfolio management API endpoints.
"""

from typing import Dict, List, Optional
from datetime import date
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.models.base import get_db_dependency
from backend.core.portfolio_manager import get_portfolio_manager

router = APIRouter()


@router.get("/positions")
async def get_positions(user_id: int = 1):
    """Get current portfolio positions"""
    manager = get_portfolio_manager(user_id)
    positions = manager.track_positions()
    
    return {
        "positions": [
            {
                "code": p.code,
                "shares": p.shares,
                "avg_price": p.avg_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
                "weight": p.weight,
                "unrealized_pnl": p.unrealized_pnl,
                "unrealized_pnl_pct": p.unrealized_pnl_pct,
                "portfolio_type": p.portfolio_type,
                "days_held": p.days_held
            }
            for p in positions
        ]
    }


@router.get("/weights")
async def get_portfolio_weights(user_id: int = 1):
    """Get portfolio weight distribution"""
    manager = get_portfolio_manager(user_id)
    weights = manager.calculate_weights()
    return weights


@router.get("/performance")
async def get_performance(
    user_id: int = 1,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get portfolio performance metrics"""
    manager = get_portfolio_manager(user_id)
    performance = manager.calculate_performance(start_date, end_date)
    return performance


@router.post("/rebalance/core")
async def rebalance_core_portfolio(
    user_id: int = 1,
    target_etfs: List[str] = Query(..., description="Target core ETF codes")
):
    """Generate rebalancing orders for core portfolio"""
    manager = get_portfolio_manager(user_id)
    
    # Get current prices (simplified - would fetch real prices)
    current_prices = {code: 1.0 for code in target_etfs}
    
    orders = manager.rebalance_core(target_etfs, current_prices)
    
    return {
        "orders": [
            {
                "code": o.code,
                "side": o.side,
                "quantity": o.quantity,
                "order_type": o.order_type,
                "limit_price": o.limit_price,
                "reason": o.reason
            }
            for o in orders
        ]
    }