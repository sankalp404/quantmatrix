from __future__ import annotations

"""Market data task suite

Sections:
- Backfill: populate `price_data` with recent daily OHLCV (delta-only)
- Indicators: compute and persist `MarketSnapshot` for symbols
- History: write immutable daily `MarketAnalysisHistory`
- Chart metrics: TD Sequential, gaps and trendlines enrichment

All tasks are safe to run repeatedly (idempotent writes; ON CONFLICT for bars).
"""

from celery import shared_task
import asyncio
from datetime import datetime
from typing import List, Set

from backend.database import SessionLocal
from backend.models import PriceData
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.models.market_data import MarketSnapshotHistory, MarketSnapshot
from backend.models import IndexConstituent
from backend.services.market.market_data_service import market_data_service
from backend.models import Position
from backend.config import settings

import json
# ============================= Single-Symbol Refresh =============================


@shared_task(name="backend.tasks.market_data_tasks.refresh_single_symbol")
def refresh_single_symbol(symbol: str) -> dict:
    """Delta backfill and recompute indicators for a single symbol (DB-first, no provider TA).

    Steps:
    - Backfill last ~200 bars for symbol (delta-only inserts)
    - Recompute indicators from local DB and persist snapshot
    """
    if not symbol:
        return {"status": "error", "error": "symbol required"}
    sym = str(symbol).upper()
    _set_task_status("refresh_single_symbol", "running", {"symbol": sym})
    session = SessionLocal()
    try:
        # Backfill (delta-only)
        backfill_symbols([sym])
        # Recompute from DB
        snap = market_data_service.compute_snapshot_from_db(session, sym)
        if snap:
            market_data_service.persist_snapshot(session, sym, snap)
            res = {"status": "ok", "symbol": sym, "recomputed": True}
        else:
            res = {"status": "ok", "symbol": sym, "recomputed": False}
        _set_task_status("refresh_single_symbol", "ok", res)
        return res
    finally:
        session.close()


# ============================= Index Fundamentals Enrichment =============================


@shared_task(name="backend.tasks.market_data_tasks.enrich_index_fundamentals")
def enrich_index_fundamentals(indices: List[str] | None = None, limit_per_run: int = 500) -> dict:
    """Fill sector/industry/market_cap on IndexConstituent using DB-first snapshots.

    - Reads latest MarketSnapshot for a symbol; if missing, computes snapshot from DB
    - Only if still missing, fetch fundamentals via providers (FMP/yfinance fallback)
    - Updates IndexConstituent rows with any available fundamentals
    """
    _set_task_status("enrich_index_fundamentals", "running")
    session = SessionLocal()
    try:
        q = session.query(IndexConstituent)
        if indices:
            q = q.filter(IndexConstituent.index_name.in_([i.upper() for i in indices]))
        # Prefer rows missing any of the fields
        rows = (
            q.filter(
                (IndexConstituent.sector.is_(None))
                | (IndexConstituent.industry.is_(None))
                | (IndexConstituent.market_cap.is_(None))
            )
            .order_by(IndexConstituent.symbol.asc())
            .limit(limit_per_run)
            .all()
        )
        updated = 0
        for r in rows:
            sym = (r.symbol or "").upper()
            if not sym:
                continue
            # Use snapshot if present; else compute from DB (fast)
            snap = market_data_service.get_snapshot_from_store(session, sym)
            if not snap:
                snap = market_data_service.compute_snapshot_from_db(session, sym)
            # If still missing, compute from providers (slow path) but only for fundamentals
            if not snap or (snap.get("sector") is None and snap.get("industry") is None and snap.get("market_cap") is None):
                try:
                    # Reuse provider fundamentals logic by triggering provider snapshot compute
                    # but we won't persist unless needed downstream
                    import asyncio as _aio
                    loop = _aio.new_event_loop()
                    _aio.set_event_loop(loop)
                    prov = loop.run_until_complete(market_data_service.compute_snapshot_from_providers(sym))
                    if prov:
                        for k in ("sector", "industry", "market_cap"):
                            if prov.get(k) is not None:
                                snap = snap or {}
                                snap[k] = prov.get(k)
                except Exception:
                    pass
            if not snap:
                continue
            changed = False
            if r.sector is None and snap.get("sector") is not None:
                r.sector = snap.get("sector")
                changed = True
            if r.industry is None and snap.get("industry") is not None:
                r.industry = snap.get("industry")
                changed = True
            if r.market_cap is None and snap.get("market_cap") is not None:
                try:
                    r.market_cap = int(snap.get("market_cap"))
                except Exception:
                    pass
                else:
                    changed = True
            if changed:
                updated += 1
        if updated:
            session.commit()
        res = {"status": "ok", "inspected": len(rows), "updated": updated}
        _set_task_status("enrich_index_fundamentals", "ok", res)
        return res
    finally:
        session.close()


