"""
Order management module with IOPV-based limit orders and CST timezone handling.
Implements precise execution windows and idempotency.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, time, timedelta
from dataclasses import dataclass, field
import hashlib
import json
import pytz
import pandas as pd
from enum import Enum

from backend.config.config import get_config_manager
from backend.models import Orders, Transactions
from backend.models.portfolio import OrderStatus, TransactionType
from backend.models.base import get_db

logger = logging.getLogger(__name__)

# China Standard Time
CST = pytz.timezone('Asia/Shanghai')


class ExecutionWindow(Enum):
    """Trade execution windows"""
    MORNING_1 = "10:30"
    AFTERNOON_1 = "14:00"
    
    @classmethod
    def get_next_window(cls, current_time: datetime) -> Tuple[str, datetime]:
        """Get next execution window from current time"""
        current_cst = current_time.astimezone(CST)
        current_time_only = current_cst.time()
        
        morning_window = time(10, 30)
        afternoon_window = time(14, 0)
        market_close = time(15, 0)
        
        if current_time_only < morning_window:
            # Next is morning window today
            window_time = current_cst.replace(hour=10, minute=30, second=0, microsecond=0)
            return cls.MORNING_1.value, window_time
        elif current_time_only < afternoon_window:
            # Next is afternoon window today
            window_time = current_cst.replace(hour=14, minute=0, second=0, microsecond=0)
            return cls.AFTERNOON_1.value, window_time
        elif current_time_only < market_close:
            # Still in afternoon session
            window_time = current_cst.replace(hour=14, minute=0, second=0, microsecond=0)
            return cls.AFTERNOON_1.value, window_time
        else:
            # Next trading day morning
            next_day = current_cst + timedelta(days=1)
            # Skip weekends
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            window_time = next_day.replace(hour=10, minute=30, second=0, microsecond=0)
            return cls.MORNING_1.value, window_time


@dataclass
class OrderRequest:
    """Order request with IOPV bands"""
    code: str
    side: str  # BUY or SELL
    quantity: float
    target_weight: float
    iopv: float
    window: str = ExecutionWindow.MORNING_1.value
    reason: str = ""
    iopv_at_order: float = 0
    idempotency_key: str = field(default="")
    
    def __post_init__(self):
        """Generate idempotency key if not provided"""
        if not self.idempotency_key:
            self.idempotency_key = self._generate_idempotency_key()
    
    def _generate_idempotency_key(self) -> str:
        """Generate idempotency key from order parameters"""
        key_data = {
            'date': str(date.today()),
            'code': self.code,
            'target_weight': self.target_weight,
            'window': self.window
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()


@dataclass
class LimitOrder:
    """Limit order with IOPV bands"""
    code: str
    side: str
    quantity: float
    limit_price: float
    iopv_band_lower: float
    iopv_band_upper: float
    iopv_at_order: float
    window: str
    expire_time: datetime
    idempotency_key: str
    reason: str = ""
    status: str = "PENDING"


class FeeModel:
    """Configurable fee model"""
    
    def __init__(self, commission_rate: float = 0.00005, impact_cost_bp: float = 3):
        """
        Initialize fee model
        
        Args:
            commission_rate: Commission rate (default 0.05bp = 0.00005)
            impact_cost_bp: Impact cost in basis points (default 3bp)
        """
        self.commission_rate = commission_rate
        self.impact_cost_bp = impact_cost_bp / 10000  # Convert bp to decimal
    
    def calculate_fees(self, 
                      order_value: float, 
                      is_aggressive: bool = False) -> Dict[str, float]:
        """
        Calculate transaction fees
        
        Args:
            order_value: Total order value
            is_aggressive: Whether order is aggressive (crosses spread)
            
        Returns:
            Dictionary of fee components
        """
        commission = order_value * self.commission_rate
        
        # Impact cost higher for aggressive orders
        if is_aggressive:
            impact_cost = order_value * self.impact_cost_bp * 1.5
        else:
            impact_cost = order_value * self.impact_cost_bp
        
        # Minimum commission
        commission = max(commission, 5.0)  # Minimum 5 yuan
        
        return {
            'commission': commission,
            'impact_cost': impact_cost,
            'total_cost': commission + impact_cost,
            'cost_rate': (commission + impact_cost) / order_value
        }


class OrderManager:
    """Order generation and management with IOPV bands"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        self.fee_model = FeeModel(
            commission_rate=self.config.execution_settings.commission_rate,
            impact_cost_bp=self.config.execution_settings.slippage_estimate * 10000
        )
        self._order_cache = {}
    
    def generate_limit_orders(self,
                             order_requests: List[OrderRequest],
                             current_prices: Dict[str, float],
                             iopv_data: Dict[str, Dict[str, float]]) -> List[LimitOrder]:
        """
        Generate limit orders with IOPV bands
        limit = IOPV × [0.999, 1.001]
        
        Args:
            order_requests: List of order requests
            current_prices: Current market prices
            iopv_data: IOPV and premium data
            
        Returns:
            List of limit orders
        """
        orders = []
        current_time = datetime.now(CST)
        
        for request in order_requests:
            # Check idempotency
            if self._check_idempotency(request.idempotency_key):
                logger.info(f"Order already exists for key {request.idempotency_key}")
                continue
            
            # Get IOPV or use current price as fallback
            if request.code in iopv_data:
                iopv = iopv_data[request.code].get('iopv', current_prices.get(request.code, 0))
            else:
                iopv = current_prices.get(request.code, 0)
            
            if iopv <= 0:
                logger.error(f"Invalid IOPV for {request.code}")
                continue
            
            # Calculate IOPV bands
            iopv_band_lower = iopv * 0.999  # -0.1%
            iopv_band_upper = iopv * 1.001  # +0.1%
            
            # Set limit price based on side
            if request.side == "BUY":
                limit_price = iopv_band_upper
            else:  # SELL
                limit_price = iopv_band_lower
            
            # Get execution window
            window_name, window_time = ExecutionWindow.get_next_window(current_time)
            
            # Set expiration (end of day)
            expire_time = current_time.replace(hour=15, minute=0, second=0, microsecond=0)
            if expire_time < current_time:
                # Next trading day
                expire_time += timedelta(days=1)
                while expire_time.weekday() >= 5:
                    expire_time += timedelta(days=1)
            
            # Create limit order
            order = LimitOrder(
                code=request.code,
                side=request.side,
                quantity=request.quantity,
                limit_price=limit_price,
                iopv_band_lower=iopv_band_lower,
                iopv_band_upper=iopv_band_upper,
                iopv_at_order=iopv,
                window=window_name,
                expire_time=expire_time,
                idempotency_key=request.idempotency_key,
                reason=request.reason
            )
            
            orders.append(order)
            
            # Cache for idempotency
            self._order_cache[request.idempotency_key] = order
        
        return orders
    
    def _check_idempotency(self, key: str) -> bool:
        """Check if order with idempotency key already exists"""
        # Check cache first
        if key in self._order_cache:
            return True
        
        # Check database
        with get_db() as db:
            existing = db.query(Orders).filter(
                Orders.user_id == self.user_id,
                Orders.idempotency_key == key,
                Orders.created_at >= date.today()
            ).first()
            
            return existing is not None
    
    def submit_orders(self, orders: List[LimitOrder]) -> Dict[str, Any]:
        """
        Submit orders to database/broker
        
        Args:
            orders: List of limit orders
            
        Returns:
            Submission results
        """
        results = {
            'submitted': [],
            'failed': [],
            'skipped': []
        }
        
        with get_db() as db:
            for order in orders:
                try:
                    # Check idempotency again
                    if self._check_idempotency(order.idempotency_key):
                        results['skipped'].append({
                            'code': order.code,
                            'reason': 'Duplicate order'
                        })
                        continue
                    
                    # Create database order
                    db_order = Orders(
                        user_id=self.user_id,
                        code=order.code,
                        order_type="LIMIT",
                        side=TransactionType.BUY if order.side == "BUY" else TransactionType.SELL,
                        quantity=order.quantity,
                        limit_price=order.limit_price,
                        iopv_band_lower=order.iopv_band_lower,
                        iopv_band_upper=order.iopv_band_upper,
                        iopv_at_order=order.iopv_at_order,
                        execution_window=order.window,
                        expire_time=order.expire_time,
                        idempotency_key=order.idempotency_key,
                        status=OrderStatus.PENDING,
                        order_reason=order.reason,
                        created_at=datetime.now(CST)
                    )
                    
                    db.add(db_order)
                    db.commit()
                    
                    results['submitted'].append({
                        'code': order.code,
                        'side': order.side,
                        'quantity': order.quantity,
                        'limit_price': order.limit_price,
                        'window': order.window
                    })
                    
                    logger.info(
                        f"Order submitted: {order.side} {order.quantity} shares of "
                        f"{order.code} @ {order.limit_price:.3f} (IOPV: {order.iopv_at_order:.3f})"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to submit order for {order.code}: {e}")
                    results['failed'].append({
                        'code': order.code,
                        'error': str(e)
                    })
        
        return results
    
    def check_fill_status(self, window: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Check order fill status for current or specified window
        
        Args:
            window: Execution window to check (uses current if not specified)
            
        Returns:
            List of order status updates
        """
        if not window:
            _, window_time = ExecutionWindow.get_next_window(datetime.now(CST))
            window = window_time.strftime("%H:%M")
        
        status_updates = []
        
        with get_db() as db:
            # Get pending orders for window
            pending_orders = db.query(Orders).filter(
                Orders.user_id == self.user_id,
                Orders.status == OrderStatus.PENDING,
                Orders.execution_window == window,
                Orders.created_at >= date.today()
            ).all()
            
            for order in pending_orders:
                # In production, would check with broker API
                # For now, simulate based on price
                fill_status = self._simulate_fill(order)
                
                if fill_status['filled']:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = fill_status['filled_quantity']
                    order.filled_price = fill_status['filled_price']
                    order.filled_at = datetime.now(CST)
                    
                    # Create transaction record
                    transaction = Transactions(
                        user_id=self.user_id,
                        code=order.code,
                        action=order.side,
                        price=fill_status['filled_price'],
                        shares=fill_status['filled_quantity'],
                        fee=fill_status['fee'],
                        transaction_date=date.today(),
                        notes=f"Filled at {window} window"
                    )
                    db.add(transaction)
                    
                    status_updates.append({
                        'code': order.code,
                        'status': 'FILLED',
                        'filled_price': fill_status['filled_price'],
                        'filled_quantity': fill_status['filled_quantity']
                    })
                elif datetime.now(CST) > order.expire_time:
                    # Order expired
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now(CST)
                    
                    status_updates.append({
                        'code': order.code,
                        'status': 'EXPIRED',
                        'reason': 'Not filled by end of day'
                    })
                else:
                    status_updates.append({
                        'code': order.code,
                        'status': 'PENDING',
                        'window': order.execution_window
                    })
            
            db.commit()
        
        return status_updates
    
    def _simulate_fill(self, order: Orders) -> Dict[str, Any]:
        """Simulate order fill for testing"""
        import random
        
        # Simulate 80% fill rate
        if random.random() < 0.8:
            # Simulate partial fills
            fill_ratio = random.uniform(0.8, 1.0)
            filled_quantity = order.quantity * fill_ratio
            
            # Simulate price improvement
            if order.side == TransactionType.BUY:
                filled_price = order.limit_price * random.uniform(0.998, 1.0)
            else:
                filled_price = order.limit_price * random.uniform(1.0, 1.002)
            
            # Calculate fees
            order_value = filled_quantity * filled_price
            fees = self.fee_model.calculate_fees(order_value)
            
            return {
                'filled': True,
                'filled_quantity': filled_quantity,
                'filled_price': filled_price,
                'fee': fees['total_cost']
            }
        
        return {'filled': False}
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel a pending order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Success status
        """
        try:
            with get_db() as db:
                order = db.query(Orders).filter(
                    Orders.id == order_id,
                    Orders.user_id == self.user_id,
                    Orders.status == OrderStatus.PENDING
                ).first()
                
                if order:
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now(CST)
                    db.commit()
                    
                    logger.info(f"Order {order_id} cancelled")
                    return True
                else:
                    logger.warning(f"Order {order_id} not found or not cancellable")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders for user"""
        with get_db() as db:
            orders = db.query(Orders).filter(
                Orders.user_id == self.user_id,
                Orders.status == OrderStatus.PENDING
            ).all()
            
            return [{
                'id': o.id,
                'code': o.code,
                'side': o.side.value,
                'quantity': o.quantity,
                'limit_price': o.limit_price,
                'window': o.execution_window,
                'expire_time': o.expire_time,
                'reason': o.order_reason
            } for o in orders]
    
    def calculate_order_impact(self, 
                              orders: List[LimitOrder],
                              portfolio_value: float) -> Dict[str, float]:
        """
        Calculate expected impact of orders on portfolio
        
        Args:
            orders: List of orders to execute
            portfolio_value: Current portfolio value
            
        Returns:
            Impact metrics
        """
        total_buy_value = sum(
            o.quantity * o.limit_price 
            for o in orders if o.side == "BUY"
        )
        
        total_sell_value = sum(
            o.quantity * o.limit_price 
            for o in orders if o.side == "SELL"
        )
        
        net_exposure_change = total_buy_value - total_sell_value
        
        # Calculate fees
        total_fees = 0
        for order in orders:
            order_value = order.quantity * order.limit_price
            fees = self.fee_model.calculate_fees(order_value)
            total_fees += fees['total_cost']
        
        return {
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'net_exposure_change': net_exposure_change,
            'expected_fees': total_fees,
            'portfolio_impact_pct': (net_exposure_change / portfolio_value) * 100 if portfolio_value > 0 else 0
        }


def get_order_manager(user_id: int) -> OrderManager:
    """Get order manager instance for user"""
    return OrderManager(user_id)