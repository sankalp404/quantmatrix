"""
QuantMatrix Database Models
==========================

Centralized model imports for the QuantMatrix application.
All database models are imported here for easy access.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the Base class for all models
Base = declarative_base()

# Core User Management
from .user import User, UserRole

# Account Management
from .account import (
    BrokerAccount, AccountCredentials, AccountSync,
    BrokerType, AccountType, AccountStatus
)

# Instruments & Positions
from .instrument import Instrument, InstrumentAlias, InstrumentType
from .position import Position, PositionHistory, PositionType

# Transactions & Tax Management
from .transaction import Transaction, Dividend, TransactionSyncStatus
from .tax_lots import TaxLot, TaxLotSale, TaxStrategy, TaxReport

# Market Data
from .market_data import (
    StockInfo, PriceData, ATRData, SectorMetrics,
    MarketDataSync, DataQuality
)

# Strategies (avoiding conflicts - import from main strategies.py)
from .strategy import (
    Strategy, StrategyRun, StrategyPerformance, BacktestRun,
    StrategyType, StrategyStatus
)

# Signals (avoiding notification conflict)
from .signals import Signal, MarketDataCache

# Notifications (main notifications model)
from .notification import (
    Notification, NotificationTemplate, NotificationPreference, NotificationDelivery
)

# Alerts & Audit
from .alert import Alert, AlertCondition, AlertTemplate, AlertHistory
from .audit import AuditLog, DataChangeLog, SecurityEvent

# CSV Import & Integration
from .csv_import import CSVImport
from .strategy_integration import StrategyService, StrategyExecution

# Market Analysis
from .market_analysis import (
    MarketAnalysisCache, StockUniverse, ScanHistory,
    PolygonApiUsage, MarketDataProvider
)

# Options Trading
from .options import (
    TastytradeAccount, OptionPosition, OptionGreeks, TradingStrategy
)

# Portfolio Management (avoiding account conflicts)
from .portfolio import Holding, Category, HoldingCategory, PortfolioSnapshot

# Trading
from .trade import Trade, TradeSignal 