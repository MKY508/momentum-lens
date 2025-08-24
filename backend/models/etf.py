"""
ETF-related database models.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Date, Boolean, Index, UniqueConstraint, Text
from sqlalchemy.sql import func
from datetime import datetime, date

from .base import Base


class ETFInfo(Base):
    """ETF information and metadata"""
    __tablename__ = "etf_info"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)  # Core or Satellite
    style = Column(String(30), nullable=False)  # Style, Sector, Theme, Cross-border
    tracking_index = Column(String(20))
    
    # Fund details
    fund_company = Column(String(100))
    inception_date = Column(Date)
    aum = Column(Float)  # Assets under management in billions
    expense_ratio = Column(Float)  # Annual expense ratio
    
    # Trading information
    exchange = Column(String(10))  # SH or SZ
    lot_size = Column(Integer, default=100)
    
    # Tracking and liquidity metrics
    tracking_error = Column(Float)  # Annual tracking error
    avg_daily_volume = Column(Float)  # 30-day average daily volume
    avg_spread = Column(Float)  # Average bid-ask spread
    
    # Status flags
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=True)
    has_options = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)
    
    def __repr__(self):
        return f"<ETFInfo(code={self.code}, name={self.name}, category={self.category})>"


class PriceHistory(Base):
    """ETF price history and trading data (TimescaleDB hypertable)"""
    __tablename__ = "price_history"
    
    # For TimescaleDB, use composite primary key without auto-increment id
    # This improves performance for time-series data
    code = Column(String(10), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    turnover = Column(Float)  # Trading value in CNY
    
    # IOPV and premium/discount
    iopv = Column(Float)  # Indicative Optimized Portfolio Value
    premium_discount = Column(Float)  # (Price - IOPV) / IOPV
    
    # Technical indicators (pre-calculated for performance)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    ma120 = Column(Float)
    ma200 = Column(Float)
    
    # Volatility metrics
    atr20 = Column(Float)  # 20-day Average True Range
    atr20_pct = Column(Float)  # ATR20 as percentage of price
    volatility20 = Column(Float)  # 20-day realized volatility
    
    # Returns (using exact trading days)
    daily_return = Column(Float)
    return_5d = Column(Float)
    return_20d = Column(Float)
    return_60d = Column(Float)  # r60 - exact 60 trading days
    return_120d = Column(Float)  # r120 - exact 120 trading days
    rho90 = Column(Float)  # 90-day correlation using log returns
    
    # Volume metrics
    volume_ratio = Column(Float)  # Volume / 20-day average volume
    
    # Data quality and anomaly detection
    is_trading_day = Column(Boolean, default=True)
    is_outlier = Column(Boolean, default=False)  # |return| > 15% without announcement
    data_source = Column(String(20))  # eastmoney, akshare, sina, tushare, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # No need for unique constraint since (code, date) is primary key
        # Add separate indexes for better query performance
        Index('ix_price_history_date', 'date'),
        Index('ix_price_history_code', 'code'),
        Index('ix_price_history_return_60d', 'return_60d'),
        Index('ix_price_history_return_120d', 'return_120d'),
        {'comment': 'TimescaleDB hypertable for ETF price history'}
    )
    
    def __repr__(self):
        return f"<PriceHistory(code={self.code}, date={self.date}, close={self.close})>"


class RealtimeQuote(Base):
    """Real-time ETF quotes"""
    __tablename__ = "realtime_quotes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    
    # Current price data
    last_price = Column(Float, nullable=False)
    bid_price = Column(Float)
    ask_price = Column(Float)
    bid_volume = Column(Float)
    ask_volume = Column(Float)
    
    # Day statistics
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    prev_close = Column(Float)
    volume = Column(Float)
    turnover = Column(Float)
    
    # IOPV
    iopv = Column(Float)
    premium_discount = Column(Float)
    
    # Market depth (Level 1)
    bid1_price = Column(Float)
    bid1_volume = Column(Float)
    ask1_price = Column(Float)
    ask1_volume = Column(Float)
    
    # Additional depth levels (if available)
    bid2_price = Column(Float)
    bid2_volume = Column(Float)
    ask2_price = Column(Float)
    ask2_volume = Column(Float)
    
    bid3_price = Column(Float)
    bid3_volume = Column(Float)
    ask3_price = Column(Float)
    ask3_volume = Column(Float)
    
    bid4_price = Column(Float)
    bid4_volume = Column(Float)
    ask4_price = Column(Float)
    ask4_volume = Column(Float)
    
    bid5_price = Column(Float)
    bid5_volume = Column(Float)
    ask5_price = Column(Float)
    ask5_volume = Column(Float)
    
    # Update timestamp
    quote_time = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<RealtimeQuote(code={self.code}, last={self.last_price}, time={self.quote_time})>"


class ETFHoldings(Base):
    """ETF constituent holdings (for transparency)"""
    __tablename__ = "etf_holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    etf_code = Column(String(10), nullable=False, index=True)
    holding_date = Column(Date, nullable=False)
    
    # Constituent details
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(100))
    weight = Column(Float, nullable=False)  # Percentage weight in ETF
    shares = Column(Float)  # Number of shares held
    market_value = Column(Float)  # Market value in CNY
    
    # Ranking
    rank = Column(Integer)  # Rank by weight
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('etf_code', 'holding_date', 'stock_code', name='uq_etf_holdings'),
        Index('ix_etf_holdings_etf_date', 'etf_code', 'holding_date'),
    )
    
    def __repr__(self):
        return f"<ETFHoldings(etf={self.etf_code}, stock={self.stock_code}, weight={self.weight}%)>"