# ============================= Snapshot Fundamentals Backfill =============================


@shared_task(name="backend.tasks.market_data_tasks.fill_missing_snapshot_fundamentals")
def fill_missing_snapshot_fundamentals(limit_per_run: int = 500) -> dict:
    """Fill missing sector/industry/market_cap on MarketSnapshot rows.

    DB-first: try compute_snapshot_from_db; if still missing, fallback to providers.
    Persists updated snapshot via market_data_service.persist_snapshot.
    """
    _set_task_status("fill_missing_snapshot_fundamentals", "running")
    session = SessionLocal()
    try:
        from backend.models.market_data import MarketSnapshot as _MS

        rows = (
            session.query(_MS)
            .filter(
                _MS.analysis_type == "technical_snapshot",
                (
                    (_MS.sector.is_(None))
                    | (_MS.industry.is_(None))
                    | (_MS.market_cap.is_(None))
                ),
            )
            .order_by(_MS.analysis_timestamp.desc())
            .limit(limit_per_run)
            .all()
        )
        updated = 0
        for r in rows:
            sym = (r.symbol or "").upper()
            if not sym:
                continue
            # Build from DB first (no external calls)
            snap = market_data_service.compute_snapshot_from_db(session, sym)
            # If fundamentals still missing, fetch fundamentals only (FMP-first, no price fetch)
            needs_funda = (
                not snap
                or (
                    snap.get("name") is None
                    and snap.get("sector") is None
                    and snap.get("industry") is None
                    and snap.get("sub_industry") is None
                    and snap.get("market_cap") is None
                )
            )
            if needs_funda:
                funda = market_data_service.get_fundamentals_info(sym)
                if funda:
                    snap = snap or {}
                    for k in ("name", "sector", "industry", "sub_industry", "market_cap"):
                        if funda.get(k) is not None:
                            snap[k] = funda.get(k)
            if not snap:
                continue
            # Persist only if something new available
            if (
                (getattr(r, "name", None) is None and snap.get("name") is not None)
                or (r.sector is None and snap.get("sector") is not None)
                or (r.industry is None and snap.get("industry") is not None)
                or (getattr(r, "sub_industry", None) is None and snap.get("sub_industry") is not None)
                or (r.market_cap is None and snap.get("market_cap") is not None)
            ):
                market_data_service.persist_snapshot(session, sym, {**(r.raw_analysis or {}), **snap})
                updated += 1
        res = {"status": "ok", "inspected": len(rows), "updated": updated}
        _set_task_status("fill_missing_snapshot_fundamentals", "ok", res)
        return res
    finally:
        session.close()

async def _get_tracked_symbols(db) -> Set[str]:
    """Universe helper: portfolio-held symbols only (distinct, non-null)."""
    symbols: Set[str] = set()
    for (symbol,) in db.query(Position.symbol).distinct():
        if symbol:
            symbols.add(symbol)
    return symbols


# ============================= Task Status Helper =============================


def _set_task_status(task_name: str, status: str, payload: dict | None = None) -> None:
    try:
        r = market_data_service.redis_client
        r.set(
            f"taskstatus:{task_name}:last",
            json.dumps(
                {
                    "task": task_name,
                    "status": status,
                    "ts": datetime.utcnow().isoformat(),
                    "payload": payload or {},
                }
            ),
        )
    except Exception:
        pass


# ============================= Tracked Universe Cache =============================


def _get_tracked_universe_from_db(session: SessionLocal) -> set[str]:
    """Union of all seen index constituents (active or inactive) and portfolio symbols."""
    tracked: set[str] = set()
    # Index constituents table, if present
    try:
        for (sym,) in session.query(IndexConstituent.symbol).distinct():
            if sym:
                tracked.add(sym.upper())
    except Exception:
        pass
    # Portfolio symbols
    for (sym,) in session.query(Position.symbol).distinct():
        if sym:
            tracked.add(sym.upper())
    return tracked


