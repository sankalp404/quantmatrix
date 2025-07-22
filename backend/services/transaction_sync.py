"""
Transaction Sync Service
Syncs transaction data from IBKR and persists it locally for fast access
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from backend.models import SessionLocal
from backend.models.portfolio import Account
from backend.models.transactions import Transaction, Dividend, TransactionSyncStatus
from backend.services.ibkr_client import ibkr_client
from backend.services.tastytrade_client import tastytrade_client

logger = logging.getLogger(__name__)

class TransactionSyncService:
    """Service for syncing and persisting transaction data from IBKR."""
    
    def __init__(self):
        self.sync_in_progress = {}  # Track ongoing syncs per account
        
    async def sync_all_accounts(self, days: int = 365) -> Dict[str, Any]:
        """Sync transaction data for all active accounts."""
        db = SessionLocal()
        results = {}
        
        try:
            # Get all active accounts
            accounts = db.query(Account).filter(Account.is_active == True).all()
            
            for account in accounts:
                if account.broker == 'IBKR':
                    try:
                        result = await self.sync_account_transactions(account.account_number, days)
                        results[account.account_number] = result
                    except Exception as e:
                        logger.error(f"Error syncing account {account.account_number}: {e}")
                        results[account.account_number] = {'error': str(e)}
                        
            return {
                'status': 'completed',
                'accounts_synced': len([r for r in results.values() if 'error' not in r]),
                'accounts_failed': len([r for r in results.values() if 'error' in r]),
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in sync_all_accounts: {e}")
            return {'status': 'error', 'error': str(e)}
        finally:
            db.close()
    
    async def sync_account_transactions(self, account_number: str, days: int = 365) -> Dict[str, Any]:
        """Sync transactions for a specific account."""
        if account_number in self.sync_in_progress:
            return {'status': 'already_in_progress'}
            
        self.sync_in_progress[account_number] = True
        db = SessionLocal()
        
        try:
            # Get account record
            account = db.query(Account).filter(Account.account_number == account_number).first()
            if not account:
                return {'status': 'error', 'error': 'Account not found'}
            
            # Get or create sync status
            sync_status = db.query(TransactionSyncStatus).filter(
                TransactionSyncStatus.account_id == account.id
            ).first()
            
            if not sync_status:
                sync_status = TransactionSyncStatus(
                    account_id=account.id,
                    sync_status='pending'
                )
                db.add(sync_status)
                db.flush()
            
            # Update sync status
            sync_status.sync_status = 'in_progress'
            sync_status.last_sync_date = datetime.utcnow()
            db.commit()
            
            # Fetch transaction data from IBKR
            logger.info(f"Fetching transactions for account {account_number} from IBKR...")
            ibkr_transactions = await ibkr_client.get_account_statements(account_number, days)
            ibkr_dividends = await ibkr_client.get_dividend_history(account_number, days)
            
            # Sync transactions
            transactions_synced = await self._sync_transactions(db, account, ibkr_transactions)
            
            # Sync dividends
            dividends_synced = await self._sync_dividends(db, account, ibkr_dividends)
            
            # Update sync status
            sync_status.sync_status = 'completed'
            sync_status.last_successful_sync = datetime.utcnow()
            sync_status.total_transactions = transactions_synced
            sync_status.total_dividends = dividends_synced
            sync_status.error_count = 0
            sync_status.last_error = None
            
            if ibkr_transactions:
                sync_status.earliest_transaction_date = min(
                    datetime.strptime(t['date'], '%Y-%m-%d') for t in ibkr_transactions
                )
                sync_status.latest_transaction_date = max(
                    datetime.strptime(t['date'], '%Y-%m-%d') for t in ibkr_transactions
                )
            
            db.commit()
            
            logger.info(f"✅ Synced {transactions_synced} transactions and {dividends_synced} dividends for account {account_number}")
            
            return {
                'status': 'success',
                'transactions_synced': transactions_synced,
                'dividends_synced': dividends_synced,
                'account_id': account_number,
                'sync_duration_seconds': (datetime.utcnow() - sync_status.last_sync_date).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error syncing transactions for account {account_number}: {e}")
            
            # Update sync status with error
            if 'sync_status' in locals():
                sync_status.sync_status = 'failed'
                sync_status.last_error = str(e)
                sync_status.error_count += 1
                db.commit()
            
            return {'status': 'error', 'error': str(e)}
        finally:
            self.sync_in_progress.pop(account_number, None)
            db.close()
    
    async def sync_tastytrade_transactions(self, account_number: str, days: int = 365) -> Dict[str, Any]:
        """Sync TastyTrade transactions for a specific account."""
        if account_number in self.sync_in_progress:
            return {'status': 'already_in_progress'}
            
        self.sync_in_progress[account_number] = True
        db = SessionLocal()
        
        try:
            # Get account record (create if doesn't exist)
            account = db.query(Account).filter(Account.account_number == account_number).first()
            if not account:
                # Create TastyTrade account
                account = Account(
                    account_number=account_number,
                    account_name=f"TastyTrade {account_number}",
                    account_type='taxable',
                    broker='TASTYTRADE',
                    is_active=True,
                    currency='USD'
                )
                db.add(account)
                db.flush()
            
            # Get or create sync status
            sync_status = db.query(TransactionSyncStatus).filter(
                TransactionSyncStatus.account_id == account.id
            ).first()
            
            if not sync_status:
                sync_status = TransactionSyncStatus(
                    account_id=account.id,
                    sync_status='pending'
                )
                db.add(sync_status)
                db.flush()
            
            # Update sync status
            sync_status.sync_status = 'in_progress'
            sync_status.last_sync_date = datetime.utcnow()
            db.commit()
            
            # Fetch transaction data from TastyTrade
            logger.info(f"Fetching TastyTrade transactions for account {account_number}...")
            tt_transactions = await tastytrade_client.get_transaction_history(account_number, days)
            tt_dividends = await tastytrade_client.get_dividend_history(account_number, days)
            
            # Sync transactions
            transactions_synced = await self._sync_tastytrade_transactions(db, account, tt_transactions)
            
            # Sync dividends
            dividends_synced = await self._sync_tastytrade_dividends(db, account, tt_dividends)
            
            # Update sync status
            sync_status.sync_status = 'completed'
            sync_status.last_successful_sync = datetime.utcnow()
            sync_status.total_transactions = transactions_synced
            sync_status.total_dividends = dividends_synced
            sync_status.error_count = 0
            sync_status.last_error = None
            
            if tt_transactions:
                sync_status.earliest_transaction_date = min(
                    datetime.strptime(t['date'], '%Y-%m-%d') for t in tt_transactions
                )
                sync_status.latest_transaction_date = max(
                    datetime.strptime(t['date'], '%Y-%m-%d') for t in tt_transactions
                )
            
            db.commit()
            
            logger.info(f"✅ Synced {transactions_synced} TastyTrade transactions and {dividends_synced} dividends for account {account_number}")
            
            return {
                'status': 'success',
                'transactions_synced': transactions_synced,
                'dividends_synced': dividends_synced,
                'account_id': account_number,
                'brokerage': 'tastytrade',
                'sync_duration_seconds': (datetime.utcnow() - sync_status.last_sync_date).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error syncing TastyTrade transactions for account {account_number}: {e}")
            
            # Update sync status with error
            if 'sync_status' in locals():
                sync_status.sync_status = 'failed'
                sync_status.last_error = str(e)
                sync_status.error_count += 1
                db.commit()
            
            return {'status': 'error', 'error': str(e)}
        finally:
            self.sync_in_progress.pop(account_number, None)
            db.close()
    
    async def _sync_transactions(self, db: Session, account: Account, ibkr_transactions: List[Dict]) -> int:
        """Sync transaction data to database."""
        synced_count = 0
        
        for txn_data in ibkr_transactions:
            try:
                # Check if transaction already exists
                existing = db.query(Transaction).filter(
                    and_(
                        Transaction.account_id == account.id,
                        Transaction.external_id == txn_data.get('execution_id') or txn_data.get('id'),
                        Transaction.symbol == txn_data['symbol']
                    )
                ).first()
                
                if existing:
                    continue  # Skip if already exists
                
                # Create new transaction record
                transaction = Transaction(
                    account_id=account.id,
                    external_id=txn_data.get('execution_id') or txn_data.get('id'),
                    order_id=txn_data.get('order_id'),
                    execution_id=txn_data.get('execution_id'),
                    symbol=txn_data['symbol'],
                    description=txn_data.get('description', ''),
                    transaction_type=txn_data['type'],
                    action=txn_data.get('action', ''),
                    quantity=float(txn_data['quantity']),
                    price=float(txn_data['price']),
                    amount=float(txn_data['amount']),
                    commission=float(txn_data.get('commission', 0)),
                    fees=float(txn_data.get('fees', 0)),
                    net_amount=float(txn_data['net_amount']),
                    currency=txn_data.get('currency', 'USD'),
                    exchange=txn_data.get('exchange', ''),
                    contract_type=txn_data.get('contract_type', 'STK'),
                    transaction_date=datetime.strptime(f"{txn_data['date']} {txn_data.get('time', '00:00:00')}", '%Y-%m-%d %H:%M:%S'),
                    settlement_date=datetime.strptime(txn_data['settlement_date'], '%Y-%m-%d') if txn_data.get('settlement_date') else None,
                    source='ibkr'
                )
                
                db.add(transaction)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing transaction {txn_data}: {e}")
                continue
        
        db.commit()
        return synced_count
    
    async def _sync_dividends(self, db: Session, account: Account, ibkr_dividends: List[Dict]) -> int:
        """Sync dividend data to database."""
        synced_count = 0
        
        for div_data in ibkr_dividends:
            try:
                # Check if dividend already exists
                existing = db.query(Dividend).filter(
                    and_(
                        Dividend.account_id == account.id,
                        Dividend.symbol == div_data['symbol'],
                        Dividend.ex_date == datetime.strptime(div_data['ex_date'], '%Y-%m-%d')
                    )
                ).first()
                
                if existing:
                    continue  # Skip if already exists
                
                # Create new dividend record
                dividend = Dividend(
                    account_id=account.id,
                    external_id=div_data.get('external_id') or f"{div_data['symbol']}-{div_data['ex_date']}",
                    symbol=div_data['symbol'],
                    ex_date=datetime.strptime(div_data['ex_date'], '%Y-%m-%d'),
                    pay_date=datetime.strptime(div_data['pay_date'], '%Y-%m-%d') if div_data.get('pay_date') else None,
                    dividend_per_share=float(div_data['dividend_per_share']),
                    shares_held=float(div_data.get('shares_held', 0)),
                    total_dividend=float(div_data['total_dividend']),
                    tax_withheld=float(div_data.get('tax_withheld', 0)),
                    net_dividend=float(div_data['net_dividend']),
                    currency=div_data.get('currency', 'USD'),
                    frequency=div_data.get('frequency', 'quarterly'),
                    dividend_type=div_data.get('type', 'ordinary'),
                    source='ibkr'
                )
                
                db.add(dividend)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing dividend {div_data}: {e}")
                continue
        
        db.commit()
        return synced_count
    
    async def _sync_tastytrade_transactions(self, db: Session, account: Account, tt_transactions: List[Dict]) -> int:
        """Sync TastyTrade transaction data to database."""
        synced_count = 0
        
        for txn_data in tt_transactions:
            try:
                # Check if transaction already exists
                existing = db.query(Transaction).filter(
                    and_(
                        Transaction.account_id == account.id,
                        Transaction.external_id == txn_data.get('execution_id') or txn_data.get('id'),
                        Transaction.symbol == txn_data['symbol']
                    )
                ).first()
                
                if existing:
                    continue  # Skip if already exists
                
                # Create new transaction record
                transaction = Transaction(
                    account_id=account.id,
                    external_id=txn_data.get('execution_id') or txn_data.get('id'),
                    order_id=txn_data.get('order_id'),
                    execution_id=txn_data.get('execution_id'),
                    symbol=txn_data['symbol'],
                    description=txn_data.get('description', ''),
                    transaction_type=txn_data['type'],
                    action=txn_data.get('action', ''),
                    quantity=float(txn_data['quantity']),
                    price=float(txn_data['price']),
                    amount=float(txn_data['amount']),
                    commission=float(txn_data.get('commission', 0)),
                    fees=float(txn_data.get('fees', 0)),
                    net_amount=float(txn_data['net_amount']),
                    currency=txn_data.get('currency', 'USD'),
                    exchange=txn_data.get('exchange', 'TASTYTRADE'),
                    contract_type=txn_data.get('contract_type', 'STK'),
                    transaction_date=datetime.strptime(f"{txn_data['date']} {txn_data.get('time', '00:00:00')}", '%Y-%m-%d %H:%M:%S'),
                    settlement_date=datetime.strptime(txn_data['settlement_date'], '%Y-%m-%d') if txn_data.get('settlement_date') else None,
                    source='tastytrade'
                )
                
                db.add(transaction)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing TastyTrade transaction {txn_data}: {e}")
                continue
        
        db.commit()
        return synced_count
    
    async def _sync_tastytrade_dividends(self, db: Session, account: Account, tt_dividends: List[Dict]) -> int:
        """Sync TastyTrade dividend data to database."""
        synced_count = 0
        
        for div_data in tt_dividends:
            try:
                # Check if dividend already exists
                existing = db.query(Dividend).filter(
                    and_(
                        Dividend.account_id == account.id,
                        Dividend.symbol == div_data['symbol'],
                        Dividend.ex_date == datetime.strptime(div_data['ex_date'], '%Y-%m-%d')
                    )
                ).first()
                
                if existing:
                    continue  # Skip if already exists
                
                # Create new dividend record
                dividend = Dividend(
                    account_id=account.id,
                    external_id=div_data.get('external_id') or f"tt_{div_data['symbol']}-{div_data['ex_date']}",
                    symbol=div_data['symbol'],
                    ex_date=datetime.strptime(div_data['ex_date'], '%Y-%m-%d'),
                    pay_date=datetime.strptime(div_data['pay_date'], '%Y-%m-%d') if div_data.get('pay_date') else None,
                    dividend_per_share=float(div_data['dividend_per_share']),
                    shares_held=float(div_data.get('shares_held', 0)),
                    total_dividend=float(div_data['total_dividend']),
                    tax_withheld=float(div_data.get('tax_withheld', 0)),
                    net_dividend=float(div_data['net_dividend']),
                    currency=div_data.get('currency', 'USD'),
                    frequency=div_data.get('frequency', 'quarterly'),
                    dividend_type=div_data.get('type', 'ordinary'),
                    source='tastytrade'
                )
                
                db.add(dividend)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing TastyTrade dividend {div_data}: {e}")
                continue
        
        db.commit()
        return synced_count
    
    async def get_transactions_from_db(self, account_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get transaction data from local database (fast)."""
        db = SessionLocal()
        
        try:
            # Build query
            query = db.query(Transaction)
            
            if account_id:
                account = db.query(Account).filter(Account.account_number == account_id).first()
                if account:
                    query = query.filter(Transaction.account_id == account.id)
            
            # Filter by date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Transaction.transaction_date >= cutoff_date)
            
            # Order by date (newest first)
            transactions = query.order_by(desc(Transaction.transaction_date)).all()
            
            # Convert to dict format
            transaction_list = []
            for txn in transactions:
                transaction_list.append({
                    'id': f"db_{txn.id}",
                    'date': txn.transaction_date.strftime('%Y-%m-%d'),
                    'time': txn.transaction_date.strftime('%H:%M:%S'),
                    'symbol': txn.symbol,
                    'description': txn.description,
                    'type': txn.transaction_type,
                    'action': txn.action,
                    'quantity': txn.quantity,
                    'price': txn.price,
                    'amount': txn.amount,
                    'commission': txn.commission,
                    'fees': txn.fees,
                    'net_amount': txn.net_amount,
                    'currency': txn.currency,
                    'exchange': txn.exchange,
                    'order_id': txn.order_id,
                    'execution_id': txn.execution_id,
                    'contract_type': txn.contract_type,
                    'account': account_id,
                    'settlement_date': txn.settlement_date.strftime('%Y-%m-%d') if txn.settlement_date else None,
                    'source': 'local_db'
                })
            
            # Calculate summary
            buy_transactions = [t for t in transaction_list if t['type'] == 'BUY']
            sell_transactions = [t for t in transaction_list if t['type'] == 'SELL']
            
            total_buy_amount = sum(t['amount'] for t in buy_transactions)
            total_sell_amount = sum(t['amount'] for t in sell_transactions)
            total_fees = sum(t['commission'] for t in transaction_list)
            
            summary = {
                'total_transactions': len(transaction_list),
                'buy_transactions': len(buy_transactions),
                'sell_transactions': len(sell_transactions),
                'total_buy_amount': total_buy_amount,
                'total_sell_amount': total_sell_amount,
                'total_fees': total_fees,
                'net_trading_amount': total_sell_amount - total_buy_amount - total_fees
            }
            
            return {
                'transactions': transaction_list,
                'summary': summary,
                'source': 'local_database',
                'data_freshness': 'cached'
            }
            
        except Exception as e:
            logger.error(f"Error getting transactions from DB: {e}")
            return {'error': str(e)}
        finally:
            db.close()
    
    async def get_dividends_from_db(self, account_id: Optional[str] = None, days: int = 365) -> Dict[str, Any]:
        """Get dividend data from local database (fast)."""
        db = SessionLocal()
        
        try:
            # Build query
            query = db.query(Dividend)
            
            if account_id:
                account = db.query(Account).filter(Account.account_number == account_id).first()
                if account:
                    query = query.filter(Dividend.account_id == account.id)
            
            # Filter by date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Dividend.ex_date >= cutoff_date)
            
            # Order by ex_date (newest first)
            dividends = query.order_by(desc(Dividend.ex_date)).all()
            
            # Convert to dict format
            dividend_list = []
            for div in dividends:
                dividend_list.append({
                    'symbol': div.symbol,
                    'ex_date': div.ex_date.strftime('%Y-%m-%d'),
                    'pay_date': div.pay_date.strftime('%Y-%m-%d') if div.pay_date else None,
                    'dividend_per_share': div.dividend_per_share,
                    'shares_held': div.shares_held,
                    'total_dividend': div.total_dividend,
                    'tax_withheld': div.tax_withheld,
                    'net_dividend': div.net_dividend,
                    'currency': div.currency,
                    'frequency': div.frequency,
                    'type': div.dividend_type,
                    'account': account_id,
                    'source': 'local_db'
                })
            
            # Calculate summary
            total_dividends = sum(d['total_dividend'] for d in dividend_list)
            total_tax_withheld = sum(d['tax_withheld'] for d in dividend_list)
            net_dividends = sum(d['net_dividend'] for d in dividend_list)
            
            summary = {
                'total_dividend_payments': len(dividend_list),
                'total_gross_dividends': total_dividends,
                'total_tax_withheld': total_tax_withheld,
                'total_net_dividends': net_dividends,
                'average_dividend': total_dividends / len(dividend_list) if dividend_list else 0
            }
            
            return {
                'dividends': dividend_list,
                'summary': summary,
                'source': 'local_database',
                'data_freshness': 'cached'
            }
            
        except Exception as e:
            logger.error(f"Error getting dividends from DB: {e}")
            return {'error': str(e)}
        finally:
            db.close()

    async def sync_tastytrade_portfolio(self) -> Dict[str, Any]:
        """Sync TastyTrade portfolio holdings and account data to database."""
        db = SessionLocal()
        results = {}
        
        try:
            # Get TastyTrade accounts
            tt_accounts = db.query(Account).filter(
                Account.is_active == True,
                Account.broker == 'TASTYTRADE'
            ).all()
            
            if not tt_accounts:
                return {'error': 'No active TastyTrade accounts found'}
            
            # Connect to TastyTrade if not connected
            if not tastytrade_client.connected:
                connection_success = await tastytrade_client.connect()
                if not connection_success:
                    return {'error': 'Failed to connect to TastyTrade'}
            
            total_holdings_synced = 0
            
            for account in tt_accounts:
                try:
                    logger.info(f"Syncing TastyTrade portfolio for account {account.account_number}")
                    
                    # Get positions from TastyTrade
                    positions = await tastytrade_client.get_positions(account.account_number)
                    
                    # Get account balances
                    account_data = await tastytrade_client.get_account_balance(account.account_number)
                    
                    # Sync holdings to database
                    holdings_synced = await self._sync_tastytrade_holdings(db, account, positions)
                    
                    # Create/update portfolio snapshot with balances
                    snapshot_created = await self._create_tastytrade_portfolio_snapshot(db, account, account_data, positions)
                    
                    total_holdings_synced += holdings_synced
                    
                    results[account.account_number] = {
                        'account_id': account.account_number,
                        'holdings_synced': holdings_synced,
                        'snapshot_created': snapshot_created,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"✅ Synced {holdings_synced} TastyTrade holdings for account {account.account_number}")
                    
                except Exception as e:
                    logger.error(f"Error syncing TastyTrade account {account.account_number}: {e}")
                    results[account.account_number] = {'error': str(e)}
            
            db.commit()
            
            return {
                'status': 'success',
                'total_holdings_synced': total_holdings_synced,
                'accounts_processed': len(results),
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing TastyTrade portfolio: {e}")
            return {'error': str(e)}
        finally:
            db.close()
    
    async def _sync_tastytrade_holdings(self, db: Session, account: Account, positions: List[Dict]) -> int:
        """Sync TastyTrade positions to Holdings table."""
        from backend.models.portfolio import Holding
        
        holdings_synced = 0
        
        try:
            # Clear existing holdings for this account (we'll repopulate)
            db.query(Holding).filter(Holding.account_id == account.id).delete()
            
            # Process positions in batches to avoid database parameter limits
            for position in positions:
                try:
                    # Extract position data
                    quantity = float(position.get('quantity', 0))
                    average_open_price = float(position.get('average_open_price', 0))
                    close_price = float(position.get('close_price', 0))
                    market_value = float(position.get('market_value', 0))
                    instrument_type = position.get('instrument_type', 'STK')
                    multiplier = int(position.get('multiplier', 100))
                    
                    # Calculate correct total unrealized P&L for options
                    if instrument_type in ['Equity Option', 'Future Option', 'Option']:
                        # For options: cost_basis = avg_price * quantity * multiplier
                        cost_basis = average_open_price * abs(quantity) * multiplier
                        current_value = close_price * abs(quantity) * multiplier
                        total_unrealized_pnl = current_value - cost_basis
                        
                        logger.debug(f"Option {position.get('symbol')}: cost_basis=${cost_basis:.2f}, current_value=${current_value:.2f}, P&L=${total_unrealized_pnl:.2f}")
                    else:
                        # For stocks: standard calculation
                        cost_basis = average_open_price * abs(quantity)
                        current_value = close_price * abs(quantity)
                        total_unrealized_pnl = current_value - cost_basis
                    
                    # Map TastyTrade position data to our Holding model
                    holding = Holding(
                        account_id=account.id,
                        symbol=position.get('symbol', ''),
                        quantity=quantity,
                        average_cost=average_open_price,
                        current_price=close_price,
                        market_value=market_value,
                        unrealized_pnl=total_unrealized_pnl,  # Use calculated total P&L, not day gain
                        unrealized_pnl_pct=0.0,  # Calculate from PnL and cost basis
                        day_pnl=float(position.get('unrealized_day_gain', 0)),  # Day gain goes here
                        day_pnl_pct=0.0,
                        currency='USD',  # TastyTrade is USD only
                        exchange=position.get('exchange', ''),
                        contract_type=instrument_type,
                        sector=position.get('sector', ''),
                        industry=position.get('industry', ''),
                        market_cap=position.get('market_cap', 0),
                        last_updated=datetime.utcnow()
                    )
                    
                    # Calculate unrealized PnL percentage if we have cost basis
                    if cost_basis > 0:
                        holding.unrealized_pnl_pct = (holding.unrealized_pnl / cost_basis) * 100
                    
                    db.add(holding)
                    holdings_synced += 1
                    
                    logger.info(f"Added TastyTrade holding: {holding.symbol} qty={holding.quantity} P&L=${holding.unrealized_pnl:.2f}")
                    
                except Exception as e:
                    logger.error(f"Error processing TastyTrade position {position}: {e}")
                    continue
            
            return holdings_synced
            
        except Exception as e:
            logger.error(f"Error syncing TastyTrade holdings: {e}")
            db.rollback()
            return 0
    
    async def _create_tastytrade_portfolio_snapshot(self, db: Session, account: Account, account_data: Dict, positions: List[Dict]) -> bool:
        """Create portfolio snapshot with TastyTrade account balance data."""
        from backend.models.portfolio import PortfolioSnapshot
        
        try:
            # Calculate portfolio totals
            total_equity_value = sum(float(pos.get('market_value', 0)) for pos in positions)
            total_unrealized_pnl = sum(float(pos.get('unrealized_pnl', 0)) for pos in positions)
            total_day_pnl = sum(float(pos.get('day_pnl', 0)) for pos in positions)
            
            # Extract account balance data
            total_cash = float(account_data.get('cash_balance', 0))
            buying_power = float(account_data.get('buying_power', 0))
            margin_used = float(account_data.get('margin_used', 0))
            margin_available = float(account_data.get('margin_available', 0))
            
            # Create snapshot
            snapshot = PortfolioSnapshot(
                account_id=account.id,
                snapshot_date=datetime.utcnow(),
                total_value=total_equity_value + total_cash,
                total_cash=total_cash,
                total_equity_value=total_equity_value,
                unrealized_pnl=total_unrealized_pnl,
                realized_pnl=0.0,  # Would need transaction history
                day_pnl=total_day_pnl,
                day_pnl_pct=(total_day_pnl / total_equity_value * 100) if total_equity_value > 0 else 0,
                buying_power=buying_power,
                margin_used=margin_used,
                margin_available=margin_available
            )
            
            db.add(snapshot)
            return True
            
        except Exception as e:
            logger.error(f"Error creating TastyTrade portfolio snapshot: {e}")
            return False

# Create global instance
transaction_sync_service = TransactionSyncService() 