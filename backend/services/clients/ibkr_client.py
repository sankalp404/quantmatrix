#!/usr/bin/env python3
"""
Production-Grade IBKR Client with Enhanced Connection Management
Implements all best practices discovered from IBKR SDK research.

Key Features:
- Single connection enforcement
- Dynamic client ID management  
- Proper connection cleanup
- Retry logic with exponential backoff
- Session management
- Transaction and tax lot sync
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from decimal import Decimal

try:
    from ib_insync import IB, util, Contract, Stock, Option
    IBKR_AVAILABLE = True
except ImportError:
    try:
        # Fallback to older ib_insync if available
        from ib_insync import IB, util, Contract, Stock, Option
        IBKR_AVAILABLE = True
    except ImportError:
        IBKR_AVAILABLE = False
        IB = None

try:
    from backend.config import settings
    from backend.services.market_data import market_data_service
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

class EnhancedIBKRClient:
    """
    Production-grade IBKR client implementing best practices:
    - Single connection management
    - Client ID conflict resolution  
    - Proper session handling
    - Robust error recovery
    - Transaction and tax lot sync
    """
    
    _instance = None
    _connection_lock = asyncio.Lock() if IBKR_AVAILABLE else None
    
    def __new__(cls):
        """Singleton pattern to enforce single connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            
            if not IBKR_AVAILABLE:
                logger.error("IBKR library not available - install ib_insync or ib_async")
                self.ib = None
                return
                
            self.ib = IB()
            self.connected = False
            self.client_id = None
            self.connection_start_time = None
            self.last_heartbeat = None
            self.retry_count = 0
            self.max_retries = 5
            self.base_retry_delay = 2  # seconds
            
            # Connection tracking
            self.managed_accounts = []
            self.connection_health = {
                'status': 'disconnected',
                'last_successful_request': None,
                'consecutive_failures': 0,
                'connection_uptime': 0
            }
            
    async def connect_with_retry(self, max_attempts: int = 5) -> bool:
        """
        Connect to IBKR with advanced retry logic and conflict resolution.
        
        Args:
            max_attempts: Maximum connection attempts
            
        Returns:
            bool: True if connected successfully
        """
        if not IBKR_AVAILABLE:
            logger.error("❌ IBKR library not available")
            return False
            
        async with self._connection_lock:
            # Check if already connected
            if self.connected and self.ib.isConnected():
                logger.info("✅ Already connected to IBKR")
                return True
            
            # Clean up any existing connection
            await self._cleanup_connection()
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"🔄 IBKR connection attempt {attempt}/{max_attempts}")
                    
                    # Generate unique client ID to avoid conflicts
                    self.client_id = self._generate_client_id()
                    
                    # Attempt connection with timeout
                    await asyncio.wait_for(
                        self.ib.connectAsync(
                            host=settings.IBKR_HOST,
                            port=settings.IBKR_PORT,
                            clientId=self.client_id,
                            timeout=30
                        ),
                        timeout=30
                    )
                    
                    # Wait for connection to stabilize
                    await asyncio.sleep(2)
                    
                    # Verify connection by getting managed accounts
                    if await self._verify_connection():
                        self.connected = True
                        self.connection_start_time = datetime.now()
                        self.retry_count = 0
                        self.connection_health['status'] = 'connected'
                        
                        logger.info(f"✅ Successfully connected to IBKR with client ID {self.client_id}")
                        logger.info(f"📊 Managed accounts: {self.managed_accounts}")
                        
                        # Start health monitoring
                        asyncio.create_task(self._monitor_connection_health())
                        
                        return True
                    else:
                        logger.warning(f"⚠️ Connection established but verification failed")
                        await self._cleanup_connection()
                        
                except asyncio.TimeoutError:
                    logger.error(f"❌ Connection timeout on attempt {attempt}")
                except ConnectionRefusedError:
                    logger.error(f"❌ Connection refused - check TWS/Gateway is running")
                except Exception as e:
                    logger.error(f"❌ Connection failed on attempt {attempt}: {e}")
                
                # Exponential backoff with jitter
                if attempt < max_attempts:
                    delay = self.base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.info(f"⏳ Waiting {delay:.1f}s before retry...")
                    await asyncio.sleep(delay)
            
            logger.error(f"💥 Failed to connect after {max_attempts} attempts")
            return False
    
    def _generate_client_id(self) -> int:
        """Generate unique client ID to avoid conflicts."""
        # Use base client ID + timestamp + random to ensure uniqueness
        base_id = getattr(settings, 'IBKR_CLIENT_ID', 1)
        timestamp_component = int(time.time()) % 1000  # Last 3 digits of timestamp
        random_component = random.randint(1, 99)
        
        # Ensure we stay within IBKR's client ID range (typically 0-32767)
        client_id = (base_id * 1000 + timestamp_component + random_component) % 32767
        
        # Avoid client ID 0 as it can cause issues
        return max(1, client_id)
    
    async def _verify_connection(self) -> bool:
        """Verify connection by testing basic functionality."""
        try:
            # Test 1: Get managed accounts
            accounts = self.ib.managedAccounts()
            if accounts:
                self.managed_accounts = accounts
                logger.info(f"✅ Verification: Found {len(accounts)} managed accounts")
            else:
                logger.warning("⚠️ Verification: No managed accounts found")
                return False
            
            # Test 2: Request current time
            current_time = await self.ib.reqCurrentTimeAsync()
            if current_time:
                logger.info(f"✅ Verification: Server time received: {current_time}")
            else:
                logger.warning("⚠️ Verification: Could not get server time")
                return False
            
            # Test 3: Quick account summary check
            if accounts:
                try:
                    summary = self.ib.accountSummary(accounts[0])
                    if summary:
                        logger.info(f"✅ Verification: Account summary available")
                    else:
                        logger.warning("⚠️ Verification: Account summary empty")
                except Exception as e:
                    logger.warning(f"⚠️ Verification: Account summary failed: {e}")
            
            self.last_heartbeat = datetime.now()
            self.connection_health['last_successful_request'] = self.last_heartbeat
            self.connection_health['consecutive_failures'] = 0
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection verification failed: {e}")
            return False
    
    async def _cleanup_connection(self):
        """Properly cleanup existing connection."""
        try:
            if self.ib and self.ib.isConnected():
                logger.info("🧹 Cleaning up existing IBKR connection...")
                self.ib.disconnect()
                await asyncio.sleep(1)  # Allow cleanup to complete
                
            self.connected = False
            self.client_id = None
            self.managed_accounts = []
            self.connection_health['status'] = 'disconnected'
            
        except Exception as e:
            logger.error(f"❌ Error during connection cleanup: {e}")
    
    async def _monitor_connection_health(self):
        """Monitor connection health and attempt reconnection if needed."""
        while self.connected:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.ib.isConnected():
                    logger.warning("⚠️ Connection lost - attempting reconnection...")
                    self.connected = False
                    await self.connect_with_retry()
                    continue
                
                # Update connection uptime
                if self.connection_start_time:
                    uptime = (datetime.now() - self.connection_start_time).total_seconds()
                    self.connection_health['connection_uptime'] = uptime
                
                # Heartbeat test
                try:
                    current_time = await self.ib.reqCurrentTimeAsync()
                    if current_time:
                        self.last_heartbeat = datetime.now()
                        self.connection_health['last_successful_request'] = self.last_heartbeat
                        self.connection_health['consecutive_failures'] = 0
                        logger.debug(f"💓 Heartbeat successful: {current_time}")
                    else:
                        raise Exception("No response to heartbeat")
                        
                except Exception as e:
                    self.connection_health['consecutive_failures'] += 1
                    logger.warning(f"💔 Heartbeat failed: {e}")
                    
                    # If too many consecutive failures, reconnect
                    if self.connection_health['consecutive_failures'] >= 3:
                        logger.error("💥 Too many heartbeat failures - reconnecting...")
                        self.connected = False
                        await self.connect_with_retry()
                
            except Exception as e:
                logger.error(f"❌ Error in connection health monitor: {e}")
                await asyncio.sleep(5)
    
    async def get_enhanced_account_statements(self, account_id: str, days: int = 30) -> List[Dict]:
        """
        Get comprehensive account statements with enhanced error handling.
        
        Uses multiple methods to fetch complete historical data including chunked requests.
        """
        if not await self._ensure_connected():
            return []
            
        try:
            logger.info(f"📊 Fetching enhanced statements for account {account_id} ({days} days)")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            transactions = []
            
            # ENHANCED APPROACH: Use multiple methods to get complete historical data
            
            # Method 1: Get recent trades from current session (limited historical range)
            try:
                trades = self.ib.trades()
                logger.info(f"🔄 Found {len(trades)} trades in current session")
                
                for trade in trades:
                    for fill in trade.fills:
                        execution = fill.execution
                        contract = fill.contract
                        
                        if execution.acctNumber != account_id:
                            continue
                            
                        exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                        if exec_time < start_date:
                            continue
                        
                        transaction = {
                            'id': execution.execId,
                            'order_id': execution.orderId,
                            'account': execution.acctNumber,
                            'symbol': contract.symbol,
                            'description': f"{contract.symbol} {contract.secType}",
                            'type': 'TRADE',
                            'action': 'BUY' if execution.side == 'BOT' else 'SELL',
                            'quantity': float(execution.shares),
                            'price': float(execution.price),
                            'amount': float(execution.shares) * float(execution.price),
                            'commission': float(fill.commissionReport.commission) if fill.commissionReport else 0.0,
                            'currency': contract.currency or 'USD',
                            'exchange': execution.exchange,
                            'date': exec_time.strftime('%Y-%m-%d'),
                            'time': exec_time.strftime('%H:%M:%S'),
                            'settlement_date': (exec_time + timedelta(days=2)).strftime('%Y-%m-%d'),
                            'source': 'ibkr_enhanced_trades',
                            'contract_type': contract.secType,
                            'execution_id': execution.execId,
                            'net_amount': float(execution.shares) * float(execution.price) + (float(fill.commissionReport.commission) if fill.commissionReport else 0.0)
                        }
                        
                        transactions.append(transaction)
                        
            except Exception as e:
                logger.error(f"❌ Error getting trades: {e}")
            
            # Method 2: Standalone executions (limited info, no contract details)
            try:
                executions = self.ib.executions()
                logger.info(f"📈 Found {len(executions)} standalone executions")
                
                # Create a set of execution IDs we already processed from trades
                processed_exec_ids = {t['execution_id'] for t in transactions}
                
                for execution in executions:
                    if execution.acctNumber == account_id and execution.execId not in processed_exec_ids:
                        exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                        if exec_time >= start_date:
                            
                            transaction = {
                                'id': execution.execId,
                                'order_id': execution.orderId,
                                'account': execution.acctNumber,
                                'symbol': 'UNKNOWN',  # No contract info available
                                'description': f"Execution {execution.execId}",
                                'type': 'TRADE',
                                'action': 'BUY' if execution.side == 'BOT' else 'SELL',
                                'quantity': float(execution.shares),
                                'price': float(execution.price),
                                'amount': float(execution.shares) * float(execution.price),
                                'commission': 0.0,  # No commission info available
                                'currency': 'USD',  # Default
                                'exchange': execution.exchange,
                                'date': exec_time.strftime('%Y-%m-%d'),
                                'time': exec_time.strftime('%H:%M:%S'),
                                'settlement_date': (exec_time + timedelta(days=2)).strftime('%Y-%m-%d'),
                                'source': 'ibkr_enhanced_standalone',
                                'contract_type': 'STK',  # Default
                                'execution_id': execution.execId,
                                'net_amount': float(execution.shares) * float(execution.price)
                            }
                            
                            transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"❌ Error getting standalone executions: {e}")
            
            # Method 3: CHUNKED HISTORICAL DATA RETRIEVAL (for data older than TWS session)
            if days > 90:  # Only use chunked approach for longer periods
                logger.info(f"🔄 Using chunked retrieval for {days} days (longer than 90 days)")
                try:
                    historical_transactions = await self._get_chunked_historical_executions(account_id, start_date, end_date)
                    
                    # Deduplicate against existing transactions
                    existing_exec_ids = {t['execution_id'] for t in transactions}
                    new_historical = [t for t in historical_transactions if t['execution_id'] not in existing_exec_ids]
                    
                    if new_historical:
                        transactions.extend(new_historical)
                        logger.info(f"📊 Added {len(new_historical)} historical transactions from chunked retrieval")
                    else:
                        logger.info("📊 No new historical transactions found in chunked retrieval")
                        
                except Exception as e:
                    logger.error(f"❌ Error in chunked historical retrieval: {e}")
            
            # Sort by date/time descending
            transactions.sort(key=lambda x: f"{x['date']} {x['time']}", reverse=True)
            
            logger.info(f"✅ Enhanced statements: {len(transactions)} transactions for {account_id} (range: {start_date.date()} to {end_date.date()})")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced account statements: {e}")
            return []
    
    async def _get_chunked_historical_executions(self, account_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get historical executions using chunked date ranges to work around IBKR limitations.
        
        IBKR's execution history is limited, so we break down large requests into smaller chunks.
        This helps retrieve data from much further back (e.g., May 2024).
        """
        if not await self._ensure_connected():
            return []
        
        try:
            logger.info(f"📅 Chunked historical retrieval: {start_date.date()} to {end_date.date()}")
            
            all_historical_transactions = []
            chunk_size_days = 30  # Process 30 days at a time
            
            current_end = end_date
            total_chunks = 0
            
            while current_end > start_date:
                current_start = max(start_date, current_end - timedelta(days=chunk_size_days))
                total_chunks += 1
                
                logger.info(f"📊 Processing chunk {total_chunks}: {current_start.date()} to {current_end.date()}")
                
                try:
                    # Use IBKR's reqExecutions with date filter
                    from ib_insync import ExecutionFilter
                    
                    # Create execution filter for this time range
                    exec_filter = ExecutionFilter()
                    exec_filter.acctCode = account_id
                    # Note: IBKR's ExecutionFilter doesn't support date ranges directly
                    # So we'll get all executions and filter by date locally
                    
                    # Request executions (this gets ALL executions for the account)
                    # Fix asyncio event loop issue
                    try:
                        executions = await self.ib.reqExecutionsAsync(exec_filter)
                    except AttributeError:
                        # Fallback to synchronous method if async version doesn't exist
                        executions = self.ib.reqExecutions(exec_filter)
                    
                    if executions:
                        logger.info(f"🔍 Got {len(executions)} total executions from IBKR")
                        
                        # Filter by our date range locally
                        chunk_transactions = []
                        for execution_detail in executions:
                            execution = execution_detail.execution
                            contract = execution_detail.contract
                            
                            # Parse execution time and filter by date range
                            exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                            
                            if current_start <= exec_time <= current_end:
                                transaction = {
                                    'id': execution.execId,
                                    'order_id': execution.orderId,
                                    'account': execution.acctNumber,
                                    'symbol': contract.symbol,
                                    'description': f"{contract.symbol} {contract.secType} - Historical",
                                    'type': 'TRADE',
                                    'action': 'BUY' if execution.side == 'BOT' else 'SELL',
                                    'quantity': float(execution.shares),
                                    'price': float(execution.price),
                                    'amount': float(execution.shares) * float(execution.price),
                                    'commission': 0.0,  # Commission info may not be available in historical data
                                    'currency': contract.currency or 'USD',
                                    'exchange': execution.exchange,
                                    'date': exec_time.strftime('%Y-%m-%d'),
                                    'time': exec_time.strftime('%H:%M:%S'),
                                    'settlement_date': (exec_time + timedelta(days=2)).strftime('%Y-%m-%d'),
                                    'source': 'ibkr_chunked_historical',
                                    'contract_type': contract.secType,
                                    'execution_id': execution.execId,
                                    'net_amount': float(execution.shares) * float(execution.price)
                                }
                                
                                chunk_transactions.append(transaction)
                        
                        if chunk_transactions:
                            all_historical_transactions.extend(chunk_transactions)
                            logger.info(f"✅ Chunk {total_chunks}: Found {len(chunk_transactions)} transactions")
                        else:
                            logger.info(f"📊 Chunk {total_chunks}: No transactions in date range")
                    
                    else:
                        logger.info(f"📊 Chunk {total_chunks}: No executions returned from IBKR")
                    
                    # Small delay between chunks to avoid overwhelming IBKR API
                    await asyncio.sleep(0.5)
                    
                except Exception as chunk_error:
                    logger.error(f"❌ Error in chunk {total_chunks} ({current_start.date()} to {current_end.date()}): {chunk_error}")
                
                # Move to previous chunk
                current_end = current_start - timedelta(days=1)
                
                # Safety limit to prevent infinite loops
                if total_chunks > 50:  # Max ~4 years of data
                    logger.warning(f"⚠️ Reached safety limit of {total_chunks} chunks")
                    break
            
            logger.info(f"🎯 Chunked retrieval complete: {len(all_historical_transactions)} historical transactions from {total_chunks} chunks")
            return all_historical_transactions
            
        except Exception as e:
            logger.error(f"❌ Error in chunked historical executions: {e}")
            return []
    
    async def get_enhanced_tax_lots(self, account_id: str) -> List[Dict]:
        """
        Get enhanced tax lots using multiple methods for maximum coverage.
        FIXED: Better fallback when trades don't exist + proper market price handling
        """
        if not await self._ensure_connected():
            return []
            
        try:
            logger.info(f"📊 Fetching enhanced tax lots for account {account_id}")
            
            tax_lots = []
            
            # Get current positions to derive tax lots from
            positions = self.ib.positions(account_id)
            logger.info(f"📈 Found {len(positions)} positions for tax lot calculation")
            
            for position in positions:
                if position.position > 0:  # Only long positions have traditional tax lots
                    
                    # Try to get detailed executions for this symbol
                    try:
                        # ENHANCED APPROACH: Try multiple methods to get historical trade data
                        
                        # Method 1: Get all executions for this account and filter by symbol
                        all_executions = self.ib.executions(account_id)
                        symbol_executions = [
                            exec for exec in all_executions 
                            if (exec.contract.symbol == position.contract.symbol and 
                                exec.execution.side == 'BOT')  # Only buy orders create tax lots
                        ]
                        
                        logger.info(f"Found {len(symbol_executions)} historical executions for {position.contract.symbol}")
                        
                        # Method 2: Also try trades() as a backup
                        trades = self.ib.trades()
                        symbol_trades = []
                        
                        for trade in trades:
                            # Check if this trade is for our symbol and account
                            if (trade.contract.symbol == position.contract.symbol and
                                any(fill.execution.acctNumber == account_id and fill.execution.side == 'BOT' 
                                    for fill in trade.fills)):
                                symbol_trades.append(trade)
                        
                        logger.info(f"Found {len(symbol_trades)} historical trades for {position.contract.symbol}")
                        
                        # Combine both approaches - prefer executions if available
                        historical_data_found = len(symbol_executions) > 0 or len(symbol_trades) > 0
                        
                        if historical_data_found:
                            # PRIORITY 1: Use direct executions data (more reliable)
                            if symbol_executions:
                                logger.info(f"Processing {len(symbol_executions)} executions for {position.contract.symbol}")
                                
                                # Sort executions by time
                                symbol_executions.sort(key=lambda exec: exec.execution.time)
                                
                                for exec_data in symbol_executions:
                                    execution = exec_data.execution
                                    contract = exec_data.contract
                                    
                                    # Ensure this is the right account and side
                                    if execution.acctNumber != account_id or execution.side != 'BOT':
                                        continue
                                    
                                    exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                                    days_held = (datetime.now() - exec_time).days
                                    
                                    # Get current market price
                                    try:
                                        current_price = await market_data_service.get_current_price(position.contract.symbol)
                                        if not current_price or current_price <= 0:
                                            current_price = position.avgCost
                                    except Exception as e:
                                        logger.warning(f"Market data service unavailable for {position.contract.symbol}: {e}")
                                        current_price = position.avgCost
                                    
                                    cost_per_share = execution.price
                                    shares = execution.shares
                                    current_value = shares * current_price
                                    cost_basis = shares * cost_per_share
                                    unrealized_pnl = current_value - cost_basis
                                    unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                                    
                                    tax_lot = {
                                        'lot_id': f"enhanced_ibkr_{execution.execId}",
                                        'account_id': account_id,
                                        'symbol': position.contract.symbol,
                                        'acquisition_date': exec_time.strftime('%Y-%m-%d'),
                                        'quantity': float(shares),
                                        'cost_per_share': float(cost_per_share),
                                        'current_price': float(current_price),
                                        'cost_basis': float(cost_basis),
                                        'current_value': float(current_value),
                                        'unrealized_pnl': float(unrealized_pnl),
                                        'unrealized_pnl_pct': float(unrealized_pnl_pct),
                                        'days_held': days_held,
                                        'is_long_term': days_held >= 365,
                                        'contract_type': position.contract.secType,
                                        'currency': position.contract.currency or 'USD',
                                        'execution_id': execution.execId,
                                        'source': 'ibkr_real_execution'
                                    }
                                    
                                    tax_lots.append(tax_lot)
                                    
                            # PRIORITY 2: Fall back to trades data if no executions
                            elif symbol_trades:
                                logger.info(f"Falling back to trades data for {position.contract.symbol}")
                                
                                # Sort by first fill execution time
                                symbol_trades.sort(key=lambda trade: min(fill.execution.time for fill in trade.fills))
                                
                                # Create tax lots from trade fills
                                for trade in symbol_trades:
                                    for fill in trade.fills:
                                        execution = fill.execution
                                        contract = fill.contract
                                        
                                        # Only process buys for this account
                                        if execution.acctNumber != account_id or execution.side != 'BOT':
                                            continue
                                            
                                        exec_time = pd.to_datetime(execution.time).replace(tzinfo=None)
                                        days_held = (datetime.now() - exec_time).days
                                        
                                        # Get current market price
                                        try:
                                            current_price = await market_data_service.get_current_price(position.contract.symbol)
                                            if not current_price or current_price <= 0:
                                                current_price = position.avgCost
                                        except Exception as e:
                                            logger.warning(f"Market data service unavailable for {position.contract.symbol}: {e}")
                                            current_price = position.avgCost
                                        
                                        cost_per_share = execution.price
                                        shares = execution.shares
                                        current_value = shares * current_price
                                        cost_basis = shares * cost_per_share
                                        unrealized_pnl = current_value - cost_basis
                                        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                                        
                                        tax_lot = {
                                            'lot_id': f"enhanced_ibkr_{execution.execId}",
                                            'account_id': account_id,
                                            'symbol': position.contract.symbol,
                                            'acquisition_date': exec_time.strftime('%Y-%m-%d'),
                                            'quantity': float(shares),
                                            'cost_per_share': float(cost_per_share),
                                            'current_price': float(current_price),
                                            'cost_basis': float(cost_basis),
                                            'current_value': float(current_value),
                                            'unrealized_pnl': float(unrealized_pnl),
                                            'unrealized_pnl_pct': float(unrealized_pnl_pct),
                                            'days_held': days_held,
                                            'is_long_term': days_held >= 365,
                                            'contract_type': position.contract.secType,
                                            'currency': position.contract.currency or 'USD',
                                            'execution_id': execution.execId,
                                            'source': 'ibkr_real_trade'
                                        }
                                        
                                        tax_lots.append(tax_lot)
                        else:
                            # LAST RESORT: No historical data found, create estimated tax lot
                            logger.error(f"❌ NO REAL TAX LOT DATA FOUND for {position.contract.symbol} - using ESTIMATED tax lot (this should be avoided!)")
                            logger.error(f"   - Executions found: {len(symbol_executions) if 'symbol_executions' in locals() else 0}")
                            logger.error(f"   - Trades found: {len(symbol_trades) if 'symbol_trades' in locals() else 0}")
                            logger.error(f"   - This indicates missing historical trade data from IBKR")
                            
                            # Get current market price safely
                            try:
                                current_price = await market_data_service.get_current_price(position.contract.symbol)
                                if not current_price or current_price <= 0:
                                    current_price = position.avgCost
                            except Exception as e:
                                logger.warning(f"Market data failed for {position.contract.symbol}: {e}")
                                current_price = position.avgCost
                            
                            # Create estimated tax lot from position data
                            cost_basis = float(position.position * position.avgCost)
                            current_value = float(position.position * current_price)
                            unrealized_pnl = current_value - cost_basis
                            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                            
                            tax_lot = {
                                'lot_id': f"⚠️_ESTIMATED_{position.contract.symbol}_{account_id}",
                                'account_id': account_id,
                                'symbol': position.contract.symbol,
                                'acquisition_date': '2024-05-09',  # Default to your start date
                                'quantity': float(position.position),
                                'cost_per_share': float(position.avgCost),
                                'current_price': float(current_price),
                                'cost_basis': cost_basis,
                                'current_value': current_value,
                                'unrealized_pnl': unrealized_pnl,
                                'unrealized_pnl_pct': unrealized_pnl_pct,
                                'days_held': (datetime.now() - datetime.strptime('2024-05-09', '%Y-%m-%d')).days,
                                'is_long_term': True,  # Assume long-term for estimated
                                'contract_type': position.contract.secType,
                                'currency': position.contract.currency or 'USD',
                                'execution_id': None,
                                'source': '⚠️_ESTIMATED_TAX_LOT_⚠️'
                            }
                            
                            tax_lots.append(tax_lot)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing tax lots for {position.contract.symbol}: {e}")
                        
                        # LAST RESORT FALLBACK: Create basic estimated tax lot
                        try:
                            tax_lot = {
                                'lot_id': f"basic_{position.contract.symbol}_{account_id}",
                                'account_id': account_id,
                                'symbol': position.contract.symbol,
                                'acquisition_date': '2024-05-09',
                                'quantity': float(position.position),
                                'cost_per_share': float(position.avgCost),
                                'current_price': float(position.avgCost),  # Fallback to avg cost
                                'cost_basis': float(position.position * position.avgCost),
                                'current_value': float(position.position * position.avgCost),
                                'unrealized_pnl': 0.0,  # Can't calculate without current price
                                'unrealized_pnl_pct': 0.0,
                                'days_held': 0,
                                'is_long_term': False,
                                'contract_type': position.contract.secType,
                                'currency': position.contract.currency or 'USD',
                                'execution_id': None,
                                'source': 'ibkr_basic_fallback'
                            }
                            
                            tax_lots.append(tax_lot)
                            logger.info(f"Created basic fallback tax lot for {position.contract.symbol}")
                            
                        except Exception as fallback_error:
                            logger.error(f"❌ Even fallback failed for {position.contract.symbol}: {fallback_error}")
            
            logger.info(f"✅ Enhanced tax lots: {len(tax_lots)} lots for {account_id}")
            return tax_lots
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced tax lots: {e}")
            return []
    
    async def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection."""
        if not self.connected or not self.ib.isConnected():
            logger.warning("🔄 Not connected - attempting to reconnect...")
            return await self.connect_with_retry()
        return True
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status information."""
        status = {
            'connected': self.connected,
            'client_id': self.client_id,
            'managed_accounts': self.managed_accounts,
            'health': self.connection_health.copy()
        }
        
        if self.connection_start_time:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()
            status['uptime_seconds'] = uptime
            status['uptime_formatted'] = str(timedelta(seconds=int(uptime)))
        
        return status
    
    async def disconnect(self):
        """Properly disconnect from IBKR."""
        try:
            if self.ib and self.ib.isConnected():
                logger.info("🔌 Disconnecting from IBKR...")
                self.ib.disconnect()
                
            self.connected = False
            self.client_id = None
            self.managed_accounts = []
            self.connection_health['status'] = 'disconnected'
            
            logger.info("✅ Disconnected from IBKR")
            
        except Exception as e:
            logger.error(f"❌ Error during disconnect: {e}")

# Global enhanced client instance
enhanced_ibkr_client = EnhancedIBKRClient() 