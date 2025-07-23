from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from backend.models import get_db
from backend.models.trade import Trade, TradeSignal
from backend.models.portfolio import Account, Holding
from backend.services.market_data import market_data_service
from backend.core.strategies.atr_matrix import atr_matrix_strategy

router = APIRouter()

# Pydantic models
class TradeCreate(BaseModel):
    account_id: int
    symbol: str
    side: str  # BUY, SELL
    quantity: float
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP
    price: Optional[float] = None  # For LIMIT orders
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK
    strategy_name: Optional[str] = None
    notes: Optional[str] = None

class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    total_value: float
    status: str
    order_type: str
    strategy_name: Optional[str]
    execution_time: Optional[datetime]
    realized_pnl: Optional[float]
    
    class Config:
        from_attributes = True

class SignalExecuteRequest(BaseModel):
    signal_id: int
    account_id: int
    quantity: Optional[float] = None  # If not provided, will calculate based on strategy
    order_type: str = "MARKET"

class StrategyTradeRequest(BaseModel):
    account_id: int
    symbol: str
    strategy_name: str = "ATR_MATRIX"
    position_size_pct: Optional[float] = None  # % of portfolio to risk
    dry_run: bool = True  # Paper trading by default

class RiskCheckResponse(BaseModel):
    approved: bool
    reason: str
    max_position_size: float
    current_portfolio_risk: float
    estimated_risk: float
    warnings: List[str]

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade_data: TradeCreate,
    db: Session = Depends(get_db)
):
    """Execute a trade order."""
    # Validate account
    account = db.query(Account).filter(Account.id == trade_data.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get current price if market order
    if trade_data.order_type == "MARKET":
        current_price = await market_data_service.get_current_price(trade_data.symbol)
        if not current_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot get current price for {trade_data.symbol}"
            )
        execution_price = current_price
    else:
        execution_price = trade_data.price
    
    if not execution_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price is required for limit orders"
        )
    
    # Perform risk checks
    risk_check = await _perform_risk_checks(
        trade_data.account_id,
        trade_data.symbol,
        trade_data.side,
        trade_data.quantity,
        execution_price,
        db
    )
    
    if not risk_check["approved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trade rejected: {risk_check['reason']}"
        )
    
    # Create trade record
    trade = Trade(
        account_id=trade_data.account_id,
        symbol=trade_data.symbol.upper(),
        side=trade_data.side,
        quantity=Decimal(str(trade_data.quantity)),
        price=Decimal(str(execution_price)),
        total_value=Decimal(str(trade_data.quantity * execution_price)),
        order_type=trade_data.order_type,
        time_in_force=trade_data.time_in_force,
        strategy_name=trade_data.strategy_name,
        order_time=datetime.now(),
        execution_time=datetime.now(),  # Simulated immediate execution
        status="FILLED",
        is_paper_trade=account.is_paper_trading,
        notes=trade_data.notes
    )
    
    db.add(trade)
    db.flush()
    
    # Update or create position
    await _update_position_from_trade(trade, db)
    
    db.commit()
    db.refresh(trade)
    
    return trade

@router.post("/signal/execute", response_model=TradeResponse)
async def execute_signal(
    request: SignalExecuteRequest,
    db: Session = Depends(get_db)
):
    """Execute a trade based on a signal."""
    # Get the signal
    signal = db.query(TradeSignal).filter(TradeSignal.id == request.signal_id).first()
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )
    
    if signal.is_executed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signal has already been executed"
        )
    
    # Get portfolio for position sizing
    portfolio = db.query(Account).filter(Account.id == request.account_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Calculate quantity if not provided
    quantity = request.quantity
    if not quantity:
        # Use strategy position sizing
        current_price = signal.recommended_price or signal.trigger_price
        quantity = atr_matrix_strategy.calculate_position_size(
            signal.symbol,
            float(current_price),
            float(portfolio.total_value)
        )
    
    # Create trade request
    trade_data = TradeCreate(
        account_id=request.account_id,
        symbol=signal.symbol,
        side="BUY" if signal.signal_type == "ENTRY" else "SELL",
        quantity=quantity,
        order_type=request.order_type,
        price=float(signal.recommended_price) if signal.recommended_price else None,
        strategy_name=signal.strategy_name
    )
    
    # Execute the trade
    trade = await execute_trade(trade_data, db)
    
    # Mark signal as executed
    signal.is_executed = True
    signal.execution_price = trade.price
    db.commit()
    
    return trade

@router.post("/strategy/execute", response_model=TradeResponse)
async def execute_strategy_trade(
    request: StrategyTradeRequest,
    db: Session = Depends(get_db)
):
    """Execute a trade based on strategy analysis."""
    # Get technical analysis
    technical_data = await market_data_service.get_technical_analysis(request.symbol)
    if not technical_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for {request.symbol}"
        )
    
    # Run strategy analysis
    analysis = await atr_matrix_strategy.analyze(request.symbol, technical_data)
    
    # Look for entry signals
    entry_signals = [s for s in analysis.signals if s.signal_type == "ENTRY"]
    if not entry_signals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No entry signals found for this symbol"
        )
    
    entry_signal = entry_signals[0]  # Take the first/strongest signal
    
    # Get portfolio for position sizing
    portfolio = db.query(Account).filter(Account.id == request.account_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Calculate position size
    current_price = technical_data.get('close', 0)
    position_size_pct = request.position_size_pct or 2.0  # Default 2% risk
    
    quantity = atr_matrix_strategy.calculate_position_size(
        request.symbol,
        current_price,
        float(portfolio.total_value),
        position_size_pct / 100
    )
    
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calculated position size is zero or negative"
        )
    
    # Create trade request
    trade_data = TradeCreate(
        account_id=request.account_id,
        symbol=request.symbol,
        side="BUY",
        quantity=quantity,
        order_type="MARKET",
        strategy_name=request.strategy_name,
        notes=f"ATR Matrix entry: {entry_signal.metadata.get('entry_reason', '')}"
    )
    
    if request.dry_run:
        # Return simulated trade without executing
        return TradeResponse(
            id=0,
            symbol=request.symbol,
            side="BUY",
            quantity=quantity,
            price=current_price,
            total_value=quantity * current_price,
            status="SIMULATED",
            order_type="MARKET",
            strategy_name=request.strategy_name,
            execution_time=datetime.now()
        )
    
    # Execute the actual trade
    return await execute_trade(trade_data, db)

