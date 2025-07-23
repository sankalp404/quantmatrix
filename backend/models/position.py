"""
Portfolio Positions
=================================

Current portfolio positions across all accounts and brokers.
Real-time position tracking with P&L calculations.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, DECIMAL, Enum as SQLEnum, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from decimal import Decimal

from . import Base

# =============================================================================
# ENUMS
# =============================================================================

class PositionType(enum.Enum):
    LONG = "long"              # Long equity position
    SHORT = "short"            # Short equity position
    OPTION_LONG = "option_long"    # Long options
    OPTION_SHORT = "option_short"  # Short options
    FUTURE_LONG = "future_long"    # Long futures
    FUTURE_SHORT = "future_short"  # Short futures

class PositionStatus(enum.Enum):
    OPEN = "open"              # Active position
    CLOSED = "closed"          # Position closed out
    EXPIRED = "expired"        # Options/futures expired

# =============================================================================
# POSITION MODELS
# =============================================================================

class Position(Base):
    """
    Current portfolio position in a security.
    Represents what you currently own/owe.
    """
    __tablename__ = "positions"
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("broker_accounts.id"), nullable=False, index=True)
    
    # Security identification
    symbol = Column(String(20), nullable=False, index=True)
    instrument_type = Column(String(20), default="STOCK")  # STOCK, OPTION, FUTURE, etc.
    
    # Position details
    position_type = Column(SQLEnum(PositionType), nullable=False)
    quantity = Column(DECIMAL(15, 6), nullable=False)  # Shares/contracts held
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN, nullable=False)
    
    # Cost basis (aggregate from tax lots)
    average_cost = Column(DECIMAL(15, 4), nullable=False)  # Average cost per share
    total_cost_basis = Column(DECIMAL(15, 2), nullable=False)  # Total cost basis
    
    # Current market values
    current_price = Column(DECIMAL(15, 4))  # Latest market price
    market_value = Column(DECIMAL(15, 2))   # current_price * quantity
    
    # P&L calculations
    unrealized_pnl = Column(DECIMAL(15, 2))     # market_value - total_cost_basis
    unrealized_pnl_pct = Column(DECIMAL(8, 4))  # unrealized_pnl / total_cost_basis * 100
    day_pnl = Column(DECIMAL(15, 2))            # Today's P&L change
    day_pnl_pct = Column(DECIMAL(8, 4))         # Today's % change
    
    # Options-specific fields
    option_type = Column(String(4))             # "CALL", "PUT"
    strike_price = Column(DECIMAL(15, 4))       # Strike price for options
    expiration_date = Column(DateTime)          # Expiration for options/futures
    option_multiplier = Column(Integer, default=100)  # Usually 100 for equity options
    
    # Greeks (for options)
    delta = Column(DECIMAL(8, 6))
    gamma = Column(DECIMAL(8, 6))
    theta = Column(DECIMAL(8, 6))
    vega = Column(DECIMAL(8, 6))
    iv = Column(DECIMAL(8, 4))  # Implied volatility
    
    # Risk metrics
    position_size_pct = Column(DECIMAL(6, 3))   # % of portfolio
    sector = Column(String(50))                 # Market sector
    beta = Column(DECIMAL(6, 3))               # Beta vs market
    
    # Last update info
    price_updated_at = Column(DateTime)         # When price was last updated
    position_updated_at = Column(DateTime)      # When position was last changed
    
    # Data source
    last_sync_id = Column(Integer, ForeignKey("account_syncs.id"))
    broker_position_id = Column(String(100))    # Broker's internal position ID
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="positions")
    account = relationship("BrokerAccount", back_populates="positions")
    instrument = relationship("Instrument", foreign_keys=[symbol],
                            primaryjoin="Position.symbol == Instrument.symbol")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_positions_user_account", "user_id", "account_id"),
        Index("idx_positions_symbol", "symbol"),
        Index("idx_positions_status", "status"),
        Index("idx_positions_type", "position_type"),
        Index("idx_positions_updated_at", "updated_at"),    )
    
    @property
    def is_option(self) -> bool:
        """Check if this is an options position."""
        return self.position_type in [PositionType.OPTION_LONG, PositionType.OPTION_SHORT]
    
    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.position_type in [PositionType.LONG, PositionType.OPTION_LONG, PositionType.FUTURE_LONG]
    
    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.position_type in [PositionType.SHORT, PositionType.OPTION_SHORT, PositionType.FUTURE_SHORT]
    
    @property
    def display_symbol(self) -> str:
        """Human-readable symbol with options details."""
        if self.is_option:
            exp_str = self.expiration_date.strftime("%y%m%d") if self.expiration_date else "XX"
            strike_str = f"{self.strike_price:.0f}" if self.strike_price else "0"
            return f"{self.symbol}_{exp_str}_{self.option_type[0]}{strike_str}"
        return self.symbol
    
    def update_market_data(self, price: float, day_change: float = None):
        """Update position with latest market data."""
        self.current_price = Decimal(str(price))
        self.market_value = self.quantity * self.current_price
        
        # Calculate unrealized P&L
        if self.is_long:
            self.unrealized_pnl = self.market_value - self.total_cost_basis
        else:  # Short position
            self.unrealized_pnl = self.total_cost_basis - self.market_value
        
        # Calculate percentage
        if self.total_cost_basis > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.total_cost_basis) * 100
        
        # Day P&L if provided
        if day_change is not None:
            self.day_pnl = self.quantity * Decimal(str(day_change))
            if self.market_value > 0:
                self.day_pnl_pct = (self.day_pnl / (self.market_value - self.day_pnl)) * 100
        
        self.price_updated_at = datetime.now()
    
    def calculate_position_size_pct(self, total_portfolio_value: float):
        """Calculate position size as percentage of total portfolio."""
        if total_portfolio_value > 0 and self.market_value:
            self.position_size_pct = (abs(float(self.market_value)) / total_portfolio_value) * 100

class PositionHistory(Base):
    """
    Historical position snapshots for performance tracking.
    Captures position state at specific points in time.
    """
    __tablename__ = "position_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Snapshot date
    snapshot_date = Column(DateTime, nullable=False, index=True)
    snapshot_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Position data at snapshot time
    quantity = Column(DECIMAL(15, 6), nullable=False)
    price = Column(DECIMAL(15, 4), nullable=False)
    market_value = Column(DECIMAL(15, 2), nullable=False)
    unrealized_pnl = Column(DECIMAL(15, 2))
    total_cost_basis = Column(DECIMAL(15, 2), nullable=False)
    
    # Performance metrics
    day_return = Column(DECIMAL(8, 4))      # 1-day return %
    week_return = Column(DECIMAL(8, 4))     # 1-week return %
    month_return = Column(DECIMAL(8, 4))    # 1-month return %
    inception_return = Column(DECIMAL(8, 4))  # Return since first purchase
    
    # Risk metrics
    volatility = Column(DECIMAL(8, 4))      # Historical volatility
    max_drawdown = Column(DECIMAL(8, 4))    # Maximum drawdown from peak
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    position = relationship("Position")
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("idx_position_history_position_date", "position_id", "snapshot_date"),
        Index("idx_position_history_user_date", "user_id", "snapshot_date"),    )
