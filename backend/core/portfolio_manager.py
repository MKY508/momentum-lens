"""
Portfolio management module for position tracking and rebalancing.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from backend.config.config import get_config_manager
from backend.models import Holdings, Transactions, Orders, PortfolioSnapshot, User
from backend.models.portfolio import TransactionType, OrderStatus
from backend.models.base import get_db
from backend.core.decision_engine import TradingSignal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Position data structure"""
    code: str
    shares: float
    avg_price: float
    current_price: float
    market_value: float
    weight: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    portfolio_type: str
    days_held: int
    entry_price: float = 0
    entry_date: Optional[date] = None
    last_change_at: Optional[date] = None
    min_holding_until: Optional[date] = None


@dataclass
class Order:
    """Order data structure"""
    code: str
    side: str  # BUY or SELL
    quantity: float
    order_type: str  # MARKET or LIMIT
    limit_price: Optional[float] = None
    iopv_band_lower: Optional[float] = None
    iopv_band_upper: Optional[float] = None
    reason: str = ""


class PortfolioManager:
    """Portfolio and position management"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        self._positions_cache = None
        self._last_cache_update = None
    
    def track_positions(self, force_refresh: bool = False) -> List[Position]:
        """
        Track current portfolio positions
        
        Args:
            force_refresh: Force refresh from database
            
        Returns:
            List of current positions
        """
        # Check cache
        if not force_refresh and self._positions_cache and self._last_cache_update:
            if datetime.now() - self._last_cache_update < timedelta(minutes=5):
                return self._positions_cache
        
        positions = []
        
        with get_db() as db:
            holdings = db.query(Holdings).filter(
                Holdings.user_id == self.user_id,
                Holdings.is_active == True
            ).all()
            
            for holding in holdings:
                position = Position(
                    code=holding.code,
                    shares=holding.shares,
                    avg_price=holding.avg_entry_price,
                    current_price=holding.current_price or holding.avg_entry_price,
                    market_value=holding.market_value or (holding.shares * holding.avg_entry_price),
                    weight=holding.weight or 0,
                    unrealized_pnl=holding.unrealized_pnl or 0,
                    unrealized_pnl_pct=holding.unrealized_pnl_pct or 0,
                    portfolio_type=holding.portfolio_type or "Unknown",
                    days_held=holding.days_held or 0
                )
                positions.append(position)
        
        # Update cache
        self._positions_cache = positions
        self._last_cache_update = datetime.now()
        
        return positions
    
    def calculate_weights(self, positions: Optional[List[Position]] = None) -> Dict[str, float]:
        """
        Calculate portfolio weights
        
        Args:
            positions: List of positions (will fetch if not provided)
            
        Returns:
            Dictionary of weights by category and individual positions
        """
        if positions is None:
            positions = self.track_positions()
        
        total_value = sum(p.market_value for p in positions)
        
        if total_value == 0:
            return {
                'total_value': 0,
                'core_weight': 0,
                'satellite_weight': 0,
                'positions': {}
            }
        
        # Calculate category weights
        core_value = sum(p.market_value for p in positions if p.portfolio_type == "Core")
        satellite_value = sum(p.market_value for p in positions if p.portfolio_type == "Satellite")
        
        # Calculate individual weights
        position_weights = {
            p.code: p.market_value / total_value
            for p in positions
        }
        
        return {
            'total_value': total_value,
            'core_weight': core_value / total_value,
            'satellite_weight': satellite_value / total_value,
            'positions': position_weights
        }
    
    def rebalance_core(self, 
                      current_prices: Dict[str, float],
                      market_regime: Dict[str, Any]) -> List[Order]:
        """
        Rebalance core portfolio to FIXED target allocations
        
        Core targets (fixed):
        - 510300/159919: 20%
        - 510880: 15%
        - 511990: 10%
        - 518880: 10%
        - 513500: 5%
        
        Args:
            current_prices: Current prices for all ETFs
            market_regime: Current market regime info
            
        Returns:
            List of orders to execute
        """
        orders = []
        positions = self.track_positions()
        weights = self.calculate_weights(positions)
        
        # Fixed core ETF targets
        CORE_TARGETS = {
            '510300': 0.20,  # CSI 300
            '159919': 0.20,  # CSI 300 alternative
            '510880': 0.15,  # Dividend ETF
            '511990': 0.10,  # Bond ETF
            '518880': 0.10,  # Gold ETF
            '513500': 0.05   # S&P 500
        }
        
        # Get total portfolio value
        total_value = weights['total_value']
        
        # Current core positions
        core_positions = {p.code: p for p in positions if p.portfolio_type == "Core"}
        
        # Determine bandwidth based on CHOP
        if market_regime.get('chop', False):
            bandwidth = 0.07  # ±7pp in CHOP
        else:
            bandwidth = 0.05  # Normal ±5pp
        
        # Generate rebalancing orders
        for etf_code in target_etfs:
            if etf_code not in current_prices:
                logger.warning(f"No price available for {etf_code}")
                continue
            
            current_price = current_prices[etf_code]
            target_shares = target_value_per_etf / current_price
            
            if etf_code in core_positions:
                # Existing position - adjust
                current_shares = core_positions[etf_code].shares
                share_diff = target_shares - current_shares
                
                if abs(share_diff * current_price) > total_value * self.config.portfolio_settings.rebalance_threshold:
                    # Significant difference, create order
                    if share_diff > 0:
                        order = Order(
                            code=etf_code,
                            side="BUY",
                            quantity=abs(share_diff),
                            order_type="LIMIT",
                            limit_price=current_price * 1.001,  # Small premium for execution
                            reason="Core rebalancing - increase position"
                        )
                    else:
                        order = Order(
                            code=etf_code,
                            side="SELL",
                            quantity=abs(share_diff),
                            order_type="LIMIT",
                            limit_price=current_price * 0.999,  # Small discount for execution
                            reason="Core rebalancing - reduce position"
                        )
                    orders.append(order)
            else:
                # New position
                order = Order(
                    code=etf_code,
                    side="BUY",
                    quantity=target_shares,
                    order_type="LIMIT",
                    limit_price=current_price * 1.001,
                    reason="Core rebalancing - new position"
                )
                orders.append(order)
        
        # Remove ETFs no longer in target
        for code, position in core_positions.items():
            if code not in target_etfs:
                order = Order(
                    code=code,
                    side="SELL",
                    quantity=position.shares,
                    order_type="MARKET",
                    reason="Core rebalancing - exit position"
                )
                orders.append(order)
        
        return orders
    
    def rotate_satellite(self,
                        target_etfs: List[str],
                        current_prices: Dict[str, float],
                        signals: List[TradingSignal],
                        days_since_entry: Dict[str, int] = None) -> List[Order]:
        """
        Rotate satellite portfolio based on momentum signals
        Start with 5% each leg, increase to 10% after one week confirmation
        
        Args:
            target_etfs: List of target satellite ETF codes
            current_prices: Current prices for all ETFs
            signals: Trading signals from decision engine
            days_since_entry: Days since position entry
            
        Returns:
            List of orders to execute
        """
        orders = []
        positions = self.track_positions()
        weights = self.calculate_weights(positions)
        
        # Get total portfolio value
        total_value = weights['total_value']
        
        # Satellite starts at 5%, increases to 10% after 7 days
        INITIAL_WEIGHT = 0.05
        CONFIRMED_WEIGHT = 0.10
        CONFIRMATION_DAYS = 7
        
        # Current satellite positions
        satellite_positions = {p.code: p for p in positions if p.portfolio_type == "Satellite"}
        
        # Sort signals by momentum score
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY and s.portfolio_type == "Satellite"]
        buy_signals.sort(key=lambda x: x.momentum_score, reverse=True)
        
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL and s.portfolio_type == "Satellite"]
        
        # Process sell signals first
        for signal in sell_signals:
            if signal.code in satellite_positions:
                position = satellite_positions[signal.code]
                order = Order(
                    code=signal.code,
                    side="SELL",
                    quantity=position.shares,
                    order_type="MARKET",
                    reason=f"Satellite rotation - exit (score: {signal.momentum_score:.2f})"
                )
                orders.append(order)
                
                # Remove from positions dict
                del satellite_positions[signal.code]
        
        # Calculate available capital for new positions
        current_satellite_value = sum(p.market_value for p in satellite_positions.values())
        available_capital = target_satellite_value - current_satellite_value
        
        # Process buy signals
        for signal in buy_signals[:6]:  # Max 6 satellite positions
            if signal.code in satellite_positions:
                # Already holding, check if we should add
                if signal.action == "ADD":
                    position = satellite_positions[signal.code]
                    current_weight = position.market_value / total_value
                    
                    if current_weight < signal.suggested_weight:
                        # Add to position
                        target_value = total_value * signal.suggested_weight
                        additional_value = target_value - position.market_value
                        
                        if additional_value > 0 and signal.code in current_prices:
                            additional_shares = additional_value / current_prices[signal.code]
                            
                            order = Order(
                                code=signal.code,
                                side="BUY",
                                quantity=additional_shares,
                                order_type="LIMIT",
                                limit_price=current_prices[signal.code] * 1.001,
                                reason=f"Satellite rotation - add to position (score: {signal.momentum_score:.2f})"
                            )
                            orders.append(order)
            else:
                # New position
                if available_capital > 0 and signal.code in current_prices:
                    # Start with 5% for new positions
                    position_value = min(
                        available_capital,
                        total_value * INITIAL_WEIGHT
                    )
                    shares = position_value / current_prices[signal.code]
                    
                    order = Order(
                        code=signal.code,
                        side="BUY",
                        quantity=shares,
                        order_type="LIMIT",
                        limit_price=current_prices[signal.code] * 1.001,
                        iopv_band_lower=current_prices[signal.code] * (1 + self.config.execution_settings.iopv_band_lower),
                        iopv_band_upper=current_prices[signal.code] * (1 + self.config.execution_settings.iopv_band_upper),
                        reason=f"Satellite rotation - new position (score: {signal.momentum_score:.2f})"
                    )
                    orders.append(order)
                    
                    available_capital -= position_value
        
        return orders
    
    def generate_orders(self, 
                       signals: List[TradingSignal],
                       current_prices: Dict[str, float],
                       iopv_data: Optional[Dict[str, Dict]] = None) -> List[Order]:
        """
        Generate orders from trading signals with IOPV bands
        
        Args:
            signals: Trading signals from decision engine
            current_prices: Current market prices
            iopv_data: IOPV and premium data
            
        Returns:
            List of orders to execute
        """
        orders = []
        positions = self.track_positions()
        position_dict = {p.code: p for p in positions}
        
        for signal in signals:
            if signal.code not in current_prices:
                continue
            
            current_price = current_prices[signal.code]
            
            # Get IOPV data if available
            iopv_info = iopv_data.get(signal.code, {}) if iopv_data else {}
            iopv = iopv_info.get('iopv', current_price)
            
            # Calculate IOPV bands
            iopv_band_lower = iopv * (1 + self.config.execution_settings.iopv_band_lower)
            iopv_band_upper = iopv * (1 + self.config.execution_settings.iopv_band_upper)
            
            # Generate order based on signal
            if signal.signal_type == SignalType.BUY:
                # Calculate position size
                portfolio_value = sum(p.market_value for p in positions)
                position_value = portfolio_value * signal.suggested_weight
                shares = position_value / current_price
                
                # Round to lot size
                lot_size = 100  # Standard A-share lot size
                shares = round(shares / lot_size) * lot_size
                
                if shares > 0:
                    order = Order(
                        code=signal.code,
                        side="BUY",
                        quantity=shares,
                        order_type="LIMIT",
                        limit_price=min(current_price * 1.002, iopv_band_upper),
                        iopv_band_lower=iopv_band_lower,
                        iopv_band_upper=iopv_band_upper,
                        reason=f"{signal.action} - Score: {signal.momentum_score:.2f}"
                    )
                    orders.append(order)
            
            elif signal.signal_type == SignalType.SELL:
                if signal.code in position_dict:
                    position = position_dict[signal.code]
                    
                    order = Order(
                        code=signal.code,
                        side="SELL",
                        quantity=position.shares,
                        order_type="LIMIT" if signal.signal_strength.value != "STRONG" else "MARKET",
                        limit_price=max(current_price * 0.998, iopv_band_lower) if signal.signal_strength.value != "STRONG" else None,
                        iopv_band_lower=iopv_band_lower,
                        iopv_band_upper=iopv_band_upper,
                        reason=f"{signal.action} - Score: {signal.momentum_score:.2f}"
                    )
                    orders.append(order)
        
        return orders
    
    def execute_order(self, order: Order) -> bool:
        """
        Execute an order (record in database)
        
        Args:
            order: Order to execute
            
        Returns:
            Success status
        """
        try:
            with get_db() as db:
                # Create order record
                db_order = Orders(
                    user_id=self.user_id,
                    code=order.code,
                    order_type=order.order_type,
                    side=TransactionType.BUY if order.side == "BUY" else TransactionType.SELL,
                    quantity=order.quantity,
                    limit_price=order.limit_price,
                    iopv_band_lower=order.iopv_band_lower,
                    iopv_band_upper=order.iopv_band_upper,
                    status=OrderStatus.PENDING,
                    order_reason=order.reason,
                    created_at=datetime.now()
                )
                
                db.add(db_order)
                db.commit()
                
                logger.info(f"Order created: {order.side} {order.quantity} shares of {order.code}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to execute order: {e}")
            return False
    
    def update_holdings(self, transaction: Transactions) -> bool:
        """
        Update holdings based on executed transaction
        Track entry_price, entry_date, last_change_at, min_holding_until
        
        Args:
            transaction: Executed transaction
            
        Returns:
            Success status
        """
        try:
            with get_db() as db:
                holding = db.query(Holdings).filter(
                    Holdings.user_id == self.user_id,
                    Holdings.code == transaction.code,
                    Holdings.is_active == True
                ).first()
                
                current_date = date.today()
                
                if transaction.action == TransactionType.BUY:
                    if holding:
                        # Update existing holding
                        total_value = (holding.shares * holding.avg_entry_price) + \
                                     (transaction.shares * transaction.price)
                        total_shares = holding.shares + transaction.shares
                        
                        holding.shares = total_shares
                        holding.avg_entry_price = total_value / total_shares if total_shares > 0 else 0
                        holding.updated_at = datetime.now()
                    else:
                        # Create new holding
                        holding = Holdings(
                            user_id=self.user_id,
                            code=transaction.code,
                            shares=transaction.shares,
                            avg_entry_price=transaction.price,
                            entry_date=transaction.transaction_date,
                            current_price=transaction.price,
                            market_value=transaction.shares * transaction.price,
                            portfolio_type=transaction.portfolio_type,
                            is_active=True,
                            created_at=datetime.now()
                        )
                        db.add(holding)
                
                elif transaction.action == TransactionType.SELL:
                    if holding:
                        holding.shares -= transaction.shares
                        
                        if holding.shares <= 0:
                            # Close position
                            holding.is_active = False
                            holding.shares = 0
                        
                        holding.updated_at = datetime.now()
                
                db.commit()
                logger.info(f"Holdings updated for {transaction.code}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update holdings: {e}")
            return False
    
    def calculate_performance(self, 
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Dictionary of performance metrics
        """
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        with get_db() as db:
            # Get portfolio snapshots
            snapshots = db.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.user_id == self.user_id,
                PortfolioSnapshot.date >= start_date,
                PortfolioSnapshot.date <= end_date
            ).order_by(PortfolioSnapshot.date).all()
            
            if not snapshots:
                return {
                    'total_return': 0,
                    'daily_return': 0,
                    'volatility': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            # Calculate returns
            values = [s.total_value for s in snapshots]
            returns = pd.Series(values).pct_change().dropna()
            
            # Calculate metrics
            total_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0
            daily_return = returns.mean()
            volatility = returns.std()
            
            # Sharpe ratio (assuming risk-free rate of 2% annually)
            risk_free_rate = 0.02 / 252  # Daily risk-free rate
            sharpe_ratio = (daily_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Max drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            return {
                'total_return': total_return,
                'daily_return': daily_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio * np.sqrt(252),  # Annualized
                'max_drawdown': max_drawdown
            }


def get_portfolio_manager(user_id: int) -> PortfolioManager:
    """Get portfolio manager instance for user"""
    return PortfolioManager(user_id)