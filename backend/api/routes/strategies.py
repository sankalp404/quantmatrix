"""
DCA and ATR Strategy Routes
Updated backend services for production DCA strategies and ATR calculations
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.models import get_db  # Fixed import
from pydantic import BaseModel
from backend.services.dca_strategy import dca_strategy_service, DCAStrategy
from backend.services.atr_calculator import atr_calculator_service

router = APIRouter()

@router.get("/dca/recommendations")
async def get_dca_recommendations(
    account_id: Optional[str] = Query(None),
    strategy: str = Query("standard", description="DCA strategy: conservative, standard, aggressive, balanced"),
    db: Session = Depends(get_db)
):
    """Get DCA recommendations for portfolio or specific account."""
    
    try:
        # Validate strategy
        try:
            dca_strategy = DCAStrategy(strategy.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")
        
        # Get recommendations
        result = await dca_strategy_service.get_portfolio_recommendations(
            account_id=account_id,
            strategy=dca_strategy
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating DCA recommendations: {str(e)}")

@router.get("/dca/strategies")
async def get_available_strategies():
    """Get list of available DCA strategies."""
    
    strategies = [
        {
            "id": "conservative",
            "name": "Benjamin Graham Conservative",
            "description": "Value-focused approach with emphasis on large-cap defensive stocks",
            "risk_level": "Low",
            "typical_allocation": "Defensive 60%, Growth 25%, Speculative 10%, Cash 5%"
        },
        {
            "id": "standard", 
            "name": "Warren Buffett Standard",
            "description": "Long-term quality business focus with patient capital appreciation",
            "risk_level": "Medium",
            "typical_allocation": "Quality 70%, Growth 20%, Speculative 10%"
        },
        {
            "id": "aggressive",
            "name": "Peter Lynch Aggressive", 
            "description": "Growth-oriented approach with focus on emerging winners",
            "risk_level": "High",
            "typical_allocation": "Growth 50%, Large-cap 30%, Small-cap 20%"
        },
        {
            "id": "balanced",
            "name": "Ray Dalio Balanced",
            "description": "Diversification-focused approach with risk parity principles",
            "risk_level": "Medium",
            "typical_allocation": "Diversified across sectors and asset classes"
        }
    ]
    
    return {
        "status": "success",
        "data": strategies
    }

@router.get("/atr/portfolio")
async def get_portfolio_atr_analysis(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    account_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get ATR analysis for portfolio symbols."""
    
    try:
        symbol_list = []
        
        if symbols:
            # Use provided symbols
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        else:
            # Get symbols from portfolio
            # In production, query from database based on account_id
            # For now, use common symbols as example
            symbol_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No symbols provided")
        
        # Calculate ATR for all symbols
        atr_results = await atr_calculator_service.calculate_atr_for_portfolio(symbol_list)
        
        # Format results for API response
        formatted_results = {}
        for symbol, atr_data in atr_results.items():
            formatted_results[symbol] = {
                "symbol": atr_data.symbol,
                "current_atr": atr_data.current_atr,
                "atr_percentage": atr_data.atr_percentage,
                "volatility_rating": atr_data.volatility_rating,
                "trend": atr_data.trend,
                "recommendation": atr_calculator_service.get_atr_recommendation(atr_data),
                "last_updated": atr_data.last_updated.isoformat(),
                "period": atr_data.period
            }
        
        return {
            "status": "success",
            "data": {
                "atr_analysis": formatted_results,
                "summary": {
                    "total_symbols": len(formatted_results),
                    "high_volatility_count": sum(1 for r in formatted_results.values() if r["volatility_rating"] in ["HIGH", "EXTREME"]),
                    "low_volatility_count": sum(1 for r in formatted_results.values() if r["volatility_rating"] == "LOW"),
                    "average_atr_percentage": sum(r["atr_percentage"] for r in formatted_results.values()) / len(formatted_results) if formatted_results else 0
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating ATR analysis: {str(e)}")

@router.get("/atr/symbol/{symbol}")
async def get_symbol_atr_analysis(
    symbol: str,
    period: int = Query(14, description="ATR calculation period")
):
    """Get detailed ATR analysis for a specific symbol."""
    
    try:
        symbol = symbol.upper()
        
        # Calculate ATR for the symbol
        atr_data = await atr_calculator_service.calculate_atr(symbol, period)
        
        return {
            "status": "success",
            "data": {
                "symbol": atr_data.symbol,
                "current_atr": atr_data.current_atr,
                "atr_percentage": atr_data.atr_percentage,
                "volatility_rating": atr_data.volatility_rating,
                "trend": atr_data.trend,
                "recommendation": atr_calculator_service.get_atr_recommendation(atr_data),
                "last_updated": atr_data.last_updated.isoformat(),
                "period": atr_data.period,
                "interpretation": {
                    "volatility_description": _get_volatility_description(atr_data.volatility_rating),
                    "trend_description": _get_trend_description(atr_data.trend),
                    "dca_suitability": _get_dca_suitability(atr_data.volatility_rating)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating ATR for {symbol}: {str(e)}")

def _get_volatility_description(rating: str) -> str:
    """Get human-readable volatility description."""
    descriptions = {
        "LOW": "Low volatility indicates stable price movements with minimal daily fluctuations",
        "MEDIUM": "Moderate volatility shows normal market price swings",
        "HIGH": "High volatility indicates significant daily price movements",
        "EXTREME": "Extreme volatility shows very large daily price swings with high risk"
    }
    return descriptions.get(rating, "Unknown volatility level")

def _get_trend_description(trend: str) -> str:
    """Get human-readable trend description."""
    descriptions = {
        "INCREASING": "Volatility is increasing - market uncertainty is rising",
        "DECREASING": "Volatility is decreasing - market is becoming more stable", 
        "STABLE": "Volatility is stable - consistent market behavior"
    }
    return descriptions.get(trend, "Unknown trend")

def _get_dca_suitability(rating: str) -> str:
    """Get DCA strategy suitability based on volatility."""
    suitability = {
        "LOW": "Excellent for regular DCA - stable entry points",
        "MEDIUM": "Good for DCA - balanced approach recommended",
        "HIGH": "Very good for DCA - volatility helps smooth entry costs",
        "EXTREME": "Use smaller DCA amounts more frequently to manage risk"
    }
    return suitability.get(rating, "Standard DCA approach") 