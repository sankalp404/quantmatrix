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

Safe Patterns (Enforced)
------------------------
- Single DB path: all tests must use the `db_session` fixture. Direct `SessionLocal`/`engine`/`create_engine` imports in tests are blocked.
- Destructive tests: must be marked `@pytest.mark.destructive` and only run with `ALLOW_DESTRUCTIVE_TESTS=1` or `--allow-destructive-tests`.
- Schema guard: DB tests skip if core tables (e.g., `users`, `broker_accounts`) are missing in the test DB.
- Misconfig guard: DB tests skip if `TEST_DATABASE_URL` is unset or equals `DATABASE_URL`.
- Alembic: test migrations run only against `TEST_DATABASE_URL`.

Env Guidance
------------
- Leave production `.env` untouched.
- For pytest/CI, load a test-safe env (e.g., `.env.test`) that sets:
  - `TEST_DATABASE_URL=postgresql://quantmatrix:quantmatrix@postgres:5432/quantmatrix_test`
  - Optionally set `DATABASE_URL` to a throwaway dev DB when running tests locally; avoid pointing to prod.
- Docker Compose runtime can continue using `.env`; test jobs should override with `.env.test` or exported vars.

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

