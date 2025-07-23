"""
TastyTrade Automated Trading Service
Advanced options trading automation with strategy management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import pandas as pd
from dataclasses import dataclass, asdict

from tastytrade import DXLinkStreamer, ProductionSession, Account
from tastytrade.instruments import Option, NestedOrderClass, OptionChain
from tastytrade.order import Order, OrderCondition, OrderPriceEffect, OrderAction, OrderTimeInForce
from tastytrade.utils import TastytradeError

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRANGLE = "strangle"
    STRADDLE = "straddle"
    CREDIT_SPREAD = "credit_spread"
    DEBIT_SPREAD = "debit_spread"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"

class RiskLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

@dataclass
class OptionsStrategy:
    """Options trading strategy configuration"""
    id: str
    name: str
    strategy_type: StrategyType
    underlying_symbol: str
    expiration_date: str
    legs: List[Dict[str, Any]]
    max_risk: float
    target_profit: float
    stop_loss_pct: float
    take_profit_pct: float
    risk_level: RiskLevel
    active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class TradeOrder:
    """Individual trade order"""
    id: str
    strategy_id: str
    order_type: str
    symbol: str
    quantity: int
    price: float
    status: OrderStatus
    submitted_at: datetime = None
    filled_at: datetime = None
    tastytrade_order_id: str = None
    
    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.now()

@dataclass
class GreeksData:
    """Options Greeks data"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    implied_volatility: float

