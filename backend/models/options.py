"""
Options Trading Models
=====================

Handles options-specific data that extends the universal Instrument model.
All options instruments are stored in the main instruments table.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey,
    DECIMAL, Numeric, Float, Text, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from . import Base

# =============================================================================
# ENUMS  
# =============================================================================

class TradingStrategyType(enum.Enum):
    ATR_MATRIX = "atr_matrix"
    WHEEL = "wheel"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    IRON_CONDOR = "iron_condor"
    BUTTERFLY = "butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    CUSTOM = "custom"

# =============================================================================
# OPTIONS MODELS (Using Universal Instruments)
# =============================================================================

class TastytradeAccount(Base):
    """Tastytrade account information for options trading."""
    __tablename__ = "tastytrade_accounts"
    
    id = Column(Integer, primary_key=True)
    account_number = Column(String(50), unique=True, nullable=False)
    nickname = Column(String(100))
    account_type = Column(String(50))
    is_margin = Column(Boolean, default=False)
    day_trader_status = Column(Boolean, default=False)
    account_status = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OptionPosition(Base):
    """Options position tracking - uses universal Instrument model."""
    __tablename__ = "option_positions"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    
    # Position details
    quantity = Column(Integer, nullable=False)
    average_open_price = Column(Numeric(10, 4))
    average_close_price = Column(Numeric(10, 4))
    current_price = Column(Numeric(12, 4))
    market_value = Column(Numeric(12, 2))
    
    # P&L tracking
    unrealized_pnl = Column(Numeric(12, 2))
    realized_pnl = Column(Numeric(12, 2))
    day_pnl = Column(Numeric(12, 2))
    
    # Status and timestamps
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TastytradeAccount")
    instrument = relationship("Instrument")

class OptionGreeks(Base):
    """Option Greeks tracking."""
    __tablename__ = "option_greeks"
    
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Greeks
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    rho = Column(Float)
    
    # IV and other metrics
    implied_volatility = Column(Float)
    theoretical_price = Column(Numeric(10, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)

class TradingStrategy(Base):
    """Options trading strategies.""" 
    __tablename__ = "trading_strategies"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    strategy_type = Column(SQLEnum(TradingStrategyType), nullable=False)
    
    # Strategy configuration
    parameters = Column(JSON)
    target_profit_pct = Column(Float)
    max_loss_pct = Column(Float)
    
    # Performance tracking
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    total_pnl = Column(Numeric(15, 2), default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TastytradeAccount") 