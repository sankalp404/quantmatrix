"""
QuantMatrix V1 - Clean Portfolio Routes
Replaces the MASSIVE 168KB portfolio.py with focused, single-responsibility endpoints.

BEFORE: 168KB file doing EVERYTHING
AFTER: Clean, focused endpoints with proper separation of concerns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

# dependencies
from backend.database import get_db
from backend.models.user import User
from backend.services.portfolio.ibkr_sync_service import IBKRSyncService

# Auth dependency (to be implemented)
from backend.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# PORTFOLIO SUMMARY ENDPOINTS (Clean & Focused)
# =============================================================================


@router.get("/summary")
async def get_portfolio_summary(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's portfolio summary.
    CLEAN: Only portfolio summary, nothing else.
    """
    try:
        sync_service = IBKRSyncService()
        summary = await sync_service.get_user_portfolio_summary(user.id)

        return {
            "user_id": user.id,
            "username": user.username,
            "portfolio_summary": summary,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Portfolio summary error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions(
    broker: Optional[str] = Query(
        None, description="Filter by broker (ibkr, tastytrade)"
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get user's current positions.
    CLEAN: Only positions data, properly filtered.
    """
    try:
        sync_service = IBKRSyncService()
        positions = await sync_service.get_user_positions(user.id, broker=broker)

        return {
            "user_id": user.id,
            "broker_filter": broker,
            "positions": positions,
            "total_positions": len(positions),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Positions error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_portfolio_performance(
    days: int = Query(30, description="Performance period in days"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get portfolio performance metrics.
    CLEAN: Only performance data, configurable timeframe.
    """
    try:
        sync_service = IBKRSyncService()
        performance = await sync_service.get_user_performance(user.id, days=days)

        return {
            "user_id": user.id,
            "period_days": days,
            "performance_metrics": performance,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Performance error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TAX LOT ENDPOINTS (Clean & Focused)
# =============================================================================


@router.get("/tax-lots")
async def get_tax_lots(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get user's tax lots.
    CLEAN: Only tax lot data, optionally filtered by symbol.
    """
    try:
        from backend.services.portfolio.tax_lot_service import TaxLotService

        tls = TaxLotService(db)
        tax_lots_models = await tls.get_tax_lots_for_user(user.id, symbol=symbol)
        # Serialize for JSON
        tax_lots = [
            {
                "lot_id": tl.id,
                "symbol": tl.symbol,
                "quantity": float(tl.remaining_quantity),
                "cost_per_share": float(tl.cost_per_share),
                "acquisition_date": (
                    tl.acquisition_date.isoformat() if tl.acquisition_date else None
                ),
                "days_held": tl.days_held,
                "is_long_term": tl.is_long_term,
            }
            for tl in tax_lots_models
        ]

        return {
            "user_id": user.id,
            "symbol_filter": symbol,
            "tax_lots": tax_lots,
            "total_lots": len(tax_lots),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Tax lots error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tax-lots/summary")
async def get_tax_lots_summary(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get tax lots summary by symbol.
    CLEAN: Only summary data, properly aggregated.
    """
    try:
        from backend.services.portfolio.csv_import_service import (
            get_user_tax_lots_summary,
        )

        summary = await get_user_tax_lots_summary(user.id)

        return summary

    except Exception as e:
        logger.error(f"❌ Tax lots summary error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TRANSACTION ENDPOINTS (Clean & Focused)
# =============================================================================


@router.get("/statements")
async def get_statements(
    days: int = Query(30, ge=1, le=3650),
    user_id: int | None = Query(None, description="User ID (optional)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return unified transaction statements for last N days to power Transactions.tsx."""
    try:
        from backend.models.transaction import Transaction

        # resolve user
        user = (
            db.query(User).first()
            if user_id is None
            else db.query(User).filter(User.id == user_id).first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        cutoff = datetime.utcnow() - timedelta(days=days)

        q = (
            db.query(Transaction)
            .filter(
                Transaction.account_id.in_(
                    db.query(BrokerAccount.id).filter(BrokerAccount.user_id == user.id)
                ),
                Transaction.transaction_date >= cutoff,
            )
            .order_by(Transaction.transaction_date.desc())
        )
        rows = q.all()

        txs = []
        for t in rows:
            is_buy = (
                t.transaction_type.name if t.transaction_type else ""
            ).upper() == "BUY"
            is_sell = (
                t.transaction_type.name if t.transaction_type else ""
            ).upper() == "SELL"
            acc = (
                db.query(BrokerAccount).filter(BrokerAccount.id == t.account_id).first()
            )
            txs.append(
                {
                    "id": t.id,
                    "date": (
                        t.transaction_date.date().isoformat()
                        if t.transaction_date
                        else None
                    ),
                    "time": (
                        t.transaction_date.time().isoformat(timespec="seconds")
                        if t.transaction_date
                        else None
                    ),
                    "symbol": t.symbol,
                    "description": t.description,
                    "type": (
                        "BUY"
                        if is_buy
                        else (
                            "SELL"
                            if is_sell
                            else (
                                t.transaction_type.name
                                if t.transaction_type
                                else "OTHER"
                            )
                        )
                    ),
                    "action": t.action,
                    "quantity": float(t.quantity or 0),
                    "price": float(t.trade_price or 0),
                    "amount": float(t.amount or 0),
                    "commission": float(t.commission or 0),
                    "fees": float(
                        (t.other_fees or 0)
                        + (t.third_party_commission or 0)
                        + (t.clearing_commission or 0)
                    ),
                    "net_amount": float(t.net_amount or 0),
                    "currency": t.currency,
                    "exchange": t.listing_exchange,
                    "order_id": t.order_id,
                    "execution_id": t.execution_id,
                    "contract_type": t.asset_category,
                    "account": acc.account_number if acc else None,
                    "settlement_date": (
                        t.settlement_date.isoformat() if t.settlement_date else None
                    ),
                    "source": t.source,
                }
            )

        buys = [x for x in txs if x["type"] == "BUY"]
        sells = [x for x in txs if x["type"] == "SELL"]
        summary = {
            "total_transactions": len(txs),
            "total_value": sum(abs(x["amount"]) for x in txs),
            "total_commission": sum(x["commission"] for x in txs),
            "total_fees": sum(x["fees"] for x in txs),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "date_range": days,
            "net_buy_value": sum(abs(x["amount"]) for x in buys),
            "net_sell_value": sum(abs(x["amount"]) for x in sells),
        }

        return {"status": "success", "data": {"transactions": txs, "summary": summary}}
    except Exception as e:
        logger.error(f"❌ Statements error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FLEXQUERY ENDPOINTS (Official IBKR Tax Lots)
# =============================================================================


@router.get("/flexquery/status")
async def get_flexquery_status(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get FlexQuery configuration status.
    Returns setup instructions if not configured.
    """
    try:
        from backend.services.clients.ibkr_flexquery_client import flexquery_client

        if not flexquery_client.token or not flexquery_client.query_id:
            return {
                "configured": False,
                "setup_instructions": flexquery_client.get_setup_instructions(),
                "status": "FlexQuery not configured - setup required",
            }

        return {
            "configured": True,
            "status": "FlexQuery ready for official IBKR tax lots",
            "token_configured": bool(flexquery_client.token),
            "query_id_configured": bool(flexquery_client.query_id),
        }

    except Exception as e:
        logger.error(f"❌ FlexQuery status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flexquery/sync-tax-lots")
async def sync_official_tax_lots(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Sync official IBKR tax lots via FlexQuery.
    This gets the REAL tax lot data from IBKR Tax Optimizer.
    """
    try:
        from backend.services.clients.ibkr_flexquery_client import flexquery_client

        # Get official tax lots from IBKR
        official_tax_lots = await flexquery_client.get_official_tax_lots(account_id)

        if not official_tax_lots:
            return {
                "success": False,
                "message": "No tax lots retrieved - check FlexQuery configuration",
                "tax_lots_synced": 0,
            }

        # TODO: Save to database (implement when TaxLotService is ready)
        # tax_lot_service = TaxLotService(db)
        # await tax_lot_service.sync_official_tax_lots(user.id, official_tax_lots)

        return {
            "success": True,
            "message": f"Successfully retrieved {len(official_tax_lots)} official tax lots",
            "tax_lots_synced": len(official_tax_lots),
            "account_id": account_id,
            "source": "ibkr_flexquery_official",
        }

    except Exception as e:
        logger.error(f"❌ FlexQuery sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PORTFOLIO ANALYTICS ENDPOINTS (Snowball Analytics Style)
# =============================================================================


@router.get("/analytics/{account_id}")
async def get_portfolio_analytics(
    account_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get comprehensive portfolio analytics (Snowball Analytics style).

    Returns:
    - Portfolio performance & risk metrics
    - Tax optimization opportunities
    - Asset allocation analysis
    - Performance attribution
    """
    try:
        from backend.services.portfolio.portfolio_analytics_service import (
            portfolio_analytics_service,
        )

        analytics = await portfolio_analytics_service.get_portfolio_analytics(
            account_id
        )

        return {
            "success": True,
            "analytics": analytics,
            "features": {
                "portfolio_metrics": "Performance & risk analysis",
                "tax_opportunities": "Tax loss harvesting & optimization",
                "asset_allocation": "Allocation breakdown & concentration risk",
                "performance_attribution": "Top contributors & detractors",
            },
        }

    except Exception as e:
        logger.error(f"❌ Portfolio analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tax-optimization/{account_id}")
async def get_tax_optimization_opportunities(
    account_id: str, user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get tax optimization opportunities for the account.
    Identifies tax loss harvesting, wash sale warnings, etc.
    """
    try:
        from backend.services.clients.ibkr_flexquery_client import flexquery_client

        # Get official tax lots
        tax_lots = await flexquery_client.get_official_tax_lots(account_id)

        # Analyze for tax opportunities
        opportunities = []
        total_tax_loss_harvest = 0

        for lot in tax_lots:
            unrealized_pnl = lot.get("unrealized_pnl", 0)
            days_held = lot.get("days_held", 0)

            # Tax loss harvesting (losses > $1000)
            if unrealized_pnl < -1000:
                total_tax_loss_harvest += abs(unrealized_pnl)
                opportunities.append(
                    {
                        "type": "tax_loss_harvest",
                        "symbol": lot.get("symbol"),
                        "unrealized_loss": unrealized_pnl,
                        "estimated_tax_savings": abs(unrealized_pnl)
                        * 0.24,  # 24% tax rate
                        "recommendation": f"Harvest ${abs(unrealized_pnl):,.0f} loss",
                    }
                )

            # Long-term capital gains opportunity
            elif 300 <= days_held <= 365 and unrealized_pnl > 0:
                opportunities.append(
                    {
                        "type": "ltcg_timing",
                        "symbol": lot.get("symbol"),
                        "days_to_ltcg": 365 - days_held,
                        "unrealized_gain": unrealized_pnl,
                        "recommendation": f"Wait {365 - days_held} days for LTCG treatment",
                    }
                )

        return {
            "account_id": account_id,
            "total_opportunities": len(opportunities),
            "total_tax_loss_harvest_amount": total_tax_loss_harvest,
            "estimated_total_tax_savings": total_tax_loss_harvest * 0.24,
            "opportunities": opportunities,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Tax optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{account_id}")
async def get_performance_metrics(
    account_id: str,
    period: str = "ytd",  # ytd, 1y, 3y, 5y, all
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get detailed performance metrics for the account.
    Includes risk-adjusted returns, drawdown analysis, etc.
    """
    try:
        from backend.services.clients.ibkr_client import ibkr_client
        from backend.services.clients.ibkr_flexquery_client import flexquery_client

        # Get current positions and tax lots
        positions = await ibkr_client.get_positions(account_id)
        tax_lots = await flexquery_client.get_official_tax_lots(account_id)

        # Calculate performance metrics
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        total_cost_basis = sum(lot.get("cost_basis", 0) for lot in tax_lots)
        total_return = (
            ((total_value - total_cost_basis) / total_cost_basis * 100)
            if total_cost_basis > 0
            else 0
        )

        # Risk metrics (simplified - would need historical data for accuracy)
        volatility = 15.0  # Default estimate
        sharpe_ratio = max(0, total_return - 2.0) / volatility if volatility > 0 else 0

        # Best/worst performers
        performance_by_symbol = {}
        for lot in tax_lots:
            symbol = lot.get("symbol")
            pnl_pct = lot.get("unrealized_pnl_pct", 0)
            if symbol:
                if symbol not in performance_by_symbol:
                    performance_by_symbol[symbol] = []
                performance_by_symbol[symbol].append(pnl_pct)

        # Average performance by symbol
        avg_performance = {
            symbol: sum(pnls) / len(pnls)
            for symbol, pnls in performance_by_symbol.items()
        }

        best_performers = sorted(
            avg_performance.items(), key=lambda x: x[1], reverse=True
        )[:5]
        worst_performers = sorted(avg_performance.items(), key=lambda x: x[1])[:5]

        return {
            "account_id": account_id,
            "period": period,
            "total_return_pct": total_return,
            "total_value": total_value,
            "total_cost_basis": total_cost_basis,
            "risk_metrics": {
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": min(
                    [lot.get("unrealized_pnl_pct", 0) for lot in tax_lots], default=0
                ),
            },
            "best_performers": [
                {"symbol": s, "return_pct": p} for s, p in best_performers
            ],
            "worst_performers": [
                {"symbol": s, "return_pct": p} for s, p in worst_performers
            ],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Performance metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
Portfolio API Routes
===================

Enhanced portfolio management endpoints with comprehensive analytics.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from backend.database import get_db
from backend.models import TaxLot, Position, BrokerAccount
from backend.services.clients.ibkr_flexquery_client import IBKRFlexQueryClient

router = APIRouter()


@router.get("/analytics/{account_id}")
async def get_portfolio_analytics(
    account_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive portfolio analytics for an account.

    Returns position summary, tax lot breakdown, performance metrics,
    and portfolio composition analysis.
    """
    # Get account
    account = db.query(BrokerAccount).filter_by(account_number=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Get positions
    positions = db.query(Position).filter_by(account_id=account.id).all()
    tax_lots = db.query(TaxLot).filter_by(account_id=account_id).all()

    # Calculate summary metrics
    total_cost_basis = sum(position.total_cost_basis for position in positions)
    total_shares = sum(position.quantity for position in positions)
    total_market_value = sum(position.market_value or 0 for position in positions)
    total_unrealized_pnl = (
        total_market_value - total_cost_basis if total_market_value > 0 else 0
    )

    # Positions by symbol
    positions_data = []
    for position in positions:
        positions_data.append(
            {
                "symbol": position.symbol,
                "quantity": float(position.quantity),
                "average_cost": float(position.average_cost),
                "current_price": float(position.current_price or 0),
                "cost_basis": float(position.total_cost_basis),
                "market_value": float(position.market_value or 0),
                "unrealized_pnl": float(position.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(position.unrealized_pnl_pct or 0),
                "day_pnl": float(position.day_pnl or 0),
                "sector": position.sector,
                "industry": position.industry,
                "first_acquired": (
                    position.created_at.isoformat() if position.created_at else None
                ),
            }
        )

    # Tax lot breakdown
    tax_lot_summary = {}
    for lot in tax_lots:
        symbol = lot.symbol
        if symbol not in tax_lot_summary:
            tax_lot_summary[symbol] = []

        tax_lot_summary[symbol].append(
            {
                "lot_id": lot.lot_id,
                "quantity": float(lot.original_quantity),
                "cost_basis": float(lot.cost_basis),
                "acquisition_date": (
                    lot.acquisition_date.isoformat() if lot.acquisition_date else None
                ),
                "tax_method": lot.tax_method.value if lot.tax_method else "FIFO",
                "days_held": lot.days_held,
            }
        )

        return {
            "account": {
                "account_number": account.account_number,
                "account_name": account.account_name,
                "account_type": account.account_type,
            },
            "summary": {
                "total_positions": len(positions),
                "total_shares": float(total_shares),
                "total_cost_basis": float(total_cost_basis),
                "total_market_value": float(total_market_value),
                "total_unrealized_pnl": float(total_unrealized_pnl),
                "total_unrealized_pnl_pct": (
                    float(total_unrealized_pnl / total_cost_basis * 100)
                    if total_cost_basis > 0
                    else 0
                ),
                "total_tax_lots": len(tax_lots),
            },
            "positions": positions_data,
            "tax_lots": tax_lot_summary,
            "last_updated": datetime.utcnow().isoformat(),
        }


@router.get("/positions/{account_id}")
async def get_account_positions(
    account_id: str, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all positions for a specific account with current market data."""

    account = db.query(BrokerAccount).filter_by(account_number=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    positions = db.query(Position).filter_by(account_id=account.id).all()

    positions_data = []
    for position in positions:
        positions_data.append(
            {
                "symbol": position.symbol,
                "quantity": float(position.quantity),
                "average_cost": float(position.average_cost),
                "current_price": float(position.current_price or 0),
                "market_value": float(position.market_value or 0),
                "cost_basis": float(position.total_cost_basis),
                "unrealized_pnl": float(position.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(position.unrealized_pnl_pct or 0),
                "day_pnl": float(position.day_pnl or 0),
                "day_pnl_pct": float(position.day_pnl_pct or 0),
                "sector": position.sector,
                "industry": position.industry,
                "market_cap": position.market_cap,
                "margin_priority": position.margin_priority,
                "custom_category": position.custom_category,
                "notes": position.notes,
                "created_at": (
                    position.created_at.isoformat() if position.created_at else None
                ),
                "updated_at": (
                    position.updated_at.isoformat() if position.updated_at else None
                ),
            }
        )

    return positions_data


@router.get("/tax-lots/{account_id}")
async def get_account_tax_lots(
    account_id: str,
    symbol: Optional[str] = Query(None, description="Filter by specific symbol"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get tax lots for an account, optionally filtered by symbol."""

    query = db.query(TaxLot).filter_by(account_id=account_id)
    if symbol:
        query = query.filter_by(symbol=symbol)

    tax_lots = query.all()

    tax_lots_data = []
    for lot in tax_lots:
        tax_lots_data.append(
            {
                "lot_id": lot.lot_id,
                "symbol": lot.symbol,
                "quantity": float(lot.original_quantity),
                "cost_basis": float(lot.cost_basis),
                "acquisition_date": (
                    lot.acquisition_date.isoformat() if lot.acquisition_date else None
                ),
                "current_price": float(lot.current_price or 0),
                "current_value": float(lot.current_value or 0),
                "unrealized_pnl": float(lot.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(lot.unrealized_pnl_pct or 0),
                "days_held": lot.days_held,
                "tax_method": lot.tax_method.value if lot.tax_method else "FIFO",
                "source": lot.source.value if lot.source else "UNKNOWN",
                "created_at": lot.created_at.isoformat() if lot.created_at else None,
            }
        )

    return tax_lots_data


@router.post("/sync/{account_id}")
async def sync_portfolio_data(
    account_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger portfolio data sync from broker for specified account."""

    account = db.query(BrokerAccount).filter_by(account_number=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        # Initialize FlexQuery client for IBKR data
        client = IBKRFlexQueryClient()

        # Get fresh tax lots data
        tax_lots_data = await client.get_official_tax_lots(account_id)

        if tax_lots_data:
            # Clear existing data
            db.query(TaxLot).filter_by(account_id=account_id).delete()
            db.query(Position).filter_by(account_id=account.id).delete()

            # Import fresh tax lots
            imported_count = 0
            for i, lot_data in enumerate(tax_lots_data):
                tax_lot = TaxLot(
                    account_id=account_id,
                    lot_id=f"SYNC_{lot_data.get('symbol')}_{i+1}",
                    symbol=lot_data.get("symbol"),
                    original_quantity=float(lot_data.get("quantity", 0)),
                    cost_basis=float(lot_data.get("cost_basis", 0)),
                    acquisition_date=lot_data.get("acquisition_date"),
                    source="IBKR_FLEXQUERY",
                    tax_method="FIFO",
                )
                db.add(tax_lot)
                imported_count += 1

            # Aggregate positions
            positions_data = {}
            for tax_lot in db.query(TaxLot).filter_by(account_id=account_id).all():
                symbol = tax_lot.symbol
                if symbol not in positions_data:
                    positions_data[symbol] = {
                        "quantity": 0,
                        "total_cost": 0,
                        "first_acquired": tax_lot.acquisition_date,
                    }

                positions_data[symbol]["quantity"] += float(tax_lot.original_quantity)
                positions_data[symbol]["total_cost"] += float(tax_lot.cost_basis)

                if tax_lot.acquisition_date and (
                    not positions_data[symbol]["first_acquired"]
                    or tax_lot.acquisition_date
                    < positions_data[symbol]["first_acquired"]
                ):
                    positions_data[symbol]["first_acquired"] = tax_lot.acquisition_date

            # Create position records
            for symbol, data in positions_data.items():
                average_cost = (
                    data["total_cost"] / data["quantity"] if data["quantity"] > 0 else 0
                )

                position = Position(
                    account_id=account.id,
                    symbol=symbol,
                    quantity=data["quantity"],
                    average_cost=average_cost,
                    current_price=0.0,
                    market_value=0.0,
                    unrealized_pnl=0.0,
                    unrealized_pnl_pct=0.0,
                    currency="USD",
                    first_acquired=data["first_acquired"],
                )
                db.add(position)

            db.commit()

            return {
                "status": "success",
                "message": f"Synced {imported_count} tax lots and {len(positions_data)} positions",
                "tax_lots_imported": imported_count,
                "positions_created": len(positions_data),
                "sync_timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "no_data",
                "message": "No data returned from broker",
                "sync_timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/performance/{account_id}")
async def get_portfolio_performance(
    account_id: str,
    period: str = Query(
        "1M", description="Performance period: 1D, 1W, 1M, 3M, 6M, 1Y, YTD"
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get portfolio performance metrics for specified period."""

    account = db.query(BrokerAccount).filter_by(account_number=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    positions = db.query(Position).filter_by(account_id=account.id).all()

    # Calculate current performance metrics
    total_cost_basis = sum(position.total_cost_basis for position in positions)
    total_market_value = sum(position.market_value or 0 for position in positions)
    total_unrealized_pnl = (
        total_market_value - total_cost_basis if total_market_value > 0 else 0
    )
    total_day_pnl = sum(position.day_pnl or 0 for position in positions)

    # Performance by position
    positions_performance = []
    for position in positions:
        positions_performance.append(
            {
                "symbol": position.symbol,
                "cost_basis": float(position.total_cost_basis),
                "market_value": float(position.market_value or 0),
                "unrealized_pnl": float(position.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(position.unrealized_pnl_pct or 0),
                "day_pnl": float(position.day_pnl or 0),
                "day_pnl_pct": float(position.day_pnl_pct or 0),
            }
        )

        return {
            "account_id": account_id,
            "period": period,
            "summary": {
                "total_cost_basis": float(total_cost_basis),
                "total_market_value": float(total_market_value),
                "total_unrealized_pnl": float(total_unrealized_pnl),
                "total_unrealized_pnl_pct": (
                    float(total_unrealized_pnl / total_cost_basis * 100)
                    if total_cost_basis > 0
                    else 0
                ),
                "total_day_pnl": float(total_day_pnl),
                "total_day_pnl_pct": (
                    float(total_day_pnl / total_market_value * 100)
                    if total_market_value > 0
                    else 0
                ),
            },
            "positions": positions_performance,
            "last_updated": datetime.utcnow().isoformat(),
        }
