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
from typing import List, Set, Dict, Optional

from backend.database import SessionLocal
from backend.models import PriceData
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.models.market_data import MarketSnapshotHistory, MarketSnapshot
from backend.models import IndexConstituent
from backend.services.market.market_data_service import (
    market_data_service,
    compute_coverage_status,
)
from backend.models import Position
from backend.config import settings
from .task_utils import task_run

import json

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_event_loop() -> asyncio.AbstractEventLoop:
    """Create and register a fresh event loop (caller must close)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def _increment_provider_usage(usage: Dict[str, int], result: dict | None) -> None:
    provider = (result or {}).get("provider") or "unknown"
    usage[provider] = usage.get(provider, 0) + 1
# ============================= Single-Symbol Refresh =============================


@shared_task(name="backend.tasks.market_data_tasks.refresh_single_symbol")
@task_run("refresh_single_symbol", lock_key=lambda symbol: str(symbol).upper() if symbol else None)
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
@task_run("enrich_index_fundamentals")
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
                    loop = _setup_event_loop()
                    try:
                        prov = loop.run_until_complete(market_data_service.compute_snapshot_from_providers(sym))
                    finally:
                        loop.close()
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
@task_run("fill_missing_snapshot_fundamentals")
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
@task_run("update_tracked_symbol_cache")
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
            loop = None
            try:
                loop = _setup_event_loop()
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
            finally:
                if loop:
                    loop.close()
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
@task_run("backfill_new_tracked")
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
@task_run("backfill_last_200_bars")
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
        loop = _setup_event_loop()
        try:
            tracked_total = len(symbols)
            updated_total = 0
            up_to_date_total = 0
            skipped_empty = 0
            bars_inserted_total = 0
            errors = 0
            provider_usage: Dict[str, int] = {}
            for symbol in sorted(symbols):
                try:
                    res = loop.run_until_complete(
                        market_data_service.backfill_daily_bars(
                            session, symbol, lookback_period="1y", max_bars=270
                        )
                    )
                    status = (res or {}).get("status")
                    inserted = int((res or {}).get("inserted") or 0)
                    _increment_provider_usage(provider_usage, res)
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
        finally:
            loop.close()
        res = {
            "status": "ok",
            "tracked_total": tracked_total,
            "updated_total": updated_total,
            "up_to_date_total": up_to_date_total,
            "skipped_empty": skipped_empty,
            "bars_inserted_total": bars_inserted_total,
            "errors": errors,
            "provider_usage": provider_usage,
        }
        _set_task_status("backfill_last_200_bars", "ok", res)
        return res
    finally:
        session.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_symbols")
@task_run("backfill_symbols")
def backfill_symbols(symbols: List[str]) -> dict:
    """Delta backfill last-200 daily bars for a provided symbol list."""
    session = SessionLocal()
    try:
        loop = _setup_event_loop()
        throttle = getattr(settings, "MARKET_PROVIDER_POLICY", "paid").lower() != "paid"
        sleep_fn = None
        if throttle:
            try:
                import time as _time

                sleep_fn = _time.sleep
            except Exception:
                sleep_fn = None
        try:
            backfilled = 0
            errors = 0
            provider_usage: Dict[str, int] = {}
            for symbol in [s.upper() for s in symbols or []]:
                try:
                    res = loop.run_until_complete(
                        market_data_service.backfill_daily_bars(
                            session, symbol, lookback_period="1y", max_bars=270
                        )
                    )
                    if (res or {}).get("status") != "empty":
                        backfilled += 1
                    _increment_provider_usage(provider_usage, res)
                except Exception:
                    errors += 1
                    session.rollback()
                if throttle and sleep_fn:
                    sleep_fn(0.6)
        finally:
            loop.close()
        return {
            "status": "ok",
            "symbols": len(symbols or []),
            "backfilled": backfilled,
            "errors": errors,
            "provider_usage": provider_usage,
        }
    finally:
        session.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_index_universe")
@task_run("backfill_index_universe")
def backfill_index_universe(batch_size: int = 100) -> dict:
    """Bootstrap-only: backfill last-200 OHLCV for SP500/NASDAQ100/DOW30 (batched)."""
    _set_task_status("backfill_index_universe", "running")
    loop = _setup_event_loop()
    symbols: Set[str] = set()
    try:
        for idx in ["SP500", "NASDAQ100", "DOW30"]:
            try:
                cons = loop.run_until_complete(market_data_service.get_index_constituents(idx))
                symbols.update(cons)
            except Exception:
                continue
    finally:
        loop.close()
    symbols = {s.upper() for s in symbols if s}
    total = len(symbols)
    done = 0
    errors = 0
    ordered = sorted(symbols)
    provider_usage: Dict[str, int] = {}
    throttle = getattr(settings, "MARKET_PROVIDER_POLICY", "paid").lower() != "paid"
    sleep_fn = None
    if throttle:
        try:
            import time as _time

            sleep_fn = _time.sleep
        except Exception:
            sleep_fn = None
    for i in range(0, total, batch_size):
        chunk = ordered[i : i + batch_size]
        res = backfill_symbols(chunk)
        done += int(res.get("backfilled", 0))
        errors += int(res.get("errors", 0))
        for provider, count in (res.get("provider_usage") or {}).items():
            provider_usage[provider] = provider_usage.get(provider, 0) + count
        # Adaptive wait only in free-tier mode
        if throttle and sleep_fn:
            sleep_fn(2.5)
    res = {
        "status": "ok",
        "total_symbols": total,
        "completed_batches": (total + batch_size - 1) // batch_size,
        "backfilled": done,
        "errors": errors,
        "provider_usage": provider_usage,
    }
    _set_task_status("backfill_index_universe", "ok", res)
    return res


# ============================= Index Constituents =============================


@shared_task(name="backend.tasks.market_data_tasks.refresh_index_constituents")
@task_run("refresh_index_constituents")
def refresh_index_constituents() -> dict:
    """Refresh index constituents table for SP500, NASDAQ100, DOW30 (and keep inactive).

    - Inserts new symbols and marks them active
    - If a symbol disappears from a list, we mark it inactive and set became_inactive_at
    """
    _set_task_status("refresh_index_constituents", "running")
    loop = _setup_event_loop()
    results = {}
    session = SessionLocal()
    try:
        from datetime import datetime

        now = datetime.utcnow()
        # Preflight: ensure at least one provider path is available
        from backend.config import settings as _settings
        preflight = {
            "has_fmp_key": bool(getattr(_settings, "FMP_API_KEY", "")),
        }
        for idx in ["SP500", "NASDAQ100", "DOW30"]:
            try:
                symbols = set(loop.run_until_complete(market_data_service.get_index_constituents(idx)))
            except Exception as e:
                results[idx] = {"error": str(e)}
                continue
            # Read provider meta if present
            provider_used = "unknown"
            fallback_used = None
            try:
                meta_raw = market_data_service.redis_client.get(f"index_constituents:{idx}:meta")
                if meta_raw:
                    meta = json.loads(meta_raw)
                    provider_used = meta.get("provider_used", provider_used)
                    fallback_used = meta.get("fallback_used", False)
            except Exception:
                pass
            # existing rows
            existing_rows = (
                session.query(IndexConstituent)
                .filter(IndexConstituent.index_name == idx)
                .all()
            )
            existing_map = {r.symbol: r for r in existing_rows}
            # upsert new/active
            inserted = 0
            updated_active = 0
            for sym in symbols:
                row = existing_map.get(sym)
                if row:
                    if not row.is_active:
                        row.is_active = True
                        row.became_inactive_at = None
                        updated_active += 1
                    row.last_refreshed_at = now
                else:
                    session.add(
                        IndexConstituent(index_name=idx, symbol=sym, is_active=True)
                    )
                    inserted += 1
            # mark inactive
            inactivated = 0
            for sym, row in existing_map.items():
                if sym not in symbols and row.is_active:
                    row.is_active = False
                    row.became_inactive_at = now
                    row.last_refreshed_at = now
                    inactivated += 1
            session.commit()
            results[idx] = {
                "fetched": len(symbols),
                "inserted": inserted,
                "reactivated": updated_active,
                "inactivated": inactivated,
                "provider_used": provider_used,
                "fallback_used": fallback_used,
            }
        res = {"status": "ok", "preflight": preflight, "indices": results}
        _set_task_status("refresh_index_constituents", "ok", res)
        return res
    finally:
        session.close()
        loop.close()


@shared_task(name="backend.tasks.market_data_tasks.bootstrap_universe")
@task_run("bootstrap_universe", lock_key=lambda: "bootstrap_universe")
def bootstrap_universe() -> dict:
    """Run the full universe bootstrap chain in-process and return a rollup."""
    def _summarize(step: str, payload: dict | None) -> str:
        data = payload or {}
        if step == "refresh_index_constituents":
            idx = data.get("indices") or {}
            parts = [f"{name}: {stats.get('fetched', 0)} symbols via {stats.get('provider_used', 'n/a')}" for name, stats in idx.items()]
            return "; ".join(parts) or "Refreshed index members"
        if step == "update_tracked_symbol_cache":
            return f"{data.get('tracked_all', 0)} tracked ({data.get('new', 0)} new)"
        if step == "backfill_index_universe":
            return f"Backfilled {data.get('backfilled', 0)} of {data.get('total_symbols', 0)} symbols"
        if step == "backfill_last_200_bars":
            return f"Inserted {data.get('bars_inserted_total', 0)} bars across {data.get('tracked_total', 0)} tracked"
        if step == "backfill_5m_last_n_days":
            return f"5m processed {data.get('processed', 0)} symbols (n={data.get('symbols', 0)})"
        if step == "recompute_indicators_universe":
            return f"Recomputed indicators for {data.get('processed', data.get('symbols', 0))} symbols"
        if step == "record_daily_history":
            return f"Wrote {data.get('written', 0)} snapshot rows"
        return data.get("status", "ok")

    rollup: dict = {"steps": []}

    def _append(step_name: str, result: dict) -> None:
        rollup["steps"].append(
            {
                "name": step_name,
                "summary": _summarize(step_name, result),
                "result": result,
            }
        )

    res1 = refresh_index_constituents()
    _append("refresh_index_constituents", res1)

    res2 = update_tracked_symbol_cache()
    _append("update_tracked_symbol_cache", res2)

    res3 = backfill_index_universe()
    _append("backfill_index_universe", res3)

    res4 = backfill_last_200_bars()
    _append("backfill_last_200_bars", res4)

    if _is_5m_backfill_enabled():
        res5 = backfill_5m_last_n_days(n_days=1, batch_size=50)
    else:
        res5 = {"status": "skipped", "reason": "5m backfill disabled by admin toggle"}
    _append("backfill_5m_last_n_days", res5)

    res6 = recompute_indicators_universe(batch_size=50)
    _append("recompute_indicators_universe", res6)

    res7 = record_daily_history()
    _append("record_daily_history", res7)

    rollup["status"] = "ok"
    rollup["overall_summary"] = "; ".join(step["summary"] for step in rollup["steps"] if step.get("summary"))
    return rollup


# ============================= Recompute Indicators and Chart Metrics =============================


@shared_task(name="backend.tasks.market_data_tasks.recompute_indicators_universe")
@task_run("recompute_indicators_universe")
def recompute_indicators_universe(batch_size: int = 50) -> dict:
    """Recompute indicators for the tracked universe from local DB (orchestrator only)."""
    _set_task_status("recompute_indicators_universe", "running")
    loop = _setup_event_loop()
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
        loop.close()


# ============================= Daily Analysis History =============================


@shared_task(name="backend.tasks.market_data_tasks.record_daily_history")
@task_run("record_daily_history")
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


# ============================= 5m Intraday Backfill and Retention =============================


def _is_5m_backfill_enabled() -> bool:
    """Check admin toggle stored in Redis; default to enabled on errors."""
    try:
        raw = market_data_service.redis_client.get("coverage:backfill_5m_enabled")
        if raw is None:
            return True
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode()
        return str(raw).strip().lower() not in ("0", "false", "off", "disabled")
    except Exception:
        # Fail open if Redis unavailable so daily flows aren't blocked
        return True


@shared_task(name="backend.tasks.market_data_tasks.backfill_5m_for_symbols")
@task_run("backfill_5m_for_symbols")
def backfill_5m_for_symbols(symbols: List[str], n_days: int = 5) -> dict:
    """Delta backfill last N days of 5m bars for a provided symbol list."""
    if not _is_5m_backfill_enabled():
        return {
            "status": "skipped",
            "reason": "5m backfill disabled by admin toggle",
            "symbols": len(symbols or []),
            "processed": 0,
            "errors": 0,
            "provider_usage": {},
        }
    session = SessionLocal()
    loop = None
    try:
        loop = _setup_event_loop()
        processed = 0
        errors = 0
        provider_usage: Dict[str, int] = {}
        for sym in [s.upper() for s in symbols or []]:
            try:
                res = loop.run_until_complete(
                    market_data_service.backfill_intraday_5m(session, sym, lookback_days=n_days)
                )
                if (res or {}).get("status") != "empty":
                    processed += 1
                _increment_provider_usage(provider_usage, res)
            except Exception:
                errors += 1
                session.rollback()
        return {
            "status": "ok",
            "symbols": len(symbols or []),
            "processed": processed,
            "errors": errors,
            "provider_usage": provider_usage,
        }
    finally:
        session.close()
        if loop:
            loop.close()


@shared_task(name="backend.tasks.market_data_tasks.backfill_5m_last_n_days")
@task_run("backfill_5m_last_n_days")
def backfill_5m_last_n_days(n_days: int = 5, batch_size: int = 50) -> dict:
    """Backfill last N days of 5m bars for tracked universe in batches."""
    if not _is_5m_backfill_enabled():
        return {
            "status": "skipped",
            "reason": "5m backfill disabled by admin toggle",
            "symbols": 0,
            "processed": 0,
            "errors": 0,
            "provider_usage": {},
        }
    session = SessionLocal()
    loop = None
    try:
        syms = sorted(_get_tracked_universe_from_db(session))
        total = len(syms)
        done = 0
        errors = 0
        loop = _setup_event_loop()
        provider_usage: Dict[str, int] = {}
        for i in range(0, total, max(1, batch_size)):
            chunk = syms[i : i + batch_size]
            for sym in chunk:
                try:
                    res = loop.run_until_complete(
                        market_data_service.backfill_intraday_5m(session, sym, lookback_days=n_days)
                    )
                    if (res or {}).get("status") != "empty":
                        done += 1
                    _increment_provider_usage(provider_usage, res)
                except Exception:
                    errors += 1
                    session.rollback()
        return {"status": "ok", "symbols": total, "processed": done, "errors": errors, "provider_usage": provider_usage}
    finally:
        session.close()
        if loop:
            loop.close()


@shared_task(name="backend.tasks.market_data_tasks.enforce_price_data_retention")
@task_run("enforce_price_data_retention")
def enforce_price_data_retention(max_days_5m: int = 90) -> dict:
    """Delete 5m bars older than max_days_5m to control storage."""
    session = SessionLocal()
    try:
        from backend.models import PriceData
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=max_days_5m)
        deleted = (
            session.query(PriceData)
            .filter(PriceData.interval == "5m", PriceData.date < cutoff)
            .delete(synchronize_session=False)
        )
        session.commit()
        return {"status": "ok", "deleted": int(deleted or 0), "cutoff": cutoff.isoformat()}
    finally:
        session.close()


# ============================= Coverage instrumentation =============================


@shared_task(name="backend.tasks.market_data_tasks.monitor_coverage_health")
@task_run("monitor_coverage_health")
def monitor_coverage_health() -> dict:
    """Snapshot coverage health into Redis so the Admin UI can show stale counts."""
    session = SessionLocal()
    try:
        snapshot = market_data_service.coverage_snapshot(session)
        status_info = snapshot.get("status") or compute_coverage_status(snapshot)
        payload = {
            "snapshot": snapshot,
            "updated_at": datetime.utcnow().isoformat(),
            "status": status_info,
        }
        redis_client = market_data_service.redis_client
        history_entry = {
            "ts": payload["updated_at"],
            "daily_pct": status_info.get("daily_pct"),
            "m5_pct": status_info.get("m5_pct"),
            "stale_daily": status_info.get("stale_daily"),
            "stale_m5": status_info.get("stale_m5"),
            "label": status_info.get("label"),
        }
        try:
            pipe = redis_client.pipeline()
            pipe.set("coverage:health:last", json.dumps(payload), ex=86400)
            pipe.lpush("coverage:health:history", json.dumps(history_entry))
            pipe.ltrim("coverage:health:history", 0, 47)
            pipe.execute()
        except Exception:
            pass
        return {
            "status": status_info.get("label"),
            "daily_pct": status_info.get("daily_pct"),
            "m5_pct": status_info.get("m5_pct"),
            "stale_daily": status_info.get("stale_daily"),
            "stale_m5": status_info.get("stale_m5"),
            "tracked_count": snapshot.get("tracked_count", 0),
            "symbols": snapshot.get("symbols", 0),
        }
    finally:
        session.close()

