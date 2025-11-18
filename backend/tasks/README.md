QuantMatrix Market Data Tasks
=============================

Purpose
-------
End-to-end market data pipeline built around a simple, scalable principle: fetch and store OHLCV once (PriceData), compute everything else locally and deterministically (indicators, chart metrics, history) from the database. No internet calls for metrics, ever.

Task Inventory
--------------
Backfill (writes `price_data`)
- backfill_index_universe(batch_size=20): Fetch daily OHLCV for SP500/NASDAQ100/DOW30 (batched; delta-only).
- backfill_last_200_bars(): Fetch daily OHLCV for portfolio-held symbols (delta-only).

Indicators (writes `market_analysis_cache`)
- recompute_indicators_universe(batch_size=50): Consolidated compute for indices + portfolio from PriceData. Fills all core indicators (RSI, SMA/EMA, MACD, ATR, perf windows, MA bucket, distances) and chart metrics (TD counts, gaps, trendlines) in one pass.

Constituents (DB + cache)
- refresh_index_constituents(): Persist SP500/NASDAQ100/DOW30 to `index_constituents`, track `is_active`/first/last seen.
- update_tracked_symbol_cache(): Build Redis `tracked:all` and `tracked:new` from DB (index_constituents ∪ portfolio).
- backfill_new_tracked(): Backfill only newly tracked symbols from Redis `tracked:new`, then clear it.

History (writes `market_analysis_history`)
- record_daily_history(symbols=None): Persist immutable daily snapshots (denormalized heads + full payload). Defaults to portfolio symbols.

Schedules (Celery Beat)
-----------------------
Configured in `backend/tasks/celery_app.py` (UTC):
- weekly-refresh-index-constituents: weekly Sunday morning
- update-tracked-symbol-cache: nightly build tracked set + delta list
- backfill-new-tracked: nightly backfill of only additions
- backfill-last-200: nightly safety backfill for portfolio
- recompute-indicators-universe: nightly consolidated indicators + chart metrics
- record-daily-history: after close
- ibkr-daily-flex-sync: nightly comprehensive FlexQuery sync

Runbooks
--------
Bootstrap (full universe)
1) `backfill_index_universe.delay(batch_size=30)` (10–20m)
2) `backfill_last_200_bars.delay()` (1–3m)
3) `recompute_indicators_universe.delay(batch_size=60)` (fast; local-only)
4) `record_daily_history.delay()` (optional)

Daily manual refresh
- `recompute_indicators_universe.delay(batch_size=60)`
- Optional: `record_daily_history.delay(symbols=[...])`

Notes & Troubleshooting
-----------------------
- Providers: prefer FMP/TwelveData; fallback yfinance. Cache in Redis; compute locally from `price_data`.
- Retention: ~270 daily bars support SMA200/252d windows; increase if needed.
- Worker offline or tasks pending: check `docker compose logs celery_worker`, verify includes, restart worker/beat; requeue tasks.
