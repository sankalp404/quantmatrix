import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json

from backend.models import SessionLocal
from backend.models.portfolio import Account, Holding, PortfolioSnapshot
from backend.models.tax_lots import TaxLot
from backend.services.ibkr_client import ibkr_client
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class PortfolioSyncService:
    """Service to sync real IBKR data to database for persistence and analysis."""
    
    def __init__(self):
        self.account_mapping = {
            'U19490886': {
                'name': 'Taxable Account',
                'type': 'taxable'  # Use string instead of AccountType.TAXABLE
            },
            'U15891532': {
                'name': 'Tax-Deferred Account', 
                'type': 'traditional_ira'  # Use string instead of AccountType.TRADITIONAL_IRA
            }
        }
    
    async def sync_all_accounts(self) -> Dict:
        """Sync all IBKR accounts to database."""
        db = SessionLocal()
        results = {}
        
        try:
            # Get dual account data from IBKR
            dual_portfolio_data = await ibkr_client.get_dual_account_summary()
            
            if 'error' in dual_portfolio_data:
                logger.error(f"IBKR connection error: {dual_portfolio_data['error']}")
                return {'error': dual_portfolio_data['error']}
            
            # Sync each account
            for account_id, portfolio_data in dual_portfolio_data.get('accounts', {}).items():
                if 'error' not in portfolio_data:
                    result = await self._sync_account(db, account_id, portfolio_data)
                    results[account_id] = result
                else:
                    results[account_id] = {'error': portfolio_data['error']}
            
            db.commit()
            logger.info(f"✅ Successfully synced {len(results)} accounts")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing accounts: {e}")
            results = {'error': str(e)}
        finally:
            db.close()
        
        return results
    
    async def _sync_account(self, db: Session, account_id: str, portfolio_data: Dict) -> Dict:
        """Sync a single account's data."""
        
        # Get or create account record
        account = db.query(Account).filter(Account.account_number == account_id).first()
        
        if not account:
            # Create new account with default user_id = 1 (we'll need a default user)
            account_config = self.account_mapping.get(account_id, {
                'name': f'Account {account_id}',
                'type': 'taxable'  # Use string instead of AccountType enum
            })
            
            account = Account(
                user_id=1,  # Default user - we'll need to create this
                account_number=account_id,
                account_name=account_config['name'],
                account_type=account_config['type'],  # This is now a string, not enum
                broker='IBKR',
                is_active=True
            )
            db.add(account)
            db.flush()  # Get the ID
            logger.info(f"Created new account: {account_id}")
        
        # FIXED: Actually sync the holdings data!
        holdings_result = await self._sync_holdings(db, account, portfolio_data)
        
        # Create portfolio snapshot for historical tracking
        snapshot_result = await self._create_portfolio_snapshot(db, account, portfolio_data)
        
        return {
            'account_id': account_id,
            'holdings_synced': holdings_result['count'],
            'snapshot_created': snapshot_result.get('created', False),
            'total_value': portfolio_data.get('account_summary', {}).get('net_liquidation', 0),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _sync_holdings(self, db: Session, account: Account, portfolio_data: Dict) -> Dict:
        """Sync holdings with real-time market data."""
        positions = portfolio_data.get('all_positions', [])
        synced_count = 0
        
        # Get current holdings from database
        existing_holdings = {h.symbol: h for h in db.query(Holding).filter(Holding.account_id == account.id).all()}
        
        # Track which symbols we've seen
        current_symbols = set()
        
        for position in positions:
            symbol = position.get('symbol', '')
            if not symbol or len(symbol) > 20:  # Skip invalid symbols
                continue
            
            current_symbols.add(symbol)
            
            # Get real-time market price (from our market data service)
            try:
                market_price = await market_data_service.get_current_price(symbol)
                if not market_price:
                    market_price = position.get('market_price', position.get('avg_cost', 0))
            except:
                market_price = position.get('market_price', position.get('avg_cost', 0))
            
            # Calculate real P&L
            quantity = position.get('position', 0)
            avg_cost = position.get('avg_cost', 0)
            market_value = market_price * quantity
            unrealized_pnl = (market_price - avg_cost) * quantity
            unrealized_pnl_pct = (unrealized_pnl / (avg_cost * abs(quantity)) * 100) if avg_cost != 0 else 0
            
            # Get additional market data
            sector = 'Other'
            industry = 'Other'
            market_cap = 0
            
            try:
                stock_info = await market_data_service.get_stock_info(symbol)
                sector = stock_info.get('sector', 'Other')
                industry = stock_info.get('industry', 'Other')
                market_cap = stock_info.get('market_cap', 0)
            except:
                pass
            
            # Update or create holding
            if symbol in existing_holdings:
                holding = existing_holdings[symbol]
                # Update with latest data
                holding.quantity = quantity
                holding.average_cost = avg_cost
                holding.current_price = market_price
                holding.market_value = market_value
                holding.unrealized_pnl = unrealized_pnl
                holding.unrealized_pnl_pct = unrealized_pnl_pct
                holding.sector = sector
                holding.industry = industry
                holding.market_cap = market_cap
                holding.last_updated = datetime.now()
            else:
                # Create new holding
                holding = Holding(
                    account_id=account.id,
                    symbol=symbol,
                    quantity=quantity,
                    average_cost=avg_cost,
                    current_price=market_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    currency=position.get('currency', 'USD'),
                    exchange=position.get('exchange', ''),
                    contract_type=position.get('contract_type', 'STK'),
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap,
                    first_acquired=datetime.now(),
                    last_updated=datetime.now()
                )
                db.add(holding)
            
            synced_count += 1
        
        # Mark holdings as inactive if they're no longer in IBKR (sold positions)
        for symbol, holding in existing_holdings.items():
            if symbol not in current_symbols:
                # Position was closed - update quantity to 0 but keep for historical tracking
                holding.quantity = 0
                holding.market_value = 0
                holding.unrealized_pnl = 0
                holding.unrealized_pnl_pct = 0
                holding.last_updated = datetime.now()
        
        return {'count': synced_count}
    
    async def _create_portfolio_snapshot(self, db: Session, account: Account, portfolio_data: Dict) -> Dict:
        """Create daily portfolio snapshot for historical analysis."""
        today = datetime.now().date()
        
        # Check if snapshot already exists for today
        existing_snapshot = db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.account_id == account.id,
            PortfolioSnapshot.snapshot_date >= datetime.combine(today, datetime.min.time()),
            PortfolioSnapshot.snapshot_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).first()
        
        account_summary = portfolio_data.get('account_summary', {})
        
        snapshot_data = {
            'account_id': account.id,
            'snapshot_date': datetime.now(),
            'total_value': account_summary.get('net_liquidation', 0),
            'total_cash': account_summary.get('total_cash', 0),
            'total_equity_value': sum(pos.get('position_value', 0) for pos in portfolio_data.get('all_positions', [])),
            'unrealized_pnl': account_summary.get('unrealized_pnl', 0),
            'realized_pnl': account_summary.get('realized_pnl', 0),
            'day_pnl': 0,  # Calculate from previous snapshot
            'day_pnl_pct': 0,  # Calculate from previous snapshot
            'buying_power': account_summary.get('buying_power', 0),
            'margin_used': 0,  # Calculate later
            'margin_available': account_summary.get('available_funds', 0),
            'holdings_snapshot': json.dumps(portfolio_data.get('all_positions', [])),
            'sector_allocation': json.dumps(portfolio_data.get('sector_allocation', {}))
        }
        
        if existing_snapshot:
            # Update existing snapshot
            for key, value in snapshot_data.items():
                if key != 'account_id':  # Don't update the FK
                    setattr(existing_snapshot, key, value)
            created = False
        else:
            # Create new snapshot
            snapshot = PortfolioSnapshot(**snapshot_data)
            db.add(snapshot)
            created = True
        
        return {'created': created}
    
    async def get_portfolio_summary(self, account_id: str = None) -> Dict:
        """Get portfolio summary from database (cached data)."""
        db = SessionLocal()
        try:
            query = db.query(Account)
            if account_id:
                query = query.filter(Account.account_id == account_id)
            
            accounts = query.all()
            result = {}
            
            for account in accounts:
                holdings = db.query(Holding).filter(
                    Holding.account_id == account.id,
                    Holding.quantity != 0  # Only active positions
                ).all()
                
                total_value = sum(h.market_value for h in holdings)
                total_unrealized_pnl = sum(h.unrealized_pnl for h in holdings)
                
                result[account.account_id] = {
                    'account_name': account.account_name,
                    'account_type': account.account_type.value,
                    'total_value': total_value,
                    'unrealized_pnl': total_unrealized_pnl,
                    'positions_count': len(holdings),
                    'holdings': [
                        {
                            'symbol': h.symbol,
                            'quantity': h.quantity,
                            'current_price': h.current_price,
                            'market_value': h.market_value,
                            'unrealized_pnl_pct': h.unrealized_pnl_pct,
                            'sector': h.sector
                        } for h in holdings
                    ]
                }
            
            return result
            
        finally:
            db.close()

# Global instance
portfolio_sync_service = PortfolioSyncService() 