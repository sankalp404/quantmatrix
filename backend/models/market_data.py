"""
Market Data Models
==================

Models for storing market data, price history, and analysis.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from . import Base


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
        Index("idx_sector_market_cap", "sector", "market_cap"),
        Index("idx_last_updated", "last_updated"),
    )


class PriceData(Base):
    """Historical and real-time price data"""

    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    instrument_id = Column(
        Integer, ForeignKey("instruments.id"), nullable=True, index=True
    )  # Fixed: Missing FK
    date = Column(DateTime, index=True, nullable=False)

    # OHLCV data
    open_price = Column(
        Float, nullable=True
    )  # Made nullable - not always available from tax lots
    high_price = Column(
        Float, nullable=True
    )  # Made nullable - not always available from tax lots
    low_price = Column(
        Float, nullable=True
    )  # Made nullable - not always available from tax lots
    close_price = Column(
        Float, nullable=False
    )  # Keep required - this is our main price data
    adjusted_close = Column(Float)
    volume = Column(Integer)

    # Calculated fields
    true_range = Column(Float)  # For ATR calculation

    # Data quality and source
    data_source = Column(String(50))
    interval = Column(String(10))  # '1d', '1h', '5m'
    is_adjusted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    instrument = relationship(
        "Instrument", back_populates="price_data"
    )  # Fixed: Added missing relationship

    __table_args__ = (
        UniqueConstraint("symbol", "date", "interval", name="uq_symbol_date_interval"),
        Index("idx_symbol_date", "symbol", "date"),
        Index("idx_date_range", "date"),
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
    volatility_trend = Column(String(20))  # INCREASING, DECREASING, STABLE

    # Supporting data
    current_price = Column(Float)
    data_points_used = Column(Integer)  # Number of price points in calculation

    # Quality metrics
    calculation_confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    data_source = Column(String(50))
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "symbol", "calculation_date", "period", name="uq_symbol_date_period"
        ),
        Index("idx_symbol_updated", "symbol", "last_updated"),
        Index("idx_volatility_rating", "volatility_rating"),
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
    dca_buy_threshold = Column(Float)  # % decline for buy signal
    dca_sell_threshold = Column(Float)  # % gain for sell signal

    # Data quality
    sample_size = Column(Integer)  # Number of stocks in calculation
    last_calculated = Column(DateTime, default=datetime.utcnow)
    calculation_period_days = Column(Integer, default=90)

    __table_args__ = (
        Index("idx_growth_oriented", "is_growth_oriented"),
        Index("idx_last_calculated", "last_calculated"),
    )


class MarketDataSync(Base):
    """Track data synchronization jobs and status"""

    __tablename__ = "market_data_sync"

    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(
        String(50), nullable=False
    )  # 'PRICE_DATA', 'STOCK_INFO', 'ATR_CALC'
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
        Index("idx_sync_type_status", "sync_type", "status"),
        Index("idx_started_at", "started_at"),
    )


class DataQuality(Base):
    """Data quality metrics and monitoring"""

    __tablename__ = "data_quality"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    symbol = Column(String(20), index=True)  # Optional for table-wide metrics

    # Quality metrics
    metric_name = Column(
        String(100), nullable=False
    )  # 'COMPLETENESS', 'FRESHNESS', 'ACCURACY'
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
        Index("idx_table_metric", "table_name", "metric_name"),
        Index("idx_status_measured", "status", "measured_at"),
    )


# =============================================================================
# MARKET ANALYSIS (merged from market_analysis.py)
# =============================================================================


class MarketAnalysisCache(Base):
    """Cache for comprehensive market analysis results."""

    __tablename__ = "market_analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    analysis_type = Column(
        String(50), nullable=False
    )  # 'atr_matrix', 'company_profile', 'technical_analysis'
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    expiry_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Market data
    current_price = Column(Float)
    market_cap = Column(Float)
    sector = Column(String(100))
    industry = Column(String(100))
    fund_membership = Column(String(200))

    # Technical indicators
    atr_value = Column(Float)
    atr_distance = Column(Float)
    atr_percent = Column(Float)
    rsi = Column(Float)
    ma_alignment = Column(Boolean)

    # ATR Matrix specific
    confidence_score = Column(Float)
    entry_signal = Column(Boolean)
    stop_loss_price = Column(Float)
    target_prices = Column(JSON)  # Array of target prices
    risk_reward_ratio = Column(Float)

    # Company analysis
    company_synopsis = Column(Text)
    analyst_rating = Column(String(20))
    analyst_target = Column(Float)
    news_sentiment = Column(Float)

    # Raw analysis data (JSON)
    raw_analysis = Column(JSON)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_valid = Column(Boolean, default=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_symbol_analysis_type", "symbol", "analysis_type"),
        Index("idx_symbol_expiry", "symbol", "expiry_timestamp"),
        Index("idx_analysis_timestamp", "analysis_timestamp"),
        Index("idx_entry_signal", "entry_signal"),
    )


class StockUniverse(Base):
    """Comprehensive stock universe for scanning."""

    __tablename__ = "stock_universe"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(200))
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    market_cap = Column(Float, index=True)

    # Classification
    market_cap_category = Column(
        String(20), index=True
    )  # 'mega', 'large', 'mid', 'small', 'micro'
    is_sp500 = Column(Boolean, default=False, index=True)
    is_nasdaq100 = Column(Boolean, default=False, index=True)
    is_russell2000 = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # Scanning metadata
    last_scanned = Column(DateTime(timezone=True))
    scan_priority = Column(Integer, default=50)  # 1-100, higher = higher priority
    avg_volume = Column(Float)
    price_range_52w_low = Column(Float)
    price_range_52w_high = Column(Float)

    # Data source tracking
    polygon_available = Column(Boolean, default=False)
    alpha_vantage_available = Column(Boolean, default=True)
    yfinance_available = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_market_cap_category", "market_cap_category"),
        Index("idx_scan_priority", "scan_priority"),
        Index("idx_sector_active", "sector", "is_active"),
    )


class ScanHistory(Base):
    """History of comprehensive scans performed."""

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(
        String(50), nullable=False
    )  # 'atr_matrix', 'morning_brew', 'signals'
    scan_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Scan parameters
    total_symbols_scanned = Column(Integer)
    symbols_with_data = Column(Integer)
    analysis_duration_seconds = Column(Float)

    # Results
    opportunities_found = Column(Integer)
    signals_sent = Column(Integer)
    errors_encountered = Column(Integer)

    # Metadata
    scan_parameters = Column(JSON)  # Store scan criteria
    top_results = Column(JSON)  # Store top opportunities
    error_log = Column(JSON)  # Store any errors

    # Discord integration
    discord_sent = Column(Boolean, default=False)
    discord_timestamp = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_scan_type_timestamp", "scan_type", "scan_timestamp"),
        Index("idx_opportunities_found", "opportunities_found"),
    )


class PolygonApiUsage(Base):
    """Track Polygon.io API usage for optimization."""

    __tablename__ = "polygon_api_usage"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(100), nullable=False)
    symbol = Column(String(10), index=True)
    request_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # API metrics
    response_time_ms = Column(Float)
    status_code = Column(Integer)
    credits_used = Column(Integer)
    rate_limit_remaining = Column(Integer)

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Data efficiency
    cache_hit = Column(Boolean, default=False)
    data_source = Column(String(50))  # polygon, alpha_vantage, yfinance

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_endpoint_timestamp", "endpoint", "request_timestamp"),
        Index("idx_symbol_timestamp", "symbol", "request_timestamp"),
    )


class MarketDataProvider(Base):
    """Track multiple market data providers and their availability."""

    __tablename__ = "market_data_providers"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(50), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)

    # API limits
    requests_per_minute = Column(Integer)
    requests_per_day = Column(Integer)
    monthly_quota = Column(Integer)

    # Usage tracking
    requests_today = Column(Integer, default=0)
    requests_this_month = Column(Integer, default=0)
    last_request_timestamp = Column(DateTime(timezone=True))

    # Performance metrics
    avg_response_time_ms = Column(Float)
    success_rate_pct = Column(Float)
    last_error = Column(Text)

    # Configuration
    api_key_configured = Column(Boolean, default=False)
    priority_order = Column(Integer, default=10)  # Lower = higher priority

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_provider_priority", "priority_order"),
        Index("idx_provider_active", "is_active"),
    )
