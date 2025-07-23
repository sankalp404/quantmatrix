import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

try:
    from tastytrade import Session, Account, DXLinkStreamer
    from tastytrade.account import CurrentPosition
    from tastytrade.instruments import get_option_chain, Equity, Option
    from tastytrade.dxfeed import Quote, Greeks, Trade
    from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType
    TASTYTRADE_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("tastytrade SDK not available - options trading integration disabled")
    TASTYTRADE_AVAILABLE = False

from backend.config import settings

logger = logging.getLogger(__name__)

class TastytradeClient:
    """Client for interacting with Tastytrade API using the official SDK."""
    
    def __init__(self):
        self.session = None
        self.streamer = None
        self.connected = False
        self.accounts = []
        
    async def connect(self) -> bool:
        """Connect to Tastytrade API using the correct SDK 10.x API."""
        if not TASTYTRADE_AVAILABLE:
            logger.warning("Tastytrade SDK not available")
            return False
            
        try:
            if not self.connected:
                logger.info("Connecting to Tastytrade API...")
                
                # Use the configured environment (don't fallback if live account)
                is_test_env = settings.TASTYTRADE_IS_TEST
                env_name = "CERTIFICATION" if is_test_env else "PRODUCTION"
                
                logger.info(f"Attempting connection to {env_name} environment...")
                self.session = Session(
                    settings.TASTYTRADE_USERNAME,
                    settings.TASTYTRADE_PASSWORD,
                    is_test=is_test_env
                )
                
                # Test the connection by getting accounts
                self.accounts = await Account.a_get(self.session)
                self.connected = True
                
                logger.info(f"✅ Connected to Tastytrade {env_name} - {len(self.accounts)} accounts found")
                return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to Tastytrade {env_name if 'env_name' in locals() else 'UNKNOWN'}: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Tastytrade."""
        try:
            if self.streamer:
                await self.streamer.close()
                self.streamer = None
                
            if self.session:
                self.session = None
                
            self.connected = False
            logger.info("Disconnected from Tastytrade")
        except Exception as e:
            logger.error(f"Error disconnecting from Tastytrade: {e}")
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all Tastytrade accounts."""
        if not TASTYTRADE_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            account_data = []
            for account in self.accounts:
                # Create account info with only available attributes
                account_info = {
                    'account_id': account.account_number,
                    'account_number': account.account_number,
                    'account-number': account.account_number,  # TastyTrade format
                    'account_type': getattr(account, 'account_type', 'Options Trading'),
                    'nickname': getattr(account, 'nickname', f"TastyTrade {account.account_number}"),
                    'is_margin': getattr(account, 'margin_or_cash', 'Cash') == 'Margin',
                    'is-test-drive': getattr(account, 'is_test_drive', False),
                    'account-type': 'brokerage',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add any other available attributes safely
                for attr in ['day_trader_status', 'account_status', 'is_closed']:
                    if hasattr(account, attr):
                        account_info[attr] = getattr(account, attr)
                
                account_data.append(account_info)
                logger.info(f"Successfully processed TastyTrade account: {account.account_number}")
            
            return account_data
            
        except Exception as e:
            logger.error(f"Error getting Tastytrade accounts: {e}")
            return []
    
    async def get_account_balance(self, account_number: str = None) -> Dict[str, Any]:
        """Get account balance and buying power."""
        if not TASTYTRADE_AVAILABLE:
            return {'error': 'Tastytrade not available'}
            
        try:
            if not self.connected:
                await self.connect()
            
            # Use specified account or first account
            account = None
            if account_number:
                account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            else:
                account = self.accounts[0] if self.accounts else None
            
            if not account:
                return {'error': 'Account not found'}
            
            # Get balance information
            balances = await account.a_get_balances(self.session)
            
            return {
                'account_number': account.account_number,
                'net_liquidating_value': float(balances.net_liquidating_value),
                'total_cash': float(balances.total_cash),
                'available_trading_funds': float(balances.available_trading_funds),
                'buying_power': float(balances.buying_power),
                'day_trading_buying_power': float(balances.day_trading_buying_power),
                'maintenance_requirement': float(balances.maintenance_requirement),
                'margin_equity': float(balances.margin_equity),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {'error': str(e)}
    
    async def get_positions(self, account_number: str = None) -> List[Dict[str, Any]]:
        """Get current positions including options."""
        if not TASTYTRADE_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            account = None
            if account_number:
                account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            else:
                account = self.accounts[0] if self.accounts else None
            
            if not account:
                return []
            
            positions = await account.a_get_positions(self.session)
            
            position_data = []
            for pos in positions:
                position_info = {
                    'symbol': pos.symbol,
                    'instrument_type': pos.instrument_type.value,
                    'underlying_symbol': pos.underlying_symbol,
                    'quantity': float(pos.quantity),
                    'quantity_direction': pos.quantity_direction,
                    'average_open_price': float(pos.average_open_price),
                    'market_value': float(pos.close_price * pos.quantity) if pos.close_price else 0,
                    'close_price': float(pos.close_price) if pos.close_price else 0,
                    'unrealized_day_gain': float(pos.realized_day_gain) if pos.realized_day_gain else 0,
                    'multiplier': pos.multiplier,
                    'account_number': pos.account_number,
                    'created_at': pos.created_at.isoformat() if pos.created_at else None,
                    'updated_at': pos.updated_at.isoformat() if pos.updated_at else None
                }
                
                # Add options-specific data if it's an option
                if pos.instrument_type.value in ['Equity Option', 'Future Option']:
                    # Parse option symbol (e.g., 'PLTR  250815C00195000')
                    symbol = pos.symbol
                    strike_price = None
                    expiration_date = None
                    option_type = None
                    
                    try:
                        if len(symbol) >= 18:  # Standard option symbol format
                            # Parse expiration date (YYMMDD)
                            exp_str = symbol[6:12]  # chars 6-11
                            expiration_date = f"20{exp_str[:2]}-{exp_str[2:4]}-{exp_str[4:6]}"
                            
                            # Parse option type (C or P)
                            option_type_char = symbol[12]  # char 12
                            option_type = 'Call' if option_type_char == 'C' else 'Put'
                            
                            # Parse strike price (in thousandths)
                            strike_str = symbol[13:]  # chars 13+
                            if strike_str.isdigit():
                                strike_price = float(strike_str) / 1000.0
                                
                    except Exception as e:
                        logger.debug(f"Could not parse option symbol {symbol}: {e}")
                    
                    position_info.update({
                        'strike_price': strike_price,
                        'expiration_date': expiration_date,
                        'option_type': option_type,
                        'expires_at': pos.expires_at.isoformat() if pos.expires_at else None
                    })
                
                position_data.append(position_info)
            
            return position_data
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_option_chain(self, underlying_symbol: str, expiration_date: str = None) -> Dict[str, Any]:
        """Get options chain for underlying symbol."""
        if not TASTYTRADE_AVAILABLE:
            return {'error': 'Tastytrade not available'}
            
        try:
            if not self.connected:
                await self.connect()
            
            # Get option chain
            chain = get_option_chain(self.session, underlying_symbol)
            
            if not chain:
                return {'error': f'No options chain found for {underlying_symbol}'}
            
            # Process chain data
            options_data = {}
            for exp_date, options in chain.items():
                exp_str = exp_date.strftime('%Y-%m-%d')
                
                # Skip if specific expiration requested and doesn't match
                if expiration_date and exp_str != expiration_date:
                    continue
                
                calls = []
                puts = []
                
                for option in options:
                    option_data = {
                        'symbol': option.symbol,
                        'strike_price': float(option.strike_price),
                        'option_type': option.option_type.value,
                        'expiration_date': exp_str,
                        'days_to_expiration': (exp_date - datetime.now().date()).days,
                        'streamer_symbol': option.streamer_symbol
                    }
                    
                    if option.option_type.value == 'Call':
                        calls.append(option_data)
                    else:
                        puts.append(option_data)
                
                options_data[exp_str] = {
                    'calls': sorted(calls, key=lambda x: x['strike_price']),
                    'puts': sorted(puts, key=lambda x: x['strike_price']),
                    'expiration_date': exp_str,
                    'days_to_expiration': (exp_date - datetime.now().date()).days
                }
            
            return {
                'underlying_symbol': underlying_symbol,
                'options_data': options_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting option chain for {underlying_symbol}: {e}")
            return {'error': str(e)}
    
    async def get_real_time_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get real-time quotes for symbols."""
        if not TASTYTRADE_AVAILABLE:
            return {}
            
        try:
            if not self.connected:
                await self.connect()
            
            quotes_data = {}
            
            # Use streaming data for real-time quotes
            async with DXLinkStreamer(self.session) as streamer:
                await streamer.subscribe(Quote, symbols)
                
                # Collect quotes for a short time
                end_time = datetime.now() + timedelta(seconds=5)
                while datetime.now() < end_time:
                    try:
                        quote = await asyncio.wait_for(streamer.get_event(Quote), timeout=1.0)
                        quotes_data[quote.event_symbol] = {
                            'symbol': quote.event_symbol,
                            'bid_price': float(quote.bid_price) if quote.bid_price else 0,
                            'ask_price': float(quote.ask_price) if quote.ask_price else 0,
                            'bid_size': float(quote.bid_size) if quote.bid_size else 0,
                            'ask_size': float(quote.ask_size) if quote.ask_size else 0,
                            'last_price': (float(quote.bid_price) + float(quote.ask_price)) / 2 if quote.bid_price and quote.ask_price else 0,
                            'timestamp': datetime.now().isoformat()
                        }
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error getting quote: {e}")
                        break
            
            return quotes_data
            
        except Exception as e:
            logger.error(f"Error getting real-time quotes: {e}")
            return {}
    
    async def get_options_greeks(self, option_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get real-time Greeks for options."""
        if not TASTYTRADE_AVAILABLE:
            return {}
            
        try:
            if not self.connected:
                await self.connect()
            
            greeks_data = {}
            
            async with DXLinkStreamer(self.session) as streamer:
                await streamer.subscribe(Greeks, option_symbols)
                
                # Collect Greeks for a short time
                end_time = datetime.now() + timedelta(seconds=5)
                while datetime.now() < end_time:
                    try:
                        greeks = await asyncio.wait_for(streamer.get_event(Greeks), timeout=1.0)
                        greeks_data[greeks.event_symbol] = {
                            'symbol': greeks.event_symbol,
                            'price': float(greeks.price) if greeks.price else 0,
                            'volatility': float(greeks.volatility) if greeks.volatility else 0,
                            'delta': float(greeks.delta) if greeks.delta else 0,
                            'gamma': float(greeks.gamma) if greeks.gamma else 0,
                            'theta': float(greeks.theta) if greeks.theta else 0,
                            'rho': float(greeks.rho) if greeks.rho else 0,
                            'vega': float(greeks.vega) if greeks.vega else 0,
                            'timestamp': datetime.now().isoformat()
                        }
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error getting Greeks: {e}")
                        break
            
            return greeks_data
            
        except Exception as e:
            logger.error(f"Error getting options Greeks: {e}")
            return {}
    
    async def place_option_order(self, account_number: str, option_symbol: str, action: str, 
                               quantity: int, order_type: str = 'LIMIT', price: float = None) -> Dict[str, Any]:
        """Place an options order."""
        if not TASTYTRADE_AVAILABLE:
            return {'error': 'Tastytrade not available'}
            
        try:
            if not self.connected:
                await self.connect()
            
            account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            if not account:
                return {'error': 'Account not found'}
            
            # Get the option instrument
            option = Option.get(self.session, option_symbol)
            if not option:
                return {'error': f'Option {option_symbol} not found'}
            
            # Convert action string to OrderAction enum
            action_map = {
                'BUY_TO_OPEN': OrderAction.BUY_TO_OPEN,
                'SELL_TO_OPEN': OrderAction.SELL_TO_OPEN,
                'BUY_TO_CLOSE': OrderAction.BUY_TO_CLOSE,
                'SELL_TO_CLOSE': OrderAction.SELL_TO_CLOSE
            }
            
            order_action = action_map.get(action.upper())
            if not order_action:
                return {'error': f'Invalid action: {action}'}
            
            # Build the leg
            leg = option.build_leg(Decimal(str(quantity)), order_action)
            
            # Create the order
            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.LIMIT if order_type.upper() == 'LIMIT' else OrderType.MARKET,
                legs=[leg],
                price=Decimal(str(price)) if price else None
            )
            
            # Place the order (dry run for safety)
            response = await account.a_place_order(self.session, order, dry_run=True)
            
            return {
                'order_id': response.order.id if response.order else None,
                'status': 'submitted',
                'account_number': account_number,
                'symbol': option_symbol,
                'action': action,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'estimated_fees': float(response.fee_calculation.total_fees) if response.fee_calculation else 0,
                'buying_power_effect': float(response.buying_power_effect.change_in_buying_power) if response.buying_power_effect else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error placing option order: {e}")
            return {'error': str(e)}
    
    async def get_order_history(self, account_number: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent order history."""
        if not TASTYTRADE_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            if not account:
                return []
            
            # Get orders from the last N days
            start_date = datetime.now() - timedelta(days=days)
            orders = await account.a_get_orders(self.session, start_date=start_date.date())
            
            order_history = []
            for order in orders:
                order_data = {
                    'order_id': order.id,
                    'status': order.status.value,
                    'underlying_symbol': order.underlying_symbol,
                    'order_type': order.order_type.value,
                    'time_in_force': order.time_in_force.value,
                    'price': float(order.price) if order.price else None,
                    'quantity': sum(float(leg.quantity) for leg in order.legs),
                    'filled_quantity': sum(float(leg.quantity) - float(leg.remaining_quantity) for leg in order.legs),
                    'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                    'legs': []
                }
                
                # Add leg details
                for leg in order.legs:
                    leg_data = {
                        'symbol': leg.symbol,
                        'instrument_type': leg.instrument_type.value,
                        'action': leg.action.value,
                        'quantity': float(leg.quantity),
                        'remaining_quantity': float(leg.remaining_quantity),
                        'fills': [
                            {
                                'price': float(fill.price),
                                'quantity': float(fill.quantity),
                                'time': fill.time.isoformat() if fill.time else None
                            } for fill in leg.fills
                        ]
                    }
                    order_data['legs'].append(leg_data)
                
                order_history.append(order_data)
            
            return order_history
            
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []

    async def get_transaction_history(self, account_number: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get transaction history for a specific TastyTrade account."""
        if not TASTYTRADE_AVAILABLE or not self.connected:
            logger.warning("TastyTrade not connected")
            return []
        
        try:
            # Find the account
            account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            if not account:
                logger.error(f"Account {account_number} not found")
                return []
            
            # Get transaction history using the TastyTrade API
            from tastytrade.account import get_transactions
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Fetch transactions from TastyTrade
            transactions = await get_transactions(
                session=self.session,
                account=account.account_number,
                start_date=start_date,
                end_date=end_date
            )
            
            # Transform TastyTrade transactions to our standard format
            transformed_transactions = []
            for txn in transactions:
                transformed_txn = {
                    'id': f"tt_{txn.id}",
                    'date': txn.executed_at.strftime('%Y-%m-%d') if txn.executed_at else '',
                    'time': txn.executed_at.strftime('%H:%M:%S') if txn.executed_at else '',
                    'symbol': getattr(txn.instrument, 'symbol', '') if txn.instrument else '',
                    'description': txn.action or '',
                    'type': 'BUY' if txn.action in ['Buy to Open', 'Buy to Close'] else 'SELL',
                    'action': txn.action or '',
                    'quantity': float(txn.quantity) if txn.quantity else 0,
                    'price': float(txn.price) if txn.price else 0,
                    'amount': float(txn.value) if txn.value else 0,
                    'commission': float(txn.commission) if txn.commission else 0,
                    'fees': float(txn.regulatory_fees) if hasattr(txn, 'regulatory_fees') and txn.regulatory_fees else 0,
                    'net_amount': float(txn.net_value) if txn.net_value else 0,
                    'currency': 'USD',
                    'exchange': 'TASTYTRADE',
                    'order_id': str(txn.order_id) if txn.order_id else '',
                    'execution_id': str(txn.id),
                    'contract_type': getattr(txn.instrument, 'instrument_type', 'EQUITY') if txn.instrument else 'EQUITY',
                    'account': account_number,
                    'settlement_date': txn.clearing_date.strftime('%Y-%m-%d') if txn.clearing_date else None,
                    'source': 'tastytrade'
                }
                transformed_transactions.append(transformed_txn)
            
            logger.info(f"Retrieved {len(transformed_transactions)} transactions for TastyTrade account {account_number}")
            return transformed_transactions
            
        except Exception as e:
            logger.error(f"Error getting TastyTrade transaction history: {e}")
            return []
    
    async def get_all_transactions(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """Get transaction history for all TastyTrade accounts."""
        if not self.connected:
            await self.connect()
        
        all_transactions = {}
        for account in self.accounts:
            transactions = await self.get_transaction_history(account.account_number, days)
            all_transactions[account.account_number] = transactions
        
        return all_transactions
    
    async def get_dividend_history(self, account_number: str, days: int = 365) -> List[Dict[str, Any]]:
        """Get dividend history for a specific TastyTrade account."""
        if not TASTYTRADE_AVAILABLE or not self.connected:
            logger.warning("TastyTrade not connected")
            return []
        
        try:
            # Find the account
            account = next((acc for acc in self.accounts if acc.account_number == account_number), None)
            if not account:
                logger.error(f"Account {account_number} not found")
                return []
            
            # Get dividend transactions from transaction history
            transactions = await self.get_transaction_history(account_number, days)
            
            # Filter for dividend transactions
            dividend_transactions = []
            for txn in transactions:
                if 'dividend' in txn['description'].lower() or 'distribution' in txn['description'].lower():
                    dividend_txn = {
                        'symbol': txn['symbol'],
                        'ex_date': txn['date'],  # TastyTrade might not have exact ex-date
                        'pay_date': txn['date'],
                        'dividend_per_share': abs(txn['amount'] / txn['quantity']) if txn['quantity'] > 0 else 0,
                        'shares_held': txn['quantity'],
                        'total_dividend': abs(txn['amount']),
                        'tax_withheld': 0,  # TastyTrade might not break this out
                        'net_dividend': abs(txn['net_amount']),
                        'currency': txn['currency'],
                        'frequency': 'quarterly',  # Default assumption
                        'type': 'ordinary',
                        'account': account_number,
                        'external_id': txn['id'],
                        'source': 'tastytrade'
                    }
                    dividend_transactions.append(dividend_txn)
            
            logger.info(f"Retrieved {len(dividend_transactions)} dividend payments for TastyTrade account {account_number}")
            return dividend_transactions
            
        except Exception as e:
            logger.error(f"Error getting TastyTrade dividend history: {e}")
            return []

# Global Tastytrade client instance
tastytrade_client = TastytradeClient() 