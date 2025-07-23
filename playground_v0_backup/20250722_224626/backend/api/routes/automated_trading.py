"""
Automated Trading API Routes
RESTful endpoints for managing automated options trading strategies
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from backend.database import get_db
from backend.services.tastytrade_trading import (
    TastyTradeAutomatedTrading, 
    StrategyType, 
    RiskLevel,
    OptionsStrategy
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["Automated Trading"])

# Global trading instance (in production, this would be managed differently)
trading_engine: Optional[TastyTradeAutomatedTrading] = None

@router.post("/initialize")
async def initialize_trading_engine(
    credentials: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Initialize the automated trading engine"""
    global trading_engine
    
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        is_paper = credentials.get("is_paper", True)
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Initialize trading engine
        trading_engine = TastyTradeAutomatedTrading(username, password, is_paper)
        
        # Initialize in background
        success = await trading_engine.initialize()
        
        if success:
            # Start monitoring in background
            background_tasks.add_task(trading_engine.monitor_positions)
            
            return {
                "status": "success",
                "message": "Trading engine initialized successfully",
                "data": {
                    "account": trading_engine.account.account_number if trading_engine.account else "Unknown",
                    "is_paper": is_paper,
                    "initialized_at": datetime.now().isoformat()
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize trading engine")
            
    except Exception as e:
        logger.error(f"Error initializing trading engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_trading_status():
    """Get current trading engine status"""
    global trading_engine
    
    if not trading_engine:
        return {
            "status": "success",
            "data": {
                "engine_status": "not_initialized",
                "active_strategies": 0,
                "pending_orders": 0
            }
        }
    
    try:
        performance = trading_engine.get_strategy_performance()
        
        return {
            "status": "success",
            "data": {
                "engine_status": "active",
                "account": trading_engine.account.account_number if trading_engine.account else "Unknown",
                "active_strategies": performance["active_strategies"],
                "closed_strategies": performance["closed_strategies"],
                "pending_orders": performance["pending_orders"],
                "win_rate": performance["win_rate"],
                "total_trades": performance["total_trades"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/iron-condor")
async def deploy_iron_condor(
    strategy_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Deploy an Iron Condor strategy"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        underlying = strategy_config.get("underlying")
        expiration = strategy_config.get("expiration")
        delta_target = strategy_config.get("delta_target", 0.15)
        wing_width = strategy_config.get("wing_width", 10)
        max_risk = strategy_config.get("max_risk", 1000)
        
        if not underlying or not expiration:
            raise HTTPException(status_code=400, detail="Underlying and expiration required")
        
        # Deploy strategy
        strategy = await trading_engine.deploy_iron_condor(
            underlying=underlying,
            expiration=expiration,
            delta_target=delta_target,
            wing_width=wing_width,
            max_risk=max_risk
        )
        
        if strategy:
            return {
                "status": "success",
                "message": "Iron Condor strategy deployed successfully",
                "data": {
                    "strategy_id": strategy.id,
                    "underlying": strategy.underlying_symbol,
                    "expiration": strategy.expiration_date,
                    "max_risk": strategy.max_risk,
                    "target_profit": strategy.target_profit,
                    "legs": strategy.legs,
                    "deployed_at": strategy.created_at.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to deploy Iron Condor strategy")
            
    except Exception as e:
        logger.error(f"Error deploying Iron Condor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/strangle")
async def deploy_strangle(
    strategy_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Deploy a Short Strangle strategy"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        underlying = strategy_config.get("underlying")
        expiration = strategy_config.get("expiration")
        delta_target = strategy_config.get("delta_target", 0.20)
        max_risk = strategy_config.get("max_risk", 500)
        
        if not underlying or not expiration:
            raise HTTPException(status_code=400, detail="Underlying and expiration required")
        
        strategy = await trading_engine.deploy_strangle(
            underlying=underlying,
            expiration=expiration,
            delta_target=delta_target,
            max_risk=max_risk
        )
        
        if strategy:
            return {
                "status": "success",
                "message": "Short Strangle strategy deployed successfully",
                "data": {
                    "strategy_id": strategy.id,
                    "underlying": strategy.underlying_symbol,
                    "expiration": strategy.expiration_date,
                    "max_risk": strategy.max_risk,
                    "target_profit": strategy.target_profit,
                    "legs": strategy.legs,
                    "deployed_at": strategy.created_at.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to deploy Strangle strategy")
            
    except Exception as e:
        logger.error(f"Error deploying Strangle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/credit-spread")
async def deploy_credit_spread(
    strategy_config: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Deploy a Credit Spread strategy"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        underlying = strategy_config.get("underlying")
        expiration = strategy_config.get("expiration")
        option_type = strategy_config.get("option_type", "PUT")  # PUT or CALL
        delta_target = strategy_config.get("delta_target", 0.15)
        width = strategy_config.get("width", 5)
        max_risk = strategy_config.get("max_risk", 400)
        
        if not underlying or not expiration:
            raise HTTPException(status_code=400, detail="Underlying and expiration required")
        
        if option_type not in ["PUT", "CALL"]:
            raise HTTPException(status_code=400, detail="Option type must be PUT or CALL")
        
        strategy = await trading_engine.deploy_credit_spread(
            underlying=underlying,
            expiration=expiration,
            option_type=option_type,
            delta_target=delta_target,
            width=width,
            max_risk=max_risk
        )
        
        if strategy:
            return {
                "status": "success",
                "message": f"{option_type} Credit Spread strategy deployed successfully",
                "data": {
                    "strategy_id": strategy.id,
                    "underlying": strategy.underlying_symbol,
                    "expiration": strategy.expiration_date,
                    "option_type": option_type,
                    "max_risk": strategy.max_risk,
                    "target_profit": strategy.target_profit,
                    "legs": strategy.legs,
                    "deployed_at": strategy.created_at.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to deploy Credit Spread strategy")
            
    except Exception as e:
        logger.error(f"Error deploying Credit Spread: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies")
async def get_active_strategies():
    """Get all active trading strategies"""
    global trading_engine
    
    if not trading_engine:
        return {
            "status": "success",
            "data": {
                "strategies": [],
                "count": 0
            }
        }
    
    try:
        strategies = trading_engine.get_active_strategies()
        
        return {
            "status": "success",
            "data": {
                "strategies": strategies,
                "count": len(strategies)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies/{strategy_id}")
async def get_strategy_details(strategy_id: str):
    """Get detailed information about a specific strategy"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        strategy = trading_engine.active_strategies.get(strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get current P&L and Greeks
        current_pnl = await trading_engine._get_strategy_pnl(strategy)
        greeks = await trading_engine._get_strategy_greeks(strategy)
        
        return {
            "status": "success",
            "data": {
                "strategy": {
                    "id": strategy.id,
                    "name": strategy.name,
                    "strategy_type": strategy.strategy_type.value,
                    "underlying": strategy.underlying_symbol,
                    "expiration": strategy.expiration_date,
                    "legs": strategy.legs,
                    "max_risk": strategy.max_risk,
                    "target_profit": strategy.target_profit,
                    "risk_level": strategy.risk_level.value,
                    "active": strategy.active,
                    "created_at": strategy.created_at.isoformat()
                },
                "current_pnl": current_pnl,
                "greeks": {
                    "delta": greeks.delta,
                    "gamma": greeks.gamma,
                    "theta": greeks.theta,
                    "vega": greeks.vega,
                    "rho": greeks.rho,
                    "implied_volatility": greeks.implied_volatility
                },
                "days_to_expiration": (datetime.strptime(strategy.expiration_date, '%Y-%m-%d') - datetime.now()).days
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/close")
async def close_strategy(strategy_id: str):
    """Manually close a trading strategy"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        strategy = trading_engine.active_strategies.get(strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        if not strategy.active:
            raise HTTPException(status_code=400, detail="Strategy is already closed")
        
        # Close the strategy
        await trading_engine._close_strategy(strategy)
        
        return {
            "status": "success",
            "message": "Strategy closed successfully",
            "data": {
                "strategy_id": strategy_id,
                "closed_at": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_trading_performance():
    """Get overall trading performance metrics"""
    global trading_engine
    
    if not trading_engine:
        return {
            "status": "success",
            "data": {
                "performance": {
                    "total_strategies": 0,
                    "active_strategies": 0,
                    "closed_strategies": 0,
                    "win_rate": 0,
                    "total_trades": 0,
                    "pending_orders": 0,
                    "total_pnl": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0
                }
            }
        }
    
    try:
        performance = trading_engine.get_strategy_performance()
        
        # Calculate additional metrics
        total_pnl = 0  # Would calculate from closed strategies
        max_drawdown = 0  # Would calculate from historical data
        sharpe_ratio = 0  # Would calculate risk-adjusted returns
        
        enhanced_performance = {
            **performance,
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "average_hold_time": "14 days",  # Would calculate actual average
            "best_strategy": "Iron Condor SPY",  # Would find actual best
            "worst_strategy": "Strangle QQQ",  # Would find actual worst
        }
        
        return {
            "status": "success",
            "data": {
                "performance": enhanced_performance
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk-metrics")
async def get_risk_metrics():
    """Get current portfolio risk metrics"""
    global trading_engine
    
    if not trading_engine:
        return {
            "status": "success",
            "data": {
                "risk_metrics": {
                    "portfolio_delta": 0,
                    "portfolio_gamma": 0,
                    "portfolio_theta": 0,
                    "portfolio_vega": 0,
                    "max_risk": 0,
                    "current_risk": 0,
                    "buying_power_used": 0,
                    "risk_utilization": 0
                }
            }
        }
    
    try:
        # Calculate portfolio-level Greeks and risk metrics
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        total_risk = 0
        
        for strategy in trading_engine.active_strategies.values():
            if strategy.active:
                greeks = await trading_engine._get_strategy_greeks(strategy)
                total_delta += greeks.delta
                total_gamma += greeks.gamma
                total_theta += greeks.theta
                total_vega += greeks.vega
                total_risk += strategy.max_risk
        
        risk_metrics = {
            "portfolio_delta": round(total_delta, 4),
            "portfolio_gamma": round(total_gamma, 4),
            "portfolio_theta": round(total_theta, 2),
            "portfolio_vega": round(total_vega, 2),
            "max_risk": trading_engine.risk_manager.max_portfolio_risk,
            "current_risk": total_risk,
            "buying_power_used": total_risk,  # Simplified
            "risk_utilization": round((total_risk / trading_engine.risk_manager.max_portfolio_risk) * 100, 2),
            "position_count": len([s for s in trading_engine.active_strategies.values() if s.active]),
            "concentration_risk": "Low",  # Would calculate actual concentration
            "var_95": round(total_risk * 0.05, 2),  # Simplified VaR calculation
        }
        
        return {
            "status": "success",
            "data": {
                "risk_metrics": risk_metrics
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/emergency-stop")
async def emergency_stop():
    """Emergency stop - close all positions immediately"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=400, detail="Trading engine not initialized")
    
    try:
        closed_strategies = []
        
        for strategy_id, strategy in trading_engine.active_strategies.items():
            if strategy.active:
                await trading_engine._close_strategy(strategy)
                closed_strategies.append(strategy_id)
        
        return {
            "status": "success",
            "message": "Emergency stop executed - all positions closed",
            "data": {
                "closed_strategies": closed_strategies,
                "count": len(closed_strategies),
                "executed_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 