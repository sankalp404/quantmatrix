"""
Pytest configuration and common fixtures for test suite.
Provides database, user, and mock client fixtures for comprehensive testing.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Generator, Dict, Any
from unittest.mock import Mock, AsyncMock
import pandas as pd

# Import models and services
from backend.models import Base
from backend.models.users import User, UserRole
from backend.models.market_data import Instrument, PriceData
from backend.models.strategies import Strategy, StrategyType
from backend.config import settings

# Database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Fix imports to use singular model names
try:
    from backend.models import User, UserRole, BrokerAccount, Instrument
    from backend.database import SessionLocal, engine, Base
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    IMPORT_ERROR = str(e)

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def db_session(engine):
    """Create fresh database session for each test."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@quantmatrix.com",
        role=UserRole.TRADER,
        is_active=True
    )
    user.set_password("testpassword123")
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user

@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin test user."""
    user = User(
        username="admin",
        email="admin@quantmatrix.com", 
        role=UserRole.ADMIN,
        is_active=True
    )
    user.set_password("adminpass123")
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user

@pytest.fixture
def sample_instruments(db_session) -> Dict[str, Instrument]:
    """Create sample instruments for testing."""
    instruments = {}
    
    # Tech stocks
    for symbol in ["AAPL", "MSFT", "NVDA", "GOOGL", "META"]:
        instrument = Instrument(
            symbol=symbol,
            name=f"{symbol} Inc.",
            instrument_type="stock",
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            is_active=True
        )
        db_session.add(instrument)
        instruments[symbol] = instrument
    
    # ETFs
    for symbol in ["SPY", "QQQ", "IWM", "VTI"]:
        instrument = Instrument(
            symbol=symbol,
            name=f"{symbol} ETF",
            instrument_type="etf", 
            exchange="NYSE",
            currency="USD",
            sector="ETF",
            is_active=True
        )
        db_session.add(instrument)
        instruments[symbol] = instrument
    
    db_session.commit()
    return instruments

@pytest.fixture
def sample_price_data(db_session, sample_instruments) -> Dict[str, list]:
    """Create sample price data for testing."""
    price_data = {}
    
    base_date = datetime.now() - timedelta(days=30)
    
    for symbol, instrument in sample_instruments.items():
        prices = []
        base_price = 150.0 if symbol == "AAPL" else 100.0
        
        for i in range(30):  # 30 days of data
            date = base_date + timedelta(days=i)
            
            # Generate realistic OHLC data with some volatility
            price_change = (i % 5 - 2) * 2.0  # -4 to +4 variation
            open_price = base_price + price_change
            high_price = open_price + abs(price_change) + 1.0
            low_price = open_price - abs(price_change) - 1.0
            close_price = open_price + (price_change * 0.5)
            volume = 1000000 + (i * 10000)
            
            price = PriceData(
                instrument_id=instrument.id,
                date=date.date(),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                adjusted_close=close_price
            )
            
            db_session.add(price)
            prices.append(price)
        
        price_data[symbol] = prices
    
    db_session.commit()
    return price_data

@pytest.fixture
def sample_ohlc_dataframe() -> pd.DataFrame:
    """Create sample OHLC DataFrame for ATR testing."""
    return pd.DataFrame({
        'date': pd.date_range(start='2025-01-01', periods=20, freq='D'),
        'open': [150.0, 151.2, 149.8, 152.1, 150.5, 148.9, 151.3, 153.2, 152.1, 150.8,
                149.2, 151.7, 154.1, 152.8, 151.4, 149.9, 152.6, 155.2, 153.7, 151.9],
        'high': [152.1, 153.0, 151.2, 154.3, 152.8, 150.1, 153.7, 155.8, 154.2, 152.9,
                150.8, 153.2, 156.4, 154.9, 153.1, 151.4, 154.8, 157.1, 155.9, 153.7],
        'low': [149.5, 150.1, 148.2, 150.9, 149.1, 147.8, 150.2, 152.1, 151.0, 149.7,
               148.1, 150.5, 152.8, 151.5, 150.2, 148.8, 151.3, 153.9, 152.6, 150.8],
        'close': [151.2, 149.8, 152.1, 150.5, 148.9, 151.3, 153.2, 152.1, 150.8, 149.2,
                 151.7, 154.1, 152.8, 151.4, 149.9, 152.6, 155.2, 153.7, 151.9, 152.4],
        'volume': [1200000, 1350000, 1100000, 1450000, 1300000, 1250000, 1400000, 1500000,
                  1380000, 1280000, 1320000, 1480000, 1550000, 1420000, 1360000, 1290000,
                  1460000, 1620000, 1580000, 1440000]
    })

@pytest.fixture
def mock_ibkr_client():
    """Mock IBKR client for testing."""
    mock_client = Mock()
    mock_client.connect_with_retry = AsyncMock(return_value=True)
    mock_client.get_enhanced_account_statements = AsyncMock(return_value=[
        {
            'id': 'test_123',
            'symbol': 'AAPL',
            'action': 'BUY',
            'quantity': 100,
            'price': 150.00,
            'date': '2025-01-15',
            'account': 'U19490886'
        }
    ])
    mock_client.get_enhanced_tax_lots = AsyncMock(return_value=[
        {
            'lot_id': 'lot_123',
            'symbol': 'AAPL',
            'quantity': 100,
            'cost_per_share': 150.00,
            'acquisition_date': '2025-01-15',
            'account_id': 'U19490886'
        }
    ])
    return mock_client

@pytest.fixture
def mock_tastytrade_client():
    """Mock TastyTrade client for testing."""
    mock_client = Mock()
    mock_client.authenticate = AsyncMock(return_value=True)
    mock_client.get_positions = AsyncMock(return_value=[
        {
            'symbol': 'AAPL',
            'quantity': 100,
            'average_price': 150.00,
            'market_value': 15200.00,
            'unrealized_pnl': 200.00
        }
    ])
    return mock_client

@pytest.fixture
def mock_market_data_service():
    """Mock market data service for testing."""
    mock_service = Mock()
    mock_service.get_current_price = AsyncMock(return_value=152.00)
    mock_service.get_stock_info = AsyncMock(return_value={
        'sector': 'Technology',
        'market_cap': 2500000000000,
        'pe_ratio': 25.5
    })
    mock_service.get_ohlc_data = AsyncMock(return_value=pd.DataFrame({
        'open': [150.0, 151.0], 
        'high': [152.0, 153.0],
        'low': [149.0, 150.0],
        'close': [151.0, 152.0]
    }))
    return mock_service

@pytest.fixture
def sample_csv_data():
    """Sample IBKR CSV data for testing."""
    return """Date,Time,Symbol,Action,Quantity,Price,Amount,Commission,Currency
2025-01-15,10:30:00,AAPL,BUY,100,150.00,15000.00,1.00,USD
2025-01-16,14:20:00,MSFT,BUY,50,300.00,15000.00,1.00,USD
2025-01-17,11:45:00,NVDA,SELL,25,800.00,20000.00,1.50,USD"""

@pytest.fixture
def sample_strategy_config():
    """Sample strategy configuration for testing."""
    return {
        'strategy_type': StrategyType.ATR_OPTIONS,
        'capital': 10000.0,
        'profit_target': 0.20,
        'stop_loss': 0.05,
        'reinvest_percentage': 0.80,
        'max_position_size': 0.10,
        'risk_per_trade': 0.02
    }

# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Coverage markers
pytest_plugins = ["pytest_asyncio"] 