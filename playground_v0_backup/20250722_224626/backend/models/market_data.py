"""
Production Market Data Models
Database persistence for real market data from IBKR and external APIs
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional

from backend.models import Base  # Fixed import

class StockInfo(Base):
    """Company information and fundamentals"""
    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    company_name = Column(String(255))
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    market_cap = Column(Float)
    
    # Fundamental data
    pe_ratio = Column(Float)
    dividend_yield = Column(Float)
    beta = Column(Float)
    revenue_growth = Column(Float)
    profit_margin = Column(Float)
    
    # Exchange and trading info
    exchange = Column(String(20))
    currency = Column(String(10))
    country = Column(String(50))
    
    # Data source and freshness
    data_source = Column(String(50))  # 'IBKR', 'FMP', 'ALPHA_VANTAGE'
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_sector_market_cap', 'sector', 'market_cap'),
        Index('idx_last_updated', 'last_updated'),
    )

class PriceData(Base):
    """Historical and real-time price data"""
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    
    # OHLCV data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    adjusted_close = Column(Float)
    volume = Column(Integer)
    
    # Calculated fields
    true_range = Column(Float)  # For ATR calculation
    
    # Data quality and source
    data_source = Column(String(50))
    interval = Column(String(10))  # '1d', '1h', '5m'
    is_adjusted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'date', 'interval', name='uq_symbol_date_interval'),
        Index('idx_symbol_date', 'symbol', 'date'),
        Index('idx_date_range', 'date'),
    )

class ATRData(Base):
    """Calculated ATR (Average True Range) data"""
    __tablename__ = "atr_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    calculation_date = Column(DateTime, index=True, nullable=False)
    
    # ATR calculations
    period = Column(Integer, default=14)  # ATR period
    current_atr = Column(Float, nullable=False)
    atr_percentage = Column(Float, nullable=False)  # ATR as % of price
    
    # Volatility analysis
    volatility_rating = Column(String(20))  # LOW, MEDIUM, HIGH, EXTREME
    volatility_trend = Column(String(20))   # INCREASING, DECREASING, STABLE
    
    # Supporting data
    current_price = Column(Float)
    data_points_used = Column(Integer)  # Number of price points in calculation
    
    # Quality metrics
    calculation_confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    data_source = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'calculation_date', 'period', name='uq_symbol_date_period'),
        Index('idx_symbol_updated', 'symbol', 'last_updated'),
        Index('idx_volatility_rating', 'volatility_rating'),
    )

class SectorMetrics(Base):
    """Sector-level volatility and performance metrics"""
    __tablename__ = "sector_metrics"

    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), unique=True, index=True, nullable=False)
    
    # Volatility characteristics
    avg_atr_percentage = Column(Float)
    median_atr_percentage = Column(Float)
    volatility_percentile_90 = Column(Float)
    volatility_percentile_10 = Column(Float)
    
    # Growth characteristics
    is_growth_oriented = Column(Boolean)
    avg_revenue_growth = Column(Float)
    avg_pe_ratio = Column(Float)
    
    # DCA strategy parameters
    dca_buy_threshold = Column(Float)    # % decline for buy signal
    dca_sell_threshold = Column(Float)   # % gain for sell signal
    
    # Data quality
    sample_size = Column(Integer)  # Number of stocks in calculation
    last_calculated = Column(DateTime, default=datetime.utcnow)
    calculation_period_days = Column(Integer, default=90)
    
    __table_args__ = (
        Index('idx_growth_oriented', 'is_growth_oriented'),
        Index('idx_last_calculated', 'last_calculated'),
    )

class MarketDataSync(Base):
    """Track data synchronization jobs and status"""
    __tablename__ = "market_data_sync"

    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)  # 'PRICE_DATA', 'STOCK_INFO', 'ATR_CALC'
    symbol = Column(String(20), index=True)  # None for sector-wide syncs
    
    # Sync details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(20))  # 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    
    # Results
    records_processed = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Data source and configuration
    data_source = Column(String(50))
    sync_config = Column(Text)  # JSON config for the sync job
    
    __table_args__ = (
        Index('idx_sync_type_status', 'sync_type', 'status'),
        Index('idx_started_at', 'started_at'),
    )

class DataQuality(Base):
    """Data quality metrics and monitoring"""
    __tablename__ = "data_quality"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    symbol = Column(String(20), index=True)  # Optional for table-wide metrics
    
    # Quality metrics
    metric_name = Column(String(100), nullable=False)  # 'COMPLETENESS', 'FRESHNESS', 'ACCURACY'
    metric_value = Column(Float, nullable=False)
    threshold_min = Column(Float)
    threshold_max = Column(Float)
    
    # Status
    status = Column(String(20))  # 'PASS', 'WARN', 'FAIL'
    description = Column(Text)
    
    # Timing
    measured_at = Column(DateTime, default=datetime.utcnow, index=True)
    measurement_period = Column(String(50))  # 'DAILY', 'HOURLY', 'REAL_TIME'
    
    __table_args__ = (
        Index('idx_table_metric', 'table_name', 'metric_name'),
        Index('idx_status_measured', 'status', 'measured_at'),
    ) 