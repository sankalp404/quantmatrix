Architecture Overview
=====================

Components
----------
- Backend: FastAPI service exposing REST endpoints
- DB: Postgres (state) + Redis (cache/queue)
- Frontend: React SPA consuming backend APIs
- Brokers: IBKR (FlexQuery + TWS) and TastyTrade (SDK)

Broker Data Strategy
--------------------
- IBKR FlexQuery (system of record): trades, cash transactions (dividends/fees/taxes), tax lots (cost basis), account balances, margin interest, transfers, options (open + historical exercises). Persist into `trades`, `transactions`, `dividends`, `tax_lots`, `account_balances`, `margin_interest`, `transfers`, `options`.
- Implementation status: FlexQuery single-report fetch with cached XML; tax lots, options (positions + exercises), trades are parsed and persisted. Cash transactions (incl. dividends), account balances, margin interest, and transfers are now implemented and persisted. Celery task `sync_all_ibkr_accounts` can enqueue comprehensive syncs for all enabled IBKR accounts. Configure long history via `IBKR_FLEX_LOOKBACK_YEARS` in `.env` and FlexQuery template.
- IBKR TWS/Gateway (live overlay): intraday prices/positions, managed accounts discovery, account summary. Do not overwrite official cost basis; only update live prices/market values.
- TastyTrade SDK: discovery + positions/trades/transactions/dividends/balances via credentials. No hardcoded account numbers; env/secure storage only.

Data Flow
---------
1) Startup: create tables; optional account seeding (env-driven only).
2) Sync: FlexQuery comprehensive sync writes authoritative rows; live overlay updates prices/positions only.
3) Market data: provider-prioritized OHLCV fetch (FMP→TwelveData→yfinance), Redis caching, local indicator compute (pandas/numpy), snapshot persistence, scheduled backfills and history.
4) API: backend serves portfolio endpoints; frontend is read-only except trade execution paths.

Security
--------
- Env-only secrets; JWT planned for user auth; scoped tokens for prod

