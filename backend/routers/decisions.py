"""
Trading decision API endpoints with precise requirements.
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, WebSocket
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import asyncio
import json
import logging

from backend.models.base import get_db_dependency
from backend.core.decision_engine import get_decision_engine
from backend.core.data_fetcher import get_data_fetcher
from backend.core.portfolio_manager import get_portfolio_manager
from backend.core.risk_manager import get_risk_manager
from backend.core.order_manager import get_order_manager
from backend.utils.websocket_manager import WebSocketManager

router = APIRouter()
ws_manager = WebSocketManager()
logger = logging.getLogger(__name__)


class DecisionRequest(BaseModel):
    """Request model for decision calculation"""
    date: Optional[date] = Field(default=None, description="Decision date")
    preset: str = Field(default="balanced", description="Trading preset")
    holdings: Optional[List[Dict]] = Field(default=None, description="Current holdings")
    candidate_pool: Optional[List[str]] = Field(default=None, description="ETF candidate pool")
    thresholds: Optional[Dict[str, float]] = Field(default=None, description="Custom thresholds")


@router.post("/calculate")
async def calculate_decisions(
    request: DecisionRequest,
    user_id: int = 1,
    db: Session = Depends(get_db_dependency)
):
    """
    Calculate trading decisions with precise requirements
    
    Returns complete decision card with environment, picks, core_dca, and alerts
    """
    decision_date = request.date or date.today()
    
    # Get engines
    engine = get_decision_engine()
    data_fetcher = get_data_fetcher()
    portfolio_manager = get_portfolio_manager(user_id)
    risk_manager = get_risk_manager(user_id)
    
    # Apply preset if specified
    if request.preset:
        from backend.config.config import get_config_manager, TradingPreset
        config_manager = get_config_manager()
        try:
            preset = TradingPreset(request.preset)
            config_manager.apply_preset(preset)
        except ValueError:
            pass  # Use current config if invalid preset
    
    # Fetch market indicators
    from backend.models import MarketIndicators
    indicators = db.query(MarketIndicators).filter(
        MarketIndicators.date == decision_date
    ).first()
    
    if not indicators:
        indicators = await data_fetcher.fetch_market_indicators(decision_date)
    
    # Get ETF prices for candidate pool
    candidate_codes = request.candidate_pool or []
    if not candidate_codes:
        # Get default pool from config
        from backend.config.config import get_config_manager
        config_manager = get_config_manager()
        etf_pools = config_manager.get_etf_pools()
        candidate_codes = [etf.code for etf in etf_pools if etf.enabled]
    
    # Fetch ETF prices
    etf_prices = await data_fetcher.fetch_etf_prices(
        candidate_codes,
        start_date=decision_date - timedelta(days=250),
        end_date=decision_date
    )
    
    # Calculate scores for all ETFs
    etf_scores = {}
    for code in candidate_codes:
        if code not in etf_prices:
            continue
        
        df = etf_prices[code]
        if len(df) >= 120:
            # Calculate returns using exact 60/120 trading days
            current_price = df.iloc[-1]['close']
            price_60d_ago = df.iloc[-60]['close'] if len(df) >= 60 else df.iloc[0]['close']
            price_120d_ago = df.iloc[-120]['close'] if len(df) >= 120 else df.iloc[0]['close']
            
            return_60d = (current_price - price_60d_ago) / price_60d_ago
            return_120d = (current_price - price_120d_ago) / price_120d_ago
            
            # Calculate momentum score (FIXED: 0.6 × r60 + 0.4 × r120)
            score = engine.calculate_momentum_score(return_60d, return_120d)
            etf_scores[code] = score
    
    # Get HS300 price history for regime assessment
    hs300_data = await data_fetcher.fetch_hs300_data(
        start_date=decision_date - timedelta(days=250),
        end_date=decision_date
    )
    
    # Calculate ATR and other indicators
    if not hs300_data.empty:
        atr20, atr20_pct = data_fetcher.calculate_atr(hs300_data)
        hs300_data['ma200'] = data_fetcher.calculate_ma200(hs300_data)
        hs300_data['atr20'] = atr20
        hs300_data['atr20_pct'] = atr20_pct
    
    # Assess market regime with CHOP (2 out of 3 conditions)
    regime = engine.assess_market_regime(
        indicators,
        etf_scores=etf_scores,
        price_history=hs300_data
    )
    
    # Get current holdings
    from backend.models import Holdings
    holdings = request.holdings if request.holdings else []
    if not holdings:
        holdings = db.query(Holdings).filter(
            Holdings.user_id == user_id,
            Holdings.is_active == True
        ).all()
    
    # Generate signals
    signals = engine.generate_signals(
        decision_date,
        etf_prices,
        indicators,
        holdings
    )
    
    # Get IOPV data
    iopv_data = await data_fetcher.get_iopv_premium(candidate_codes)
    
    # Generate picks based on signals
    picks = []
    sorted_signals = sorted(signals, key=lambda x: x.momentum_score, reverse=True)
    
    for signal in sorted_signals[:5]:  # Top 5 picks
        # Check correlation with existing holdings
        correlation_matrix = engine._calculate_correlation_matrix(etf_prices)
        holding_codes = [h.code for h in holdings]
        
        passes_corr, max_corr, avg_corr, anchor_code = engine.check_correlation(
            signal.code,
            holding_codes,
            correlation_matrix,
            anchor_first=True
        )
        
        pick = {
            "code": signal.code,
            "target_weight": signal.suggested_weight,
            "rho": max_corr,
            "score": signal.momentum_score,
            "reason": f"{signal.action}: {signal.notes if signal.notes else 'Top momentum, low correlation'}",
            "r60": signal.return_60d,
            "r120": signal.return_120d
        }
        
        # Add IOPV info if available
        if signal.code in iopv_data:
            pick["iopv"] = iopv_data[signal.code].get('iopv', 0)
            pick["premium_discount"] = iopv_data[signal.code].get('premium_discount', 0)
        
        picks.append(pick)
    
    # Determine core DCA recommendations
    core_dca = {
        "510300": {"target": 0.20, "action": "MAINTAIN"},
        "510880": {"target": 0.15, "action": "MAINTAIN"},
        "511990": {"target": 0.10, "action": "MAINTAIN"},
        "518880": {"target": 0.10, "action": "MAINTAIN"},
        "513500": {"target": 0.05, "action": "MAINTAIN"}
    }
    
    # Generate risk alerts
    positions = portfolio_manager.track_positions()
    alerts = risk_manager.generate_alerts(
        positions,
        market_regime=regime,
        etf_prices=etf_prices
    )
    
    # Format alerts for response
    alert_list = []
    for alert in alerts:
        alert_dict = {
            "type": alert.alert_type.value,
            "level": alert.risk_level.value,
            "code": alert.code,
            "message": alert.message,
            "action": alert.action_required
        }
        alert_list.append(alert_dict)
    
    # Add market regime change alerts
    if regime['yearline'] and not regime['chop']:
        alert_list.append({
            "type": "YEARLINE_UP",
            "level": "LOW",
            "message": "Market above MA200, trend mode active",
            "action": "CONSIDER ADDING POSITIONS"
        })
    elif not regime['yearline']:
        alert_list.append({
            "type": "YEARLINE_DOWN",
            "level": "HIGH",
            "message": "Market below MA200, defensive mode",
            "action": "REDUCE RISK EXPOSURE"
        })
    
    if regime['chop']:
        alert_list.append({
            "type": "CHOP_ON",
            "level": "MEDIUM",
            "message": f"CHOP conditions met: {', '.join(regime['chop_conditions_met'])}",
            "action": "WIDEN REBALANCE BANDS TO ±7pp"
        })
    
    return {
        "environment": {
            "yearline": regime['yearline'],
            "atr20_pct": regime['atr20_pct'],
            "chop": regime['chop'],
            "regime": regime['regime'].value,
            "chop_conditions_met": regime['chop_conditions_met']
        },
        "picks": picks,
        "core_dca": core_dca,
        "alerts": alert_list,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/current")
async def get_current_decisions(
    user_id: int = 1,
    db: Session = Depends(get_db_dependency)
):
    """
    Get current decision card with IOPV bands and time windows
    """
    # Get order manager
    order_manager = get_order_manager(user_id)
    
    # Get pending orders
    pending_orders = order_manager.get_pending_orders()
    
    # Get next execution window
    from backend.core.order_manager import ExecutionWindow
    window_name, window_time = ExecutionWindow.get_next_window(datetime.now())
    
    # Get current positions
    portfolio_manager = get_portfolio_manager(user_id)
    positions = portfolio_manager.track_positions()
    
    # Format position data
    position_data = []
    for pos in positions:
        position_data.append({
            "code": pos.code,
            "shares": pos.shares,
            "weight": pos.weight,
            "unrealized_pnl": pos.unrealized_pnl,
            "unrealized_pnl_pct": pos.unrealized_pnl_pct,
            "days_held": pos.days_held,
            "portfolio_type": pos.portfolio_type
        })
    
    # Format pending orders with IOPV bands
    order_data = []
    for order in pending_orders:
        order_data.append({
            "code": order['code'],
            "side": order['side'],
            "quantity": order['quantity'],
            "limit_price": order['limit_price'],
            "window": order['window'],
            "expire_time": order['expire_time'].isoformat() if order['expire_time'] else None,
            "reason": order['reason']
        })
    
    return {
        "current_positions": position_data,
        "pending_orders": order_data,
        "next_window": {
            "name": window_name,
            "time": window_time.isoformat()
        },
        "execution_windows": [
            {"name": "Morning", "time": "10:30"},
            {"name": "Afternoon", "time": "14:00"}
        ]
    }


@router.get("/momentum-scores")
async def get_momentum_scores(
    codes: List[str],
    db: Session = Depends(get_db_dependency)
):
    """Calculate momentum scores for specified ETFs"""
    engine = get_decision_engine()
    scores = {}
    
    for code in codes:
        # Get price history (simplified)
        from backend.models import PriceHistory
        prices = db.query(PriceHistory).filter(
            PriceHistory.code == code
        ).order_by(PriceHistory.date.desc()).limit(120).all()
        
        if len(prices) >= 120:
            # Calculate returns
            current = prices[0].close
            price_60d = prices[59].close if len(prices) > 59 else prices[-1].close
            price_120d = prices[119].close if len(prices) > 119 else prices[-1].close
            
            return_60d = (current - price_60d) / price_60d
            return_120d = (current - price_120d) / price_120d
            
            # FIXED formula: 0.6 × r60 + 0.4 × r120
            score = engine.calculate_momentum_score(return_60d, return_120d)
            scores[code] = {
                "score": score,
                "return_60d": return_60d,
                "return_120d": return_120d,
                "formula": "0.6 × r60 + 0.4 × r120"
            }
    
    return scores


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket, user_id: int = 1):
    """
    WebSocket endpoint for real-time alert streaming
    Push enumerated alert events with snapshots
    """
    await ws_manager.connect(websocket, user_id)
    
    try:
        # Get risk manager
        risk_manager = get_risk_manager(user_id)
        portfolio_manager = get_portfolio_manager(user_id)
        
        while True:
            # Check for new alerts every 10 seconds
            await asyncio.sleep(10)
            
            # Get current positions
            positions = portfolio_manager.track_positions()
            
            # Generate alerts
            alerts = risk_manager.generate_alerts(positions)
            
            # Send alerts through WebSocket
            for alert in alerts:
                alert_data = {
                    "type": "alert",
                    "data": {
                        "alert_type": alert.alert_type.value,
                        "risk_level": alert.risk_level.value,
                        "code": alert.code,
                        "message": alert.message,
                        "value": alert.value,
                        "threshold": alert.threshold,
                        "action_required": alert.action_required,
                        "timestamp": alert.timestamp.isoformat()
                    },
                    "snapshot": {
                        "positions": len(positions),
                        "total_value": sum(p.market_value for p in positions)
                    }
                }
                
                await ws_manager.send_to_user(user_id, json.dumps(alert_data))
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket, user_id)