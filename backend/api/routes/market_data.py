"""
QuantMatrix V1 - Market Data Routes

Clean, service-driven endpoints for prices, snapshots, tracked universe, backfills,
indicator recompute, and history. DB-first strategy: compute from local `price_data`.
Providers are used only for OHLCV backfills (paid provider prioritized).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from datetime import datetime

# dependencies
from backend.database import get_db
from backend.models.user import User
from backend.services.market.market_data_service import MarketDataService
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
from backend.api.dependencies import get_optional_user
from backend.models.index_constituent import IndexConstituent

logger = logging.getLogger(__name__)

router = APIRouter()

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
    task = refresh_index_constituents.delay()
    return {"task_id": task.id}


@router.get("/tracked")
async def get_tracked() -> Dict[str, Any]:
    from backend.services.market.market_data_service import market_data_service

    r = market_data_service.redis_client
    import json as _json

    all_raw = r.get("tracked:all")
    new_raw = r.get("tracked:new")
    return {
        "all": _json.loads(all_raw) if all_raw else [],
        "new": _json.loads(new_raw) if new_raw else [],
    }


@router.post("/tracked/update")
async def post_update_tracked(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    task = update_tracked_symbol_cache.delay()
    return {"task_id": task.id}


# =============================================================================
# Backfills (OHLCV) and Indicators
# =============================================================================


@router.post("/backfill/index-universe")
async def post_backfill_index_universe(
    batch_size: int = Query(20, ge=5, le=100),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Bootstrap helper: enqueue batched backfill for SP500/NASDAQ100/DOW30 constituents."""
    task = backfill_index_universe.delay(batch_size=batch_size)
    return {"task_id": task.id}


@router.post("/backfill/tracked-new")
async def post_backfill_tracked_new(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    task = backfill_new_tracked.delay()
    return {"task_id": task.id}


@router.post("/backfill/last-200")
async def post_backfill_last200(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    task = backfill_last_200_bars.delay()
    return {"task_id": task.id}


@router.post("/backfill/symbols")
async def post_backfill_symbols(
    symbols: List[str] = Query(..., description="Repeat the parameter to provide multiple symbols"),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Enqueue delta backfill for a provided list of symbols."""
    if not symbols:
        raise HTTPException(status_code=400, detail="symbols required")
    task = backfill_symbols.delay([s.upper() for s in symbols if s])
    return {"task_id": task.id}


@router.post("/indicators/recompute-universe")
async def post_recompute_universe(
    batch_size: int = Query(50, ge=10, le=200),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    task = recompute_indicators_universe.delay(batch_size)
    return {"task_id": task.id}


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
    task = refresh_single_symbol.delay(symbol.upper())
    return {"task_id": task.id}


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

