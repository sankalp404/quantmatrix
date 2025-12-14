"""
QuantMatrix V1 - Database Configuration
======================================

Central database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from typing import Generator

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://quantmatrix:quantmatrix@localhost:5432/quantmatrix"
)

APP_DATABASE_URL = DATABASE_URL

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=300,
)

# Raw factory kept private; SessionLocal wrapper enforces test safety in pytest
_RAW_SESSION_FACTORY = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _assert_test_db_guard():
    """Abort if pytest tries to use the app database.

    Rules:
    - If running under pytest (PYTEST_CURRENT_TEST or QUANTMATRIX_TESTING), require TEST_DATABASE_URL.
    - If TEST_DATABASE_URL equals APP_DATABASE_URL, abort.
    """
    is_testing = bool(
        os.getenv("PYTEST_CURRENT_TEST") or os.getenv("QUANTMATRIX_TESTING")
    )
    if not is_testing:
        return
    test_db_url = os.getenv("TEST_DATABASE_URL", "")
    if not test_db_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required for tests; refusing to use APP_DATABASE_URL"
        )
    if test_db_url == APP_DATABASE_URL:
        raise RuntimeError(
            "TEST_DATABASE_URL equals APP_DATABASE_URL; aborting to avoid destructive operations"
        )


def SessionLocal():
    """Guarded session factory. In tests, refuses to hit the app DB."""
    _assert_test_db_guard()
    return _RAW_SESSION_FACTORY()

# Base class for all models (re-export from models)
from backend.models import Base


# Dependency for getting database sessions
def get_db() -> Generator:
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Direct session creation for scripts
def create_session():
    """Create a database session for scripts and services."""
    return SessionLocal()


# Database initialization
def init_db():
    """Initialize database.

    Production/dev: rely on Alembic migrations exclusively.
    Tests: table lifecycle is handled in backend/tests/conftest.py against TEST_DATABASE_URL.
    """
    # No-op intentionally to avoid schema drift; migrations run on startup.
    return


# Health check
def check_db_health() -> bool:
    """Check if database is accessible."""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False
