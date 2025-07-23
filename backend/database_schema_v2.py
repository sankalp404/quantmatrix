"""
QuantMatrix V2 Database Schema - Perfect Multi-User Trading Platform
====================================================================

This schema is designed based on:
1. Current platform experience and data integrity issues
2. Multi-user scalability requirements  
3. Production-grade constraints and relationships
4. TastyTrade + IBKR integration lessons learned
5. Tax lot accuracy and portfolio management needs

Key Design Principles:
- Multi-tenancy with proper user isolation
- Strict data integrity constraints
- Audit trails for all financial data
- Optimized for portfolio management workflows
- Future-proof for authentication and admin features
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, 
    ForeignKey, UniqueConstraint, Index, CheckConstraint,
    TIMESTAMP, Enum as SQLEnum, JSON, DECIMAL
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

# =============================================================================
# ENUMS & TYPES
# =============================================================================

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

class AccountType(enum.Enum):
    MARGIN = "margin"
    CASH = "cash"
    IRA = "ira"
    ROTH_IRA = "roth_ira"

class BrokerType(enum.Enum):
    IBKR = "ibkr"
    TASTYTRADE = "tastytrade"
    SCHWAB = "schwab"  # Future
    FIDELITY = "fidelity"  # Future

class InstrumentType(enum.Enum):
    STOCK = "stock"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    CRYPTO = "crypto"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"

class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    OPTION_ASSIGNMENT = "option_assignment"
    OPTION_EXERCISE = "option_exercise"
    OPTION_EXPIRATION = "option_expiration"

class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    ASSIGNED = "assigned"
    EXPIRED = "expired"

# =============================================================================
# CORE USER & AUTHENTICATION
# =============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # OAuth users may not have password
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    
    # Authentication & Access
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(TIMESTAMP(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(TIMESTAMP(timezone=True))
    
    # Preferences
    timezone = Column(String(50), default="UTC")
    currency_preference = Column(String(3), default="USD")
    notification_preferences = Column(JSON)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_last_login', 'last_login'),
    )

# =============================================================================
# BROKERAGE ACCOUNTS
# =============================================================================

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Account Identification
    broker = Column(SQLEnum(BrokerType), nullable=False)
    account_number = Column(String(50), nullable=False)
    account_name = Column(String(100))  # User-friendly name
    account_type = Column(SQLEnum(AccountType), default=AccountType.MARGIN)
    
    # Connection Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_syncing_enabled = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(TIMESTAMP(timezone=True))
    last_sync_status = Column(String(50))  # success, error, partial
    sync_error_message = Column(Text)
    
    # API Configuration (encrypted in production)
    api_credentials = Column(JSON)  # Store encrypted credentials
    sync_preferences = Column(JSON)  # What to sync, frequency, etc.
    
    # Account Metadata
    base_currency = Column(String(3), default="USD")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    tax_lots = relationship("TaxLot", back_populates="account", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('broker', 'account_number', name='uq_broker_account'),
        Index('idx_accounts_user_broker', 'user_id', 'broker'),
        Index('idx_accounts_sync_status', 'last_sync_at', 'is_syncing_enabled'),
    )

# =============================================================================
# FINANCIAL INSTRUMENTS
# =============================================================================

class Instrument(Base):
    __tablename__ = "instruments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Primary Identification
    symbol = Column(String(50), nullable=False, index=True)
    instrument_type = Column(SQLEnum(InstrumentType), nullable=False)
    
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
    multiplier = Column(Integer, default=100)  # Contract multiplier
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    positions = relationship("Position", back_populates="instrument")
    transactions = relationship("Transaction", back_populates="instrument")
    market_data = relationship("MarketData", back_populates="instrument")
    
    __table_args__ = (
        Index('idx_instruments_symbol_type', 'symbol', 'instrument_type'),
        Index('idx_instruments_underlying', 'underlying_symbol'),
        Index('idx_instruments_expiration', 'expiration_date'),
        CheckConstraint('strike_price > 0', name='ck_strike_price_positive'),
        CheckConstraint(
            "(instrument_type != 'option') OR (underlying_symbol IS NOT NULL AND option_type IS NOT NULL AND strike_price IS NOT NULL AND expiration_date IS NOT NULL)",
            name='ck_option_fields_required'
        ),
    )

# =============================================================================
# POSITIONS (CURRENT HOLDINGS)
# =============================================================================

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    
    # Position Data
    quantity = Column(DECIMAL(15, 6), nullable=False)  # Can be negative for short positions
    average_cost = Column(DECIMAL(10, 4), nullable=False)
    current_price = Column(DECIMAL(10, 4))
    
    # Calculated Fields (updated by background jobs)
    market_value = Column(DECIMAL(15, 2))
    unrealized_pnl = Column(DECIMAL(15, 2))
    unrealized_pnl_percent = Column(DECIMAL(8, 4))
    day_pnl = Column(DECIMAL(15, 2))
    day_pnl_percent = Column(DECIMAL(8, 4))
    
    # Position Metadata
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN)
    opened_date = Column(DateTime)
    closed_date = Column(DateTime)
    
    # User Customization
    notes = Column(Text)
    tags = Column(JSON)  # User-defined tags
    alerts_enabled = Column(Boolean, default=True)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="positions")
    instrument = relationship("Instrument", back_populates="positions")
    tax_lots = relationship("TaxLot", back_populates="position")
    
    __table_args__ = (
        UniqueConstraint('account_id', 'instrument_id', name='uq_account_instrument'),
        Index('idx_positions_account_status', 'account_id', 'status'),
        Index('idx_positions_quantity', 'quantity'),
        CheckConstraint('quantity != 0', name='ck_quantity_not_zero'),
        CheckConstraint('average_cost > 0', name='ck_average_cost_positive'),
    )

# =============================================================================
# TRANSACTIONS (TRADE HISTORY)
# =============================================================================

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    
    # External IDs (for deduplication)
    external_id = Column(String(100))  # Broker's transaction ID
    order_id = Column(String(100))
    execution_id = Column(String(100))
    
    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    quantity = Column(DECIMAL(15, 6), nullable=False)
    price = Column(DECIMAL(10, 4), nullable=False)
    
    # Financial Details
    gross_amount = Column(DECIMAL(15, 2), nullable=False)  # quantity * price
    commission = Column(DECIMAL(10, 2), default=0)
    fees = Column(DECIMAL(10, 2), default=0)
    net_amount = Column(DECIMAL(15, 2), nullable=False)  # gross - commission - fees
    
    # Timing
    transaction_date = Column(TIMESTAMP(timezone=True), nullable=False)
    settlement_date = Column(DateTime)
    trade_date = Column(DateTime)  # May differ from transaction_date
    
    # Metadata
    description = Column(Text)
    source = Column(String(50))  # api, csv_import, manual, etc.
    currency = Column(String(3), default="USD")
    exchange = Column(String(20))
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    synced_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    instrument = relationship("Instrument", back_populates="transactions")
    tax_lots = relationship("TaxLot", back_populates="source_transaction")
    
    __table_args__ = (
        UniqueConstraint('account_id', 'external_id', name='uq_account_external_id'),
        Index('idx_transactions_account_date', 'account_id', 'transaction_date'),
        Index('idx_transactions_symbol_date', 'instrument_id', 'transaction_date'),
        Index('idx_transactions_type', 'transaction_type'),
        CheckConstraint('quantity != 0', name='ck_transaction_quantity_not_zero'),
        CheckConstraint('price > 0', name='ck_transaction_price_positive'),
    )

# =============================================================================
# TAX LOTS (COST BASIS TRACKING)
# =============================================================================

class TaxLot(Base):
    __tablename__ = "tax_lots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    source_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    
    # Tax Lot Details
    shares_purchased = Column(DECIMAL(15, 6), nullable=False)
    shares_remaining = Column(DECIMAL(15, 6), nullable=False)
    cost_per_share = Column(DECIMAL(10, 4), nullable=False)
    total_cost = Column(DECIMAL(15, 2), nullable=False)
    
    # Dates
    purchase_date = Column(DateTime, nullable=False)
    acquisition_date = Column(DateTime)  # For transfers, may differ from purchase
    
    # Tax Information
    is_long_term = Column(Boolean, default=False)  # > 1 year holding
    is_wash_sale = Column(Boolean, default=False)
    
    # Calculated Fields
    current_value = Column(DECIMAL(15, 2))
    unrealized_pnl = Column(DECIMAL(15, 2))
    unrealized_pnl_percent = Column(DECIMAL(8, 4))
    days_held = Column(Integer)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="tax_lots")
    position = relationship("Position", back_populates="tax_lots")
    source_transaction = relationship("Transaction", back_populates="tax_lots")
    
    __table_args__ = (
        Index('idx_tax_lots_position', 'position_id'),
        Index('idx_tax_lots_purchase_date', 'purchase_date'),
        Index('idx_tax_lots_remaining', 'shares_remaining'),
        CheckConstraint('shares_purchased > 0', name='ck_shares_purchased_positive'),
        CheckConstraint('shares_remaining >= 0', name='ck_shares_remaining_non_negative'),
        CheckConstraint('shares_remaining <= shares_purchased', name='ck_remaining_lte_purchased'),
        CheckConstraint('cost_per_share > 0', name='ck_cost_per_share_positive'),
    )

# =============================================================================
# MARKET DATA
# =============================================================================

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    
    # Price Data
    open_price = Column(DECIMAL(10, 4))
    high_price = Column(DECIMAL(10, 4))
    low_price = Column(DECIMAL(10, 4))
    close_price = Column(DECIMAL(10, 4))
    volume = Column(DECIMAL(15, 0))
    
    # Additional Data
    market_cap = Column(DECIMAL(20, 2))
    pe_ratio = Column(DECIMAL(8, 2))
    dividend_yield = Column(DECIMAL(6, 4))
    
    # Technical Indicators
    atr_14 = Column(DECIMAL(10, 4))
    rsi_14 = Column(DECIMAL(6, 2))
    sma_20 = Column(DECIMAL(10, 4))
    sma_50 = Column(DECIMAL(10, 4))
    
    # Timing
    data_date = Column(DateTime, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    instrument = relationship("Instrument", back_populates="market_data")
    
    __table_args__ = (
        UniqueConstraint('instrument_id', 'data_date', name='uq_instrument_date'),
        Index('idx_market_data_date', 'data_date'),
        Index('idx_market_data_symbol_date', 'instrument_id', 'data_date'),
    )

# =============================================================================
# ALERTS & NOTIFICATIONS
# =============================================================================

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Alert Configuration
    title = Column(String(200), nullable=False)
    description = Column(Text)
    alert_type = Column(String(50), nullable=False)  # price, volume, news, etc.
    conditions = Column(JSON, nullable=False)  # Alert conditions
    
    # Status
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(TIMESTAMP(timezone=True))
    
    # Notification Preferences
    notification_channels = Column(JSON)  # email, discord, sms, etc.
    cooldown_minutes = Column(Integer, default=60)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    __table_args__ = (
        Index('idx_alerts_user_active', 'user_id', 'is_active'),
        Index('idx_alerts_type', 'alert_type'),
    )

# =============================================================================
# SYNC & AUDIT TABLES
# =============================================================================

class SyncHistory(Base):
    __tablename__ = "sync_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Sync Details
    sync_type = Column(String(50), nullable=False)  # positions, transactions, market_data
    status = Column(String(20), nullable=False)  # success, error, partial
    
    # Results
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    
    # Error Tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Timing
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True))
    duration_seconds = Column(Integer)
    
    __table_args__ = (
        Index('idx_sync_history_account_date', 'account_id', 'started_at'),
        Index('idx_sync_history_status', 'status'),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Action Details
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer)
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    
    # Change Tracking
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_fields = Column(JSON)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    source = Column(String(50))  # api, web, sync, etc.
    
    # Timing
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_logs_table_record', 'table_name', 'record_id'),
        Index('idx_audit_logs_user_date', 'user_id', 'created_at'),
        Index('idx_audit_logs_action', 'action'),
    )

# =============================================================================
# SCHEMA CREATION & VALIDATION
# =============================================================================

def create_tables(engine):
    """Create all tables with proper constraints"""
    Base.metadata.create_all(engine)

def validate_schema():
    """Validate schema design and constraints"""
    tables = Base.metadata.tables
    print(f"✅ Schema contains {len(tables)} tables:")
    
    for table_name, table in tables.items():
        print(f"   📋 {table_name}: {len(table.columns)} columns, {len(table.constraints)} constraints")
    
    return True

if __name__ == "__main__":
    print("🏗️ QuantMatrix V2 Database Schema")
    print("=" * 50)
    validate_schema() 