@shared_task(name="backend.tasks.market_data_tasks.update_tracked_symbol_cache")
def update_tracked_symbol_cache() -> dict:
    """Compute union of tracked symbols (index_constituents ∪ portfolio) and publish deltas.

    Writes two Redis keys:
    - tracked:all → full sorted list of tracked symbols
    - tracked:new → new additions since last run (expires 24h)
    """
    _set_task_status("update_tracked_symbol_cache", "running")
    session = SessionLocal()
    try:
        redis = market_data_service.redis_client
        current = sorted(_get_tracked_universe_from_db(session))
        # Bootstrap: if nothing tracked in DB yet, seed from live index constituents
        if not current:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                index_to_symbols: dict[str, set[str]] = {
                    "SP500": set(),
                    "NASDAQ100": set(),
                    "DOW30": set(),
                }
                for idx in ["SP500", "NASDAQ100", "DOW30"]:
                    try:
                        cons = loop.run_until_complete(
                            market_data_service.get_index_constituents(idx)
                        )
                        index_to_symbols[idx].update({s.upper() for s in cons if s})
                    except Exception:
                        continue
                seed_syms: set[str] = set().union(*index_to_symbols.values())
                if seed_syms:
                    for idx, syms in index_to_symbols.items():
                        for sym in syms:
                            session.add(
                                IndexConstituent(
                                    index_name=idx, symbol=sym, is_active=True
                                )
                            )
                    session.commit()
                    current = sorted(seed_syms)
            except Exception:
                pass
        prev_raw = redis.get("tracked:all")
        prev = []
        if prev_raw:
            try:
                prev = json.loads(prev_raw)
            except Exception:
                prev = []
        prev_set = set(s.upper() for s in prev)
        additions = [s for s in current if s not in prev_set]
        redis.set("tracked:all", json.dumps(current))
        redis.setex("tracked:new", 24 * 3600, json.dumps(additions))
        res = {"status": "ok", "tracked_all": len(current), "new": len(additions)}
        _set_task_status("update_tracked_symbol_cache", "ok", res)
        return res
    finally:
        session.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_new_tracked")
def backfill_new_tracked(batch_size: int = 50) -> dict:
    """Backfill OHLCV for symbols listed in Redis tracked:new, then clear it."""
    _set_task_status("backfill_new_tracked", "running")
    redis = market_data_service.redis_client
    raw = redis.get("tracked:new")
    if not raw:
        res = {"status": "ok", "new": 0}
        _set_task_status("backfill_new_tracked", "ok", res)
        return res
    try:
        symbols = json.loads(raw)
    except Exception:
        symbols = []
    if not symbols:
        res = {"status": "ok", "new": 0}
        _set_task_status("backfill_new_tracked", "ok", res)
        return res
    # Run batched backfill using existing helper
    done = 0
    for i in range(0, len(symbols), batch_size):
        chunk = symbols[i : i + batch_size]
        res = backfill_symbols(chunk)
        done += int(res.get("backfilled", 0))
    # Clear the new list after backfill
    redis.delete("tracked:new")
    res = {"status": "ok", "requested": len(symbols), "backfilled_batches": done}
    _set_task_status("backfill_new_tracked", "ok", res)
    return res


# ============================= Backfill =============================


@shared_task(name="backend.tasks.market_data_tasks.backfill_last_200_bars")
def backfill_last_200_bars() -> dict:
    """Delta backfill last ~200 trading days for all tracked symbols (indices ∪ portfolio).

    Returns detailed counters:
    - tracked_total, updated_total, up_to_date_total, skipped_empty, bars_inserted_total, errors
    """
    _set_task_status("backfill_last_200_bars", "running")
    session = SessionLocal()
    try:
        # Use durable tracked universe (index_constituents ∪ portfolio)
        symbols = _get_tracked_universe_from_db(session)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        tracked_total = len(symbols)
        updated_total = 0
        up_to_date_total = 0
        skipped_empty = 0
        bars_inserted_total = 0
        errors = 0
        for symbol in sorted(symbols):
            try:
                res = loop.run_until_complete(
                    market_data_service.backfill_daily_bars(
                        session, symbol, lookback_period="1y", max_bars=270
                    )
                )
                status = (res or {}).get("status")
                inserted = int((res or {}).get("inserted") or 0)
                if status == "empty":
                    skipped_empty += 1
                elif inserted > 0:
                    updated_total += 1
                    bars_inserted_total += inserted
                else:
                    up_to_date_total += 1
            except Exception:
                errors += 1
                session.rollback()
        res = {
            "status": "ok",
            "tracked_total": tracked_total,
            "updated_total": updated_total,
            "up_to_date_total": up_to_date_total,
            "skipped_empty": skipped_empty,
            "bars_inserted_total": bars_inserted_total,
            "errors": errors,
        }
        _set_task_status("backfill_last_200_bars", "ok", res)
        return res
    finally:
        session.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_symbols")