@router.get("/trades/{account_id}", response_model=List[TradeResponse])
async def get_trades(
    account_id: int,
    limit: int = 100,
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get trade history for an account."""
    query = db.query(Trade).filter(Trade.account_id == account_id)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    
    if strategy:
        query = query.filter(Trade.strategy_name == strategy)
    
    trades = query.order_by(Trade.execution_time.desc()).limit(limit).all()
    return trades

@router.get("/signals/", response_model=List[Dict])
async def get_trade_signals(
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    active_only: bool = True,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get trade signals."""
    query = db.query(TradeSignal)
    
    if symbol:
        query = query.filter(TradeSignal.symbol == symbol.upper())
    
    if strategy:
        query = query.filter(TradeSignal.strategy_name == strategy)
    
    if active_only:
        query = query.filter(
            TradeSignal.is_valid == True,
            TradeSignal.is_executed == False
        )
    
    signals = query.order_by(TradeSignal.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": signal.id,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "strategy_name": signal.strategy_name,
            "signal_strength": signal.signal_strength,
            "recommended_price": float(signal.recommended_price) if signal.recommended_price else None,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "target_price": float(signal.target_price) if signal.target_price else None,
            "atr_distance": signal.atr_distance,
            "risk_reward_ratio": signal.risk_reward_ratio,
            "created_at": signal.created_at,
            "is_executed": signal.is_executed
        }
        for signal in signals
    ]

@router.post("/risk-check")
async def check_trade_risk(
    account_id: int,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    db: Session = Depends(get_db)
) -> RiskCheckResponse:
    """Perform risk checks for a potential trade."""
    result = await _perform_risk_checks(account_id, symbol, side, quantity, price, db)
    
    return RiskCheckResponse(
        approved=result["approved"],
        reason=result["reason"],
        max_position_size=result.get("max_position_size", 0),
        current_portfolio_risk=result.get("current_portfolio_risk", 0),
        estimated_risk=result.get("estimated_risk", 0),
        warnings=result.get("warnings", [])
    )

@router.get("/performance/{account_id}")
async def get_trading_performance(
    account_id: int,
    period: str = "1M",
    db: Session = Depends(get_db)
):
    """Get trading performance metrics."""
    # Get trades for the period
    trades = db.query(Trade).filter(
        Trade.account_id == account_id,
        Trade.status == "FILLED"
    ).order_by(Trade.execution_time.desc()).all()
    
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "sharpe_ratio": 0
        }
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.realized_pnl and t.realized_pnl > 0])
    losing_trades = len([t for t in trades if t.realized_pnl and t.realized_pnl < 0])
    
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    total_pnl = sum([float(t.realized_pnl) for t in trades if t.realized_pnl]) or 0
    
    wins = [float(t.realized_pnl) for t in trades if t.realized_pnl and t.realized_pnl > 0]
    losses = [float(t.realized_pnl) for t in trades if t.realized_pnl and t.realized_pnl < 0]
    
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "by_strategy": _get_strategy_performance(trades)
    }

