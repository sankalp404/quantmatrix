"""
Test configuration for QuantMatrix backend tests.
"""

import pytest
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fix imports to use correct model names from __init__.py
try:
    from backend.models import User, BrokerAccount, Instrument  # Fixed imports
    from backend.database import SessionLocal, engine, Base

    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.fixture(scope="session")
def test_db():
    """Create a test database session."""
    if not MODELS_AVAILABLE:
        pytest.skip(
            f"Models not available: {IMPORT_ERROR if not MODELS_AVAILABLE else ''}"
        )

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Create a database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")

    return User(username="testuser", email="test@example.com", full_name="Test User")
