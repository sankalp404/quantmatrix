High-priority TODO
==================

- Finalize single initial Alembic migration and apply; drop old revisions
- Remove all hardcoding: FlexQuery token/query id now only via settings (done)
- Trigger TT + IBKR sync; verify trades/transactions/dividends/balances populate
- Price refresh: POST /api/v1/market-data/prices/refresh on portfolio pages
- Options activity panel: use trades to show acquisition/close lifecycle
- Docs: completed canonicalization under docs/; keep STATUS.md updated on merges
- Schwab: OAuth app wiring; basic client + sync service; env: SCHWAB_* vars
- Tests: expand suites per TEST_PLAN.md; mark integration tests; CI recipe
- Add model uniqueness tests (Trade, Transaction, Option) [added]
  - Add API smoke tests (health, accounts, portfolio live, statements) [added]
  - Add market data service unit tests; ensure no hardcoded symbols/tokens
  - Add options activity panel tests (lifecycle mapping from trades)
  - Configure CI (pytest -q, ruff check, black --check, alembic upgrade head)

- Market Data
  - Verify no hardcoded tokens/symbols/providers; only via `settings`
  - Unit tests for price fetch fallbacks and error handling
  - Implement STRICT Weinstein Stage Analysis (weekly): 30W SMA, RS vs SPY slope, volume 50W ratio [in progress]
  - Persist technicals in `market_technicals` (alembic migration): symbol, timeframe, sma30w, slopes, rs, vol_ratio, stage
  - Nightly refresh job; enrich `/api/v1/portfolio/live` and stocks UI with `stage_weinstein`

- Portfolio/frontend
  - Stocks: add Stage/RS badges; column toggle for Stage (1–4); filter by Stage 2.
  - Options: surface lifecycle panel (acquire/close) from Trades; P/L backed by market data refresh.
  - Dashboard: add Stage distribution and Leading/Lagging counts.
- Naming cleanup: avoid the word "holdings" across API/frontend. Use "stocks" and "options" consistently.
  - Renamed: `/portfolio/holdings/stocks-only` → `/portfolio/stocks` (and `/stocks/{id}/tax-lots`)
  - Options moved under `/portfolio/options/*` (accounts, unified portfolio/summary)

Big Next Steps
==============

Migrations & Schema
-------------------
- Generate and apply initial migration reflecting current models, including:
  - `options` table (class Option) with unique constraint
  - `tax_lots` as source of cost basis
  - Equity-only `positions` (drop option-only columns)
  - Indices for performance per models/__init__.py

Market Data (Weinstein)
-----------------------
- Implement `market_technicals` table with weekly Weinstein metrics
- Batch endpoints:
  - POST `/api/v1/market-data/technical/stage/batch` { symbols[], benchmark }
  - GET `/api/v1/market-data/technical/stage/scan?stage=STAGE_2_UPTREND&universe=SP500`
- Caching & nightly refresh jobs

Broker Sync
-----------
- TastyTrade: ensure trades/transactions/dividends/balances populated; dedupe via constraints; expand history window
- IBKR: FlexQuery stability; TransactionSyncStatus writes; fallback to TWS for option positions if needed
- Add Schwab scaffolding (OAuth flow) and account seeding via env `SCHWAB_ACCOUNTS`

APIs & Frontend
---------------
- Enrich `/api/v1/portfolio/live` and `/api/v1/portfolio/stocks` with stage/RS
- Options activity panel mapping Trade lifecycle → acquisitions/closes
- Portfolio summary bar: Portfolio Value / Unrealized P&L using `/portfolio/live` by `account_id`

Strategies & Automation
-----------------------
- Add Stage 2 entry filter to strategy manager; combine with ATR sizing and MA buckets
- Execute-only via live connections; backend does analysis and readiness checks

Tests & CI
----------
- Expand endpoint tests (added): stocks/options/market-data/portfolio
- Unit tests: market_technicals calculations (weekly resample, 30W SMA slope, RS slope, volume ratio)
- Integration: TT & IBKR minimal sync flows (marked)
- CI: run ruff, black --check, pytest -q, alembic upgrade head

Docs & Cleanup
--------------
- Keep docs updated on merges: ARCHITECTURE, MODELS, ROADMAP, STATUS, TESTS
- Ensure no hardcoding; env-driven settings everywhere
- Continue removing legacy files, consolidate routes under `portfolio_*` naming