def backfill_symbols(symbols: List[str]) -> dict:
    """Delta backfill last-200 daily bars for a provided symbol list."""
    session = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        backfilled = 0
        errors = 0
        for symbol in [s.upper() for s in symbols or []]:
            try:
                res = loop.run_until_complete(
                    market_data_service.backfill_daily_bars(
                        session, symbol, lookback_period="1y", max_bars=270
                    )
                )
                if (res or {}).get("status") != "empty":
                    backfilled += 1
            except Exception:
                errors += 1
                session.rollback()
            # Pace requests only in free-tier mode
        try:
            if getattr(settings, "MARKET_PROVIDER_POLICY", "paid").lower() != "paid":
                import time as _t
                _t.sleep(0.6)
        except Exception:
            pass
        return {
            "status": "ok",
            "symbols": len(symbols or []),
            "backfilled": backfilled,
            "errors": errors,
        }
    finally:
        session.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_index_universe")
def backfill_index_universe(batch_size: int = 20) -> dict:
    """Bootstrap-only: backfill last-200 OHLCV for SP500/NASDAQ100/DOW30 (batched)."""
    _set_task_status("backfill_index_universe", "running")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    symbols: Set[str] = set()
    for idx in ["SP500", "NASDAQ100", "DOW30"]:
        try:
            cons = loop.run_until_complete(market_data_service.get_index_constituents(idx))
            symbols.update(cons)
        except Exception:
            pass
    symbols = {s.upper() for s in symbols if s}
    total = len(symbols)
    done = 0
    errors = 0
    ordered = sorted(symbols)
    for i in range(0, total, batch_size):
        chunk = ordered[i : i + batch_size]
        res = backfill_symbols(chunk)
        done += int(res.get("backfilled", 0))
        errors += int(res.get("errors", 0))
        # Adaptive wait only in free-tier mode
        try:
            if getattr(settings, "MARKET_PROVIDER_POLICY", "paid").lower() != "paid":
                import time
                time.sleep(2.5)
        except Exception:
            pass
    res = {
        "status": "ok",
        "total_symbols": total,
        "completed_batches": (total + batch_size - 1) // batch_size,
        "backfilled": done,
        "errors": errors,
    }
    _set_task_status("backfill_index_universe", "ok", res)
    return res


# ============================= Index Constituents =============================


@shared_task(name="backend.tasks.market_data_tasks.refresh_index_constituents")
def refresh_index_constituents() -> dict:
    """Refresh index constituents table for SP500, NASDAQ100, DOW30 (and keep inactive).

    - Inserts new symbols and marks them active
    - If a symbol disappears from a list, we mark it inactive and set became_inactive_at
    """
    _set_task_status("refresh_index_constituents", "running")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = {}
    session = SessionLocal()
    try:
        from datetime import datetime

        now = datetime.utcnow()
        for idx in ["SP500", "NASDAQ100", "DOW30"]:
            try:
                symbols = set(loop.run_until_complete(market_data_service.get_index_constituents(idx)))
            except Exception as e:
                results[idx] = f"error: {e}"
                continue
            # existing rows
            existing_rows = (
                session.query(IndexConstituent)
                .filter(IndexConstituent.index_name == idx)
                .all()
            )
            existing_map = {r.symbol: r for r in existing_rows}
            # upsert new/active
            for sym in symbols:
                row = existing_map.get(sym)
                if row:
                    if not row.is_active:
                        row.is_active = True
                        row.became_inactive_at = None
                    row.last_refreshed_at = now
                else:
                    session.add(
                        IndexConstituent(index_name=idx, symbol=sym, is_active=True)
                    )
            # mark inactive
            for sym, row in existing_map.items():
                if sym not in symbols and row.is_active:
                    row.is_active = False
                    row.became_inactive_at = now
                    row.last_refreshed_at = now
            session.commit()
            results[idx] = len(symbols)
        res = {"status": "ok", "indices": results}
        _set_task_status("refresh_index_constituents", "ok", res)
        return res
    finally:
        session.close()


# ============================= Recompute Indicators and Chart Metrics =============================


