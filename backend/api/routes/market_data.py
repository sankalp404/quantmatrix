"""
QuantMatrix V1 - Clean Market Data Routes
Focused endpoints for market data and analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# dependencies
from backend.database import get_db
from backend.models.user import User
from backend.services.market.market_data_service import MarketDataService
from backend.models.position import Position
from backend.models.tax_lot import TaxLot
from backend.services.analysis.atr_engine import (
    atr_engine,
)  # Updated: ATR moved to atr_engine.py
from backend.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# MARKET DATA ENDPOINTS (Clean & Focused)
# =============================================================================


@router.get("/price/{symbol}")
async def get_current_price(
    symbol: str, user: User = Depends(get_current_user)
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


@router.get("/atr/{symbol}")
async def get_atr_data(
    symbol: str,
    periods: int = Query(14, description="ATR calculation periods"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get ATR data for a symbol."""
    try:
        atr_data = await atr_engine.calculate_options_atr(symbol)

        return {
            "symbol": symbol,
            "atr_data": atr_data,
            "periods": periods,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ ATR error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PLACEHOLDER ROUTES (To be implemented)
# =============================================================================


@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    days: int = Query(30, description="Number of days"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get historical price data."""
    # TODO: Implement with market data service
    return {
        "symbol": symbol,
        "message": "Historical data endpoint - to be implemented",
        "days": days,
    }


# =============================================================================
# PRICE REFRESH (Positions & Tax Lots)
# =============================================================================


@router.post("/prices/refresh")
async def refresh_prices(
    account_id: Optional[int] = Query(
        default=None, description="Broker account ID to scope refresh"
    ),
    symbols: Optional[List[str]] = Query(
        default=None, description="Optional subset of symbols to refresh"
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Refresh current prices and recompute P&L for positions and tax lots.

    - If account_id provided, limits to that broker account
    - If symbols provided, limits to those symbols
    """
    try:
        market_service = MarketDataService()

        # Load target positions
        q = db.query(Position).filter(Position.quantity != 0)
        if account_id is not None:
            q = q.filter(Position.account_id == account_id)
        if symbols:
            q = q.filter(Position.symbol.in_(symbols))
        positions: List[Position] = q.all()

        if not positions:
            return {"updated_positions": 0, "updated_tax_lots": 0, "symbols": []}

        unique_symbols = sorted({p.symbol for p in positions if p.symbol})

        # Fetch prices concurrently
        import asyncio as _asyncio

        price_tasks = [market_service.get_current_price(sym) for sym in unique_symbols]
        prices = await _asyncio.gather(*price_tasks, return_exceptions=True)
        symbol_to_price = {}
        for sym, price in zip(unique_symbols, prices):
            try:
                if isinstance(price, (int, float)) and price > 0:
                    symbol_to_price[sym] = float(price)
            except Exception:
                continue

        # Update positions
        updated_positions = 0
        for p in positions:
            price = symbol_to_price.get(p.symbol)
            if price is None:
                continue
            try:
                quantity_abs = float(abs(p.quantity or 0))
                total_cost = float(p.total_cost_basis or 0)
                market_value = quantity_abs * price
                unrealized = market_value - total_cost
                unrealized_pct = (
                    (unrealized / total_cost * 100) if total_cost > 0 else 0.0
                )

                p.current_price = price
                p.market_value = market_value
                p.unrealized_pnl = unrealized
                p.unrealized_pnl_pct = unrealized_pct
                updated_positions += 1
            except Exception:
                continue

        # Update tax lots for same scope
        tq = db.query(TaxLot)
        if account_id is not None:
            tq = tq.filter(TaxLot.account_id == account_id)
        if symbols:
            tq = tq.filter(TaxLot.symbol.in_(symbols))
        lots: List[TaxLot] = tq.all()

        updated_lots = 0
        for lot in lots:
            price = symbol_to_price.get(lot.symbol)
            if price is None:
                continue
            try:
                qty_abs = float(abs(lot.quantity or 0))
                cost_basis = float(lot.cost_basis or 0)
                market_value = qty_abs * price
                unrealized = market_value - cost_basis
                unrealized_pct = (
                    (unrealized / cost_basis * 100) if cost_basis > 0 else 0.0
                )

                lot.current_price = price
                lot.market_value = market_value
                lot.unrealized_pnl = unrealized
                lot.unrealized_pnl_pct = unrealized_pct
                updated_lots += 1
            except Exception:
                continue

        db.flush()
        db.commit()

        return {
            "updated_positions": updated_positions,
            "updated_tax_lots": updated_lots,
            "symbols": list(symbol_to_price.keys()),
        }

    except Exception as e:
        logger.error(f"❌ Price refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# Moving Averages & Buckets
# ============================


@router.get("/technical/moving-averages/{symbol}")
async def get_moving_averages(symbol: str) -> Dict[str, Any]:
    try:
        svc = MarketDataService()
        result = await svc.get_moving_averages(symbol.upper())
        if not result:
            raise HTTPException(status_code=404, detail="No data")
        return {"symbol": symbol.upper(), "moving_averages": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MA error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technical/ma-bucket/{symbol}")
async def get_ma_bucket(symbol: str) -> Dict[str, Any]:
    try:
        svc = MarketDataService()
        result = await svc.classify_ma_bucket(symbol.upper())
        return result
    except Exception as e:
        logger.error(f"MA bucket error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================
# Stage Analysis
# ============================


@router.get("/technical/stage/{symbol}")
async def get_stage(symbol: str) -> Dict[str, Any]:
    try:
        svc = MarketDataService()
        result = await svc.get_weinstein_stage(symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Stage analysis error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
