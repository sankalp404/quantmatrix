"""Dashboard endpoint that merges summary, positions, dividends for front-end /portfolio/dashboard."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from backend.database import get_db
from backend.models.user import User
from backend.models.position import Position
from backend.models.transaction import Dividend

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard(
    user_id: int | None = Query(None),
    days: int = Query(365, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    """Simple dashboard summary until full analytics ready."""
    try:
        user = (
            db.query(User).first()
            if user_id is None
            else db.query(User).filter(User.id == user_id).first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # positions
        pos_models = db.query(Position).filter(Position.user_id == user.id).all()
        positions = [
            {
                "symbol": p.symbol,
                "quantity": float(p.quantity),
                "market_value": float(p.market_value or 0),
                "unrealized_pnl": float(p.unrealized_pnl or 0),
            }
            for p in pos_models
        ]
        total_value = sum(p["market_value"] for p in positions)
        total_cost = sum(float(p.total_cost_basis or 0) for p in pos_models)

        # dividends last X days
        cutoff = datetime.utcnow() - timedelta(days=days)
        divs = (
            db.query(Dividend)
            .filter(
                Dividend.account_id.in_(
                    db.query(Position.account_id).filter(Position.user_id == user.id)
                ),
                Dividend.ex_date >= cutoff,
            )
            .count()
        )

        summary = {
            "total_market_value": total_value,
            "total_cost_basis": total_cost,
            "unrealized_pnl": total_value - total_cost if total_cost else 0,
            "positions_count": len(positions),
            "dividends_count_last_period": divs,
        }
        return {
            "status": "success",
            "data": {
                "user_id": user.id,
                "summary": summary,
                "positions": positions,
                "generated_at": datetime.utcnow().isoformat(),
                # Minimal placeholders to satisfy frontend shape
                "total_value": total_value,
                "total_unrealized_pnl": summary["unrealized_pnl"],
                "total_unrealized_pnl_pct": (
                    (summary["unrealized_pnl"] / summary["total_cost_basis"] * 100)
                    if summary["total_cost_basis"]
                    else 0
                ),
                "day_change": 0,
                "day_change_pct": 0,
                "accounts_summary": [],
                "accounts_count": 0,
                "sector_allocation": [],
                "top_performers": [],
                "top_losers": [],
                "holdings_count": len(positions),
                "last_updated": datetime.utcnow().isoformat(),
                "brokerages": ["IBKR", "TASTYTRADE"],
            },
        }
    except Exception as e:
        logger.error(f"dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
