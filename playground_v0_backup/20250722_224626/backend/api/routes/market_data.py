from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import logging
from datetime import datetime

from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stock-info/{symbol}")
async def get_stock_info(symbol: str):
    """Get comprehensive stock information including market cap, sector, etc."""
    try:
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol")
        
        symbol = symbol.upper().strip()
        
        # Get stock info from market data service
        stock_info = await market_data_service.get_stock_info(symbol)
        
        if not stock_info:
            raise HTTPException(status_code=404, detail=f"Stock info not found for {symbol}")
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "company_name": stock_info.get('company_name', ''),
                "market_cap": stock_info.get('market_cap', 0),
                "sector": stock_info.get('sector', 'Other'),
                "industry": stock_info.get('industry', 'Other'),
                "country": stock_info.get('country', ''),
                "currency": stock_info.get('currency', 'USD'),
                "exchange": stock_info.get('exchange', ''),
                "description": stock_info.get('description', ''),
                "website": stock_info.get('website', ''),
                "employees": stock_info.get('employees', 0),
                "founded": stock_info.get('founded', ''),
                "ceo": stock_info.get('ceo', ''),
                "last_updated": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stock info: {str(e)}")

@router.get("/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """Get real-time stock quote."""
    try:
        if not symbol or len(symbol) > 10:
            raise HTTPException(status_code=400, detail="Invalid symbol")
        
        symbol = symbol.upper().strip()
        
        # Get current price from market data service
        current_price = await market_data_service.get_current_price(symbol)
        
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "price": current_price,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")

@router.get("/health")
async def market_data_health():
    """Health check for market data services."""
    try:
        # Test with a simple symbol
        test_price = await market_data_service.get_current_price('AAPL')
        
        return {
            "status": "success",
            "data": {
                "market_data_service": "operational" if test_price else "degraded",
                "test_symbol": "AAPL",
                "test_price": test_price,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Market data health check failed: {e}")
        return {
            "status": "error",
            "data": {
                "market_data_service": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        } 