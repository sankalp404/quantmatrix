"""
Test configuration for QuantMatrix backend tests.
"""

import pytest
import sys
import os


@pytest.fixture(autouse=True, scope="session")
def _enable_fast_test_mode():
    """Ensure code runs in fast test mode across the suite."""
    os.environ["QUANTMATRIX_TESTING"] = "1"
    yield
    os.environ.pop("QUANTMATRIX_TESTING", None)


# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fix imports to use correct model names from __init__.py
try:
    from backend.models import User, BrokerAccount, Instrument  # Fixed imports
    from backend.database import SessionLocal, engine, Base
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError

    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.fixture(scope="session")
def test_db(request):
    """Create a test database session."""
    if not MODELS_AVAILABLE:
        pytest.skip(
            f"Models not available: {IMPORT_ERROR if not MODELS_AVAILABLE else ''}"
        )

    # Skip DB setup entirely for no_db-marked test sessions
    if request.node.get_closest_marker("no_db"):
        yield None
        return

    # Create tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db, request):
    """Create a database session for testing."""
    if request.node.get_closest_marker("no_db"):
        yield None
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_db_before_each_test(test_db, request):
    """Ensure a clean slate before each test to avoid unique constraint conflicts."""
    if request.node.get_closest_marker("no_db"):
        yield
        return
    session = SessionLocal()
    try:
        # Delete data from all tables in reverse dependency order, if they exist
        insp = inspect(engine)
        for table in reversed(Base.metadata.sorted_tables):
            try:
                if insp.has_table(table.name):
                    session.execute(table.delete())
            except ProgrammingError:
                # Table or dependent types might not exist yet; skip
                session.rollback()
                continue
        session.commit()
        yield
    finally:
        session.close()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")

    return User(username="testuser", email="test@example.com", full_name="Test User")
