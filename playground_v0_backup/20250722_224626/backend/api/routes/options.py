from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime
import logging

from backend.services.tastytrade_client import tastytrade_client
from backend.services.atr_options_strategy import atr_options_strategy
from backend.models import SessionLocal
from backend.models.options import TradingStrategy, StrategySignal, OptionPosition

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/accounts")
async def get_tastytrade_accounts():
    """Get all Tastytrade accounts."""
    try:
        accounts = await tastytrade_client.get_accounts()
        return {
            "accounts": accounts,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting Tastytrade accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts/{account_number}/balance")
async def get_account_balance(account_number: str):
    """Get account balance and buying power."""
    try:
        balance = await tastytrade_client.get_account_balance(account_number)
        return balance
    except Exception as e:
        logger.error(f"Error getting account balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts/{account_number}/positions")
async def get_account_positions(account_number: str):
    """Get current positions including options."""
    try:
        positions = await tastytrade_client.get_positions(account_number)
        return {
            "positions": positions,
            "account_number": account_number,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/accounts/{account_number}/orders")
async def get_order_history(account_number: str, days: int = 7):
    """Get recent order history."""
    try:
        orders = await tastytrade_client.get_order_history(account_number, days)
        return {
            "orders": orders,
            "account_number": account_number,
            "days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting order history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/options/chain/{symbol}")
async def get_option_chain(symbol: str, expiration_date: Optional[str] = None):
    """Get options chain for underlying symbol."""
    try:
        chain = await tastytrade_client.get_option_chain(symbol, expiration_date)
        return chain
    except Exception as e:
        logger.error(f"Error getting option chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/options/quotes")
async def get_option_quotes(symbols: List[str]):
    """Get real-time quotes for option symbols."""
    try:
        quotes = await tastytrade_client.get_real_time_quotes(symbols)
        return {
            "quotes": quotes,
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting option quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/options/greeks")
async def get_options_greeks(symbols: List[str]):
    """Get real-time Greeks for option symbols."""
    try:
        greeks = await tastytrade_client.get_options_greeks(symbols)
        return {
            "greeks": greeks,
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting options Greeks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders/option")
async def place_option_order(
    account_number: str,
    option_symbol: str,
    action: str,
    quantity: int,
    order_type: str = "LIMIT",
    price: Optional[float] = None
):
    """Place an options order."""
    try:
        result = await tastytrade_client.place_option_order(
            account_number=account_number,
            option_symbol=option_symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
        return result
    except Exception as e:
        logger.error(f"Error placing option order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ATR Matrix Options Strategy Routes

@router.post("/strategies/atr-matrix/initialize")
async def initialize_atr_strategy(account_number: str, initial_capital: float = 10000.0):
    """Initialize a new ATR Matrix options strategy."""
    try:
        result = await atr_options_strategy.initialize_strategy(account_number, initial_capital)
        return {
            "message": "ATR Matrix options strategy initialized successfully",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error initializing ATR strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_id}/run")
async def run_atr_strategy(strategy_id: int, background_tasks: BackgroundTasks):
    """Run the ATR Matrix options strategy."""
    try:
        # Run in background to avoid timeout
        background_tasks.add_task(atr_options_strategy.run_daily_strategy, strategy_id)
        
        return {
            "message": f"ATR Matrix strategy {strategy_id} started",
            "strategy_id": strategy_id,
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running ATR strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategies")
async def get_strategies():
    """Get all trading strategies."""
    db = SessionLocal()
    try:
        strategies = db.query(TradingStrategy).filter(TradingStrategy.is_active == True).all()
        
        strategy_data = []
        for strategy in strategies:
            strategy_info = {
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type.value,
                "account_number": strategy.account.account_number,
                "allocated_capital": float(strategy.allocated_capital),
                "current_capital": float(strategy.current_capital),
                "target_capital": float(strategy.target_capital) if strategy.target_capital else None,
                "total_pnl": float(strategy.total_pnl) if strategy.total_pnl else 0,
                "total_pnl_pct": float(strategy.total_pnl_pct) if strategy.total_pnl_pct else 0,
                "profit_target_pct": float(strategy.profit_target_pct) if strategy.profit_target_pct else 0,
                "is_automated": strategy.is_automated,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at.isoformat(),
                "updated_at": strategy.updated_at.isoformat()
            }
            strategy_data.append(strategy_info)
        
        return {
            "strategies": strategy_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/strategies/{strategy_id}")
async def get_strategy_details(strategy_id: int):
    """Get detailed information about a specific strategy."""
    db = SessionLocal()
    try:
        strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get recent signals
        signals = db.query(StrategySignal).filter(
            StrategySignal.strategy_id == strategy_id
        ).order_by(StrategySignal.created_at.desc()).limit(10).all()
        
        # Get current positions
        positions = db.query(OptionPosition).filter(
            OptionPosition.strategy_id == strategy_id,
            OptionPosition.quantity != 0
        ).all()
        
        signal_data = []
        for signal in signals:
            signal_info = {
                "id": signal.id,
                "underlying_symbol": signal.underlying_symbol,
                "signal_type": signal.signal_type,
                "signal_strength": float(signal.signal_strength) if signal.signal_strength else 0,
                "target_price": float(signal.target_price) if signal.target_price else None,
                "time_horizon_days": signal.time_horizon_days,
                "recommended_action": signal.recommended_action,
                "position_size": float(signal.position_size) if signal.position_size else 0,
                "is_executed": signal.is_executed,
                "executed_at": signal.executed_at.isoformat() if signal.executed_at else None,
                "created_at": signal.created_at.isoformat()
            }
            signal_data.append(signal_info)
        
        position_data = []
        for position in positions:
            position_info = {
                "id": position.id,
                "option_symbol": position.option.symbol,
                "underlying_symbol": position.option.underlying_symbol,
                "strike_price": float(position.option.strike_price),
                "expiration_date": position.option.expiration_date.isoformat(),
                "option_type": position.option.option_type.value,
                "quantity": position.quantity,
                "average_open_price": float(position.average_open_price),
                "current_price": float(position.current_price) if position.current_price else None,
                "unrealized_pnl": float(position.unrealized_pnl) if position.unrealized_pnl else 0,
                "opened_at": position.opened_at.isoformat()
            }
            position_data.append(position_info)
        
        return {
            "strategy": {
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type.value,
                "description": strategy.description,
                "account_number": strategy.account.account_number,
                "allocated_capital": float(strategy.allocated_capital),
                "current_capital": float(strategy.current_capital),
                "target_capital": float(strategy.target_capital) if strategy.target_capital else None,
                "total_pnl": float(strategy.total_pnl) if strategy.total_pnl else 0,
                "total_pnl_pct": float(strategy.total_pnl_pct) if strategy.total_pnl_pct else 0,
                "profit_target_pct": float(strategy.profit_target_pct) if strategy.profit_target_pct else 0,
                "stop_loss_pct": float(strategy.stop_loss_pct) if strategy.stop_loss_pct else 0,
                "max_dte": strategy.max_dte,
                "min_dte": strategy.min_dte,
                "risk_reward_ratio": float(strategy.risk_reward_ratio) if strategy.risk_reward_ratio else None,
                "is_automated": strategy.is_automated,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at.isoformat(),
                "updated_at": strategy.updated_at.isoformat()
            },
            "recent_signals": signal_data,
            "current_positions": position_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting strategy details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/strategies/{strategy_id}/performance")
async def get_strategy_performance(strategy_id: int, days: int = 30):
    """Get strategy performance metrics over time."""
    db = SessionLocal()
    try:
        from backend.models.options import StrategyPerformance
        
        performance_records = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strategy_id
        ).order_by(StrategyPerformance.date.desc()).limit(days).all()
        
        performance_data = []
        for record in performance_records:
            perf_info = {
                "date": record.date.isoformat(),
                "capital_value": float(record.capital_value),
                "daily_pnl": float(record.daily_pnl) if record.daily_pnl else 0,
                "daily_pnl_pct": float(record.daily_pnl_pct) if record.daily_pnl_pct else 0,
                "cumulative_pnl": float(record.cumulative_pnl) if record.cumulative_pnl else 0,
                "cumulative_pnl_pct": float(record.cumulative_pnl_pct) if record.cumulative_pnl_pct else 0,
                "total_positions": record.total_positions if record.total_positions else 0,
                "winning_positions": record.winning_positions if record.winning_positions else 0,
                "losing_positions": record.losing_positions if record.losing_positions else 0
            }
            performance_data.append(perf_info)
        
        return {
            "strategy_id": strategy_id,
            "performance": performance_data,
            "days": days,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/strategies/{strategy_id}/toggle")
async def toggle_strategy(strategy_id: int, active: bool):
    """Activate or deactivate a strategy."""
    db = SessionLocal()
    try:
        strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy.is_active = active
        strategy.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "message": f"Strategy {'activated' if active else 'deactivated'} successfully",
            "strategy_id": strategy_id,
            "is_active": active,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/dashboard/overview")
async def get_options_dashboard():
    """Get overview dashboard data for options trading."""
    db = SessionLocal()
    try:
        # Get all active strategies
        strategies = db.query(TradingStrategy).filter(TradingStrategy.is_active == True).all()
        
        total_capital = 0
        total_pnl = 0
        total_positions = 0
        strategy_summaries = []
        
        for strategy in strategies:
            capital = float(strategy.current_capital) if strategy.current_capital else 0
            pnl = float(strategy.total_pnl) if strategy.total_pnl else 0
            
            # Count positions
            position_count = db.query(OptionPosition).filter(
                OptionPosition.strategy_id == strategy.id,
                OptionPosition.quantity != 0
            ).count()
            
            total_capital += capital
            total_pnl += pnl
            total_positions += position_count
            
            progress_to_target = 0
            if strategy.target_capital and float(strategy.target_capital) > 0:
                progress_to_target = (capital / float(strategy.target_capital)) * 100
            
            strategy_summaries.append({
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type.value,
                "current_capital": capital,
                "target_capital": float(strategy.target_capital) if strategy.target_capital else None,
                "total_pnl": pnl,
                "total_pnl_pct": float(strategy.total_pnl_pct) if strategy.total_pnl_pct else 0,
                "progress_to_target": progress_to_target,
                "position_count": position_count,
                "is_automated": strategy.is_automated
            })
        
        # Calculate overall metrics
        million_dollar_progress = (total_capital / 1000000) * 100 if total_capital > 0 else 0
        
        return {
            "overview": {
                "total_capital": total_capital,
                "total_pnl": total_pnl,
                "total_positions": total_positions,
                "million_dollar_progress": min(100, million_dollar_progress),
                "strategies_count": len(strategies)
            },
            "strategies": strategy_summaries,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting options dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close() 

# Unified Options Routes (IBKR + TastyTrade)

@router.post("/unified/sync")
async def sync_unified_options():
    """Sync options positions from both IBKR and TastyTrade to database"""
    try:
        from backend.services.options_sync import unified_options_sync
        
        result = await unified_options_sync.sync_all_options_positions()
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return {
            "status": "success",
            "message": f"Synced {result['total_options_synced']} options positions",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error syncing unified options: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unified/portfolio")
async def get_unified_options_portfolio(account_id: Optional[str] = None, broker: Optional[str] = None):
    """Get unified options portfolio from both IBKR and TastyTrade with filtering support"""
    try:
        from backend.models import SessionLocal
        from backend.models.options import OptionPosition, OptionInstrument
        from backend.models.portfolio import Account
        from collections import defaultdict
        
        db = SessionLocal()
        
        try:
            # Build query with filters
            query = db.query(OptionPosition).join(OptionInstrument).join(Account)
            
            # Apply account filtering
            if account_id:
                query = query.filter(Account.account_number == account_id)
            
            # Apply broker filtering
            if broker:
                query = query.filter(Account.broker == broker.upper())
            
            positions = query.all()
            
            if not positions:
                return {
                    "status": "success",
                    "data": {
                        "positions": [],
                        "underlyings": {},
                        "summary": {
                            "total_positions": 0,
                            "total_market_value": 0,
                            "total_unrealized_pnl": 0,
                            "calls_count": 0,
                            "puts_count": 0
                        },
                        "filtering": {
                            "account_id": account_id,
                            "broker": broker,
                            "applied": account_id is not None or broker is not None
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            # Process positions
            positions_data = []
            underlyings = defaultdict(lambda: {"calls": [], "puts": [], "total_value": 0, "total_pnl": 0})
            
            total_market_value = 0
            total_unrealized_pnl = 0
            calls_count = 0
            puts_count = 0
            
            for position in positions:
                option = position.option
                account = position.account
                
                # Calculate days to expiration - fix datetime type mismatch
                from datetime import datetime, date
                today = date.today() if hasattr(option.expiration_date, 'date') else datetime.now().date()
                exp_date = option.expiration_date.date() if hasattr(option.expiration_date, 'date') else option.expiration_date
                days_to_expiration = (exp_date - today).days
                
                position_data = {
                    "id": str(position.id),
                    "symbol": option.symbol,
                    "underlying_symbol": option.underlying_symbol,
                    "strike_price": float(option.strike_price),
                    "expiration_date": option.expiration_date.isoformat(),
                    "option_type": option.option_type.value,
                    "quantity": position.quantity,
                    "average_open_price": float(position.average_open_price),
                    "current_price": float(position.current_price or 0),
                    "market_value": float(position.market_value or 0),
                    "unrealized_pnl": float(position.unrealized_pnl or 0),
                    "unrealized_pnl_pct": float(position.unrealized_pnl_pct or 0),
                    "day_pnl": float(position.day_pnl or 0),
                    "account_number": account.account_number,
                    "broker": account.broker,
                    "days_to_expiration": days_to_expiration,
                    "multiplier": option.multiplier,
                    "last_updated": position.last_updated.isoformat() if position.last_updated else None
                }
                
                positions_data.append(position_data)
                
                # Update totals
                total_market_value += float(position.market_value or 0)
                total_unrealized_pnl += float(position.unrealized_pnl or 0)
                
                if option.option_type.value == 'call':
                    calls_count += 1
                    underlyings[option.underlying_symbol]["calls"].append(position_data)
                else:
                    puts_count += 1
                    underlyings[option.underlying_symbol]["puts"].append(position_data)
                
                underlyings[option.underlying_symbol]["total_value"] += float(position.market_value or 0)
                underlyings[option.underlying_symbol]["total_pnl"] += float(position.unrealized_pnl or 0)
            
            return {
                "status": "success",
                "data": {
                    "positions": positions_data,
                    "underlyings": dict(underlyings),
                    "summary": {
                        "total_positions": len(positions_data),
                        "total_market_value": total_market_value,
                        "total_unrealized_pnl": total_unrealized_pnl,
                        "calls_count": calls_count,
                        "puts_count": puts_count,
                        "underlyings_count": len(underlyings)
                    },
                    "filtering": {
                        "account_id": account_id,
                        "broker": broker,
                        "applied": account_id is not None or broker is not None,
                        "results_filtered": account_id is not None or broker is not None
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting unified options portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unified/summary")
async def get_unified_options_summary(account_id: Optional[str] = None, broker: Optional[str] = None):
    """Get summary of options positions with filtering support"""
    try:
        from backend.models import SessionLocal
        from backend.models.options import OptionPosition, OptionInstrument
        from backend.models.portfolio import Account
        
        db = SessionLocal()
        
        try:
            # Build query with filters
            query = db.query(OptionPosition).join(OptionInstrument).join(Account)
            
            # Apply filters
            if account_id:
                query = query.filter(Account.account_number == account_id)
                
            if broker:
                query = query.filter(Account.broker == broker.upper())
            
            positions = query.all()
            
            if not positions:
                return {
                    "status": "success",
                    "data": {
                        "total_positions": 0,
                        "total_market_value": 0,
                        "total_unrealized_pnl": 0,
                        "total_unrealized_pnl_pct": 0,
                        "total_day_pnl": 0,
                        "total_day_pnl_pct": 0,
                        "calls_count": 0,
                        "puts_count": 0,
                        "expiring_this_week": 0,
                        "expiring_this_month": 0,
                        "underlyings_count": 0,
                        "avg_days_to_expiration": 0,
                        "underlyings": [],
                        "accounts": [],
                        "brokers": [],
                        "filtering": {
                            "account_id": account_id,
                            "broker": broker,
                            "applied": account_id is not None or broker is not None
                        },
                        "message": "No options positions found with current filters"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            # Calculate summary metrics
            total_market_value = sum(float(pos.market_value or 0) for pos in positions)
            total_unrealized_pnl = sum(float(pos.unrealized_pnl or 0) for pos in positions)
            total_day_pnl = sum(float(pos.day_pnl or 0) for pos in positions)
            
            # Calculate percentages
            total_cost_basis = sum(float(pos.average_open_price) * abs(pos.quantity) * pos.option.multiplier for pos in positions)
            total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
            total_day_pnl_pct = (total_day_pnl / total_market_value * 100) if total_market_value > 0 else 0
            
            # Count by type
            calls_count = len([pos for pos in positions if pos.option.option_type.value == 'call'])
            puts_count = len([pos for pos in positions if pos.option.option_type.value == 'put'])
            
            # Expiration analysis - fix datetime type mismatch
            from datetime import datetime, timedelta, date
            now = date.today()
            week_from_now = now + timedelta(days=7)
            month_from_now = now + timedelta(days=30)
            
            expiring_this_week = len([pos for pos in positions 
                                    if (pos.option.expiration_date.date() if hasattr(pos.option.expiration_date, 'date') 
                                        else pos.option.expiration_date) <= week_from_now])
            expiring_this_month = len([pos for pos in positions 
                                     if (pos.option.expiration_date.date() if hasattr(pos.option.expiration_date, 'date') 
                                         else pos.option.expiration_date) <= month_from_now])
            
            # Days to expiration average
            days_to_exp = [((pos.option.expiration_date.date() if hasattr(pos.option.expiration_date, 'date') 
                            else pos.option.expiration_date) - now).days for pos in positions]
            avg_days_to_expiration = sum(days_to_exp) / len(days_to_exp) if days_to_exp else 0
            
            # Unique counts
            underlyings = list(set(pos.option.underlying_symbol for pos in positions))
            accounts = list(set(pos.account.account_number for pos in positions))
            brokers = list(set(pos.account.broker for pos in positions))
            
            return {
                "status": "success",
                "data": {
                    "total_positions": len(positions),
                    "total_market_value": round(total_market_value, 2),
                    "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                    "total_unrealized_pnl_pct": round(total_unrealized_pnl_pct, 2),
                    "total_day_pnl": round(total_day_pnl, 2),
                    "total_day_pnl_pct": round(total_day_pnl_pct, 2),
                    "calls_count": calls_count,
                    "puts_count": puts_count,
                    "expiring_this_week": expiring_this_week,
                    "expiring_this_month": expiring_this_month,
                    "underlyings_count": len(underlyings),
                    "avg_days_to_expiration": round(avg_days_to_expiration, 1),
                    "underlyings": underlyings,
                    "accounts": accounts,
                    "brokers": brokers,
                    "filtering": {
                        "account_id": account_id,
                        "broker": broker,
                        "applied": account_id is not None or broker is not None,
                        "results_count": len(positions)
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting unified options summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 