@shared_task(name="backend.tasks.market_data_tasks.recompute_indicators_universe")
def recompute_indicators_universe(batch_size: int = 50) -> dict:
    """Recompute indicators for the tracked universe from local DB (orchestrator only)."""
    _set_task_status("recompute_indicators_universe", "running")
    import asyncio as _aio

    loop = _aio.new_event_loop()
    _aio.set_event_loop(loop)
    session = SessionLocal()
    try:
        # Build symbol set (index_constituents ∪ portfolio)
        syms: Set[str] = set()
        try:
            for (s,) in session.query(IndexConstituent.symbol).distinct():
                if s:
                    syms.add(s)
        except Exception:
            for idx in ["SP500", "NASDAQ100", "DOW30"]:
                try:
                    cons = loop.run_until_complete(market_data_service.get_index_constituents(idx))
                    syms.update(cons)
                except Exception:
                    continue
        for (s,) in session.query(Position.symbol).distinct():
            if s:
                syms.add(s)
        ordered = sorted({s.upper() for s in syms if s})

        processed = 0
        # Chunking by batch_size
        for i in range(0, len(ordered), max(1, batch_size)):
            chunk = ordered[i : i + batch_size]
            for sym in chunk:
                try:
                    snap = market_data_service.compute_snapshot_from_db(session, sym)
                    if snap:
                        market_data_service.persist_snapshot(session, sym, snap)
                        processed += 1
                except Exception:
                    session.rollback()
        res = {"status": "ok", "symbols": len(ordered), "processed": processed}
        _set_task_status("recompute_indicators_universe", "ok", res)
        return res
    finally:
        session.close()


# ============================= Daily Analysis History =============================


@shared_task(name="backend.tasks.market_data_tasks.record_daily_history")
def record_daily_history(symbols: List[str] | None = None) -> dict:
    """Persist immutable daily snapshots to MarketAnalysisHistory.

    Reads the latest computed snapshot from MarketAnalysisCache (no provider calls).
    Falls back to compute from local DB if a snapshot row doesn't exist yet.
    """
    _set_task_status("record_daily_history", "running")
    session = SessionLocal()
    try:
        if not symbols:
            # Default to portfolio-held symbols
            symbols = [s for s, in session.query(Position.symbol).distinct() if s]
        written = 0
        for sym in sorted(set(s.upper() for s in symbols)):
            try:
                # Prefer the latest stored snapshot from cache
                row = (
                    session.query(MarketSnapshot)
                    .filter(
                        MarketSnapshot.symbol == sym,
                        MarketSnapshot.analysis_type == "technical_snapshot",
                    )
                    .order_by(MarketSnapshot.analysis_timestamp.desc())
                    .first()
                )
                if row and isinstance(row.raw_analysis, dict):
                    snapshot = dict(row.raw_analysis)
                else:
                    # Fallback: compute from local DB only (fast, no provider)
                    snapshot = market_data_service.compute_snapshot_from_db(session, sym)
                    if not snapshot:
                        continue
                # Determine as-of date from latest price_data if available
                as_of = (
                    session.query(PriceData.date)
                    .filter(PriceData.symbol == sym, PriceData.interval == "1d")
                    .order_by(PriceData.date.desc())
                    .limit(1)
                    .scalar()
                )
                from datetime import datetime as _dt

                as_of_date = as_of or _dt.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                # Upsert-like: unique on (symbol, type, as_of_date)
                existing = (
                    session.query(MarketSnapshotHistory)
                    .filter(
                        MarketSnapshotHistory.symbol == sym,
                        MarketSnapshotHistory.analysis_type == "technical_snapshot",
                        MarketSnapshotHistory.as_of_date == as_of_date,
                    )
                    .first()
                )
                if existing:
                    existing.current_price = snapshot.get("current_price")
                    existing.rsi = snapshot.get("rsi")
                    existing.atr_value = snapshot.get("atr_value")
                    existing.sma_50 = snapshot.get("sma_50")
                    existing.macd = snapshot.get("macd")
                    existing.macd_signal = snapshot.get("macd_signal")
                    existing.analysis_payload = snapshot
                else:
                    row = MarketSnapshotHistory(
                        symbol=sym,
                        analysis_type="technical_snapshot",
                        as_of_date=as_of_date,
                        current_price=snapshot.get("current_price"),
                        rsi=snapshot.get("rsi"),
                        atr_value=snapshot.get("atr_value"),
                        sma_50=snapshot.get("sma_50"),
                        macd=snapshot.get("macd"),
                        macd_signal=snapshot.get("macd_signal"),
                        analysis_payload=snapshot,
                    )
                    session.add(row)
                session.commit()
                written += 1
            except Exception:
                session.rollback()
        res = {"status": "ok", "symbols": len(symbols), "written": written}
        _set_task_status("record_daily_history", "ok", res)
        return res
    finally:
        session.close()
