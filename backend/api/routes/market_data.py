"""
QuantMatrix V1 - Market Data Routes

Clean, service-driven endpoints for prices, snapshots, tracked universe, backfills,
indicator recompute, and history. DB-first strategy: compute from local `price_data`.
Providers are used only for OHLCV backfills (paid provider prioritized).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Callable, Optional
import logging
from datetime import datetime

# dependencies
from backend.database import get_db
from backend.models.user import User
from backend.services.market.market_data_service import (
    MarketDataService,
    compute_coverage_status,
)
from backend.models.market_data import MarketSnapshot
from backend.tasks.market_data_tasks import (
    backfill_index_universe,
    record_daily_history,
    update_tracked_symbol_cache,
    backfill_new_tracked,
    backfill_symbols,
    backfill_last_200_bars,
    recompute_indicators_universe,
    refresh_index_constituents,
    refresh_single_symbol,
)
from backend.api.dependencies import get_optional_user, get_admin_user, get_market_data_viewer
from backend.models.index_constituent import IndexConstituent
from backend.models.market_data import PriceData
from backend.models.market_data import JobRun
from backend.api.routes.utils import serialize_job_runs
from backend.tasks.market_data_tasks import backfill_5m_last_n_days, enforce_price_data_retention, backfill_5m_for_symbols
from backend.tasks.market_data_tasks import bootstrap_universe
from backend.tasks.market_data_tasks import monitor_coverage_health
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _visibility_scope() -> str:
    return "all_authenticated" if settings.MARKET_DATA_SECTION_PUBLIC else "admin_only"


def _is_backfill_5m_enabled(svc: MarketDataService) -> bool:
    try:
        raw = svc.redis_client.get("coverage:backfill_5m_enabled")
        if raw is None:
            return True
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode()
        return str(raw).strip().lower() not in ("0", "false", "off", "disabled")
    except Exception:
        # Fail open if Redis not reachable
        return True


def _coverage_actions(backfill_5m_enabled: bool = True) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = [
        {
            "label": "Refresh Index Constituents",
            "task_name": "refresh_index_constituents",
            "description": "Fetch SP500 / NASDAQ100 / DOW30 members (FMP-first, Wikipedia fallback).",
        },
        {
            "label": "Update Tracked Symbols",
            "task_name": "update_tracked_symbol_cache",
            "description": "Union index constituents with held symbols and publish tracked:all/new in Redis.",
        },
        {
            "label": "Backfill Index Universe (Daily)",
            "task_name": "backfill_index_universe",
            "description": "Batched daily OHLCV backfill for the entire index universe (delta-only).",
        },
        {
            "label": "Backfill 5m Last Day",
            "task_name": "backfill_5m_last_n_days",
            "description": "Populate 5m bars for the tracked set (default 1 day) to hit the SLA banner.",
        },
    ]
    if not backfill_5m_enabled:
        for action in actions:
            if action.get("task_name") == "backfill_5m_last_n_days":
                action["disabled"] = True
                action["description"] = f"{action.get('description')} (disabled by admin toggle)"
    return actions


def _coverage_education() -> Dict[str, Any]:
    return {
        "coverage": "Coverage measures how many tracked symbols have fresh bars stored in price_data. Daily coverage should stay above 95% and 5m coverage should be refreshed at least once per trading day.",
        "tracked": "Tracked is the union of live index constituents plus any symbols seen in your brokerage accounts. Use Update Tracked after refreshing constituents to republish the universe to Redis.",
        "how_to_fix": [
            "Refresh Index Constituents to sync SP500 / NASDAQ100 / DOW30 membership.",
            "Update Tracked Symbol Cache to rebuild the Redis universe from the DB.",
            "Backfill Index Universe (Daily) to seed price_data for each index member.",
            "Backfill 5m to capture latest intraday data for freshness dashboards.",
        ],
    }


def _tracked_actions() -> List[Dict[str, str]]:
    return [
        {
            "label": "Update Tracked Symbols",
            "task_name": "update_tracked_symbol_cache",
            "description": "Rebuild tracked:all / tracked:new from DB index_constituents ∪ portfolio symbols.",
        },
        {
            "label": "Backfill New Tracked",
            "task_name": "backfill_new_tracked",
            "description": "Run delta backfill for anything just added to tracked:new and clear the queue.",
        },
        {
            "label": "Backfill Last 200 Bars",
            "task_name": "backfill_last_200_bars",
            "description": "Safety net to ensure every tracked symbol has the latest ~200 daily bars.",
        },
    ]


def _tracked_education() -> Dict[str, Any]:
    return {
        "overview": "Tracked symbols represent everything the platform monitors (index members + any holdings pulled from brokers). Coverage metrics show how fresh the price_data rows are for these symbols.",
        "details": [
            "Update Tracked Symbol Cache unions DB constituents with holdings and publishes Redis keys tracked:all and tracked:new.",
            "Backfill New Tracked picks up anything newly added to tracked:new and seeds its OHLCV bars.",
            "You can sort/filter the table by sector, industry, ATR, or stage to decide the next action.",
        ],
    }


def _enqueue_task(task_fn: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Standardize task enqueue responses."""
    result = task_fn.delay(*args, **kwargs)
    return {"task_id": result.id}


