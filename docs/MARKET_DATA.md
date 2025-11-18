# Market Data Ingest and Storage Strategy

## Goals
- Centralize market data access via `backend/services/market/market_data_service.py`
- Provide reliable indicators for last 200 trading days for: SPY, NASDAQ 100, Dow 30, and all held symbols (Russell 2000 roadmap)
- Persist lightweight, query-friendly snapshots when needed; avoid over-storing raw API payloads
- Schedule refreshes and cache to keep API usage efficient

## Scope and Sources
- OHLCV only from providers; ALL indicators computed locally from stored OHLCV
- Provider priority (paid mode): FMP → Twelve Data → yfinance; (free mode): Finnhub → Twelve Data → yfinance
- Redis cache for transient responses and computed indicators

## Data We Compute/Serve (indicator_engine)
For each symbol:
- RSI(14)
- SMA(5/8/21/20/50/100/200), EMA(10/8/21/200)
- ATR(14), ATR percent, ATR distance to SMA50
- ADX(14), DI+, DI-
- MACD(12,26,9), signal line
- Performance: 1d, 3d, 5d, 20d, 60d, 120d, 252d, MTD, QTD, YTD
- MA alignment flags, MA bucket (LEADING/LAGGING/NEUTRAL)
- Classification: sector, industry, sub-industry (best-effort)

Responsibilities by layer
-------------------------
- indicator_engine.py: Pure computations from OHLCV (SMA/EMA/RSI/ATR/MACD/ADX, perf windows, MA bucket, TD/gaps/trendlines, weekly stage helpers).
- market_data_service.py: Provider access (prices/history/info), Redis caching, DB snapshot assembly from local `price_data`, enrichment (chart metrics + fundamentals), and persistence to `MarketAnalysisCache`.
- market_data_tasks.py: Orchestration only. Builds tracked sets, backfills OHLCV, invokes service to build/enrich/persist snapshots, and records daily history.

## Persistence Model
- `market_data.PriceData`: daily/intraday OHLCV with unique `(symbol, date, interval)` (constraint: `uq_symbol_date_interval`)
- `market_data.MarketAnalysisCache`: compact latest technical snapshot per symbol with expiry (`expiry_timestamp`), including `ma_bucket`
  - Includes persisted stage fields: `stage_label`, `stage_slope_pct`, `stage_dist_pct`
- `market_data.MarketAnalysisHistory`: immutable daily snapshots keyed by `(symbol, analysis_type, as_of_date)`

## Scheduling
- Weekly constituents refresh (SP500, NASDAQ100, DOW30) → table `index_constituents`
- Nightly tracked-universe cache build (Redis: `tracked:all`, `tracked:new`)
- Nightly backfill for newly tracked symbols only (reads `tracked:new`)
- Nightly delta backfill safety for portfolio symbols (last-200)
- Nightly recompute indicators for full universe (from local `price_data`)
- Nightly history recording (`market_analysis_history`)

Paid mode operations
--------------------
- Ensure provider policy is set to paid (default): `MARKET_PROVIDER_POLICY=paid`
- Configure API keys in `.env`: `FMP_API_KEY`, `TWELVE_DATA_API_KEY`, `FINNHUB_API_KEY`
- To force ingestion now (admin flow):
  - Refresh constituents: POST `/api/v1/market-data/admin/backfill/index?index=SP500`
  - Backfill index OHLCV: POST `/api/v1/market-data/admin/backfill/index` (SP500/NASDAQ100/DOW30)
  - Refresh portfolio indicators: Celery task `refresh_portfolio_indicators`
  - Refresh index indicators: POST `/api/v1/market-data/admin/indicators/refresh-index`
  - Record history: POST `/api/v1/market-data/admin/history/record`
  - Compute chart metrics for an index: scheduled via Celery (`chart-metrics-sp500`) or call task `compute_chart_metrics_index`
  - Compute chart metrics for the universe: scheduled via Celery 

Notes on retention
------------------
- Default OHLCV backfill keeps ~270 recent daily bars to support SMA(200) and 252d windows quickly.
- For deeper history, call provider directly via service or extend tasks to multi-year fetch using FMP `historical_price_full`.

## API Contracts
- `GET /api/v1/market/prices?symbol=SPY&range=200d&interval=1d`: returns OHLCV
- `GET /api/v1/market/atr?symbol=SPY`: ATR and volatility regime
- `GET /api/v1/market/ta?symbol=SPY`: RSI, MAs, MACD, ADX, performance windows

## Index Constituents
- `backend/services/market/index_constituents_service.py` fetches SP500, NASDAQ100, DOW30 (R2K roadmap)
- Persisted in DB: `backend/models/index_constituent.py` with `is_active`, `first_seen_at`, `became_inactive_at`
- We do not drop symbols that leave an index; they are marked inactive and remain tracked

## Notes
- Provider selection is adaptive; when keys exist, paid providers take precedence
- Avoid duplicating raw provider payloads; store normalized OHLCV + compact snapshots

## End-to-End Indicator Pipeline
1) Fetch historical data
   - Source order: FMP → Twelve Data → yfinance (fallbacks) with adaptive rate limiting (free mode uses Finnhub first)
   - Cached in Redis per `(symbol, period, interval)`
2) Compute indicators (indicator_engine)
   - Core set: RSI, ATR, SMA/EMA, MACD+signal, ADX/DI, performance windows, MA alignment, ATR-matrix metrics
3) Build snapshot
   - Prefer local DB: `MarketDataService.build_snapshot_from_db_prices(db, symbol)`
   - Fallback: `MarketDataService.build_indicator_snapshot(symbol)` (pull OHLCV then compute)
   - Enrich: `MarketDataService.enrich_chart_metrics_and_fundamentals(db, symbol, snapshot)` adds TD/gaps/trendlines + best-effort sector/industry/market_cap
4) Persist snapshot
   - `MarketDataService.persist_snapshot(db, symbol, snapshot)` upserts latest into `MarketAnalysisCache` and stores `raw_analysis`
5) History recording (optional)
   - `record_daily_history` writes one row per `(symbol, as_of_date)` into `MarketAnalysisHistory` with headline fields + full payload
6) Scheduling
   - Celery Beat triggers:
     - weekly index refresh → `refresh_index_constituents`
     - nightly tracked set build → `update_tracked_symbol_cache`
     - nightly backfill of new tracked symbols → `backfill_new_tracked`
     - nightly delta backfill safety → `backfill_last_200_bars`
     - nightly universe indicators recompute → `recompute_indicators_universe`
     - nightly history write → `record_daily_history`
