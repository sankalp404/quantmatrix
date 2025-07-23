import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json
import math

from sqlalchemy.orm import Session
from backend.models import SessionLocal
from backend.models.options import (
    TastytradeAccount, TradingStrategy, StrategySignal, OptionPosition,
    OptionInstrument, OptionOrder, StrategyPerformance, CapitalAllocation,
    StrategyType, OrderAction, OrderStatus
)
from backend.services.tastytrade_client import tastytrade_client
from backend.core.strategies.atr_matrix import atr_matrix_strategy
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class ATROptionsStrategy:
    """Automated options trading strategy based on ATR Matrix signals."""
    
    def __init__(self):
        self.atr_matrix = atr_matrix_strategy
        self.profit_target_pct = 20.0  # 20% profit taking target
        self.max_position_size_pct = 5.0  # Max 5% of capital per position
        
    async def initialize_strategy(self, account_number: str, initial_capital: float = 10000.0) -> Dict[str, Any]:
        """Initialize a new ATR Matrix options strategy with capital allocation."""
        db = SessionLocal()
        
        try:
            # Ensure Tastytrade account exists
            account = await self._ensure_tastytrade_account(db, account_number)
            
            # Create or get ATR Matrix strategy
            strategy = db.query(TradingStrategy).filter(
                TradingStrategy.account_id == account.id,
                TradingStrategy.strategy_type == StrategyType.ATR_MATRIX
            ).first()
            
            if not strategy:
                strategy = TradingStrategy(
                    account_id=account.id,
                    name=f"ATR Matrix Options - {account_number}",
                    strategy_type=StrategyType.ATR_MATRIX,
                    description="Automated options trading using ATR Matrix signals with time horizon-based execution",
                    allocated_capital=Decimal(str(initial_capital)),
                    current_capital=Decimal(str(initial_capital)),
                    target_capital=Decimal("1000000.0"),  # $1M target
                    max_position_size=Decimal("5.0"),  # 5% max per position
                    profit_target_pct=Decimal("20.0"),  # 20% profit taking
                    stop_loss_pct=Decimal("50.0"),  # 50% stop loss for options
                    max_dte=45,  # Maximum 45 days to expiration
                    min_dte=7,   # Minimum 7 days to expiration
                    atr_lookback_period=14,
                    risk_reward_ratio=Decimal("2.0"),  # 2:1 risk reward
                    is_active=True,
                    is_automated=True,
                    configuration=json.dumps({
                        "target_delta_range": [0.3, 0.7],  # Target delta for options selection
                        "volatility_filter": True,
                        "liquidity_filter": True,
                        "min_open_interest": 100,
                        "max_bid_ask_spread_pct": 10.0
                    })
                )
                db.add(strategy)
                db.flush()
                
                # Create capital allocation
                allocation = CapitalAllocation(
                    account_id=account.id,
                    strategy_id=strategy.id,
                    allocated_amount=Decimal(str(initial_capital)),
                    allocation_pct=Decimal("100.0"),
                    min_allocation=Decimal("1000.0"),
                    max_allocation=Decimal("1000000.0"),
                    auto_scale_up=True,
                    auto_scale_down=True,
                    scale_up_threshold=Decimal("20.0"),
                    scale_down_threshold=Decimal("10.0")
                )
                db.add(allocation)
            
            db.commit()
            
            logger.info(f"✅ ATR Matrix options strategy initialized for {account_number} with ${initial_capital}")
            
            return {
                "strategy_id": strategy.id,
                "account_number": account_number,
                "initial_capital": initial_capital,
                "target_capital": 1000000.0,
                "status": "initialized"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error initializing ATR options strategy: {e}")
            raise
        finally:
            db.close()
    
    async def run_daily_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """Run the daily ATR Matrix options strategy."""
        db = SessionLocal()
        
        try:
            strategy = db.query(TradingStrategy).filter(TradingStrategy.id == strategy_id).first()
            if not strategy or not strategy.is_active:
                return {"error": "Strategy not found or inactive"}
            
            logger.info(f"🚀 Running ATR Matrix options strategy {strategy_id}")
            
            results = {
                "strategy_id": strategy_id,
                "signals_generated": 0,
                "positions_opened": 0,
                "positions_closed": 0,
                "total_pnl": 0.0,
                "capital_adjustments": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 1. Generate new ATR Matrix signals
            signals = await self._generate_atr_signals(db, strategy)
            results["signals_generated"] = len(signals)
            
            # 2. Process signals and open new positions
            for signal in signals:
                position_result = await self._execute_signal(db, strategy, signal)
                if position_result.get("position_opened"):
                    results["positions_opened"] += 1
            
            # 3. Monitor existing positions and close if targets hit
            close_results = await self._monitor_existing_positions(db, strategy)
            results["positions_closed"] = close_results["positions_closed"]
            results["total_pnl"] = close_results["total_pnl"]
            
            # 4. Update strategy performance
            performance = await self._update_strategy_performance(db, strategy)
            
            # 5. Handle capital scaling based on performance
            scaling_results = await self._handle_capital_scaling(db, strategy, performance)
            results["capital_adjustments"] = scaling_results
            
            db.commit()
            
            logger.info(f"✅ ATR Matrix strategy complete: {results}")
            return results
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error running ATR options strategy: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    async def _generate_atr_signals(self, db: Session, strategy: TradingStrategy) -> List[StrategySignal]:
        """Generate new ATR Matrix signals for options trading."""
        try:
            # Temporary mock implementation to get backend running
            # TODO: Implement proper integration with ATR Matrix strategy
            mock_signals = [
                {
                    "symbol": "AAPL",
                    "signal_type": "ENTRY", 
                    "time_horizon_days": 14,
                    "target_price": 185.0,
                    "current_price": 180.0,
                    "confidence_score": 0.75,
                    "atr_data": {},
                    "technical_data": {}
                },
                {
                    "symbol": "MSFT",
                    "signal_type": "ENTRY",
                    "time_horizon_days": 21, 
                    "target_price": 380.0,
                    "current_price": 370.0,
                    "confidence_score": 0.68,
                    "atr_data": {},
                    "technical_data": {}
                }
            ]
            
            options_signals = []
            
            for stock_signal in mock_signals:
                symbol = stock_signal.get("symbol")
                signal_type = stock_signal.get("signal_type", "ENTRY")
                time_horizon = stock_signal.get("time_horizon_days", 14)
                target_price = stock_signal.get("target_price")
                current_price = stock_signal.get("current_price")
                confidence = stock_signal.get("confidence_score", 0.5)
                
                if not all([symbol, target_price, current_price]) or confidence < 0.6:
                    continue
                
                # Calculate options selection criteria based on time horizon and price target
                price_move_pct = ((target_price - current_price) / current_price) * 100
                
                # Determine option type and target delta based on signal
                if price_move_pct > 2:  # Bullish signal
                    option_type = "CALL"
                    action = "BUY_TO_OPEN"
                    target_delta = 0.5  # At-the-money calls
                elif price_move_pct < -2:  # Bearish signal
                    option_type = "PUT"
                    action = "BUY_TO_OPEN"
                    target_delta = -0.5  # At-the-money puts
                else:
                    continue  # Skip low conviction signals
                
                # Calculate position size based on capital and risk
                position_size = float(strategy.current_capital) * (float(strategy.max_position_size) / 100)
                
                # Create options signal
                signal = StrategySignal(
                    strategy_id=strategy.id,
                    underlying_symbol=symbol,
                    signal_type=signal_type,
                    signal_strength=Decimal(str(confidence)),
                    target_price=Decimal(str(target_price)),
                    time_horizon_days=time_horizon,
                    risk_reward_ratio=strategy.risk_reward_ratio,
                    confidence_score=Decimal(str(confidence)),
                    target_delta=Decimal(str(abs(target_delta))),
                    max_dte=min(time_horizon + 7, strategy.max_dte),  # Add buffer to time horizon
                    min_dte=strategy.min_dte,
                    recommended_action=action,
                    position_size=Decimal(str(position_size)),
                    signal_data=json.dumps({
                        "current_price": current_price,
                        "target_price": target_price,
                        "price_move_pct": price_move_pct,
                        "option_type": option_type,
                        "atr_data": stock_signal.get("atr_data", {}),
                        "technical_data": stock_signal.get("technical_data", {})
                    }),
                    expires_at=datetime.now() + timedelta(hours=6)  # Signal expires in 6 hours
                )
                
                db.add(signal)
                options_signals.append(signal)
            
            db.flush()
            
            logger.info(f"Generated {len(options_signals)} ATR options signals")
            return options_signals
            
        except Exception as e:
            logger.error(f"Error generating ATR signals: {e}")
            return []
    
    async def _execute_signal(self, db: Session, strategy: TradingStrategy, signal: StrategySignal) -> Dict[str, Any]:
        """Execute a trading signal by finding and trading the optimal option."""
        try:
            # Get options chain for the underlying
            chain_data = await tastytrade_client.get_option_chain(signal.underlying_symbol)
            
            if "error" in chain_data:
                logger.warning(f"Could not get options chain for {signal.underlying_symbol}: {chain_data['error']}")
                return {"position_opened": False, "error": chain_data["error"]}
            
            # Find the best option to trade
            best_option = await self._select_optimal_option(chain_data, signal)
            
            if not best_option:
                logger.warning(f"No suitable option found for {signal.underlying_symbol}")
                return {"position_opened": False, "error": "No suitable option found"}
            
            # Calculate position size in contracts
            option_price = best_option.get("mid_price", 1.0)
            position_value = float(signal.position_size)
            contracts = max(1, int(position_value / (option_price * 100)))  # 100 shares per contract
            
            # Place the order
            order_result = await tastytrade_client.place_option_order(
                account_number=strategy.account.account_number,
                option_symbol=best_option["symbol"],
                action=signal.recommended_action,
                quantity=contracts,
                order_type="LIMIT",
                price=option_price * 1.05  # Add 5% buffer for fill probability
            )
            
            if "error" in order_result:
                logger.error(f"Failed to place option order: {order_result['error']}")
                return {"position_opened": False, "error": order_result["error"]}
            
            # Create database records
            option_instrument = await self._ensure_option_instrument(db, best_option)
            
            # Create order record
            order = OptionOrder(
                account_id=strategy.account_id,
                option_id=option_instrument.id,
                strategy_id=strategy.id,
                external_order_id=order_result.get("order_id"),
                action=OrderAction(signal.recommended_action.lower()),
                quantity=contracts,
                order_type="LIMIT",
                limit_price=Decimal(str(option_price * 1.05)),
                status=OrderStatus.PENDING,
                commission=Decimal(str(order_result.get("estimated_fees", 0))),
                time_in_force="DAY"
            )
            db.add(order)
            
            # Update signal as executed
            signal.is_executed = True
            signal.executed_at = datetime.now()
            signal.execution_price = Decimal(str(option_price))
            
            db.flush()
            
            logger.info(f"✅ Executed {signal.recommended_action} {contracts} contracts of {best_option['symbol']}")
            
            return {
                "position_opened": True,
                "symbol": best_option["symbol"],
                "action": signal.recommended_action,
                "contracts": contracts,
                "price": option_price,
                "order_id": order_result.get("order_id")
            }
            
        except Exception as e:
            logger.error(f"Error executing signal for {signal.underlying_symbol}: {e}")
            return {"position_opened": False, "error": str(e)}
    
    async def _select_optimal_option(self, chain_data: Dict, signal: StrategySignal) -> Optional[Dict]:
        """Select the optimal option contract based on strategy criteria."""
        try:
            signal_data = json.loads(signal.signal_data)
            option_type = signal_data.get("option_type", "CALL").lower()
            target_delta = float(signal.target_delta)
            
            current_date = datetime.now().date()
            
            # Filter options by expiration date
            valid_expirations = []
            for exp_date, options_data in chain_data["options_data"].items():
                exp_datetime = datetime.strptime(exp_date, "%Y-%m-%d").date()
                days_to_exp = (exp_datetime - current_date).days
                
                if signal.min_dte <= days_to_exp <= signal.max_dte:
                    valid_expirations.append((exp_date, options_data, days_to_exp))
            
            if not valid_expirations:
                return None
            
            # Sort by closest to ideal DTE (time horizon + 7 days buffer)
            ideal_dte = signal.time_horizon_days + 7
            valid_expirations.sort(key=lambda x: abs(x[2] - ideal_dte))
            
            # Get current underlying price for delta calculation
            current_price = signal_data.get("current_price")
            
            best_option = None
            best_score = -1
            
            # Look through the best expiration dates
            for exp_date, options_data, dte in valid_expirations[:3]:
                options_list = options_data.get("calls" if option_type == "call" else "puts", [])
                
                for option in options_list:
                    strike = option["strike_price"]
                    
                    # Calculate approximate delta based on moneyness
                    if option_type == "call":
                        moneyness = current_price / strike
                        approx_delta = max(0.1, min(0.9, moneyness * 0.6))  # Rough approximation
                    else:
                        moneyness = strike / current_price
                        approx_delta = max(0.1, min(0.9, moneyness * 0.6))
                    
                    # Score based on how close delta is to target
                    delta_score = 1 - abs(approx_delta - target_delta) / target_delta
                    
                    # Prefer closer to ATM for better liquidity
                    atm_score = 1 - abs(strike - current_price) / current_price
                    
                    # Combined score
                    total_score = (delta_score * 0.7) + (atm_score * 0.3)
                    
                    if total_score > best_score:
                        best_score = total_score
                        
                        # Get real-time quote for pricing
                        quotes = await tastytrade_client.get_real_time_quotes([option["symbol"]])
                        quote_data = quotes.get(option["symbol"], {})
                        
                        bid = quote_data.get("bid_price", 0)
                        ask = quote_data.get("ask_price", 0)
                        mid_price = (bid + ask) / 2 if bid and ask else 1.0
                        
                        best_option = {
                            **option,
                            "expiration_date": exp_date,
                            "days_to_expiration": dte,
                            "approx_delta": approx_delta,
                            "bid_price": bid,
                            "ask_price": ask,
                            "mid_price": mid_price,
                            "score": total_score
                        }
            
            return best_option
            
        except Exception as e:
            logger.error(f"Error selecting optimal option: {e}")
            return None
    
    async def _monitor_existing_positions(self, db: Session, strategy: TradingStrategy) -> Dict[str, Any]:
        """Monitor existing positions and close if profit targets or stop losses are hit."""
        try:
            positions = db.query(OptionPosition).filter(
                OptionPosition.account_id == strategy.account_id,
                OptionPosition.strategy_id == strategy.id,
                OptionPosition.quantity != 0
            ).all()
            
            positions_closed = 0
            total_pnl = 0.0
            
            for position in positions:
                # Get current option price
                current_quotes = await tastytrade_client.get_real_time_quotes([position.option.symbol])
                quote_data = current_quotes.get(position.option.symbol, {})
                
                if not quote_data:
                    continue
                
                current_price = quote_data.get("last_price", 0)
                if not current_price:
                    current_price = (quote_data.get("bid_price", 0) + quote_data.get("ask_price", 0)) / 2
                
                if not current_price:
                    continue
                
                # Calculate P&L
                entry_price = float(position.average_open_price)
                pnl_per_contract = (current_price - entry_price) * 100  # $100 per point
                total_position_pnl = pnl_per_contract * position.quantity
                pnl_pct = (total_position_pnl / float(position.position_cost)) * 100
                
                # Check if we should close the position
                should_close = False
                close_reason = None
                
                # Check profit target (20% gain)
                if pnl_pct >= float(strategy.profit_target_pct):
                    should_close = True
                    close_reason = "PROFIT_TARGET"
                
                # Check stop loss (50% loss for options)
                elif pnl_pct <= -float(strategy.stop_loss_pct):
                    should_close = True
                    close_reason = "STOP_LOSS"
                
                # Check expiration (close if less than 7 days)
                elif position.option.expiration_date.date() - datetime.now().date() < timedelta(days=7):
                    should_close = True
                    close_reason = "EXPIRATION"
                
                if should_close:
                    close_result = await self._close_position(db, position, current_price, close_reason)
                    if close_result["success"]:
                        positions_closed += 1
                        total_pnl += close_result["pnl"]
                        
                        logger.info(f"Closed position {position.option.symbol}: {close_reason} - P&L: ${close_result['pnl']:.2f}")
            
            return {
                "positions_closed": positions_closed,
                "total_pnl": total_pnl
            }
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return {"positions_closed": 0, "total_pnl": 0.0}
    
    async def _close_position(self, db: Session, position: OptionPosition, current_price: float, reason: str) -> Dict[str, Any]:
        """Close an options position."""
        try:
            # Determine closing action
            if position.quantity > 0:
                close_action = "SELL_TO_CLOSE"
            else:
                close_action = "BUY_TO_CLOSE"
            
            # Place closing order
            order_result = await tastytrade_client.place_option_order(
                account_number=position.account.account_number,
                option_symbol=position.option.symbol,
                action=close_action,
                quantity=abs(position.quantity),
                order_type="MARKET"  # Use market order for quick execution
            )
            
            if "error" in order_result:
                return {"success": False, "error": order_result["error"]}
            
            # Calculate P&L
            entry_price = float(position.average_open_price)
            pnl_per_contract = (current_price - entry_price) * 100
            total_pnl = pnl_per_contract * position.quantity
            
            # Create closing order record
            order = OptionOrder(
                account_id=position.account_id,
                option_id=position.option_id,
                strategy_id=position.strategy_id,
                external_order_id=order_result.get("order_id"),
                action=OrderAction(close_action.lower()),
                quantity=abs(position.quantity),
                order_type="MARKET",
                filled_price=Decimal(str(current_price)),
                filled_quantity=abs(position.quantity),
                status=OrderStatus.FILLED,
                commission=Decimal(str(order_result.get("estimated_fees", 0))),
                filled_at=datetime.now()
            )
            db.add(order)
            
            # Update position (set quantity to 0)
            position.quantity = 0
            position.current_price = Decimal(str(current_price))
            position.unrealized_pnl = Decimal(str(total_pnl))
            position.last_updated = datetime.now()
            
            # Update strategy capital
            position.strategy.current_capital += Decimal(str(total_pnl))
            
            db.flush()
            
            return {
                "success": True,
                "pnl": total_pnl,
                "reason": reason,
                "order_id": order_result.get("order_id")
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_capital_scaling(self, db: Session, strategy: TradingStrategy, performance: Dict) -> List[Dict]:
        """Handle automated capital scaling based on performance."""
        try:
            allocation = db.query(CapitalAllocation).filter(
                CapitalAllocation.strategy_id == strategy.id
            ).first()
            
            if not allocation or not allocation.auto_scale_up:
                return []
            
            current_pnl_pct = performance.get("total_pnl_pct", 0)
            adjustments = []
            
            # Scale up if hitting profit target
            if current_pnl_pct >= float(allocation.scale_up_threshold):
                # Increase allocation by 50% of profits
                profit_amount = float(strategy.current_capital) - float(strategy.allocated_capital)
                scale_amount = profit_amount * 0.5
                
                new_allocation = float(allocation.allocated_amount) + scale_amount
                
                # Cap at max allocation
                if allocation.max_allocation:
                    new_allocation = min(new_allocation, float(allocation.max_allocation))
                
                allocation.allocated_amount = Decimal(str(new_allocation))
                strategy.allocated_capital = Decimal(str(new_allocation))
                allocation.last_rebalance_at = datetime.now()
                
                adjustments.append({
                    "type": "scale_up",
                    "amount": scale_amount,
                    "new_allocation": new_allocation,
                    "reason": f"Profit target hit: {current_pnl_pct:.1f}%"
                })
                
                logger.info(f"🚀 Scaled up strategy capital to ${new_allocation:,.2f}")
            
            # Check if we've hit the million-dollar target
            if float(strategy.current_capital) >= 1000000:
                adjustments.append({
                    "type": "target_achieved",
                    "amount": float(strategy.current_capital),
                    "message": "🎉 $1M TARGET ACHIEVED! 🎉"
                })
                
                logger.info(f"🎉 MILLION DOLLAR TARGET ACHIEVED! Current capital: ${float(strategy.current_capital):,.2f}")
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error handling capital scaling: {e}")
            return []
    
    async def _update_strategy_performance(self, db: Session, strategy: TradingStrategy) -> Dict:
        """Update daily strategy performance metrics."""
        try:
            # Calculate performance metrics
            initial_capital = float(strategy.allocated_capital)
            current_capital = float(strategy.current_capital)
            total_pnl = current_capital - initial_capital
            total_pnl_pct = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0
            
            # Update strategy record
            strategy.total_pnl = Decimal(str(total_pnl))
            strategy.total_pnl_pct = Decimal(str(total_pnl_pct))
            strategy.updated_at = datetime.now()
            
            performance = {
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "current_capital": current_capital,
                "initial_capital": initial_capital
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error updating strategy performance: {e}")
            return {}
    
    async def _ensure_tastytrade_account(self, db: Session, account_number: str) -> TastytradeAccount:
        """Ensure Tastytrade account exists in database."""
        account = db.query(TastytradeAccount).filter(
            TastytradeAccount.account_number == account_number
        ).first()
        
        if not account:
            account = TastytradeAccount(
                account_number=account_number,
                nickname=f"Options Trading {account_number}",
                account_type="Options Trading",
                is_active=True
            )
            db.add(account)
            db.flush()
        
        return account
    
    async def _ensure_option_instrument(self, db: Session, option_data: Dict) -> OptionInstrument:
        """Ensure option instrument exists in database."""
        symbol = option_data["symbol"]
        
        instrument = db.query(OptionInstrument).filter(
            OptionInstrument.symbol == symbol
        ).first()
        
        if not instrument:
            from backend.models.options import OptionType
            
            instrument = OptionInstrument(
                symbol=symbol,
                underlying_symbol=option_data["underlying_symbol"],
                strike_price=Decimal(str(option_data["strike_price"])),
                expiration_date=datetime.strptime(option_data["expiration_date"], "%Y-%m-%d"),
                option_type=OptionType.CALL if option_data["option_type"].upper() == "CALL" else OptionType.PUT,
                streamer_symbol=option_data.get("streamer_symbol", symbol)
            )
            db.add(instrument)
            db.flush()
        
        return instrument

# Global ATR options strategy instance
atr_options_strategy = ATROptionsStrategy() 