async def _perform_risk_checks(
    account_id: int,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    db: Session
) -> Dict[str, Any]:
    """Perform comprehensive risk checks for a trade."""
    warnings = []
    
    # Get portfolio
    portfolio = db.query(Account).filter(Account.id == account_id).first()
    if not portfolio:
        return {"approved": False, "reason": "Portfolio not found"}
    
    trade_value = quantity * price
    
    # Check position size limits
    max_position_pct = 10.0  # 10% max per position
    max_position_value = float(portfolio.total_value) * (max_position_pct / 100)
    
    if side == "BUY" and trade_value > max_position_value:
        return {
            "approved": False,
            "reason": f"Position size exceeds {max_position_pct}% limit",
            "max_position_size": max_position_value / price
        }
    
    # Check daily trade limits
    today_trades = db.query(Trade).filter(
        Trade.account_id == account_id,
        Trade.execution_time >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    if today_trades >= 10:  # Max 10 trades per day
        return {"approved": False, "reason": "Daily trade limit exceeded"}
    
    # Check available cash for buys
    if side == "BUY":
        available_cash = float(portfolio.cash_balance)
        if trade_value > available_cash:
            return {
                "approved": False,
                "reason": "Insufficient cash",
                "available_cash": available_cash
            }
    
    # Check if position exists for sells
    if side == "SELL":
        position = db.query(Holding).filter(
            Holding.account_id == account_id,
            Holding.symbol == symbol.upper(),
            Holding.status == "OPEN"
        ).first()
        
        if not position or float(position.quantity) < quantity:
            return {
                "approved": False,
                "reason": "Insufficient shares to sell",
                "available_quantity": float(position.quantity) if position else 0
            }
    
    # Volatility warning
    technical_data = await market_data_service.get_technical_analysis(symbol)
    if technical_data:
        atr_percent = technical_data.get('atr_percent', 0)
        if atr_percent > 8:
            warnings.append(f"High volatility: {atr_percent:.1f}% ATR")
    
    return {
        "approved": True,
        "reason": "All risk checks passed",
        "max_position_size": max_position_value / price,
        "current_portfolio_risk": (trade_value / float(portfolio.total_value)) * 100,
        "estimated_risk": 2.0,  # Estimated based on ATR
        "warnings": warnings
    }

async def _update_position_from_trade(trade: Trade, db: Session):
    """Update position based on executed trade."""
    portfolio = db.query(Account).filter(Account.id == trade.account_id).first()
    if not portfolio:
        return
    
    # Find existing position
    position = db.query(Holding).filter(
        Holding.account_id == portfolio.id,
        Holding.symbol == trade.symbol,
        Holding.status == "OPEN"
    ).first()
    
    if trade.side == "BUY":
        if position:
            # Update existing position
            old_quantity = float(position.quantity)
            old_cost = float(position.avg_cost)
            new_quantity = old_quantity + float(trade.quantity)
            new_avg_cost = ((old_quantity * old_cost) + float(trade.total_value)) / new_quantity
            
            position.quantity = Decimal(str(new_quantity))
            position.avg_cost = Decimal(str(new_avg_cost))
        else:
            # Create new position
            stock_info = await market_data_service.get_stock_info(trade.symbol)
            position = Holding(
                account_id=portfolio.id,
                symbol=trade.symbol,
                name=stock_info.get('name', ''),
                quantity=trade.quantity,
                avg_cost=trade.price,
                current_price=trade.price,
                sector=stock_info.get('sector'),
                industry=stock_info.get('industry'),
                entry_date=trade.execution_time
            )
            db.add(position)
    
    elif trade.side == "SELL" and position:
        # Reduce position
        new_quantity = float(position.quantity) - float(trade.quantity)
        if new_quantity <= 0:
            position.status = "CLOSED"
            position.exit_date = trade.execution_time
        else:
            position.quantity = Decimal(str(new_quantity))
        
        # Calculate realized P&L
        cost_basis = float(position.avg_cost) * float(trade.quantity)
        realized_pnl = float(trade.total_value) - cost_basis
        trade.realized_pnl = Decimal(str(realized_pnl))

def _get_strategy_performance(trades: List[Trade]) -> Dict[str, Any]:
    """Calculate performance by strategy."""
    strategy_stats = {}
    
    for trade in trades:
        if not trade.strategy_name or not trade.realized_pnl:
            continue
        
        strategy = trade.strategy_name
        if strategy not in strategy_stats:
            strategy_stats[strategy] = {
                "trades": 0,
                "total_pnl": 0,
                "wins": 0,
                "losses": 0
            }
        
        strategy_stats[strategy]["trades"] += 1
        strategy_stats[strategy]["total_pnl"] += float(trade.realized_pnl)
        
        if trade.realized_pnl > 0:
            strategy_stats[strategy]["wins"] += 1
        else:
            strategy_stats[strategy]["losses"] += 1
    
    # Calculate win rates
    for strategy in strategy_stats:
        stats = strategy_stats[strategy]
        total = stats["trades"]
        stats["win_rate"] = (stats["wins"] / total) * 100 if total > 0 else 0
    
    return strategy_stats 