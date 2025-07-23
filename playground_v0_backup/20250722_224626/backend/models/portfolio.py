from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from decimal import Decimal
from backend.models import Base

class AccountType(enum.Enum):
    TAXABLE = "taxable"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    HSA = "hsa"
    BROKERAGE = "brokerage"

class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    MERGER = "merger"
    TRANSFER = "transfer"

class Account(Base):
    """IBKR accounts and other brokerage accounts."""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False)  # Changed from Enum to String to match DB
    account_number = Column(String(50))  # This maps to what we called account_id before
    broker = Column(String(50))
    api_credentials = Column(Text)
    is_active = Column(Boolean)
    is_paper_trading = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime)
    
    # Relationships
    holdings = relationship("Holding", back_populates="account")
    # tax_lots = relationship("TaxLot", back_populates="account")  # TaxLots are related to Holdings, not directly to Account
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="account")
    trades = relationship("Trade", back_populates="account")
    transactions = relationship("Transaction", back_populates="account")
    dividends = relationship("Dividend", back_populates="account")
    option_positions = relationship("OptionPosition", back_populates="account")  # Added for options

class Holding(Base):
    """Current portfolio holdings with real-time data."""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol = Column(String(50), nullable=False)  # Increased from 20 to 50 for options symbols
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    unrealized_pnl_pct = Column(Float, nullable=False)
    day_pnl = Column(Float, default=0.0)
    day_pnl_pct = Column(Float, default=0.0)
    
    # Additional metadata
    currency = Column(String(10), default="USD")
    exchange = Column(String(20))
    contract_type = Column(String(20), default="STK")  # STK, OPT, etc.
    sector = Column(String(50))
    industry = Column(String(100))
    market_cap = Column(Float)
    
    # Priority for margin calls (1 = sell first, 10 = sell last)
    margin_priority = Column(Integer, default=5)
    
    # Custom categorization
    custom_category = Column(String(100))
    notes = Column(Text)
    
    # Timestamps
    first_acquired = Column(DateTime)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="holdings")
    tax_lots = relationship("TaxLot", back_populates="holding")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_account_symbol', 'account_id', 'symbol'),
        Index('idx_symbol', 'symbol'),
        Index('idx_margin_priority', 'margin_priority'),
    )



class Category(Base):
    """Custom categorization system for holdings."""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    color = Column(String(10))  # Hex color code
    parent_category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Category type
    category_type = Column(String(50), default="custom")  # custom, sector, strategy, etc.
    
    # Target allocation (percentage)
    target_allocation_pct = Column(Float)
    min_allocation_pct = Column(Float)
    max_allocation_pct = Column(Float)
    
    # Rebalancing settings
    rebalance_threshold_pct = Column(Float, default=5.0)  # Trigger rebalancing at 5% deviation
    auto_rebalance = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent_category = relationship("Category", remote_side=[id])
    holdings_assignments = relationship("HoldingCategory", back_populates="category")

class HoldingCategory(Base):
    """Many-to-many relationship between holdings and categories."""
    __tablename__ = "holding_categories"
    
    id = Column(Integer, primary_key=True)
    holding_id = Column(Integer, ForeignKey("holdings.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    allocation_pct = Column(Float, default=100.0)  # Percentage of holding assigned to this category
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    holding = relationship("Holding")
    category = relationship("Category", back_populates="holdings_assignments")
    
    # Unique constraint
    __table_args__ = (
        Index('idx_holding_category', 'holding_id', 'category_id', unique=True),
    )

class PortfolioSnapshot(Base):
    """Daily portfolio snapshots for historical analysis."""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    snapshot_date = Column(DateTime, nullable=False)
    
    # Portfolio metrics
    total_value = Column(Float, nullable=False)
    total_cash = Column(Float, nullable=False)
    total_equity_value = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    day_pnl = Column(Float, nullable=False)
    day_pnl_pct = Column(Float, nullable=False)
    
    # Risk metrics
    beta = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    
    # Margin information
    buying_power = Column(Float)
    margin_used = Column(Float)
    margin_available = Column(Float)
    
    # Snapshot data (JSON)
    holdings_snapshot = Column(Text)  # JSON of holdings at this time
    sector_allocation = Column(Text)  # JSON of sector breakdown
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="portfolio_snapshots")
    
    # Indexes
    __table_args__ = (
        Index('idx_account_date', 'account_id', 'snapshot_date'),
        Index('idx_snapshot_date', 'snapshot_date'),
    ) 