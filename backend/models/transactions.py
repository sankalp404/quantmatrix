"""
Transaction Data Models for Local Persistence
Stores IBKR transaction data locally for fast access
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from backend.models import Base

class Transaction(Base):
    """Local storage for all transaction data from IBKR."""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Transaction identification
    external_id = Column(String(100))  # IBKR execution ID
    order_id = Column(String(50))
    execution_id = Column(String(50))
    
    # Transaction details
    symbol = Column(String(20), nullable=False)
    description = Column(Text)
    transaction_type = Column(String(20), nullable=False)  # BUY, SELL
    action = Column(String(10))  # BOT, SLD
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    
    # Fees and costs
    commission = Column(Float, default=0)
    fees = Column(Float, default=0)
    net_amount = Column(Float, nullable=False)
    
    # Metadata
    currency = Column(String(10), default="USD")
    exchange = Column(String(20))
    contract_type = Column(String(20), default="STK")
    
    # Dates
    transaction_date = Column(DateTime, nullable=False)
    settlement_date = Column(DateTime)
    
    # Data source tracking
    source = Column(String(50), default="ibkr")
    synced_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_account_symbol_date', 'account_id', 'symbol', 'transaction_date'),
        Index('idx_transaction_date', 'transaction_date'),
        Index('idx_external_id', 'external_id'),
        Index('idx_symbol', 'symbol'),
    )

class Dividend(Base):
    """Local storage for dividend payment data."""
    __tablename__ = "dividends"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Dividend identification
    external_id = Column(String(100))  # IBKR dividend ID
    
    # Dividend details
    symbol = Column(String(20), nullable=False)
    ex_date = Column(DateTime, nullable=False)
    pay_date = Column(DateTime)
    dividend_per_share = Column(Float, nullable=False)
    shares_held = Column(Float, nullable=False)
    total_dividend = Column(Float, nullable=False)
    
    # Tax information
    tax_withheld = Column(Float, default=0)
    net_dividend = Column(Float, nullable=False)
    
    # Metadata
    currency = Column(String(10), default="USD")
    frequency = Column(String(20), default="quarterly")  # quarterly, monthly, annual
    dividend_type = Column(String(20), default="ordinary")  # ordinary, special, return_of_capital
    
    # Data source tracking
    source = Column(String(50), default="ibkr")
    synced_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="dividends")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_account_symbol_exdate', 'account_id', 'symbol', 'ex_date'),
        Index('idx_ex_date', 'ex_date'),
        Index('idx_pay_date', 'pay_date'),
        Index('idx_symbol', 'symbol'),
    )

class TransactionSyncStatus(Base):
    """Track sync status for transaction data."""
    __tablename__ = "transaction_sync_status"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Sync tracking
    last_sync_date = Column(DateTime)
    last_successful_sync = Column(DateTime)
    sync_status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    
    # Data ranges
    earliest_transaction_date = Column(DateTime)
    latest_transaction_date = Column(DateTime)
    total_transactions = Column(Integer, default=0)
    total_dividends = Column(Integer, default=0)
    
    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")
    
    # Indexes
    __table_args__ = (
        Index('idx_account_status', 'account_id', 'sync_status'),
        Index('idx_last_sync', 'last_sync_date'),
    ) 