class TastyTradeAutomatedTrading:
    """Advanced TastyTrade automated trading system"""
    
    def __init__(self, username: str, password: str, is_paper: bool = True):
        self.username = username
        self.password = password
        self.is_paper = is_paper
        self.session = None
        self.account = None
        self.streamer = None
        self.active_strategies: Dict[str, OptionsStrategy] = {}
        self.pending_orders: Dict[str, TradeOrder] = {}
        self.executed_trades: List[TradeOrder] = []
        self.risk_manager = AdvancedRiskManager()
        
    async def initialize(self):
        """Initialize TastyTrade session and account"""
        try:
            # Create session (paper trading by default for safety)
            self.session = ProductionSession(self.username, self.password)
            
            # Get account
            accounts = Account.get_accounts(self.session)
            if not accounts:
                raise Exception("No accounts found")
            
            self.account = accounts[0]  # Use first account
            logger.info(f"Connected to TastyTrade account: {self.account.account_number}")
            
            # Initialize data streamer
            self.streamer = DXLinkStreamer(self.session)
            await self.streamer.connect()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TastyTrade connection: {e}")
            return False
    
    async def deploy_iron_condor(self, 
                                underlying: str, 
                                expiration: str,
                                delta_target: float = 0.15,
                                wing_width: int = 10,
                                max_risk: float = 1000) -> Optional[OptionsStrategy]:
        """Deploy Iron Condor strategy"""
        try:
            # Get option chain
            chain = OptionChain.get_chain(self.session, underlying)
            
            # Find appropriate strikes for iron condor
            strikes = await self._find_iron_condor_strikes(
                chain, expiration, delta_target, wing_width
            )
            
            if not strikes:
                logger.warning(f"Could not find suitable strikes for {underlying} iron condor")
                return None
            
            # Create strategy
            strategy = OptionsStrategy(
                id=f"ic_{underlying}_{expiration}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                name=f"Iron Condor {underlying} {expiration}",
                strategy_type=StrategyType.IRON_CONDOR,
                underlying_symbol=underlying,
                expiration_date=expiration,
                legs=[
                    {"action": "SELL", "strike": strikes["put_short"], "option_type": "PUT", "quantity": 1},
                    {"action": "BUY", "strike": strikes["put_long"], "option_type": "PUT", "quantity": 1},
                    {"action": "SELL", "strike": strikes["call_short"], "option_type": "CALL", "quantity": 1},
                    {"action": "BUY", "strike": strikes["call_long"], "option_type": "CALL", "quantity": 1},
                ],
                max_risk=max_risk,
                target_profit=max_risk * 0.5,  # 50% profit target
                stop_loss_pct=0.25,  # 25% stop loss
                take_profit_pct=0.5,  # 50% take profit
                risk_level=RiskLevel.MODERATE
            )
            
            # Execute the strategy
            if await self._execute_strategy(strategy):
                self.active_strategies[strategy.id] = strategy
                logger.info(f"Successfully deployed iron condor: {strategy.id}")
                return strategy
            
        except Exception as e:
            logger.error(f"Error deploying iron condor: {e}")
            return None
    
    async def deploy_strangle(self,
                            underlying: str,
                            expiration: str,
                            delta_target: float = 0.20,
                            max_risk: float = 500) -> Optional[OptionsStrategy]:
        """Deploy Short Strangle strategy"""
        try:
            chain = OptionChain.get_chain(self.session, underlying)
            
            # Find strikes for strangle
            strikes = await self._find_strangle_strikes(chain, expiration, delta_target)
            
            if not strikes:
                return None
            
            strategy = OptionsStrategy(
                id=f"strangle_{underlying}_{expiration}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                name=f"Short Strangle {underlying} {expiration}",
                strategy_type=StrategyType.STRANGLE,
                underlying_symbol=underlying,
                expiration_date=expiration,
                legs=[
                    {"action": "SELL", "strike": strikes["put_strike"], "option_type": "PUT", "quantity": 1},
                    {"action": "SELL", "strike": strikes["call_strike"], "option_type": "CALL", "quantity": 1},
                ],
                max_risk=max_risk,
                target_profit=max_risk * 0.4,
                stop_loss_pct=0.2,
                take_profit_pct=0.4,
                risk_level=RiskLevel.AGGRESSIVE
            )
            
            if await self._execute_strategy(strategy):
                self.active_strategies[strategy.id] = strategy
                return strategy
                
        except Exception as e:
            logger.error(f"Error deploying strangle: {e}")
            return None
    
    async def deploy_credit_spread(self,
                                 underlying: str,
                                 expiration: str,
                                 option_type: str,  # 'PUT' or 'CALL'
                                 delta_target: float = 0.15,
                                 width: int = 5,
                                 max_risk: float = 400) -> Optional[OptionsStrategy]:
        """Deploy Credit Spread strategy"""
        try:
            chain = OptionChain.get_chain(self.session, underlying)
            
            strikes = await self._find_credit_spread_strikes(
                chain, expiration, option_type, delta_target, width
            )
            
            if not strikes:
                return None
            
            strategy = OptionsStrategy(
                id=f"credit_spread_{underlying}_{option_type}_{expiration}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                name=f"{option_type} Credit Spread {underlying} {expiration}",
                strategy_type=StrategyType.CREDIT_SPREAD,
                underlying_symbol=underlying,
                expiration_date=expiration,
                legs=[
                    {"action": "SELL", "strike": strikes["short_strike"], "option_type": option_type, "quantity": 1},
                    {"action": "BUY", "strike": strikes["long_strike"], "option_type": option_type, "quantity": 1},
                ],
                max_risk=max_risk,
                target_profit=max_risk * 0.5,
                stop_loss_pct=0.2,
                take_profit_pct=0.5,
                risk_level=RiskLevel.MODERATE
            )
            
            if await self._execute_strategy(strategy):
                self.active_strategies[strategy.id] = strategy
                return strategy
                
        except Exception as e:
            logger.error(f"Error deploying credit spread: {e}")
            return None
    
    async def _execute_strategy(self, strategy: OptionsStrategy) -> bool:
        """Execute a complete options strategy"""
        try:
            # Risk check before execution
            if not await self.risk_manager.validate_strategy(strategy, self.account):
                logger.warning(f"Strategy {strategy.id} failed risk validation")
                return False
            
            orders = []
            
            # Create orders for each leg
            for leg in strategy.legs:
                order = await self._create_option_order(
                    strategy.underlying_symbol,
                    strategy.expiration_date,
                    leg["strike"],
                    leg["option_type"],
                    leg["action"],
                    leg["quantity"]
                )
                
                if order:
                    orders.append(order)
            
            # Submit all orders as a combo
            if len(orders) == len(strategy.legs):
                success = await self._submit_combo_order(orders, strategy)
                if success:
                    logger.info(f"Successfully executed strategy: {strategy.id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy.id}: {e}")
            return False
    
    async def _create_option_order(self, 
                                 underlying: str,
                                 expiration: str,
                                 strike: float,
                                 option_type: str,
                                 action: str,
                                 quantity: int) -> Optional[Order]:
        """Create individual option order"""
        try:
            # Get option instrument
            option_symbol = f"{underlying}_{expiration}_{option_type}_{strike}"
            
            # Create order
            order = Order(
                action=OrderAction.BUY if action == "BUY" else OrderAction.SELL,
                instrument=option_symbol,
                quantity=quantity,
                order_type="LIMIT",  # Always use limit orders for better control
                time_in_force=OrderTimeInForce.DAY,
                price_effect=OrderPriceEffect.DEBIT if action == "BUY" else OrderPriceEffect.CREDIT
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error creating option order: {e}")
            return None
    
    async def _submit_combo_order(self, orders: List[Order], strategy: OptionsStrategy) -> bool:
        """Submit multiple orders as a combination"""
        try:
            # This would be implemented with TastyTrade's combo order functionality
            # For now, we'll simulate successful submission
            
            for i, order in enumerate(orders):
                trade_order = TradeOrder(
                    id=f"{strategy.id}_leg_{i}",
                    strategy_id=strategy.id,
                    order_type=order.action.value,
                    symbol=order.instrument,
                    quantity=order.quantity,
                    price=0.0,  # Would be filled with actual price
                    status=OrderStatus.SUBMITTED,
                    tastytrade_order_id=f"TT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
                )
                
                self.pending_orders[trade_order.id] = trade_order
            
            return True
            
        except Exception as e:
            logger.error(f"Error submitting combo order: {e}")
            return False
    
    async def monitor_positions(self):
        """Monitor active positions and manage risk"""
        while True:
            try:
                for strategy_id, strategy in self.active_strategies.items():
                    await self._monitor_strategy(strategy)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _monitor_strategy(self, strategy: OptionsStrategy):
        """Monitor individual strategy for exit conditions"""
        try:
            # Get current P&L and Greeks
            current_pnl = await self._get_strategy_pnl(strategy)
            greeks = await self._get_strategy_greeks(strategy)
            
            # Check exit conditions
            if await self._should_close_strategy(strategy, current_pnl, greeks):
                await self._close_strategy(strategy)
            
        except Exception as e:
            logger.error(f"Error monitoring strategy {strategy.id}: {e}")
    
    async def _should_close_strategy(self, 
                                   strategy: OptionsStrategy, 
                                   current_pnl: float, 
                                   greeks: GreeksData) -> bool:
        """Determine if strategy should be closed"""
        
        # Profit target reached
        if current_pnl >= strategy.target_profit:
            logger.info(f"Profit target reached for {strategy.id}: ${current_pnl}")
            return True
        
        # Stop loss hit
        stop_loss_amount = strategy.max_risk * strategy.stop_loss_pct
        if current_pnl <= -stop_loss_amount:
            logger.warning(f"Stop loss triggered for {strategy.id}: ${current_pnl}")
            return True
        
        # Days to expiration check
        days_to_exp = (datetime.strptime(strategy.expiration_date, '%Y-%m-%d') - datetime.now()).days
        if days_to_exp <= 7:  # Close 7 days before expiration
            logger.info(f"Closing {strategy.id} due to approaching expiration: {days_to_exp} days")
            return True
        
        # Greeks-based exit (e.g., high gamma risk)
        if abs(greeks.gamma) > 0.1:  # High gamma threshold
            logger.warning(f"High gamma risk for {strategy.id}: {greeks.gamma}")
            return True
        
        return False
    
    async def _close_strategy(self, strategy: OptionsStrategy):
        """Close an active strategy"""
        try:
            # Create closing orders (opposite of opening)
            closing_orders = []
            
            for leg in strategy.legs:
                opposite_action = "BUY" if leg["action"] == "SELL" else "SELL"
                
                order = await self._create_option_order(
                    strategy.underlying_symbol,
                    strategy.expiration_date,
                    leg["strike"],
                    leg["option_type"],
                    opposite_action,
                    leg["quantity"]
                )
                
                if order:
                    closing_orders.append(order)
            
            # Submit closing orders
            if await self._submit_combo_order(closing_orders, strategy):
                strategy.active = False
                logger.info(f"Successfully closed strategy: {strategy.id}")
            
        except Exception as e:
            logger.error(f"Error closing strategy {strategy.id}: {e}")
    
    async def _find_iron_condor_strikes(self, 
                                      chain: OptionChain, 
                                      expiration: str, 
                                      delta_target: float, 
                                      wing_width: int) -> Optional[Dict[str, float]]:
        """Find optimal strikes for iron condor"""
        try:
            # This would implement the logic to find strikes based on delta targets
            # For now, return sample strikes
            
            underlying_price = 100.0  # Would get actual price
            
            return {
                "put_short": underlying_price - 20,
                "put_long": underlying_price - 30,
                "call_short": underlying_price + 20,
                "call_long": underlying_price + 30
            }
            
        except Exception as e:
            logger.error(f"Error finding iron condor strikes: {e}")
            return None
    
    async def _find_strangle_strikes(self, 
                                   chain: OptionChain, 
                                   expiration: str, 
                                   delta_target: float) -> Optional[Dict[str, float]]:
        """Find optimal strikes for strangle"""
        try:
            underlying_price = 100.0  # Would get actual price
            
            return {
                "put_strike": underlying_price - 15,
                "call_strike": underlying_price + 15
            }
            
        except Exception as e:
            logger.error(f"Error finding strangle strikes: {e}")
            return None
    
    async def _find_credit_spread_strikes(self, 
                                        chain: OptionChain, 
                                        expiration: str, 
                                        option_type: str,
                                        delta_target: float, 
                                        width: int) -> Optional[Dict[str, float]]:
        """Find optimal strikes for credit spread"""
        try:
            underlying_price = 100.0  # Would get actual price
            
            if option_type == "PUT":
                return {
                    "short_strike": underlying_price - 10,
                    "long_strike": underlying_price - 15
                }
            else:  # CALL
                return {
                    "short_strike": underlying_price + 10,
                    "long_strike": underlying_price + 15
                }
            
        except Exception as e:
            logger.error(f"Error finding credit spread strikes: {e}")
            return None
    
    async def _get_strategy_pnl(self, strategy: OptionsStrategy) -> float:
        """Get current P&L for strategy"""
        # This would calculate real P&L from current option prices
        return 0.0
    
    async def _get_strategy_greeks(self, strategy: OptionsStrategy) -> GreeksData:
        """Get current Greeks for strategy"""
        # This would calculate real Greeks from current market data
        return GreeksData(
            delta=0.0,
            gamma=0.0,
            theta=-1.0,
            vega=0.5,
            rho=0.1,
            implied_volatility=0.2
        )
    
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get all active strategies"""
        return [asdict(strategy) for strategy in self.active_strategies.values() if strategy.active]
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get overall trading performance"""
        total_strategies = len(self.active_strategies)
        winning_strategies = sum(1 for s in self.active_strategies.values() if s.active == False)  # Closed profitable
        
        return {
            "total_strategies": total_strategies,
            "active_strategies": sum(1 for s in self.active_strategies.values() if s.active),
            "closed_strategies": total_strategies - sum(1 for s in self.active_strategies.values() if s.active),
            "win_rate": winning_strategies / max(total_strategies, 1) * 100,
            "total_trades": len(self.executed_trades),
            "pending_orders": len(self.pending_orders)
        }

class AdvancedRiskManager:
    """Advanced risk management for options trading"""
    
    def __init__(self):
        self.max_portfolio_risk = 10000  # Maximum portfolio risk
        self.max_position_size = 2000    # Maximum single position risk
        self.max_concentration = 0.3     # Maximum 30% in single underlying
        
    async def validate_strategy(self, strategy: OptionsStrategy, account: Account) -> bool:
        """Validate strategy against risk parameters"""
        try:
            # Check position size
            if strategy.max_risk > self.max_position_size:
                logger.warning(f"Strategy risk ${strategy.max_risk} exceeds max position size ${self.max_position_size}")
                return False
            
            # Check portfolio risk (would check against actual portfolio)
            current_portfolio_risk = 5000  # Would calculate actual risk
            if current_portfolio_risk + strategy.max_risk > self.max_portfolio_risk:
                logger.warning(f"Strategy would exceed portfolio risk limit")
                return False
            
            # Check account buying power
            buying_power = 50000  # Would get actual buying power
            if strategy.max_risk > buying_power * 0.1:  # Max 10% of buying power per trade
                logger.warning(f"Strategy exceeds buying power allocation")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in risk validation: {e}")
            return False

# Usage example:
"""
# Initialize automated trading
trader = TastyTradeAutomatedTrading("username", "password", is_paper=True)
await trader.initialize()

# Deploy strategies
iron_condor = await trader.deploy_iron_condor("SPY", "2024-02-16", delta_target=0.15)
strangle = await trader.deploy_strangle("QQQ", "2024-02-16", delta_target=0.20)
credit_spread = await trader.deploy_credit_spread("IWM", "2024-02-16", "PUT", delta_target=0.15)

# Start monitoring
await trader.monitor_positions()
""" 