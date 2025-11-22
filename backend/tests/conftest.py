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
    from sqlalchemy import inspect
    from sqlalchemy.exc import ProgrammingError
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    IMPORT_ERROR = str(e)


@pytest.fixture(scope="session")
def test_db(request):
    """Create an isolated test database engine and metadata.

    Safety:
    - Requires TEST_DATABASE_URL. If missing, skip DB tests.
    - Refuses to run if TEST_DATABASE_URL == app DATABASE_URL.
    - Never drops/creates tables on the app engine.
    """
    if not MODELS_AVAILABLE:
        pytest.skip(
            f"Models not available: {IMPORT_ERROR if not MODELS_AVAILABLE else ''}"
        )

    # Skip DB setup entirely for no_db-marked test sessions
    if request.node.get_closest_marker("no_db"):
        yield None
        return

    import os
    from sqlalchemy import create_engine
    from backend.database import DATABASE_URL as APP_DATABASE_URL
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command

    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL not set; skipping DB tests to protect development database"
        )
    if TEST_DATABASE_URL == APP_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL equals app DATABASE_URL; aborting to avoid destructive operations"
        )

    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    # Run Alembic migrations on the test database
    cfg = AlembicConfig(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    # script_location must point to backend/alembic
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    # override URL to TEST DB
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    alembic_command.upgrade(cfg, "head")

    try:
        yield test_engine
    finally:
        # Schema remains for session; per-test transactions provide isolation
        pass


@pytest.fixture
def db_session(test_db, request):
    """Session per test with transaction + nested savepoint, rolls back after test."""
    if request.node.get_closest_marker("no_db"):
        yield None
        return
    if test_db is None:
        # Session-scoped fixture opted out of DB; provide None for this test
        yield None
        return
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import event
    connection = test_db.connect()
    transaction = connection.begin()
    SessionForTests = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionForTests()
    # Start a SAVEPOINT so code under test can call session.commit safely
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        # When the nested transaction ends, open a new one
        if trans.nested and not getattr(trans._parent, "nested", False):  # type: ignore[attr-defined]
            sess.begin_nested()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _no_global_cleanup_marker():
    """No-op cleanup; isolation handled via transaction per test."""
    yield


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")

    return User(username="testuser", email="test@example.com", full_name="Test User")
