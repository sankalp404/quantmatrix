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
from backend.models.users import User
from backend.services.market.market_data_service import MarketDataService
from backend.services.analysis.atr_calculator import atr_calculator
from backend.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# MARKET DATA ENDPOINTS (Clean & Focused)
# =============================================================================

@router.get("/price/{symbol}")
async def get_current_price(
    symbol: str,
    user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current price for a symbol."""
    try:
        market_service = MarketDataService()
        price = await market_service.get_current_price(symbol)
        
        return {
            "symbol": symbol,
            "current_price": price,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Price error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/atr/{symbol}")
async def get_atr_data(
    symbol: str,
    periods: int = Query(14, description="ATR calculation periods"),
    user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get ATR data for a symbol."""
    try:
        atr_data = await atr_calculator.calculate_options_atr(symbol)
        
        return {
            "symbol": symbol,
            "atr_data": atr_data,
            "periods": periods,
            "timestamp": datetime.now().isoformat()
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
    user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get historical price data."""
    # TODO: Implement with market data service
    return {
        "symbol": symbol,
        "message": "Historical data endpoint - to be implemented",
        "days": days
    } 