def _load_tracked_details(db: Session, symbols: List[str]) -> Dict[str, Any]:
    if not symbols:
        return {}
    sym_set = {s.upper() for s in symbols}
    rows = (
        db.query(MarketSnapshot)
        .filter(
            MarketSnapshot.symbol.in_(sym_set),
            MarketSnapshot.analysis_type == "technical_snapshot",
        )
        .order_by(MarketSnapshot.symbol.asc(), MarketSnapshot.analysis_timestamp.desc())
        .all()
    )
    price_rows = (
        db.query(PriceData.symbol, PriceData.close_price)
        .filter(PriceData.symbol.in_(sym_set), PriceData.interval == "1d")
        .distinct(PriceData.symbol)
        .order_by(PriceData.symbol.asc(), PriceData.date.desc())
        .all()
    )
    price_map = {sym.upper(): close for sym, close in price_rows if sym}

    details: Dict[str, Any] = {}
    seen: set[str] = set()

    def _to_float(value):
        try:
            return float(value) if value is not None else None
        except Exception:
            return None

    for row in rows:
        sym = (row.symbol or "").upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        details[sym] = {
            "current_price": _to_float(getattr(row, "current_price", None)) or _to_float(price_map.get(sym)),
            "atr_value": _to_float(getattr(row, "atr_value", None)),
            "stage_label": getattr(row, "stage_label", None),
            "stage_dist_pct": _to_float(getattr(row, "stage_dist_pct", None)),
            "stage_slope_pct": _to_float(getattr(row, "stage_slope_pct", None)),
            "ma_bucket": getattr(row, "ma_bucket", None),
            "sector": getattr(row, "sector", None),
            "industry": getattr(row, "industry", None),
            "market_cap": _to_float(getattr(row, "market_cap", None)),
            "last_snapshot_at": getattr(row.analysis_timestamp, "isoformat", lambda: None)(),
        }

    cons_rows = (
        db.query(
            IndexConstituent.symbol,
            IndexConstituent.index_name,
            IndexConstituent.sector,
            IndexConstituent.industry,
        )
        .filter(IndexConstituent.symbol.in_(sym_set))
        .all()
    )
    for sym, idx_name, sector, industry in cons_rows:
        symbol = (sym or "").upper()
        if not symbol:
            continue
        entry = details.setdefault(symbol, {})
        entry.setdefault("indices", set()).add(idx_name)
        entry.setdefault("sector", sector)
        entry.setdefault("industry", industry)
    for sym, entry in details.items():
        if isinstance(entry.get("indices"), set):
            entry["indices"] = sorted(entry["indices"])
        # Backfill price if still missing
        if entry.get("current_price") is None and price_map.get(sym):
            entry["current_price"] = _to_float(price_map.get(sym))
    return details

# =============================================================================
# MARKET DATA ENDPOINTS (Clean & Focused)
# Order: Prices → Snapshots → Constituents/Tracked → Backfills → Indicators → Admin
# =============================================================================


