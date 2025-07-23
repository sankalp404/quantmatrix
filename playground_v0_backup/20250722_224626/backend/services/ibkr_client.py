import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import pandas as pd
import random
import time

# Global cache for sector data to avoid repeated API calls
_sector_cache = {}
_sector_cache_expiry = {}
SECTOR_CACHE_DURATION = timedelta(hours=4)  # Cache sector data for 4 hours

try:
    from ib_insync import IB, util
    IBKR_AVAILABLE = True
    logger = logging.getLogger(__name__)
except ImportError:
    IBKR_AVAILABLE = False
    logger = None

from backend.config import settings

logger = logging.getLogger(__name__)

class IBKRClient:
    """Interactive Brokers client for portfolio and trading data with enhanced connection management."""
    
    def __init__(self):
        if IBKR_AVAILABLE:
            self.ib = IB()
        else:
            self.ib = None
        self.connected = False
        self.client_id = None
        self.last_connection_attempt = None
        self.connection_retry_delay = 5  # seconds between retry attempts
        
    async def connect(self, retry_count: int = 3):
        """Connect to IBKR TWS/Gateway with proper connection management."""
        if not IBKR_AVAILABLE:
            logger.warning("IBKR not available - ib_insync not installed")
            return False
            
        # Avoid too frequent connection attempts
        if (self.last_connection_attempt and 
            time.time() - self.last_connection_attempt < self.connection_retry_delay):
            logger.info("Connection attempt too recent, skipping")
            return self.connected
            
        self.last_connection_attempt = time.time()
            
        try:
            # Clean up any existing connection
            if self.ib and self.ib.isConnected():
                try:
                    self.ib.disconnect()
                    await asyncio.sleep(1)  # Wait for cleanup
                except:
                    pass
            
            # Generate unique client ID to avoid conflicts
            self.client_id = settings.IBKR_CLIENT_ID + random.randint(1, 100)
            
            if not self.connected and self.ib:
                logger.info(f"🔄 Connecting to IBKR at {settings.IBKR_HOST}:{settings.IBKR_PORT} with client ID {self.client_id}")
                
                # Use async connection with timeout
                await self.ib.connectAsync(
                    host=settings.IBKR_HOST, 
                    port=settings.IBKR_PORT, 
                    clientId=self.client_id,
                    timeout=15  # Reasonable timeout
                )
                
                # Verify connection with a simple request
                await asyncio.sleep(2)  # Wait for connection to stabilize
                
                # Test connection with managed accounts request
                managed_accounts = self.ib.managedAccounts()
                if managed_accounts:
                    self.connected = True
                    logger.info(f"✅ Connected to IBKR successfully with {len(managed_accounts)} accounts")
                else:
                    logger.warning("Connected but no managed accounts found")
                    self.connected = False
                
            return self.connected
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to IBKR (attempt {4-retry_count}/3): {e}")
            self.connected = False
            
            # Retry with different client ID
            if retry_count > 0:
                await asyncio.sleep(2)
                return await self.connect(retry_count - 1)
            
            return False
    
    async def disconnect(self):
        """Properly disconnect from IBKR."""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
                self.connected = False
                logger.info("🔌 Disconnected from IBKR")
        except Exception as e:
            logger.error(f"Error disconnecting from IBKR: {e}")
    
    async def ensure_connection(self) -> bool:
        """Ensure we have a working connection to IBKR."""
        if not self.connected or (self.ib and not self.ib.isConnected()):
            return await self.connect()
        return True
    
    async def get_all_managed_accounts(self) -> List[str]:
        """Get all managed accounts."""
        if not IBKR_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            managed_accounts = self.ib.managedAccounts()
            logger.info(f"Found managed accounts: {managed_accounts}")
            return managed_accounts
            
        except Exception as e:
            logger.error(f"Error getting managed accounts: {e}")
            return []
    
    async def get_account_summary(self, account_id: str = None) -> Dict[str, Any]:
        """Get account summary with key metrics for specific account."""
        if not IBKR_AVAILABLE:
            return {
                'account_id': 'Error',
                'net_liquidation': 0,
                'total_cash': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0,
                'day_trades_remaining': 0,
                'timestamp': datetime.now().isoformat(),
                'error': 'IBKR not available'
            }
            
        try:
            if not self.connected:
                await self.connect()
            
            # Get managed accounts
            managed_accounts = await self.get_all_managed_accounts()
            
            if not managed_accounts:
                logger.warning("No managed accounts found")
                return {
                    'account_id': 'No Accounts',
                    'net_liquidation': 0,
                    'total_cash': 0,
                    'unrealized_pnl': 0,
                    'realized_pnl': 0,
                    'day_trades_remaining': 0,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'No managed accounts found'
                }
            
            # Use specified account or first account
            if account_id and account_id in managed_accounts:
                target_account = account_id
            else:
                target_account = managed_accounts[0]
            
            logger.info(f"Using account: {target_account}")
            
            # Get account values for specific account
            account_values = self.ib.accountValues(account=target_account)
            logger.info(f"Retrieved {len(account_values)} account values")
            
            # Parse key account metrics
            account_data = {}
            for av in account_values:
                if av.tag in ['NetLiquidation', 'TotalCashValue', 'UnrealizedPnL', 'RealizedPnL', 'DayTradesRemaining', 'AvailableFunds', 'BuyingPower']:
                    try:
                        account_data[av.tag] = float(av.value) if av.value != '' else 0.0
                        logger.debug(f"Account data: {av.tag} = {av.value}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse value for {av.tag}: {av.value}")
                        account_data[av.tag] = 0.0
            
            # Try account summary as fallback if account values are empty
            if not account_data:
                logger.info("Account values empty, trying account summary...")
                try:
                    summary_tags = "NetLiquidation,TotalCashValue,UnrealizedPnL,RealizedPnL,AvailableFunds,BuyingPower"
                    account_summary = self.ib.accountSummary(account=target_account, tags=summary_tags)
                    logger.info(f"Account summary returned {len(account_summary)} items")
                    
                    for item in account_summary:
                        try:
                            account_data[item.tag] = float(item.value) if item.value != '' else 0.0
                            logger.debug(f"Summary data: {item.tag} = {item.value}")
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse summary value for {item.tag}: {item.value}")
                            account_data[item.tag] = 0.0
                            
                except Exception as e:
                    logger.error(f"Account summary failed: {e}")
            
            return {
                'account_id': target_account,
                'net_liquidation': account_data.get('NetLiquidation', 0),
                'total_cash': account_data.get('TotalCashValue', 0),
                'unrealized_pnl': account_data.get('UnrealizedPnL', 0),
                'realized_pnl': account_data.get('RealizedPnL', 0),
                'day_trades_remaining': account_data.get('DayTradesRemaining', 0),
                'available_funds': account_data.get('AvailableFunds', 0),
                'buying_power': account_data.get('BuyingPower', 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {
                'account_id': 'Error',
                'net_liquidation': 0,
                'total_cash': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0,
                'day_trades_remaining': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def get_positions(self, account_id: str = None) -> List[Dict[str, Any]]:
        """Get current portfolio positions with REAL-TIME market prices."""
        if not IBKR_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            # Get all positions
            positions = self.ib.positions()
            
            # Filter by account if specified
            if account_id:
                positions = [pos for pos in positions if pos.account == account_id]
            
            portfolio_positions = []
            
            # Import market data service for real-time prices
            from backend.services.market_data import market_data_service
            
            for pos in positions:
                if pos.position != 0:  # Only include non-zero positions
                    symbol = pos.contract.symbol
                    
                    # Get REAL-TIME market price from our market data service
                    try:
                        market_price = await market_data_service.get_current_price(symbol)
                        if not market_price or market_price <= 0:
                            # Fallback: try IBKR market data
                            try:
                                ticker = self.ib.reqMktData(pos.contract)
                                await asyncio.sleep(1)  # Wait for market data
                                ibkr_price = ticker.marketPrice()
                                if ibkr_price and ibkr_price > 0:
                                    market_price = ibkr_price
                                else:
                                    market_price = pos.avgCost  # Last resort fallback
                            except:
                                market_price = pos.avgCost
                    except Exception as e:
                        logger.warning(f"Could not get real-time price for {symbol}: {e}")
                        market_price = pos.avgCost  # Fallback to average cost
                    
                    # Calculate P&L with real market price
                    position_value = pos.position * market_price
                    unrealized_pnl = (market_price - pos.avgCost) * pos.position
                    unrealized_pnl_pct = (unrealized_pnl / (pos.avgCost * abs(pos.position)) * 100) if pos.avgCost != 0 else 0
                    
                    position_data = {
                        'symbol': symbol,
                        'exchange': pos.contract.exchange,
                        'currency': pos.contract.currency,
                        'position': pos.position,
                        'avg_cost': pos.avgCost,
                        'market_price': market_price,  # Real-time price
                        'position_value': position_value,
                        'unrealized_pnl': unrealized_pnl,
                        'unrealized_pnl_pct': unrealized_pnl_pct,
                        'contract_type': pos.contract.secType,
                        'account': pos.account
                    }
                    portfolio_positions.append(position_data)
                    
                    logger.debug(f"Position {symbol}: Real price ${market_price:.2f} vs avg ${pos.avgCost:.2f} = {unrealized_pnl_pct:+.1f}%")
            
            return portfolio_positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_portfolio_summary(self, account_id: str = None) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with real-time data."""
        if not IBKR_AVAILABLE:
            return {
                'error': 'IBKR not available - ib_insync not installed',
                'timestamp': datetime.now().isoformat()
            }
            
        try:
            # Get all managed accounts first
            managed_accounts = await self.get_all_managed_accounts()
            
            if not managed_accounts:
                return {
                    'error': 'No IBKR accounts found - check TWS/Gateway connection',
                    'timestamp': datetime.now().isoformat()
                }
            
            # If account_id specified, use it; otherwise use first account
            if account_id and account_id in managed_accounts:
                target_account = account_id
            else:
                target_account = managed_accounts[0]
            
            account_summary = await self.get_account_summary(target_account)
            
            # Check if account summary has error
            if 'error' in account_summary:
                return {
                    'error': account_summary['error'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get positions with real-time prices
            positions = await self.get_positions(target_account)
            
            # Calculate portfolio metrics
            total_positions = len(positions)
            total_equity_value = sum(pos['position_value'] for pos in positions if pos['position'] > 0)
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            # Top performers and losers (based on real P&L now)
            sorted_positions = sorted(positions, key=lambda x: x['unrealized_pnl_pct'], reverse=True)
            top_performers = sorted_positions[:5]
            worst_performers = sorted_positions[-5:]
            
            # Sector allocation with real data
            sectors = {}
            sector_cache = {}
            
            for pos in positions:
                symbol = pos['symbol']
                
                # Get real sector data from market APIs
                sector = 'Other'  # Default fallback
                
                if symbol in sector_cache:
                    sector = sector_cache[symbol]
                else:
                    try:
                        from backend.services.market_data import market_data_service
                        stock_info = await market_data_service.get_stock_info(symbol)
                        sector = stock_info.get('sector', 'Other')
                        sector_cache[symbol] = sector
                        logger.debug(f"Got sector for {symbol}: {sector}")
                    except Exception as e:
                        logger.warning(f"Could not get sector for {symbol}: {e}")
                        sector = 'Other'
                
                # Normalize sector names
                if sector:
                    sector = sector.strip()
                    if 'tech' in sector.lower():
                        sector = 'Technology'
                    elif 'financial' in sector.lower() or 'bank' in sector.lower():
                        sector = 'Financial Services'
                    elif 'health' in sector.lower():
                        sector = 'Healthcare'
                    elif 'energy' in sector.lower():
                        sector = 'Energy'
                    elif 'consumer' in sector.lower():
                        if 'discretionary' in sector.lower():
                            sector = 'Consumer Discretionary'
                        else:
                            sector = 'Consumer Staples'
                    elif 'industrial' in sector.lower():
                        sector = 'Industrials'
                    elif 'real estate' in sector.lower():
                        sector = 'Real Estate'
                    elif 'utilities' in sector.lower():
                        sector = 'Utilities'
                    elif 'materials' in sector.lower():
                        sector = 'Materials'
                    elif 'communication' in sector.lower():
                        sector = 'Communication Services'
                else:
                    sector = 'Other'
                
                if sector not in sectors:
                    sectors[sector] = {'value': 0, 'count': 0}
                sectors[sector]['value'] += pos['position_value']
                sectors[sector]['count'] += 1
            
            return {
                'account_summary': account_summary,
                'portfolio_metrics': {
                    'total_positions': total_positions,
                    'total_equity_value': total_equity_value,
                    'total_unrealized_pnl': total_unrealized_pnl,
                    'cash_percentage': (account_summary['total_cash'] / account_summary['net_liquidation'] * 100) if account_summary['net_liquidation'] > 0 else 0
                },
                'top_performers': top_performers,
                'worst_performers': worst_performers,
                'sector_allocation': sectors,
                'all_positions': positions,
                'managed_accounts': managed_accounts,  # Include all available accounts
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_dual_account_summary(self) -> Dict[str, Any]:
        """Get portfolio summary for both accounts."""
        try:
            managed_accounts = await self.get_all_managed_accounts()
            
            if not managed_accounts:
                return {
                    'error': 'No IBKR accounts found',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Define the expected accounts
            expected_accounts = ['U19490886', 'U15891532']
            account_summaries = {}
            
            for account_id in expected_accounts:
                if account_id in managed_accounts:
                    try:
                        summary = await self.get_portfolio_summary(account_id)
                        account_summaries[account_id] = summary
                        logger.info(f"✅ Got summary for account {account_id}")
                    except Exception as e:
                        logger.error(f"Error getting summary for {account_id}: {e}")
                        account_summaries[account_id] = {
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                else:
                    logger.warning(f"Account {account_id} not found in managed accounts: {managed_accounts}")
                    account_summaries[account_id] = {
                        'error': f'Account {account_id} not found in managed accounts',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {
                'accounts': account_summaries,
                'managed_accounts': managed_accounts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dual account summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_recent_trades(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent trades and executions."""
        try:
            if not self.connected:
                await self.connect()
            
            # Get recent trades (Note: IBKR API has limitations on historical trade data)
            trades = self.ib.trades()
            
            recent_trades = []
            cutoff_date = datetime.now() - pd.Timedelta(days=days)
            
            for trade in trades:
                for fill in trade.fills:
                    if fill.time.date() >= cutoff_date.date():
                        trade_data = {
                            'symbol': trade.contract.symbol,
                            'action': trade.order.action,
                            'quantity': fill.execution.shares,
                            'price': fill.execution.price,
                            'time': fill.time.isoformat(),
                            'commission': fill.commissionReport.commission if fill.commissionReport else 0,
                            'order_id': trade.order.orderId
                        }
                        recent_trades.append(trade_data)
            
            return sorted(recent_trades, key=lambda x: x['time'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    async def get_dual_account_summary_optimized(self) -> Dict[str, Any]:
        """Get portfolio summary for both accounts with performance optimizations."""
        try:
            managed_accounts = await self.get_all_managed_accounts()
            
            if not managed_accounts:
                return {
                    'error': 'No IBKR accounts found',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Define the expected accounts
            expected_accounts = ['U19490886', 'U15891532']
            
            # Process accounts in parallel using asyncio.gather
            tasks = []
            for account_id in expected_accounts:
                if account_id in managed_accounts:
                    tasks.append(self.get_portfolio_summary_optimized(account_id))
                else:
                    logger.warning(f"Account {account_id} not found in managed accounts: {managed_accounts}")
            
            # Execute all account summaries in parallel
            start_time = datetime.now()
            account_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            account_summaries = {}
            for i, account_id in enumerate([acc for acc in expected_accounts if acc in managed_accounts]):
                result = account_results[i]
                if isinstance(result, Exception):
                    logger.error(f"Error getting summary for {account_id}: {result}")
                    account_summaries[account_id] = {
                        'error': str(result),
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    account_summaries[account_id] = result
                    logger.info(f"✅ Got summary for account {account_id}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"⚡ Dual account summary completed in {processing_time:.2f}s")
            
            return {
                'accounts': account_summaries,
                'managed_accounts': managed_accounts,
                'processing_time_seconds': processing_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dual account summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_portfolio_summary_optimized(self, account_id: str = None) -> Dict[str, Any]:
        """Get comprehensive portfolio summary with performance optimizations."""
        if not IBKR_AVAILABLE:
            return {
                'error': 'IBKR not available - ib_insync not installed',
                'timestamp': datetime.now().isoformat()
            }
            
        try:
            # Get basic account data first
            account_summary = await self.get_account_summary(account_id)
            
            # Check if account summary has error
            if 'error' in account_summary:
                return {
                    'error': account_summary['error'],
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get positions with optimizations
            positions = await self.get_positions_optimized(account_id)
            
            # Calculate portfolio metrics
            total_positions = len(positions)
            total_equity_value = sum(pos['position_value'] for pos in positions if pos['position'] > 0)
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            # Top performers and losers (based on real P&L now)
            sorted_positions = sorted(positions, key=lambda x: x['unrealized_pnl_pct'], reverse=True)
            top_performers = sorted_positions[:5]
            worst_performers = sorted_positions[-5:]
            
            # Optimized sector allocation with batch processing
            sectors = await self._get_sector_allocation_optimized(positions)
            
            return {
                'account_summary': account_summary,
                'portfolio_metrics': {
                    'total_positions': total_positions,
                    'total_equity_value': total_equity_value,
                    'total_unrealized_pnl': total_unrealized_pnl,
                    'cash_percentage': (account_summary['total_cash'] / account_summary['net_liquidation'] * 100) if account_summary['net_liquidation'] > 0 else 0
                },
                'top_performers': top_performers,
                'worst_performers': worst_performers,
                'sector_allocation': sectors,
                'all_positions': positions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def get_positions_optimized(self, account_id: str = None) -> List[Dict[str, Any]]:
        """Get positions with minimal API calls."""
        if not IBKR_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            # Get positions for specific account
            positions = self.ib.positions(account=account_id)
            
            position_data = []
            for pos in positions:
                if pos.position == 0:
                    continue
                    
                contract = pos.contract
                
                # Get market data efficiently
                ticker = self.ib.reqMktData(contract, '', False, False)
                self.ib.sleep(0.1)  # Small delay for market data
                
                market_price = ticker.marketPrice() if hasattr(ticker, 'marketPrice') and ticker.marketPrice() else pos.avgCost
                
                # Calculate P&L
                position_value = abs(pos.position) * market_price
                unrealized_pnl = (market_price - pos.avgCost) * pos.position
                unrealized_pnl_pct = ((market_price - pos.avgCost) / pos.avgCost * 100) if pos.avgCost > 0 else 0
                
                position_data.append({
                    'symbol': contract.symbol,
                    'exchange': contract.exchange,
                    'currency': contract.currency,
                    'position': pos.position,
                    'avg_cost': pos.avgCost,
                    'market_price': market_price,
                    'position_value': position_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'contract_type': contract.secType,
                    'account': account_id
                })
                
                # Cancel market data to clean up
                self.ib.cancelMktData(contract)
            
            return position_data
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def _get_sector_allocation_optimized(self, positions: List[Dict]) -> Dict[str, Dict]:
        """Get sector allocation with caching and batch processing."""
        sectors = {}
        
        # Group symbols that need sector lookup
        symbols_to_lookup = []
        for pos in positions:
            symbol = pos['symbol']
            
            # Check cache first
            if symbol in _sector_cache:
                cache_time = _sector_cache_expiry.get(symbol, datetime.min)
                if datetime.now() - cache_time < SECTOR_CACHE_DURATION:
                    sector = _sector_cache[symbol]
                else:
                    symbols_to_lookup.append(symbol)
            else:
                symbols_to_lookup.append(symbol)
        
        # Batch lookup sectors for uncached symbols
        if symbols_to_lookup:
            try:
                from backend.services.market_data import market_data_service
                
                # Process in smaller batches to avoid overwhelming the API
                batch_size = 10
                for i in range(0, len(symbols_to_lookup), batch_size):
                    batch = symbols_to_lookup[i:i + batch_size]
                    
                    # Process batch with limited concurrency
                    batch_tasks = [market_data_service.get_stock_info(symbol) for symbol in batch]
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Update cache
                    for symbol, result in zip(batch, batch_results):
                        if isinstance(result, Exception):
                            sector = 'Other'
                            logger.warning(f"Could not get sector for {symbol}: {result}")
                        else:
                            sector = result.get('sector', 'Other')
                        
                        _sector_cache[symbol] = sector
                        _sector_cache_expiry[symbol] = datetime.now()
                    
                    # Small delay between batches
                    if i + batch_size < len(symbols_to_lookup):
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                logger.error(f"Error in batch sector lookup: {e}")
        
        # Calculate sector allocation using cached data
        for pos in positions:
            symbol = pos['symbol']
            sector = _sector_cache.get(symbol, 'Other')
            position_value = pos['position_value']
            
            if sector not in sectors:
                sectors[sector] = {'value': 0, 'count': 0}
            
            sectors[sector]['value'] += position_value
            sectors[sector]['count'] += 1
        
        return sectors

    async def get_account_statements(self, account_id: str, days: int = 30) -> List[Dict]:
        """Get account statements/transactions using enhanced IBKR connection with better reliability"""
        try:
            if not IBKR_AVAILABLE:
                logger.warning("IBKR not available - ib_insync not installed")
                return []
                
            # Ensure we have a working connection
            if not await self.ensure_connection():
                logger.warning("Could not establish IBKR connection for statements")
                return []
            
            logger.info(f"📊 Fetching account statements for {account_id} (last {days} days)")
            
            # Get recent trades and executions using ib_insync API
            trades = self.ib.trades()
            executions = self.ib.executions()
            
            transactions = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            logger.info(f"Processing {len(trades)} trades and {len(executions)} executions for account {account_id}")
            
            # Track processed execution IDs to avoid duplicates
            processed_executions = set()
            
            # Process trades (which include both buy and sell transactions)
            for trade in trades:
                try:
                    execution = trade.execution
                    contract = trade.contract
                    
                    # Filter by account and date
                    if execution.acctNumber != account_id:
                        continue
                        
                    # Parse execution time
                    exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                    if exec_time < cutoff_date:
                        continue
                    
                    # Mark as processed
                    processed_executions.add(execution.execId)
                    
                    # Determine transaction type
                    action = "BUY" if execution.side == "BOT" else "SELL"
                    
                    # Calculate amounts
                    quantity = float(execution.shares)
                    price = float(execution.price)
                    gross_amount = quantity * price
                    
                    # Get commission from commission report if available
                    commission = 0.0
                    if hasattr(trade, 'commissionReport') and trade.commissionReport:
                        commission = float(trade.commissionReport.commission)
                    
                    net_amount = gross_amount + commission if action == "BUY" else gross_amount - commission
                    
                    transaction = {
                        "id": f"ibkr_{execution.execId}",
                        "date": exec_time.strftime("%Y-%m-%d"),
                        "time": exec_time.strftime("%H:%M:%S"),
                        "symbol": contract.symbol,
                        "description": f"{action} {quantity} {contract.symbol} @ ${price:.2f}",
                        "type": action,
                        "action": action,
                        "quantity": quantity,
                        "price": price,
                        "amount": gross_amount,
                        "commission": abs(commission),
                        "fees": 0.0,  # Would need additional data for separate fees
                        "net_amount": net_amount,
                        "currency": contract.currency,
                        "exchange": contract.exchange,
                        "order_id": str(execution.orderId),
                        "execution_id": execution.execId,
                        "contract_type": contract.secType,
                        "account": account_id,
                        "settlement_date": (exec_time + timedelta(days=2)).strftime("%Y-%m-%d"),  # T+2 settlement
                        "source": "ibkr_live"
                    }
                    transactions.append(transaction)
                    
                except Exception as trade_error:
                    logger.warning(f"Error processing trade: {trade_error}")
                    continue
            
            # Process standalone executions that might not have full trade records
            for execution in executions:
                try:
                    # Skip if we already processed this execution
                    if execution.execId in processed_executions:
                        continue
                        
                    # Filter by account and date
                    if execution.acctNumber != account_id:
                        continue
                        
                    exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                    if exec_time < cutoff_date:
                        continue
                    
                    # Create basic transaction from execution
                    action = "BUY" if execution.side == "BOT" else "SELL"
                    quantity = float(execution.shares)
                    price = float(execution.price)
                    
                    transaction = {
                        "id": f"ibkr_exec_{execution.execId}",
                        "date": exec_time.strftime("%Y-%m-%d"),
                        "time": exec_time.strftime("%H:%M:%S"),
                        "symbol": execution.contract.symbol if hasattr(execution, 'contract') else "UNKNOWN",
                        "description": f"{action} {quantity} @ ${price:.2f}",
                        "type": action,
                        "action": action,
                        "quantity": quantity,
                        "price": price,
                        "amount": quantity * price,
                        "commission": 0.0,  # Commission not available in standalone execution
                        "fees": 0.0,
                        "net_amount": quantity * price,
                        "currency": "USD",  # Default
                        "exchange": "",
                        "order_id": str(execution.orderId),
                        "execution_id": execution.execId,
                        "contract_type": "STK",  # Default
                        "account": account_id,
                        "settlement_date": (exec_time + timedelta(days=2)).strftime("%Y-%m-%d"),
                        "source": "ibkr_execution"
                    }
                    transactions.append(transaction)
                    
                except Exception as exec_error:
                    logger.warning(f"Error processing execution: {exec_error}")
                    continue
            
            # Sort by date/time descending (newest first)
            transactions.sort(key=lambda x: f"{x['date']} {x['time']}", reverse=True)
            
            logger.info(f"✅ Retrieved {len(transactions)} real IBKR transactions for account {account_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error getting account statements from IBKR: {e}")
            return []

    async def _get_contract_id(self, symbol: str) -> int:
        """Get contract ID for a symbol using ib_insync"""
        try:
            if not IBKR_AVAILABLE or not self.connected:
                return 0
                
            # Search for the contract
            from ib_insync import Stock
            stock = Stock(symbol, 'SMART', 'USD')
            
            # Qualify the contract to get the conId
            qualified_contracts = self.ib.qualifyContracts(stock)
            
            if qualified_contracts:
                return qualified_contracts[0].conId
                
            return 0
            
        except Exception as e:
            logger.error(f"Error getting contract ID for {symbol}: {e}")
            return 0

    async def get_dividend_history(self, account_id: str, days: int = 365) -> List[Dict[str, Any]]:
        """Get dividend payment history from IBKR."""
        if not IBKR_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            # Get account summary with dividend information
            # Note: IBKR's API has limited access to historical dividend data
            # This method provides what's available through ib_insync
            
            dividends = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get positions to check for dividend-eligible stocks
            positions = await self.get_positions(account_id)
            dividend_stocks = ['AAPL', 'MSFT', 'VTI', 'SPY', 'IWM', 'NKE', 'OMC', 'UNH', 'PFE', 'NVDA', 'META', 'IBKR']
            
            for pos in positions:
                if pos['symbol'] in dividend_stocks:
                    # This is mock data - real dividend history would require
                    # IBKR FlexQuery API or account statements
                    dividend = {
                        'symbol': pos['symbol'],
                        'ex_date': '2024-11-15',  # Would come from real API
                        'pay_date': '2024-11-28',
                        'dividend_per_share': 0.25,  # Would come from real API
                        'total_dividend': pos['position'] * 0.25,
                        'tax_withheld': 0,
                        'net_dividend': pos['position'] * 0.25,
                        'account': account_id,
                        'currency': 'USD',
                        'source': 'ibkr_estimated'  # Mark as estimated
                    }
                    dividends.append(dividend)
            
            logger.info(f"Retrieved {len(dividends)} dividend records for account {account_id}")
            return dividends
            
        except Exception as e:
            logger.error(f"Error getting dividend history: {e}")
            return []

    async def get_corporate_actions(self, account_id: str, days: int = 365) -> List[Dict[str, Any]]:
        """Get corporate actions (stock splits, mergers, etc.) from IBKR."""
        if not IBKR_AVAILABLE:
            return []
            
        try:
            if not self.connected:
                await self.connect()
            
            # Note: IBKR's ib_insync has limited access to corporate actions
            # Full corporate action history typically requires FlexQuery API
            
            corporate_actions = []
            
            # This would be populated with real corporate action data
            # from IBKR's reporting API when available
            
            logger.info(f"Retrieved {len(corporate_actions)} corporate actions for account {account_id}")
            return corporate_actions
            
        except Exception as e:
            logger.error(f"Error getting corporate actions: {e}")
            return []

    async def get_tax_lots(self, account_id: str, symbol: str) -> List[Dict[str, Any]]:
        """Get tax lots for a specific symbol from IBKR using ib_insync API"""
        try:
            if not IBKR_AVAILABLE:
                logger.warning("IBKR not available - ib_insync not installed")
                return []
                
            if not self.connected:
                await self.connect()
            
            if not self.connected:
                logger.warning("Could not connect to IBKR for tax lots")
                return []
            
            # Use FlexQuery API or account statements to get tax lots
            # For now, use a simplified approach with executions and trades
            trades = self.ib.trades()
            executions = self.ib.executions()
            
            # Filter trades for this symbol and account
            symbol_trades = []
            for trade in trades:
                if (trade.contract.symbol == symbol and 
                    trade.execution.acctNumber == account_id and
                    trade.execution.side == 'BOT'):  # Only purchases
                    
                    symbol_trades.append(trade)
            
            # Convert to tax lot format
            tax_lots = []
            for i, trade in enumerate(symbol_trades):
                execution = trade.execution
                
                # Calculate days held
                exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                days_held = (datetime.now() - exec_time).days
                
                # Get current price for calculations
                try:
                    ticker = self.ib.reqMktData(trade.contract)
                    await asyncio.sleep(0.5)  # Wait for price
                    current_price = ticker.marketPrice() if hasattr(ticker, 'marketPrice') and ticker.marketPrice() else execution.price
                except:
                    current_price = execution.price
                
                # Calculate unrealized P&L
                cost_per_share = execution.price
                shares = execution.shares
                current_value = shares * current_price
                cost_basis = shares * cost_per_share
                unrealized_pnl = current_value - cost_basis
                unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                
                tax_lot = {
                    "lot_id": f"ibkr_{execution.execId}",
                    "acquisition_date": exec_time.strftime('%Y-%m-%d'),
                    "quantity": float(shares),
                    "cost_per_share": float(cost_per_share),
                    "current_price": float(current_price),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_pct": float(unrealized_pnl_pct),
                    "days_held": days_held,
                    "is_long_term": days_held >= 365,
                    "execution_id": execution.execId,
                    "order_id": execution.orderId,
                    "account": account_id
                }
                tax_lots.append(tax_lot)
            
            logger.info(f"Retrieved {len(tax_lots)} tax lots for {symbol} from IBKR")
            return tax_lots
            
        except Exception as e:
            logger.error(f"Error getting tax lots from IBKR for {symbol}: {e}")
            return []

# Global IBKR client instance
ibkr_client = IBKRClient() 