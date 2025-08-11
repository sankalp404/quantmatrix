Test Plan
=========

Pyramids
--------
- Unit: fast, pure logic (parsers, transforms, dedupe)
- Integration: broker SDKs/APIs via env; FlexQuery XML fixtures; DB interactions
- API smoke: minimal happy paths per route

Suites
------
- models/: uniqueness, FKs, invariants
- services/clients/:
  - ibkr_client: mock ib_insync; connection, positions, error handling
  - ibkr_flexquery_client: mock aiohttp; XML fixtures parsing; throttling backoff
  - tastytrade_client: mock tastytrade SDK; accounts/positions/history transforms
  - schwab_client: placeholder; wire up once OAuth ready
- services/portfolio/:
  - account_config_service: seeding from env; idempotency
  - broker_sync_service: routing; sync status updates; errors
  - ibkr_sync_service: flex + live merge; snapshots; cash txns
  - tastytrade_sync_service: dedupe, options positions, trades/txns/dividends
- api/: holdings, options, live, statements, dividends; SSR filters and shapes

Conventions
-----------
- pytest markers: @pytest.mark.integration for networked tests
- Env-driven secrets; never hardcode account numbers
- Run: `docker-compose exec backend pytest -q` or per-file

