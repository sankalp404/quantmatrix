"""
Database models for caching comprehensive market analysis results.
Stores heavy analysis results to avoid re-computation and improve performance.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.sql import func
from backend.models import Base

class MarketAnalysisCache(Base):
    """Cache for comprehensive market analysis results."""
    __tablename__ = "market_analysis_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)  # 'atr_matrix', 'company_profile', 'technical_analysis'
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_valid = Column(Boolean, default=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_symbol_analysis_type', 'symbol', 'analysis_type'),
        Index('idx_symbol_expiry', 'symbol', 'expiry_timestamp'),
        Index('idx_analysis_timestamp', 'analysis_timestamp'),
        Index('idx_entry_signal', 'entry_signal'),
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
    market_cap_category = Column(String(20), index=True)  # 'mega', 'large', 'mid', 'small', 'micro'
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_market_cap_category', 'market_cap_category'),
        Index('idx_scan_priority', 'scan_priority'),
        Index('idx_sector_active', 'sector', 'is_active'),
    )

class ScanHistory(Base):
    """History of comprehensive scans performed."""
    __tablename__ = "scan_history"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String(50), nullable=False)  # 'atr_matrix', 'morning_brew', 'signals'
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
    top_results = Column(JSON)      # Store top opportunities
    error_log = Column(JSON)        # Store any errors
    
    # Discord integration
    discord_sent = Column(Boolean, default=False)
    discord_timestamp = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_scan_type_timestamp', 'scan_type', 'scan_timestamp'),
        Index('idx_opportunities_found', 'opportunities_found'),
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
    
    # Data quality
    data_points_returned = Column(Integer)
    data_quality_score = Column(Float)  # 1-10 rating
    
    # Usage tracking
    daily_usage_count = Column(Integer, default=1)
    monthly_usage_count = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_endpoint_timestamp', 'endpoint', 'request_timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'request_timestamp'),
        Index('idx_daily_usage', 'daily_usage_count'),
    )

class MarketDataProvider(Base):
    """Configuration and performance tracking for market data providers."""
    __tablename__ = "market_data_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(50), unique=True, nullable=False)  # 'polygon', 'alpha_vantage', 'yfinance'
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    
    # API configuration
    api_key_configured = Column(Boolean, default=False)
    base_url = Column(String(200))
    rate_limit_per_minute = Column(Integer)
    rate_limit_per_day = Column(Integer)
    
    # Performance metrics
    avg_response_time_ms = Column(Float)
    success_rate_pct = Column(Float)
    data_quality_score = Column(Float)
    uptime_pct = Column(Float)
    
    # Usage stats
    requests_today = Column(Integer, default=0)
    requests_this_month = Column(Integer, default=0)
    last_successful_request = Column(DateTime(timezone=True))
    last_error = Column(Text)
    
    # Cost tracking
    monthly_cost_usd = Column(Float)
    cost_per_request_usd = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_provider_active', 'provider_name', 'is_active'),
        Index('idx_premium_active', 'is_premium', 'is_active'),
    ) 