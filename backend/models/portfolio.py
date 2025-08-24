"""
Portfolio and transaction models.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Date, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .base import Base


class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class OrderStatus(enum.Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Holdings(Base):
    """Current portfolio holdings"""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(10), nullable=False, index=True)
    
    # Position details with enhanced tracking
    shares = Column(Float, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Float)  # Initial entry price (for tracking)
    last_change_at = Column(Date)  # Last position change date
    min_holding_until = Column(Date)  # Minimum holding date constraint
    
    # Current metrics
    current_price = Column(Float)
    market_value = Column(Float)
    weight = Column(Float)  # Portfolio weight percentage
    
    # P&L tracking
    unrealized_pnl = Column(Float)
    unrealized_pnl_pct = Column(Float)
    realized_pnl = Column(Float)  # From partial sells
    
    # Risk metrics
    position_score = Column(Float)  # Current momentum score
    correlation_avg = Column(Float)  # Average correlation with other holdings
    days_held = Column(Integer)
    
    # Strategy classification
    portfolio_type = Column(String(20))  # Core or Satellite
    
    # Stop loss tracking
    stop_loss_price = Column(Float)
    stop_loss_pct = Column(Float)
    trailing_stop = Column(Boolean, default=False)
    highest_price = Column(Float)  # For trailing stop calculation
    
    # Flags
    is_active = Column(Boolean, default=True)
    marked_for_exit = Column(Boolean, default=False)
    exit_reason = Column(String(100))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="holdings")
    
    def __repr__(self):
        return f"<Holdings(user={self.user_id}, code={self.code}, shares={self.shares})>"


class Transactions(Base):
    """Transaction history"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Transaction details
    code = Column(String(10), index=True)  # Nullable for cash transactions
    action = Column(Enum(TransactionType), nullable=False)
    price = Column(Float)
    shares = Column(Float)
    amount = Column(Float, nullable=False)  # Total transaction amount
    
    # Fees and costs
    commission = Column(Float, default=0)
    stamp_duty = Column(Float, default=0)  # For sells only in China
    transfer_fee = Column(Float, default=0)
    total_fee = Column(Float, default=0)
    
    # Execution details
    order_id = Column(String(50))
    execution_price = Column(Float)  # Actual execution price
    slippage = Column(Float)  # Difference from intended price
    
    # Strategy context
    signal_score = Column(Float)  # Momentum score at time of trade
    portfolio_type = Column(String(20))  # Core or Satellite
    trade_reason = Column(String(100))  # Entry signal, Stop loss, Rebalance, etc.
    
    # Related order
    parent_order_id = Column(Integer)  # For partial fills
    
    # Timing
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_time = Column(DateTime(timezone=True), nullable=False)
    settlement_date = Column(Date)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(user={self.user_id}, code={self.code}, action={self.action}, amount={self.amount})>"


class Orders(Base):
    """Order management with IOPV tracking"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Order basics
    code = Column(String(10), nullable=False, index=True)
    order_type = Column(String(10), nullable=False)  # MARKET, LIMIT
    side = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Pricing with IOPV
    limit_price = Column(Float)
    iopv_at_order = Column(Float)  # IOPV when order was placed
    iopv_band_lower = Column(Float)  # IOPV × 0.999
    iopv_band_upper = Column(Float)  # IOPV × 1.001
    
    # Execution
    execution_window = Column(String(10))  # 10:30 or 14:00
    expire_time = Column(DateTime(timezone=True))
    filled_price = Column(Float)
    filled_quantity = Column(Float)
    filled_at = Column(DateTime(timezone=True))
    
    # Status
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    
    # Idempotency
    idempotency_key = Column(String(64), index=True)
    
    # Metadata
    order_reason = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    cancelled_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="orders")
    
    def __repr__(self):
        return f"<Orders(id={self.id}, code={self.code}, side={self.side}, status={self.status})>"


class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for performance tracking"""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Portfolio values
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float)
    positions_value = Column(Float)
    
    # Allocation
    core_value = Column(Float)
    core_weight = Column(Float)
    satellite_value = Column(Float)
    satellite_weight = Column(Float)
    
    # Performance
    daily_pnl = Column(Float)
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    
    # Risk metrics
    volatility = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    
    # Turnover tracking
    satellite_return = Column(Float)  # For turnover efficiency calculation
    satellite_turnover = Column(Float)  # Trading volume / portfolio value
    
    # Position count
    num_positions = Column(Integer)
    num_core = Column(Integer)
    num_satellite = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolio_snapshots")
    
    def __repr__(self):
        return f"<PortfolioSnapshot(user={self.user_id}, date={self.date}, value={self.total_value})>"