@router.get("/price/{symbol}")
async def get_current_price(
    symbol: str, user: User | None = Depends(get_optional_user)
) -> Dict[str, Any]:
    """Get current price for a symbol."""
    try:
        market_service = MarketDataService()
        price = await market_service.get_current_price(symbol)

        return {
            "symbol": symbol,
            "current_price": price,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Price error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("1y", description="e.g., 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="1d, 4h, 1h, 5m"),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """
    Daily/intraday OHLCV series for the symbol using MarketDataService policy.
    Returns list of { time, open, high, low, close, volume } with time as ISO.
    """
    try:
        svc = MarketDataService()
        # Pass max_bars=None so longer periods (e.g., 3y) are not trimmed to default 270
        df = await svc.get_historical_data(symbol=symbol.upper(), period=period, interval=interval, max_bars=None)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="No historical data")
        # Expect newest->first index; convert to ascending by date
        try:
            df_out = df.iloc[::-1].copy()
        except Exception:
            df_out = df
        # Normalize columns
        cols = {c.lower(): c for c in df_out.columns}
        def pick(col_name: str) -> str:
            for key in cols:
                if key.startswith(col_name):
                    return cols[key]
            return col_name
        o = pick("open")
        h = pick("high")
        l = pick("low")
        c = pick("close")
        v = pick("volume")
        out = []
        for ts, row in df_out.iterrows():
            out.append({
                "time": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "open": float(row.get(o, None) or row.get("open_price", 0) or 0),
                "high": float(row.get(h, None) or row.get("high_price", 0) or 0),
                "low": float(row.get(l, None) or row.get("low_price", 0) or 0),
                "close": float(row.get(c, None) or row.get("close_price", 0) or 0),
                "volume": float(row.get(v, 0) or 0),
            })
        return {"symbol": symbol.upper(), "period": period, "interval": interval, "bars": out}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ History error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# TECHNICAL SNAPSHOTS (MarketSnapshot)
# =============================================================================


@router.get("/technical/snapshot/{symbol}")
async def get_snapshot(
    symbol: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return latest technical snapshot for a symbol from MarketSnapshot."""
    row = (
        db.query(MarketSnapshot)
        .filter(
            MarketSnapshot.symbol == symbol.upper(),
            MarketSnapshot.analysis_type == "technical_snapshot",
        )
        .order_by(MarketSnapshot.analysis_timestamp.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No snapshot found")
    payload = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    return {"symbol": symbol.upper(), "snapshot": payload}


# Removed duplicate refresh; use POST /symbol/{symbol}/refresh instead


@router.get("/admin/tasks/status")
async def admin_task_status(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Return last-run status for key market-data tasks from Redis."""
    try:
        from backend.services.market.market_data_service import market_data_service

        r = market_data_service.redis_client
        keys = [
            "taskstatus:update_tracked_symbol_cache:last",
            "taskstatus:backfill_new_tracked:last",
            "taskstatus:backfill_last_200_bars:last",
            "taskstatus:backfill_index_universe:last",
            "taskstatus:refresh_index_constituents:last",
            "taskstatus:recompute_indicators_universe:last",
            "taskstatus:record_daily_history:last",
            "taskstatus:monitor_coverage_health:last",
        ]
        out: Dict[str, Any] = {}
        import json as _json

        for k in keys:
            try:
                raw = r.get(k)
                out[k] = _json.loads(raw) if raw else None
            except Exception:
                out[k] = None
        return out
    except Exception as e:
        logger.error(f"task status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Constituents & Tracked Universe (DB + Redis)
# =============================================================================


@router.get("/index/constituents")
async def get_index_constituents(
    index: str = Query("SP500", description="SP500, NASDAQ100, DOW30"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    index = index.upper()
    if index not in {"SP500", "NASDAQ100", "DOW30"}:
        raise HTTPException(status_code=400, detail="invalid index")
    q = db.query(IndexConstituent).filter(IndexConstituent.index_name == index)
    if active_only:
        q = q.filter(IndexConstituent.is_active.is_(True))
    rows = q.order_by(IndexConstituent.symbol.asc()).all()
    return {"index": index, "count": len(rows), "symbols": [r.symbol for r in rows]}


@router.post("/index/constituents/refresh")
async def post_refresh_constituents(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    return _enqueue_task(refresh_index_constituents)


@router.get("/tracked")
async def get_tracked(
    include_details: bool = Query(True),
    db: Session = Depends(get_db),
    _viewer: User = Depends(get_market_data_viewer),
) -> Dict[str, Any]:
    from backend.services.market.market_data_service import market_data_service

    r = market_data_service.redis_client

    all_raw = r.get("tracked:all")
    new_raw = r.get("tracked:new")
    all_symbols = sorted(json.loads(all_raw) if all_raw else [])
    new_symbols = json.loads(new_raw) if new_raw else []

    details = _load_tracked_details(db, all_symbols) if include_details else {}

    meta = {
        "visibility": _visibility_scope(),
        "exposed_to_all": settings.MARKET_DATA_SECTION_PUBLIC,
        "education": _tracked_education(),
        "actions": _tracked_actions(),
    }

    return {
        "all": all_symbols,
        "new": new_symbols,
        "details": details if include_details else {},
        "meta": meta,
    }


@router.post("/tracked/update")
async def post_update_tracked(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    return _enqueue_task(update_tracked_symbol_cache)


# =============================================================================
# Backfills (OHLCV) and Indicators
# =============================================================================


@router.post("/backfill/index-universe")
async def post_backfill_index_universe(
    batch_size: int = Query(20, ge=5, le=100),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Bootstrap helper: enqueue batched backfill for SP500/NASDAQ100/DOW30 constituents."""
    return _enqueue_task(backfill_index_universe, batch_size=batch_size)


@router.post("/backfill/tracked-new")
async def post_backfill_tracked_new(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    return _enqueue_task(backfill_new_tracked)


@router.post("/backfill/last-200")
async def post_backfill_last200(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    return _enqueue_task(backfill_last_200_bars)


@router.post("/backfill/symbols")
async def post_backfill_symbols(
    symbols: List[str] = Query(..., description="Repeat the parameter to provide multiple symbols"),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Enqueue delta backfill for a provided list of symbols."""
    if not symbols:
        raise HTTPException(status_code=400, detail="symbols required")
    return _enqueue_task(backfill_symbols, [s.upper() for s in symbols if s])


@router.post("/indicators/recompute-universe")
async def post_recompute_universe(
    batch_size: int = Query(50, ge=10, le=200),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    return _enqueue_task(recompute_indicators_universe, batch_size)


# =============================================================================
# Single-symbol Refresh (DB-first flow)
# =============================================================================


@router.post("/symbol/{symbol}/refresh")
async def post_refresh_symbol(
    symbol: str,
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Delta backfill and recompute indicators for a single symbol (no external TA).

    Flow: backfill_last_200_bars(symbol) → recompute from DB → persist MarketSnapshot.
    """
    return _enqueue_task(refresh_single_symbol, symbol.upper())


@router.post("/admin/history/record")
async def admin_record_history(
    symbols: List[str] | None = Query(None),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    try:
        res = record_daily_history(symbols)
        return res
    except Exception as e:
        logger.error(f"admin record history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DB History (from price_data) and Coverage
# =============================================================================


@router.get("/db/history")
async def get_db_history(
    symbol: str = Query(...),
    interval: str = Query("1d", regex="^(1d|5m)$"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return OHLCV bars for a symbol from price_data (ascending)."""
    from backend.services.market.market_data_service import MarketDataService

    svc = MarketDataService()
    try:
        parse = lambda s: datetime.fromisoformat(s) if s else None
        df = svc.get_db_history(
            db,
            symbol=symbol.upper(),
            interval=interval,
            start=parse(start),
            end=parse(end),
            limit=limit,
        )
        bars = []
        for ts, row in df.iterrows():
            bars.append(
                {
                    "time": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    "open": float(row.get("Open", 0) or 0),
                    "high": float(row.get("High", 0) or 0),
                    "low": float(row.get("Low", 0) or 0),
                    "close": float(row.get("Close", 0) or 0),
                    "volume": float(row.get("Volume", 0) or 0),
                }
            )
        return {"symbol": symbol.upper(), "interval": interval, "bars": bars}
    except Exception as e:
        logger.error(f"db history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coverage")
async def get_coverage(
    db: Session = Depends(get_db),
    _viewer: User = Depends(get_market_data_viewer),
) -> Dict[str, Any]:
    """Return coverage summary across intervals with last bar timestamps and freshness buckets."""
    try:
        svc = MarketDataService()
        snapshot: Dict[str, Any] | None = None
        updated_at: str | None = None
        source = "cache"
        history_entries: List[Dict[str, Any]] = []
        backfill_5m_enabled = _is_backfill_5m_enabled(svc)

        def _ensure_status(snap: Dict[str, Any]) -> Dict[str, Any]:
            if "status" not in snap or not snap["status"]:
                snap["status"] = compute_coverage_status(snap)
            return snap["status"]

        try:
            raw = svc.redis_client.get("coverage:health:last")
            if raw:
                cached = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                snapshot = cached.get("snapshot")
                updated_at = cached.get("updated_at")
                if snapshot is not None and cached.get("status"):
                    snapshot.setdefault("status", cached["status"])
        except Exception:
            snapshot = None

        if snapshot is None:
            snapshot = svc.coverage_snapshot(db)
            updated_at = snapshot.get("generated_at")
            source = "db"

        # Ensure downstream status logic can see the 5m toggle (for ignore-5m behavior).
        try:
            snapshot.setdefault("meta", {})["backfill_5m_enabled"] = backfill_5m_enabled
        except Exception:
            # Any failure here should fall back to the previously computed/cached snapshot.
            pass

        status_info = _ensure_status(snapshot)

        # Recompute stale/freshness and counts directly from DB to avoid stale cache artifacts.
        # IMPORTANT: This must also rebuild `daily.freshness` (and `m5.freshness`) so the UI buckets
        # never render as zeros when stale counts are non-zero.
        try:
            # Determine the universe: prefer Redis tracked:all; fallback to symbols present in DB.
            tracked_symbols: List[str] = []
            try:
                raw_tracked = svc.redis_client.get("tracked:all")
                if raw_tracked:
                    tracked_symbols = json.loads(raw_tracked.decode() if isinstance(raw_tracked, (bytes, bytearray)) else raw_tracked)  # type: ignore[arg-type]
            except Exception:
                tracked_symbols = []

            tracked_symbols = sorted({str(s).upper() for s in (tracked_symbols or []) if s})

            if not tracked_symbols:
                tracked_symbols = sorted(
                    {
                        str(s).upper()
                        for (s,) in db.query(PriceData.symbol).distinct().all()
                        if s
                    }
                )

            total_symbols = len(tracked_symbols)
            # If we're serving a cached snapshot and cannot determine any universe from
            # Redis tracked:all nor DB price_data, do NOT overwrite the cached view.
            # This keeps cache semantics stable and avoids flipping cached OK → IDLE.
            if total_symbols == 0 and source == "cache":
                raise RuntimeError("skip_db_recompute_no_universe")
            sym_set = set(tracked_symbols)

            from datetime import timedelta

            def _bucketize(ts: datetime | None, now_utc: datetime) -> str:
                if not ts:
                    return "none"
                age = now_utc - ts
                if age <= timedelta(hours=24):
                    return "<=24h"
                if age <= timedelta(hours=48):
                    return "24-48h"
                return ">48h"

            def _last_by_symbol(interval: str) -> Dict[str, datetime | None]:
                last: Dict[str, datetime | None] = {sym: None for sym in tracked_symbols}
                if not sym_set:
                    return last
                rows = (
                    db.query(PriceData.symbol, PriceData.date)
                    .filter(PriceData.interval == interval, PriceData.symbol.in_(sym_set))
                    .order_by(PriceData.symbol.asc(), PriceData.date.desc())
                    .distinct(PriceData.symbol)
                    .all()
                )
                for sym, dt in rows:
                    if sym and sym.upper() in last:
                        last[sym.upper()] = dt
                return last

            def _build_interval_section(interval: str) -> Dict[str, Any]:
                now_utc = datetime.utcnow()
                last_dt_map = _last_by_symbol(interval)
                # Serialize for API response
                last_iso_map: Dict[str, str | None] = {
                    sym: (dt.isoformat() if dt else None) for sym, dt in last_dt_map.items()
                }

                freshness = {"<=24h": 0, "24-48h": 0, ">48h": 0, "none": 0}
                stale_items: List[Dict[str, Any]] = []
                for sym, dt in last_dt_map.items():
                    bucket = _bucketize(dt, now_utc)
                    freshness[bucket] = freshness.get(bucket, 0) + 1
                    if bucket in (">48h", "none"):
                        stale_items.append(
                            {
                                "symbol": sym,
                                "last": dt.isoformat() if dt else None,
                                "bucket": bucket,
                            }
                        )
                stale_items.sort(key=lambda item: (item.get("bucket") or "", item.get("last") or "", item.get("symbol") or ""))
                stale_limit = int(getattr(settings, "COVERAGE_STALE_SAMPLE", 50))
                stale_sample = stale_items[: max(0, stale_limit)]

                fresh_24 = int(freshness["<=24h"])
                fresh_48 = int(freshness["24-48h"])
                stale_48h = int(freshness[">48h"])
                missing = int(freshness["none"])

                return {
                    # Count = symbols within freshness SLA (<=48h). This drives daily_pct.
                    "count": fresh_24 + fresh_48,
                    "last": last_iso_map,
                    "freshness": freshness,
                    # Stale sample list for UI drilldowns (full counts are in freshness + status)
                    "stale": stale_sample,
                    "fresh_24h": fresh_24,
                    "fresh_48h": fresh_48,
                    "fresh_gt48h": 0,
                    "stale_48h": stale_48h,
                    "missing": missing,
                }

            daily_section = _build_interval_section("1d")
            m5_section = _build_interval_section("5m")

            stale_daily_total = int(daily_section.get("stale_48h") or 0) + int(daily_section.get("missing") or 0)
            daily_pct = 0.0
            if total_symbols > 0:
                daily_pct = max(0.0, min(100.0, (float(daily_section.get("count") or 0) / total_symbols) * 100.0))

            status_info["daily_pct"] = daily_pct
            status_info["tracked_total"] = total_symbols
            status_info["universe"] = total_symbols
            status_info["symbols"] = total_symbols
            status_info["stale_daily"] = stale_daily_total

            snapshot["symbols"] = total_symbols
            snapshot["tracked_count"] = total_symbols
            snapshot["daily"] = daily_section
            snapshot["m5"] = m5_section

            # Recompute status label/summary based on the rebuilt snapshot.
            snapshot["status"] = compute_coverage_status(snapshot)
            status_info = snapshot["status"] or status_info
        except Exception:
            pass

        try:
            raw_history = svc.redis_client.lrange("coverage:health:history", 0, 47)
            for entry in raw_history or []:
                try:
                    payload = json.loads(entry.decode() if isinstance(entry, (bytes, bytearray)) else entry)
                    history_entries.append(payload)
                except Exception:
                    continue
            if history_entries:
                history_entries = list(reversed(history_entries))
        except Exception:
            history_entries = []

        if not history_entries and updated_at:
            history_entries = [
                {
                    "ts": updated_at,
                    "daily_pct": status_info.get("daily_pct"),
                    "m5_pct": status_info.get("m5_pct"),
                    "stale_daily": status_info.get("stale_daily"),
                    "stale_m5": status_info.get("stale_m5"),
                    "label": status_info.get("label"),
                }
            ]

        snapshot["history"] = history_entries

        sparkline_meta = {
            "daily_pct": [
                float(entry.get("daily_pct") or 0) for entry in history_entries
            ],
            "m5_pct": [
                float(entry.get("m5_pct") or 0) for entry in history_entries
            ],
            "labels": [entry.get("ts") for entry in history_entries],
            "stale_daily": [
                int(entry.get("stale_daily") or 0) for entry in history_entries
            ],
            "stale_m5": [
                int(entry.get("stale_m5") or 0) for entry in history_entries
            ],
        }

        def _kpi_cards() -> List[Dict[str, Any]]:
            tracked = int(snapshot.get("tracked_count") or 0)
            total_symbols = int(snapshot.get("symbols") or 0)
            stale_m5 = int(status_info.get("stale_m5") or 0)
            return [
                {
                    "id": "tracked",
                    "label": "Tracked Symbols",
                    "value": tracked,
                    "help": "Universe size",
                },
                {
                    "id": "daily_pct",
                    "label": "Daily Coverage %",
                    "value": status_info.get("daily_pct"),
                    "unit": "%",
                    "help": f"{snapshot.get('daily', {}).get('count', 0)} / {total_symbols} bars",
                },
                {
                    "id": "m5_pct",
                    "label": "5m Coverage %",
                    "value": status_info.get("m5_pct"),
                    "unit": "%",
                    "help": f"{snapshot.get('m5', {}).get('count', 0)} / {total_symbols} bars",
                },
                {
                    "id": "stale_daily",
                    "label": "Stale (>48h)",
                    "value": status_info.get("stale_daily"),
                    "help": "All 5m covered" if stale_m5 == 0 else f"{stale_m5} missing 5m",
                },
            ]

        sla_meta = {
            "daily_pct": status_info.get("thresholds", {}).get("daily_pct"),
            "m5_expectation": status_info.get("thresholds", {}).get("m5_expectation"),
        }

        # Clamp pct and rebuild freshness buckets
        def _clamp_pct(val: Any) -> float:
            try:
                v = float(val or 0)
                return max(0.0, min(100.0, v))
            except Exception:
                return 0.0

        status_info["daily_pct"] = _clamp_pct(status_info.get("daily_pct"))
        status_info["m5_pct"] = _clamp_pct(status_info.get("m5_pct"))

        total_symbols = int(snapshot.get("symbols") or 0)
        daily_section = snapshot.get("daily", {}) or {}
        fresh_24 = int(daily_section.get("fresh_24h") or 0)
        fresh_48 = int(daily_section.get("fresh_48h") or 0)
        stale_48h = int(daily_section.get("stale_48h") or 0)
        missing = int(daily_section.get("missing") or (daily_section.get("freshness") or {}).get("none") or 0)
        fresh_gt48 = max(0, total_symbols - fresh_24 - fresh_48 - stale_48h - missing)

        snapshot["daily"] = {
            **daily_section,
            "fresh_24h": fresh_24,
            "fresh_48h": fresh_48,
            "fresh_gt48h": fresh_gt48,
            "stale_48h": stale_48h,
            "missing": missing,
            "count": daily_section.get("count", daily_section.get("daily_count")),
        }

        age_seconds = None
        if updated_at:
            try:
                age_seconds = (datetime.utcnow() - datetime.fromisoformat(updated_at)).total_seconds()
            except Exception:
                age_seconds = None

        snapshot["meta"] = {
            "visibility": _visibility_scope(),
            "exposed_to_all": settings.MARKET_DATA_SECTION_PUBLIC,
            "education": _coverage_education(),
            "actions": _coverage_actions(backfill_5m_enabled),
            "updated_at": updated_at,
            "snapshot_age_seconds": age_seconds,
            "source": source,
            "history": history_entries,
            "sparkline": sparkline_meta,
            "sla": sla_meta,
            "kpis": _kpi_cards(),
            "backfill_5m_enabled": backfill_5m_enabled,
        }
        return snapshot
    except Exception as e:
        logger.error(f"coverage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/coverage/backfill-5m-toggle")
async def get_backfill_5m_toggle(
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    svc = MarketDataService()
    return {"backfill_5m_enabled": _is_backfill_5m_enabled(svc)}


@router.post("/admin/coverage/backfill-5m-toggle")
async def set_backfill_5m_toggle(
    enabled: bool = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    svc = MarketDataService()
    try:
        svc.redis_client.set("coverage:backfill_5m_enabled", "true" if enabled else "false")
        return {"backfill_5m_enabled": enabled}
    except Exception as e:
        logger.error(f"toggle error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update 5m backfill toggle")


@router.post("/admin/coverage/backfill-stale-daily")
async def backfill_stale_daily(
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Backfill daily bars for symbols currently marked stale (>48h) in coverage snapshot.
    """
    svc = MarketDataService()
    session = get_db()()
    try:
        snap = svc.coverage_snapshot(session)
        stale = [s.get("symbol") for s in snap.get("daily", {}).get("stale", []) if s.get("symbol")]
        if not stale:
            return {"status": "ok", "backfilled": 0, "symbols": []}
        res = backfill_symbols(stale)
        return {"status": "ok", "backfilled": res.get("backfilled"), "errors": res.get("errors"), "symbols": stale}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/admin/coverage/refresh")
async def admin_refresh_coverage(
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    """Trigger the coverage health monitor to refresh Redis cache + history."""
    return _enqueue_task(monitor_coverage_health)


@router.get("/coverage/{symbol}")
async def get_symbol_coverage(
    symbol: str,
    db: Session = Depends(get_db),
    _viewer: User = Depends(get_market_data_viewer),
) -> Dict[str, Any]:
    """Return last bar timestamps for daily and 5m for a symbol."""
    try:
        sym = symbol.upper()
        last_daily = (
            db.query(PriceData.date)
            .filter(PriceData.symbol == sym, PriceData.interval == "1d")
            .order_by(PriceData.date.desc())
            .limit(1)
            .scalar()
        )
        last_m5 = (
            db.query(PriceData.date)
            .filter(PriceData.symbol == sym, PriceData.interval == "5m")
            .order_by(PriceData.date.desc())
            .limit(1)
            .scalar()
        )
        return {
            "symbol": sym,
            "last_daily": last_daily.isoformat() if last_daily else None,
            "last_5m": last_m5.isoformat() if last_m5 else None,
        }
    except Exception as e:
        logger.error(f"symbol coverage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/bootstrap")
async def admin_bootstrap_universe(
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    """Run the full bootstrap: refresh constituents → tracked → backfills → indicators → history."""
    return _enqueue_task(bootstrap_universe)


# =============================================================================
# Admin: 5m backfill, retention, jobs and tasks (RBAC)
# =============================================================================


@router.post("/backfill/5m")
async def post_backfill_5m(
    n_days: int = Query(5, ge=1, le=60),
    batch_size: int = Query(50, ge=10, le=200),
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    return _enqueue_task(backfill_5m_last_n_days, n_days=n_days, batch_size=batch_size)


@router.post("/retention/enforce")
async def post_retention_enforce(
    max_days_5m: int = Query(90, ge=7, le=365),
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    return _enqueue_task(enforce_price_data_retention, max_days_5m=max_days_5m)


@router.get("/admin/jobs")
async def admin_get_jobs(
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100000),
    all: bool = Query(False),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    total = db.query(JobRun).count()
    query = db.query(JobRun).order_by(JobRun.started_at.desc())
    if all:
        rows = query.all()
        return {"jobs": serialize_job_runs(rows), "total": total, "limit": total, "offset": 0}
    effective_limit = limit or 50
    rows = query.offset(offset).limit(effective_limit).all()
    return {"jobs": serialize_job_runs(rows), "total": total, "limit": effective_limit, "offset": offset}


@router.get("/admin/tasks")
async def admin_list_tasks(
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    """Discover available market-data tasks (subset)."""
    tasks = [
        "update_tracked_symbol_cache",
        "backfill_new_tracked",
        "backfill_last_200_bars",
        "backfill_index_universe",
        "refresh_index_constituents",
        "recompute_indicators_universe",
        "record_daily_history",
        "refresh_single_symbol",
        "backfill_5m_last_n_days",
        "backfill_5m_for_symbols",
        "enforce_price_data_retention",
    ]
    return {"tasks": tasks}


@router.post("/admin/tasks/run")
async def admin_run_task(
    task_name: str = Query(...),
    symbols: List[str] | None = Query(None),
    n_days: int | None = Query(None),
    admin_user: User = Depends(get_admin_user),
) -> Dict[str, Any]:
    """Manually trigger selected tasks."""
    if task_name == "backfill_5m_for_symbols":
        if not symbols:
            raise HTTPException(status_code=400, detail="symbols required")
        return _enqueue_task(
            backfill_5m_for_symbols,
            [s.upper() for s in symbols if s],
            n_days=n_days or 5,
        )
    if task_name == "backfill_5m_last_n_days":
        return _enqueue_task(backfill_5m_last_n_days, n_days=n_days or 5)
    raise HTTPException(status_code=400, detail="unsupported task or not exposed here")

