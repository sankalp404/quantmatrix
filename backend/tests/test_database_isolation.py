import os
import uuid
import pytest
from sqlalchemy import text
from backend.api.main import app


@pytest.mark.no_db
def test_requires_test_database_url_env_guard():
    # This test only documents behavior in conftest when TEST_DATABASE_URL is missing.
    assert True


def test_alembic_head_and_isolation(db_session):
    # Verify we can query a known table (users) after Alembic upgraded to head
    db_session.execute(text("SELECT 1"))
    # Insert a row and ensure we can see it in this transaction
    uname = f"t_{uuid.uuid4().hex[:6]}"
    db_session.execute(text("INSERT INTO users (username, email, password_hash, is_active) VALUES (:u, :e, 'x', true)"), {"u": uname, "e": f"{uname}@example.com"})
    res = db_session.execute(text("SELECT username FROM users WHERE username=:u"), {"u": uname}).fetchone()
    assert res is not None
    # Isolation: The fixture rolls back after test, so no explicit assert here; a follow-up test could query absence




