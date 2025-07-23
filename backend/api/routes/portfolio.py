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
from datetime import datetime

# dependencies
from backend.database import get_db
from backend.models.users import User
from backend.services.portfolio.sync_service import PortfolioSyncService
from backend.services.portfolio.csv_import_service import CSVImportService
from backend.services.clients.ibkr_client import IBKRClient
from backend.services.clients.tastytrade_client import TastyTradeClient

# Auth dependency (to be implemented)
from backend.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# PORTFOLIO SUMMARY ENDPOINTS (Clean & Focused)
# =============================================================================

@router.get("/summary")
async def get_portfolio_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's portfolio summary.
    CLEAN: Only portfolio summary, nothing else.
    """
    try:
        sync_service = PortfolioSyncService(db)
        summary = await sync_service.get_user_portfolio_summary(user.id)
        
        return {
            "user_id": user.id,
            "username": user.username,
            "portfolio_summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Portfolio summary error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_positions(
    broker: Optional[str] = Query(None, description="Filter by broker (ibkr, tastytrade)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's current positions.
    CLEAN: Only positions data, properly filtered.
    """
    try:
        sync_service = PortfolioSyncService(db)
        positions = await sync_service.get_user_positions(user.id, broker=broker)
        
        return {
            "user_id": user.id,
            "broker_filter": broker,
            "positions": positions,
            "total_positions": len(positions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Positions error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_portfolio_performance(
    days: int = Query(30, description="Performance period in days"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get portfolio performance metrics.
    CLEAN: Only performance data, configurable timeframe.
    """
    try:
        sync_service = PortfolioSyncService(db)
        performance = await sync_service.get_user_performance(user.id, days=days)
        
        return {
            "user_id": user.id,
            "period_days": days,
            "performance_metrics": performance,
            "timestamp": datetime.now().isoformat()
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
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's tax lots.
    CLEAN: Only tax lot data, optionally filtered by symbol.
    """
    try:
        csv_service = CSVImportService(db)
        tax_lots = await csv_service.get_user_tax_lots(user.id, symbol=symbol)
        
        return {
            "user_id": user.id,
            "symbol_filter": symbol,
            "tax_lots": tax_lots,
            "total_lots": len(tax_lots),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Tax lots error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tax-lots/summary")
async def get_tax_lots_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get tax lots summary by symbol.
    CLEAN: Only summary data, properly aggregated.
    """
    try:
        from backend.services.portfolio.csv_import_service import get_user_tax_lots_summary
        summary = await get_user_tax_lots_summary(user.id)
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Tax lots summary error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# TRANSACTION ENDPOINTS (Clean & Focused)
# =============================================================================

@router.get("/transactions")
async def get_transactions(
    limit: int = Query(100, description="Number of transactions to return"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's transaction history.
    CLEAN: Only transaction data, configurable limit.
    """
    try:
        csv_service = CSVImportService(db)
        transactions = await csv_service.get_user_transactions(user.id, limit=limit)
        
        return {
            "user_id": user.id,
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Transactions error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# CSV IMPORT ENDPOINTS (Clean & Focused)
# =============================================================================

@router.get("/csv-import/status")
async def get_csv_import_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get CSV import status for user.
    CLEAN: Only import status, no business logic.
    """
    try:
        csv_service = CSVImportService(db)
        status = await csv_service.get_import_status(user.id)
        
        return status
        
    except Exception as e:
        logger.error(f"❌ CSV import status error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/csv-import/execute")
async def execute_csv_import(
    csv_directory: str = ".",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Execute CSV import for user's 3 IBKR files.
    CLEAN: Only import execution, delegates to service.
    """
    try:
        csv_service = CSVImportService(db)
        result = await csv_service.import_user_csv_files(user.id, csv_directory)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ CSV import execution error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# BROKER SYNC ENDPOINTS (Clean & Focused)
# =============================================================================

@router.post("/sync/ibkr")
async def sync_ibkr_portfolio(
    account_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sync portfolio data from IBKR.
    CLEAN: Only IBKR sync, delegates to service.
    """
    try:
        sync_service = PortfolioSyncService(db)
        result = await sync_service.sync_ibkr_portfolio(user.id, account_id)
        
        return {
            "user_id": user.id,
            "broker": "ibkr",
            "account_id": account_id,
            "sync_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ IBKR sync error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/tastytrade")
async def sync_tastytrade_portfolio(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sync portfolio data from TastyTrade.
    CLEAN: Only TastyTrade sync, delegates to service.
    """
    try:
        sync_service = PortfolioSyncService(db)
        result = await sync_service.sync_tastytrade_portfolio(user.id)
        
        return {
            "user_id": user.id,
            "broker": "tastytrade",
            "sync_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ TastyTrade sync error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PORTFOLIO ANALYTICS ENDPOINTS (Clean & Focused)
# =============================================================================

@router.get("/analytics/allocation")
async def get_allocation_analysis(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get portfolio allocation analysis.
    CLEAN: Only allocation data, proper categorization.
    """
    try:
        sync_service = PortfolioSyncService(db)
        allocation = await sync_service.get_allocation_analysis(user.id)
        
        return {
            "user_id": user.id,
            "allocation_analysis": allocation,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Allocation analysis error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/risk")
async def get_risk_analysis(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get portfolio risk analysis.
    CLEAN: Only risk metrics, focused analysis.
    """
    try:
        sync_service = PortfolioSyncService(db)
        risk_analysis = await sync_service.get_risk_analysis(user.id)
        
        return {
            "user_id": user.id,
            "risk_analysis": risk_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Risk analysis error for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 