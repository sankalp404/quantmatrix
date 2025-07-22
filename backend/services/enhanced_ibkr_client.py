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
        
        This is the key method for syncing transactions and tax lots.
        """
        if not await self._ensure_connected():
            return []
            
        try:
            logger.info(f"📊 Fetching enhanced statements for account {account_id} ({days} days)")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            transactions = []
            
            # Method 1: Try to get executions (trades)
            try:
                executions = self.ib.executions()
                logger.info(f"📈 Found {len(executions)} total executions")
                
                for execution in executions:
                    if execution.execution.acctNumber == account_id:
                        # Parse execution time
                        exec_time = pd.to_datetime(execution.execution.time).replace(tzinfo=None)
                        if exec_time >= start_date:
                            
                            transaction = {
                                'id': execution.execution.execId,
                                'order_id': execution.execution.orderId,
                                'account': execution.execution.acctNumber,
                                'symbol': execution.contract.symbol,
                                'description': f"{execution.contract.symbol} {execution.contract.secType}",
                                'type': 'TRADE',
                                'action': 'BUY' if execution.execution.side == 'BOT' else 'SELL',
                                'quantity': float(execution.execution.shares),
                                'price': float(execution.execution.price),
                                'amount': float(execution.execution.shares) * float(execution.execution.price),
                                'commission': 0.0,  # Will be updated from commission report
                                'currency': execution.contract.currency or 'USD',
                                'exchange': execution.execution.exchange,
                                'date': exec_time.strftime('%Y-%m-%d'),
                                'time': exec_time.strftime('%H:%M:%S'),
                                'settlement_date': (exec_time + timedelta(days=2)).strftime('%Y-%m-%d'),
                                'source': 'ibkr_enhanced',
                                'contract_type': execution.contract.secType,
                                'execution_id': execution.execution.execId
                            }
                            
                            # Get commission if available
                            if hasattr(execution, 'commissionReport') and execution.commissionReport:
                                transaction['commission'] = float(execution.commissionReport.commission)
                                transaction['amount'] = transaction['amount'] + transaction['commission']
                            
                            transactions.append(transaction)
                            
            except Exception as e:
                logger.error(f"❌ Error getting executions: {e}")
            
            # Method 2: Get trades (alternative approach)
            try:
                trades = self.ib.trades()
                logger.info(f"🔄 Found {len(trades)} total trades")
                
                for trade in trades:
                    if (hasattr(trade, 'execution') and 
                        trade.execution and 
                        trade.execution.acctNumber == account_id):
                        
                        exec_time = pd.to_datetime(trade.execution.time).replace(tzinfo=None)
                        if exec_time >= start_date:
                            
                            # Check if we already have this execution
                            existing = next((t for t in transactions if t.get('execution_id') == trade.execution.execId), None)
                            if not existing:
                                transaction = {
                                    'id': trade.execution.execId,
                                    'order_id': trade.execution.orderId,
                                    'account': trade.execution.acctNumber,
                                    'symbol': trade.contract.symbol,
                                    'description': f"{trade.contract.symbol} {trade.contract.secType}",
                                    'type': 'TRADE',
                                    'action': 'BUY' if trade.execution.side == 'BOT' else 'SELL',
                                    'quantity': float(trade.execution.shares),
                                    'price': float(trade.execution.price),
                                    'amount': float(trade.execution.shares) * float(trade.execution.price),
                                    'commission': 0.0,
                                    'currency': trade.contract.currency or 'USD',
                                    'exchange': trade.execution.exchange,
                                    'date': exec_time.strftime('%Y-%m-%d'),
                                    'time': exec_time.strftime('%H:%M:%S'),
                                    'settlement_date': (exec_time + timedelta(days=2)).strftime('%Y-%m-%d'),
                                    'source': 'ibkr_enhanced_trades',
                                    'contract_type': trade.contract.secType,
                                    'execution_id': trade.execution.execId
                                }
                                
                                if hasattr(trade, 'commissionReport') and trade.commissionReport:
                                    transaction['commission'] = float(trade.commissionReport.commission)
                                    
                                transactions.append(transaction)
                
            except Exception as e:
                logger.error(f"❌ Error getting trades: {e}")
            
            logger.info(f"✅ Enhanced statements: {len(transactions)} transactions for {account_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced account statements: {e}")
            return []
    
    async def get_enhanced_tax_lots(self, account_id: str) -> List[Dict]:
        """
        Get enhanced tax lots using multiple methods for maximum coverage.
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
                        # Get executions for this contract
                        executions = self.ib.executions()
                        symbol_executions = [
                            exec for exec in executions 
                            if (exec.contract.symbol == position.contract.symbol and
                                exec.execution.acctNumber == account_id and
                                exec.execution.side == 'BOT')  # Only buys
                        ]
                        
                        # Sort by execution time
                        symbol_executions.sort(key=lambda x: x.execution.time)
                        
                        # Create tax lots from executions
                        for i, execution in enumerate(symbol_executions):
                            exec_time = pd.to_datetime(execution.execution.time).replace(tzinfo=None)
                            
                            # Calculate days held
                            days_held = (datetime.now() - exec_time).days
                            
                            # Get current market price
                            current_price = position.marketPrice if position.marketPrice else execution.execution.price
                            
                            cost_per_share = execution.execution.price
                            shares = execution.execution.shares
                            current_value = shares * current_price
                            cost_basis = shares * cost_per_share
                            unrealized_pnl = current_value - cost_basis
                            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                            
                            tax_lot = {
                                'lot_id': f"enhanced_ibkr_{execution.execution.execId}",
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
                                'execution_id': execution.execution.execId,
                                'source': 'ibkr_enhanced'
                            }
                            
                            tax_lots.append(tax_lot)
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing tax lots for {position.contract.symbol}: {e}")
                        
                        # Fallback: Create estimated tax lot from position
                        tax_lot = {
                            'lot_id': f"estimated_{position.contract.symbol}_{account_id}",
                            'account_id': account_id,
                            'symbol': position.contract.symbol,
                            'acquisition_date': '2024-05-09',  # Default to your start date
                            'quantity': float(position.position),
                            'cost_per_share': float(position.avgCost),
                            'current_price': float(position.marketPrice) if position.marketPrice else float(position.avgCost),
                            'cost_basis': float(position.position * position.avgCost),
                            'current_value': float(position.marketValue) if position.marketValue else float(position.position * position.avgCost),
                            'unrealized_pnl': float(position.unrealizedPNL) if position.unrealizedPNL else 0.0,
                            'unrealized_pnl_pct': 0.0,
                            'days_held': 0,
                            'is_long_term': False,
                            'contract_type': position.contract.secType,
                            'currency': position.contract.currency or 'USD',
                            'execution_id': None,
                            'source': 'ibkr_estimated'
                        }
                        
                        tax_lots.append(tax_lot)
            
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