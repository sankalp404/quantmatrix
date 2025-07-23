from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging
from datetime import datetime

from backend.services.tax_lot_service import tax_lot_service
from backend.models.tax_lots import TaxLotMethod
from backend.models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cost-basis/{symbol}")
async def get_cost_basis(
    symbol: str,
    account_id: str = Query(..., description="Account ID"),
    db: Session = Depends(get_db)
):
    """Get detailed cost basis for a symbol"""
    try:
        cost_basis = await tax_lot_service.calculate_cost_basis(symbol, account_id)
        
        return {
            "status": "success",
            "data": cost_basis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cost basis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost basis: {str(e)}")

@router.post("/simulate-sale")
async def simulate_sale(
    symbol: str,
    account_id: str,
    shares_to_sell: float,
    sale_price: float,
    lot_method: TaxLotMethod = TaxLotMethod.FIFO
):
    """Simulate a sale to show tax impact before execution"""
    try:
        simulation = await tax_lot_service.simulate_sale(
            symbol=symbol,
            account_id=account_id,
            shares_to_sell=shares_to_sell,
            sale_price=sale_price,
            lot_method=lot_method
        )
        
        return {
            "status": "success",
            "data": simulation,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error simulating sale: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@router.post("/execute-sale")
async def execute_sale(
    symbol: str,
    account_id: str,
    shares_to_sell: float,
    sale_price: float,
    sale_date: datetime,
    lot_method: TaxLotMethod = TaxLotMethod.FIFO,
    commission: float = 0.0
):
    """Execute a sale and record tax lot sales"""
    try:
        sale_records = await tax_lot_service.execute_sale(
            symbol=symbol,
            account_id=account_id,
            shares_to_sell=shares_to_sell,
            sale_price=sale_price,
            sale_date=sale_date,
            lot_method=lot_method,
            commission=commission
        )
        
        return {
            "status": "success",
            "message": f"Sale executed for {shares_to_sell} shares of {symbol}",
            "data": {
                "sale_records": len(sale_records),
                "total_proceeds": shares_to_sell * sale_price,
                "lot_method": lot_method.value
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing sale: {e}")
        raise HTTPException(status_code=500, detail=f"Sale execution failed: {str(e)}")

@router.get("/tax-loss-harvesting/{account_id}")
async def analyze_tax_loss_harvesting(account_id: str):
    """Analyze positions for tax loss harvesting opportunities"""
    try:
        opportunities = await tax_lot_service.analyze_tax_loss_harvesting(account_id)
        
        return {
            "status": "success",
            "data": {
                "opportunities": opportunities,
                "total_opportunities": len(opportunities),
                "total_potential_savings": sum(opp['tax_savings'] for opp in opportunities)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing tax loss harvesting: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/tax-report/{account_id}")
async def generate_tax_report(
    account_id: str,
    tax_year: int = Query(default=2025, description="Tax year for report")
):
    """Generate comprehensive tax report for a year"""
    try:
        report = await tax_lot_service.generate_tax_report(account_id, tax_year)
        
        if not report:
            raise HTTPException(status_code=404, detail="No tax data found for specified year")
        
        return {
            "status": "success",
            "data": report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating tax report: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/holdings/{account_id}")
async def get_tax_lots_for_account(account_id: str):
    """Get all tax lots for an account"""
    try:
        # This would need to be implemented in the service
        # For now, return a placeholder
        return {
            "status": "success",
            "data": {
                "account_id": account_id,
                "tax_lots": [],
                "message": "Tax lot listing endpoint - implementation pending"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting tax lots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tax lots: {str(e)}")

@router.get("/summary/{account_id}")
async def get_tax_summary(account_id: str):
    """Get tax summary for an account"""
    try:
        # Generate current year tax report as summary
        current_year = datetime.now().year
        report = await tax_lot_service.generate_tax_report(account_id, current_year)
        
        if not report:
            return {
                "status": "success",
                "data": {
                    "account_id": account_id,
                    "message": "No tax data available",
                    "year": current_year
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Extract key metrics for summary
        summary = {
            "account_id": account_id,
            "tax_year": current_year,
            "realized_pnl": report.get('realized_gains_losses', {}).get('total_net', 0),
            "unrealized_pnl": report.get('unrealized_positions', {}).get('net_unrealized', 0),
            "loss_harvesting_potential": report.get('tax_efficiency_metrics', {}).get('loss_harvesting_potential', 0),
            "long_term_percentage": report.get('tax_efficiency_metrics', {}).get('long_term_percentage', 0),
            "sales_count": report.get('sales_count', 0)
        }
        
        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting tax summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tax summary: {str(e)}") 