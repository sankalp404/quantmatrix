"""
QuantMatrix Database Models
==========================

Centralized model imports for the QuantMatrix application.
All database models are imported here for easy access.
"""

# Core Base
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Essential Core Models (verified to exist)
from .user import User, UserRole
from .broker_account import BrokerAccount, BrokerType, AccountType

# Instruments & Market Data
from .instrument import Instrument, InstrumentType
from .market_data import PriceData, StockInfo, ATRData

# Trading & Positions
from .position import Position, PositionType, PositionStatus
from .trade import Trade, TradeSignal

# Portfolio Management (CLEANED - Removed duplicates, using Position instead)
from .portfolio import PortfolioSnapshot, Category, PositionCategory

# Tax Lots & Cost Basis (Multi-brokerage support)
from .tax_lot import TaxLot, TaxLotMethod, TaxLotSource

# Account Balances & Margin (Multi-brokerage enhanced)
from .account_balance import AccountBalance, AccountBalanceType

# Margin Interest Tracking (Multi-brokerage enhanced)
from .margin_interest import MarginInterest

# Transfers & Position Movements (Multi-brokerage enhanced)
from .transfer import Transfer, TransferType

# Transactions & Dividends
from .transaction import Transaction, TransactionType, Dividend

# Options Trading (Multi-brokerage support)
from .options import Option, OptionType

# Essential models list
__all__ = [
    "Base",
    "User",
    "UserRole",
    "BrokerAccount",
    "BrokerType",
    "AccountType",
    "Instrument",
    "InstrumentType",
    "PriceData",
    "StockInfo",
    "ATRData",
    "Position",
    "PositionType",
    "PositionStatus",
    "TaxLot",
    "TaxLotMethod",
    "TaxLotSource",
    "AccountBalance",
    "AccountBalanceType",
    "MarginInterest",
    "Transfer",
    "TransferType",
    "Transaction",
    "TransactionType",
    "Dividend",
    "Option",
    "OptionType",
    "PortfolioSnapshot",
    "Category",
    "PositionCategory",
    "Trade",
    "TradeSignal",
]
