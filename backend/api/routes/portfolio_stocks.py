"""Portfolio stocks endpoints for frontend (renamed from holdings)."""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from backend.database import get_db
from backend.models.position import Position
from backend.models import BrokerAccount
from backend.models.tax_lot import TaxLot
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stocks", response_model=Dict[str, Any])
async def get_stocks(
    user_id: int | None = Query(None, description="User ID (optional)"),
    account_id: str | None = Query(
        None, description="Filter by account number (e.g., U19490886)"
    ),
    db: Session = Depends(get_db),
):
    """Return equity positions for Stocks page (unauthenticated for now)."""
    try:
        user = (
            db.query(User).first()
            if user_id is None
            else db.query(User).filter(User.id == user_id).first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        query = (
            db.query(Position)
            .join(BrokerAccount, Position.account_id == BrokerAccount.id)
            .filter(
                Position.user_id == user.id,
                Position.instrument_type == "STOCK",
                Position.quantity != 0,
            )
        )
        if account_id:
            query = query.filter(BrokerAccount.account_number == account_id)
        positions = query.all()

        result: List[Dict[str, Any]] = []
        for p in positions:
            result.append(
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "account_number": p.account.account_number if p.account else None,
                    "broker": "IBKR",
                    "shares": float(p.quantity),
                    "current_price": float(p.current_price or 0),
                    "market_value": float(p.market_value or 0),
                    "cost_basis": float(p.total_cost_basis or 0),
                    "average_cost": float(p.average_cost or 0),
                    "unrealized_pnl": float(p.unrealized_pnl or 0),
                    "unrealized_pnl_pct": float(p.unrealized_pnl_pct or 0),
                    "day_pnl": float(p.day_pnl or 0),
                    "day_pnl_pct": float(p.day_pnl_pct or 0),
                    "sector": p.sector or "",
                    "industry": p.industry or "",
                    "last_updated": (
                        p.position_updated_at.isoformat()
                        if p.position_updated_at
                        else None
                    ),
                }
            )

        return {"status": "success", "data": {"total": len(result), "stocks": result}}
    except Exception as e:
        logger.error(f"Stocks endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{position_id}/tax-lots", response_model=Dict[str, Any])
async def get_tax_lots_for_stock(
    position_id: int = Path(..., description="Position ID"),
    db: Session = Depends(get_db),
):
    """Return tax lots associated with a Position (by FK)."""
    try:
        position = db.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        lots = (
            db.query(TaxLot)
            .filter(
                TaxLot.symbol == position.symbol,
                TaxLot.account_id == position.account_id,
            )
            .all()
        )
        result = []
        for lot in lots:
            result.append(
                {
                    "id": lot.id,
                    "shares": float(lot.quantity),
                    "shares_remaining": float(lot.quantity),
                    "purchase_date": (
                        lot.acquisition_date.isoformat()
                        if lot.acquisition_date
                        else None
                    ),
                    "cost_per_share": float(lot.cost_per_share or 0),
                    "current_value": float(lot.market_value or 0),
                    "unrealized_pnl": float(lot.unrealized_pnl or 0),
                    "unrealized_pnl_pct": float(lot.unrealized_pnl_pct or 0),
                    "is_long_term": (lot.holding_period or 0) >= 365,
                    "days_held": lot.holding_period or 0,
                }
            )
        return {
            "status": "success",
            "data": {"tax_lots": result, "processing_time_ms": 0},
        }
    except Exception as e:
        logger.error(f"Tax lots endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
