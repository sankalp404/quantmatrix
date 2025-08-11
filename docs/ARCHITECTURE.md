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
- IBKR FlexQuery: official history (trades, transactions, dividends, tax lots)
- IBKR TWS/Gateway: live positions/quotes and order routing
- TastyTrade SDK: accounts, positions, history via credentials

Data Flow
---------
1) Startup seeds default user and broker accounts (from .env, plus TT autodiscovery)
2) Sync services populate tables (positions, options, trades, transactions, dividends)
3) Market data refresh updates prices and P&L
4) Frontend renders via server-side filtered APIs

Security
--------
- Env-only secrets; JWT planned for user auth; scoped tokens for prod

