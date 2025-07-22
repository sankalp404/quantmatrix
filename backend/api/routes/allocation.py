from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging
from datetime import datetime

from backend.services.allocation_service import allocation_service
from backend.models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/current/{account_id}")
async def get_current_allocation(account_id: str):
    """Get current portfolio allocation by category"""
    try:
        allocation = await allocation_service.get_current_allocation(account_id)
        
        if not allocation:
            raise HTTPException(status_code=404, detail="Account not found or no allocation data")
        
        return {
            "status": "success",
            "data": allocation,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting current allocation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get allocation: {str(e)}")

@router.post("/target")
async def set_target_allocation(
    account_id: str,
    category_id: int,
    target_percentage: float
):
    """Set target allocation for a category"""
    try:
        if target_percentage < 0 or target_percentage > 100:
            raise HTTPException(status_code=400, detail="Target percentage must be between 0 and 100")
        
        result = await allocation_service.set_target_allocation(
            account_id=account_id,
            category_id=category_id, 
            target_percentage=target_percentage
        )
        
        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting target allocation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set target: {str(e)}")

@router.get("/rebalance/{account_id}")
async def get_rebalancing_recommendations(
    account_id: str,
    min_threshold: float = Query(default=5.0, description="Minimum percentage difference to trigger rebalancing")
):
    """Generate rebalancing recommendations"""
    try:
        recommendations = await allocation_service.generate_rebalancing_recommendations(
            account_id=account_id,
            min_threshold=min_threshold
        )
        
        if 'error' in recommendations:
            raise HTTPException(status_code=400, detail=recommendations['error'])
        
        return {
            "status": "success", 
            "data": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating rebalancing recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")

@router.post("/rebalance/execute")
async def execute_rebalancing(
    account_id: str,
    recommendations: List[Dict]
):
    """Execute rebalancing orders (simulation)"""
    try:
        orders = await allocation_service.create_rebalancing_orders(
            account_id=account_id,
            recommendations=recommendations
        )
        
        return {
            "status": "success",
            "message": f"Created {orders.get('total_orders', 0)} rebalancing orders",
            "data": orders,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing rebalancing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute rebalancing: {str(e)}")

@router.get("/drift/{account_id}")
async def analyze_allocation_drift(
    account_id: str,
    days: int = Query(default=30, description="Number of days to analyze")
):
    """Analyze allocation drift over time"""
    try:
        drift_analysis = await allocation_service.analyze_drift(
            account_id=account_id,
            days=days
        )
        
        if 'error' in drift_analysis:
            raise HTTPException(status_code=400, detail=drift_analysis['error'])
        
        return {
            "status": "success",
            "data": drift_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing drift: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze drift: {str(e)}")

@router.get("/history/{account_id}")
async def get_allocation_history(
    account_id: str,
    months: int = Query(default=12, description="Number of months of history")
):
    """Get allocation history over time"""
    try:
        history = await allocation_service.get_allocation_history(
            account_id=account_id,
            months=months
        )
        
        return {
            "status": "success",
            "data": history,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting allocation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.get("/summary/{account_id}")
async def get_allocation_summary(account_id: str):
    """Get allocation summary with key metrics"""
    try:
        current_allocation = await allocation_service.get_current_allocation(account_id)
        drift_analysis = await allocation_service.analyze_drift(account_id)
        
        if not current_allocation:
            raise HTTPException(status_code=404, detail="No allocation data found")
        
        # Calculate summary metrics
        allocations = current_allocation.get('allocations', {})
        total_categories = len([k for k in allocations.keys() if k != 'uncategorized'])
        avg_drift = sum(abs(data.get('difference', 0)) for data in allocations.values()) / len(allocations) if allocations else 0
        
        out_of_balance = sum(1 for data in allocations.values() if abs(data.get('difference', 0)) > 5)
        
        summary = {
            "account_id": account_id,
            "total_value": current_allocation.get('total_value', 0),
            "total_categories": total_categories,
            "average_drift": avg_drift,
            "categories_out_of_balance": out_of_balance,
            "balance_score": max(0, 100 - (avg_drift * 2)),  # Simple scoring system
            "needs_rebalancing": avg_drift > 5,
            "last_updated": current_allocation.get('last_updated')
        }
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting allocation summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}") 