"""
User and settings models.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    
    # Account details
    full_name = Column(String(100))
    phone = Column(String(20))
    
    # Authentication
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Permissions
    is_admin = Column(Boolean, default=False)
    can_trade = Column(Boolean, default=True)
    can_backtest = Column(Boolean, default=True)
    
    # Account balance
    cash_balance = Column(Float, default=0)
    initial_capital = Column(Float, default=1000000)
    
    # Trading limits
    max_position_size = Column(Float, default=0.15)  # Maximum single position
    max_daily_trades = Column(Integer, default=10)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    holdings = relationship("Holdings", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transactions", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Orders", back_populates="user", cascade="all, delete-orphan")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"


class UserSettings(Base):
    """User-specific settings and preferences"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Trading preferences
    preferred_preset = Column(String(20), default="balanced")  # aggressive, balanced, conservative
    custom_parameters = Column(JSON)  # Override default parameters
    
    # Risk management
    enable_stop_loss = Column(Boolean, default=True)
    stop_loss_percentage = Column(Float, default=-0.10)
    enable_trailing_stop = Column(Boolean, default=False)
    trailing_stop_percentage = Column(Float, default=-0.08)
    
    # Portfolio allocation
    core_allocation = Column(Float, default=0.6)
    satellite_allocation = Column(Float, default=0.4)
    rebalance_frequency = Column(String(20), default="monthly")  # daily, weekly, monthly, quarterly
    
    # Execution preferences
    prefer_limit_orders = Column(Boolean, default=False)
    max_slippage = Column(Float, default=0.002)
    use_iopv_bands = Column(Boolean, default=True)
    
    # Notifications
    email_notifications = Column(Boolean, default=True)
    notification_triggers = Column(JSON, default={
        "stop_loss": True,
        "new_signal": True,
        "rebalance": True,
        "large_drawdown": True,
        "execution": True
    })
    
    # Display preferences
    default_timeframe = Column(String(10), default="1D")  # 1D, 1W, 1M, 3M, 1Y
    chart_indicators = Column(JSON, default=["MA20", "MA60", "Volume"])
    table_columns = Column(JSON)  # Customizable table columns
    
    # API settings
    api_key = Column(String(100))
    api_secret = Column(String(100))
    webhook_url = Column(String(200))
    
    # Broker integration
    broker_name = Column(String(50))
    broker_account = Column(String(100))
    broker_api_key = Column(String(200))
    broker_api_secret = Column(String(200))
    
    # Advanced settings
    enable_paper_trading = Column(Boolean, default=True)
    enable_auto_trading = Column(Boolean, default=False)
    max_leverage = Column(Float, default=1.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, preset={self.preferred_preset})>"


class Session(Base):
    """User session management"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session details
    session_token = Column(String(200), unique=True, nullable=False, index=True)
    refresh_token = Column(String(200), unique=True)
    
    # Device information
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    device_type = Column(String(50))  # web, mobile, api
    
    # Session validity
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Session(user_id={self.user_id}, token={self.session_token[:10]}...)>"


class AuditLog(Base):
    """Audit trail for user actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    # Action details
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))  # Order, Trade, Settings, etc.
    entity_id = Column(Integer)
    
    # Change tracking
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AuditLog(user_id={self.user_id}, action={self.action}, time={self.created_at})>"