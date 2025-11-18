Testing Strategy
================

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

