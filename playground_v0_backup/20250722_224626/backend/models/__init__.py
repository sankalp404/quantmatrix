from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()
metadata = MetaData()

# Dependency injection for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

# Import all models to ensure they are registered
# Legacy models (to be migrated)
from .trade import Trade, TradeSignal
from .alert import Alert, AlertCondition, AlertTemplate, AlertHistory
from .user import User

# New comprehensive portfolio management models
from .portfolio import (
    Account, Holding, Category, HoldingCategory, PortfolioSnapshot,
    AccountType, TransactionType
)
from .tax_lots import TaxLot, TaxLotSale, TaxStrategy, TaxReport
from .signals import (
    Strategy, StrategyRun, Signal, Notification, MarketDataCache,
    SignalType, SignalStatus, StrategyType, NotificationType
)
from .options import (
    TastytradeAccount, OptionPosition, OptionInstrument, OptionGreeks,
    TradingStrategy, CapitalAllocation, StrategyPerformance, RiskMetrics
)
from .transactions import Transaction, Dividend, TransactionSyncStatus 