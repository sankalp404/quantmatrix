"""
Comprehensive Market Data Models - V2 Enhanced
==============================================

Incorporates existing sophisticated market data models with V2 multi-user improvements.
Designed for strategy execution, backtesting, and real-time trading.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, 
    ForeignKey, UniqueConstraint, Index, CheckConstraint,
    TIMESTAMP, Enum as SQLEnum, JSON, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from . import Base

# =============================================================================
# ENUMS
# =============================================================================

class DataProviderType(enum.Enum):
    YFINANCE = "yfinance"
    POLYGON = "polygon"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    FMP = "fmp"
    IBKR = "ibkr"
    TASTYTRADE = "tastytrade"

class VolatilityLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    EXTREME = "extreme"

class DataQualityStatus(enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

# =============================================================================
# CORE MARKET DATA
# =============================================================================

class Instrument(Base):
    """Enhanced instrument definitions supporting all asset types."""
    __tablename__ = "instruments_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Primary Identification
    symbol = Column(String(50), nullable=False, index=True)
    instrument_type = Column(String(20), nullable=False)  # stock, option, etf, future, crypto
    
    # Basic Information
    name = Column(String(255))
    exchange = Column(String(20))
    currency = Column(String(3), default="USD")
    
    # Stock/ETF Specific
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(DECIMAL(20, 2))
    
    # Option Specific
    underlying_symbol = Column(String(50))  # For options
    option_type = Column(String(4))  # CALL, PUT
    strike_price = Column(DECIMAL(10, 4))
    expiration_date = Column(DateTime)
    multiplier = Column(Integer, default=100)
    
    # Data Quality & Availability
    data_quality_score = Column(DECIMAL(3, 2), default=1.0)  # 0.0 to 1.0
    is_active = Column(Boolean, default=True)
    last_data_update = Column(TIMESTAMP(timezone=True))
    
    # Market Classification (for scanning/strategies)
    is_sp500 = Column(Boolean, default=False)
    is_nasdaq100 = Column(Boolean, default=False)
    is_russell2000 = Column(Boolean, default=False)
    market_cap_category = Column(String(20))  # mega, large, mid, small, micro
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    price_data = relationship("PriceData", back_populates="instrument")
    technical_data = relationship("TechnicalIndicators", back_populates="instrument")
    fundamental_data = relationship("FundamentalData", back_populates="instrument")
    
    __table_args__ = (
        Index('idx_symbol_type', 'symbol', 'instrument_type'),
        Index('idx_underlying', 'underlying_symbol'),
        Index('idx_sector_mcap', 'sector', 'market_cap_category'),
        Index('idx_active_quality', 'is_active', 'data_quality_score'),
    )

class PriceData(Base):
    """OHLCV price data with multiple timeframes."""
    __tablename__ = "price_data_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"), nullable=False)
    
    # Time Information
    date = Column(DateTime, nullable=False, index=True)
    interval = Column(String(10), nullable=False)  # 1d, 1h, 5m, etc.
    
    # OHLCV Data
    open_price = Column(DECIMAL(12, 4), nullable=False)
    high_price = Column(DECIMAL(12, 4), nullable=False)
    low_price = Column(DECIMAL(12, 4), nullable=False)
    close_price = Column(DECIMAL(12, 4), nullable=False)
    adjusted_close = Column(DECIMAL(12, 4))
    volume = Column(DECIMAL(15, 0))
    
    # Derived Metrics
    true_range = Column(DECIMAL(12, 4))
    price_change = Column(DECIMAL(12, 4))
    price_change_pct = Column(DECIMAL(8, 4))
    
    # Data Source & Quality
    data_source = Column(SQLEnum(DataProviderType), nullable=False)
    is_adjusted = Column(Boolean, default=True)
    confidence_score = Column(DECIMAL(3, 2), default=1.0)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    instrument = relationship("Instrument", back_populates="price_data")
    
    __table_args__ = (
        UniqueConstraint('instrument_id', 'date', 'interval', name='uq_instrument_date_interval'),
        Index('idx_date_interval', 'date', 'interval'),
        Index('idx_instrument_date', 'instrument_id', 'date'),
    )

class TechnicalIndicators(Base):
    """Calculated technical indicators (ATR, RSI, MA, etc.)."""
    __tablename__ = "technical_indicators_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"), nullable=False)
    calculation_date = Column(DateTime, nullable=False, index=True)
    
    # ATR Data (Core for ATR Matrix strategy)
    atr_14 = Column(DECIMAL(12, 4))
    atr_21 = Column(DECIMAL(12, 4))
    atr_percentage = Column(DECIMAL(8, 4))  # ATR as % of price
    volatility_rating = Column(SQLEnum(VolatilityLevel))
    volatility_trend = Column(String(20))  # INCREASING, DECREASING, STABLE
    
    # Moving Averages
    sma_10 = Column(DECIMAL(12, 4))
    sma_20 = Column(DECIMAL(12, 4))
    sma_50 = Column(DECIMAL(12, 4))
    sma_100 = Column(DECIMAL(12, 4))
    sma_200 = Column(DECIMAL(12, 4))
    ema_10 = Column(DECIMAL(12, 4))
    ema_20 = Column(DECIMAL(12, 4))
    
    # Momentum Indicators
    rsi_14 = Column(DECIMAL(6, 2))
    macd_line = Column(DECIMAL(12, 4))
    macd_signal = Column(DECIMAL(12, 4))
    macd_histogram = Column(DECIMAL(12, 4))
    
    # ATR Matrix Specific
    atr_distance = Column(DECIMAL(8, 4))  # Distance from SMA50 in ATR units
    ma_alignment = Column(Boolean)  # Are MAs aligned bullishly?
    price_position_20d = Column(DECIMAL(6, 2))  # Position in 20-day range
    
    # Volume Indicators
    volume_sma_20 = Column(DECIMAL(15, 0))
    volume_relative = Column(DECIMAL(6, 2))  # Current vs average volume
    
    # Support/Resistance
    support_level = Column(DECIMAL(12, 4))
    resistance_level = Column(DECIMAL(12, 4))
    
    # Calculation Metadata
    calculation_confidence = Column(DECIMAL(3, 2), default=1.0)
    data_points_used = Column(Integer)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    instrument = relationship("Instrument", back_populates="technical_data")
    
    __table_args__ = (
        UniqueConstraint('instrument_id', 'calculation_date', name='uq_instrument_calc_date'),
        Index('idx_atr_distance', 'atr_distance'),
        Index('idx_volatility', 'volatility_rating'),
        Index('idx_ma_alignment', 'ma_alignment'),
    )

class FundamentalData(Base):
    """Company fundamentals and financial metrics."""
    __tablename__ = "fundamental_data_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"), nullable=False)
    
    # Company Information
    company_name = Column(String(255))
    description = Column(Text)
    ceo = Column(String(100))
    employees = Column(Integer)
    founded_year = Column(Integer)
    
    # Financial Metrics
    market_cap = Column(DECIMAL(20, 2))
    pe_ratio = Column(DECIMAL(8, 2))
    forward_pe = Column(DECIMAL(8, 2))
    peg_ratio = Column(DECIMAL(6, 2))
    price_to_book = Column(DECIMAL(6, 2))
    price_to_sales = Column(DECIMAL(6, 2))
    
    # Growth Metrics
    revenue_growth_yoy = Column(DECIMAL(8, 4))
    earnings_growth_yoy = Column(DECIMAL(8, 4))
    revenue_growth_qoq = Column(DECIMAL(8, 4))
    
    # Profitability
    gross_margin = Column(DECIMAL(6, 4))
    operating_margin = Column(DECIMAL(6, 4))
    profit_margin = Column(DECIMAL(6, 4))
    roe = Column(DECIMAL(6, 4))
    roa = Column(DECIMAL(6, 4))
    
    # Dividend Information
    dividend_yield = Column(DECIMAL(6, 4))
    dividend_per_share = Column(DECIMAL(8, 4))
    payout_ratio = Column(DECIMAL(6, 4))
    
    # Risk Metrics
    beta = Column(DECIMAL(6, 4))
    debt_to_equity = Column(DECIMAL(8, 4))
    current_ratio = Column(DECIMAL(6, 2))
    quick_ratio = Column(DECIMAL(6, 2))
    
    # Analyst Data
    analyst_rating = Column(String(20))  # BUY, HOLD, SELL
    analyst_target_price = Column(DECIMAL(12, 4))
    analyst_count = Column(Integer)
    
    # Data Source & Quality
    data_source = Column(SQLEnum(DataProviderType))
    last_updated = Column(TIMESTAMP(timezone=True))
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    instrument = relationship("Instrument", back_populates="fundamental_data")
    
    __table_args__ = (
        UniqueConstraint('instrument_id', name='uq_instrument_fundamentals'),
        Index('idx_market_cap', 'market_cap'),
        Index('idx_pe_ratio', 'pe_ratio'),
        Index('idx_analyst_rating', 'analyst_rating'),
    )

# =============================================================================
# STRATEGY-FOCUSED ANALYSIS CACHING
# =============================================================================

class MarketAnalysisCache(Base):
    """Cache comprehensive market analysis for strategy execution."""
    __tablename__ = "market_analysis_cache_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # atr_matrix, momentum, etc.
    
    # Analysis Results
    overall_score = Column(DECIMAL(4, 3))  # 0.000 to 1.000
    recommendation = Column(String(20))  # BUY, SELL, HOLD, SCALE_OUT
    confidence = Column(DECIMAL(4, 3))
    
    # ATR Matrix Specific
    entry_signal = Column(Boolean, default=False)
    scale_out_signal = Column(Boolean, default=False)
    risk_signal = Column(Boolean, default=False)
    
    # Price Targets
    stop_loss_price = Column(DECIMAL(12, 4))
    target_prices = Column(JSON)  # Array of target prices
    risk_reward_ratio = Column(DECIMAL(6, 2))
    time_horizon_days = Column(Integer)
    
    # Strategy Metadata
    signal_strength = Column(DECIMAL(4, 3))
    entry_reason = Column(Text)
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, EXTREME
    
    # Analysis Data (JSON for flexibility)
    technical_analysis = Column(JSON)
    fundamental_analysis = Column(JSON)
    market_conditions = Column(JSON)
    
    # Cache Management
    analysis_timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    cache_hits = Column(Integer, default=0)
    is_valid = Column(Boolean, default=True)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('instrument_id', 'analysis_type', name='uq_instrument_analysis'),
        Index('idx_analysis_expires', 'analysis_type', 'expires_at'),
        Index('idx_entry_signal', 'entry_signal'),
        Index('idx_recommendation', 'recommendation'),
    )

# =============================================================================
# UNIVERSE & SCANNING
# =============================================================================

class StockUniverse(Base):
    """Comprehensive stock universe for strategy scanning."""
    __tablename__ = "stock_universe_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"), nullable=False)
    
    # Classification
    is_sp500 = Column(Boolean, default=False, index=True)
    is_nasdaq100 = Column(Boolean, default=False, index=True)
    is_russell2000 = Column(Boolean, default=False, index=True)
    is_etf = Column(Boolean, default=False, index=True)
    
    # Scanning Metadata
    scan_priority = Column(Integer, default=50, index=True)  # 1-100
    last_scanned = Column(TIMESTAMP(timezone=True))
    scan_frequency = Column(String(20), default="daily")  # daily, weekly, realtime
    
    # Liquidity Metrics
    avg_volume_30d = Column(DECIMAL(15, 0))
    avg_dollar_volume_30d = Column(DECIMAL(18, 2))
    bid_ask_spread_avg = Column(DECIMAL(8, 4))
    
    # Options Data (for options strategies)
    options_available = Column(Boolean, default=False)
    avg_options_volume = Column(DECIMAL(12, 0))
    implied_volatility_30d = Column(DECIMAL(8, 4))
    
    # Data Provider Availability
    polygon_available = Column(Boolean, default=False)
    alpha_vantage_available = Column(Boolean, default=True)
    yfinance_available = Column(Boolean, default=True)
    
    # Quality & Performance
    data_quality_score = Column(DECIMAL(3, 2), default=1.0)
    strategy_performance_score = Column(DECIMAL(3, 2))  # Historical strategy success
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_priority_quality', 'scan_priority', 'data_quality_score'),
        Index('idx_volume_liquidity', 'avg_volume_30d', 'avg_dollar_volume_30d'),
    )

# =============================================================================
# DATA PROVIDER MANAGEMENT
# =============================================================================

class DataProvider(Base):
    """Configuration and performance tracking for market data providers."""
    __tablename__ = "data_providers_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(SQLEnum(DataProviderType), unique=True, nullable=False)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    api_key_configured = Column(Boolean, default=False)
    base_url = Column(String(200))
    
    # Rate Limits
    rate_limit_per_minute = Column(Integer)
    rate_limit_per_day = Column(Integer)
    rate_limit_per_month = Column(Integer)
    
    # Performance Metrics
    avg_response_time_ms = Column(DECIMAL(8, 2))
    success_rate_pct = Column(DECIMAL(5, 2))
    data_quality_score = Column(DECIMAL(3, 2))
    uptime_pct = Column(DECIMAL(5, 2))
    
    # Usage Tracking
    requests_today = Column(Integer, default=0)
    requests_this_month = Column(Integer, default=0)
    last_successful_request = Column(TIMESTAMP(timezone=True))
    last_error = Column(Text)
    
    # Cost Management
    monthly_cost_usd = Column(DECIMAL(10, 2))
    cost_per_request_usd = Column(DECIMAL(10, 6))
    monthly_budget_usd = Column(DECIMAL(10, 2))
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_active_premium', 'is_active', 'is_premium'),
        Index('idx_quality_uptime', 'data_quality_score', 'uptime_pct'),
    )

class DataQuality(Base):
    """Data quality monitoring and alerting."""
    __tablename__ = "data_quality_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments_v2.id"))
    
    # Quality Metrics
    metric_name = Column(String(100), nullable=False)  # COMPLETENESS, FRESHNESS, ACCURACY
    metric_value = Column(DECIMAL(8, 4), nullable=False)
    threshold_min = Column(DECIMAL(8, 4))
    threshold_max = Column(DECIMAL(8, 4))
    
    # Status
    status = Column(SQLEnum(DataQualityStatus), nullable=False)
    description = Column(Text)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_at = Column(TIMESTAMP(timezone=True))
    
    # Timing
    measured_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    measurement_period = Column(String(50))
    
    __table_args__ = (
        Index('idx_table_metric', 'table_name', 'metric_name'),
        Index('idx_status_severity', 'status', 'severity'),
        Index('idx_unresolved', 'is_resolved', 'measured_at'),
    ) 