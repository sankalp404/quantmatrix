Testing Strategy
================

Test Database Isolation (Backend)
---------------------------------
- Set `TEST_DATABASE_URL` to a separate Postgres database (not equal to `DATABASE_URL`).
- The test suite will:
  - Run Alembic migrations to head on the test database at session start.
  - Create a per-test transaction and roll it back after each test for isolation.
- Example (Docker):
  - Export `TEST_DATABASE_URL` in your shell or `.env`.
  - Run: `./run.sh test`

Do/Don't
--------
- Do: use the `db_session` fixture provided in `backend/tests/conftest.py`.
- Do: assume Alembic has upgraded the test DB to head before tests run.
- Don’t: call `init_db()` or instantiate `SessionLocal()` directly in tests.
- Don’t: rely on app `DATABASE_URL`; all DB tests must run on `TEST_DATABASE_URL`.

Goals
-----
- Fast unit tests for services and clients
- Focused integration tests for brokers and market data
- Smoke tests for API routes

How to run
----------
- docker-compose exec backend pytest -q
- Single file: docker-compose exec backend pytest backend/tests/test_client_tastytrade.py -q

Scopes
------
- Unit: deterministic logic (parsers, transforms, dedupe)
- Integration (flagged): real broker/market API using env credentials
- API: minimal happy-path per route

Conventions
-----------
- Read secrets from env (never hardcode account numbers)
- Mark networked tests with @pytest.mark.integration
- Use AsyncMock/patch for SDKs in unit tests

