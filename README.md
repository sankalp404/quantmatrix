QuantMatrix
===========

Monorepo for the QuantMatrix trading platform.

- Backend: FastAPI + SQLAlchemy + Alembic (Docker)
- Frontend: React + Vite + Chakra UI (Docker)
- DB: Postgres + Redis

Quick Start
-----------
- docker-compose up -d --build
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000

Migrations
----------
- docker-compose exec backend alembic revision -m "message" --autogenerate
- docker-compose exec backend alembic upgrade head

Docs
----
- Canonical docs live under `docs/`:
  - Architecture: `docs/ARCHITECTURE.md`
  - Models: `docs/MODELS.md`
  - Tests: `docs/TESTS.md`, `docs/TEST_PLAN.md`
  - Roadmap/Status: `docs/ROADMAP.md`, `docs/STATUS.md`
  - Brokers: `docs/BROKERS.md`
  - TODOs: `docs/TODO.md`

API Map (v1)
------------
- Portfolio:
  - Live: `/api/v1/portfolio/live`
  - Stocks: `/api/v1/portfolio/stocks`, `/api/v1/portfolio/stocks/{position_id}/tax-lots`
  - Options: `/api/v1/portfolio/options/accounts`, `/api/v1/portfolio/options/unified/portfolio`, `/api/v1/portfolio/options/unified/summary`
  - Statements: `/api/v1/portfolio/statements`
  - Dividends: `/api/v1/portfolio/dividends`
- Market Data:
  - Refresh prices: `POST /api/v1/market-data/prices/refresh`
  - Technicals: `GET /api/v1/market-data/technical/moving-averages/{symbol}`
  - MA bucket: `GET /api/v1/market-data/technical/ma-bucket/{symbol}`
  - Stage (Weinstein): `GET /api/v1/market-data/technical/stage/{symbol}`

Naming
------
- Position = equities (stocks/ETFs)
- Option = option contracts (per-contract state)
- Avoid “holdings” in routes and UI; use “stocks” and “options” consistently

