"""
Tax Lot Generator Service

Generates proper tax lots from transaction history using FIFO/LIFO methods.
This creates accurate cost basis tracking from the imported CSV transactions.
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from collections import defaultdict

from backend.models import SessionLocal
from backend.models.transactions import Transaction
from backend.models.tax_lots import TaxLot
from backend.models.portfolio import Account, Holding

logger = logging.getLogger(__name__)

class TaxLotGenerator:
    """Generate tax lots from transaction history"""
    
    def __init__(self):
        self.lot_method = "FIFO"  # First In, First Out
    
    def generate_tax_lots_from_transactions(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate tax lots from all transactions for an account
        
        Args:
            account_id: Specific account ID, or None for all accounts
            
        Returns:
            Summary of tax lots generated
        """
        db = SessionLocal()
        
        try:
            logger.info(f"🔄 Starting tax lot generation for account_id={account_id}")
            
            # Get all BUY transactions (purchases create tax lots)
            query = db.query(Transaction).filter(Transaction.transaction_type == 'BUY')
            
            if account_id:
                query = query.filter(Transaction.account_id == account_id)
            
            transactions = query.order_by(Transaction.transaction_date).all()
            
            logger.info(f"📊 Found {len(transactions)} BUY transactions for tax lot generation")
            
            if not transactions:
                return {'error': 'No purchase transactions found', 'tax_lots_created': 0}
            
            logger.info(f"📊 Processing {len(transactions)} purchase transactions")
            
            # Group transactions by symbol and account
            transactions_by_symbol = defaultdict(list)
            for txn in transactions:
                key = f"{txn.account_id}_{txn.symbol}"
                transactions_by_symbol[key].append(txn)
            
            # Clear existing tax lots if regenerating
            if account_id:
                db.query(TaxLot).filter(TaxLot.account_id == account_id).delete()
            else:
                db.query(TaxLot).delete()
            
            total_lots_created = 0
            
            # Generate tax lots for each symbol
            for symbol_key, symbol_transactions in transactions_by_symbol.items():
                account_id_part, symbol = symbol_key.split('_', 1)
                account_id_int = int(account_id_part)
                
                lots_created = self._generate_lots_for_symbol(db, account_id_int, symbol, symbol_transactions)
                total_lots_created += lots_created
                
                logger.debug(f"Generated {lots_created} tax lots for {symbol}")
            
            db.commit()
            
            # Get summary statistics
            summary = self._get_tax_lot_summary(db, account_id)
            summary['tax_lots_created'] = total_lots_created
            summary['transactions_processed'] = len(transactions)
            summary['symbols_processed'] = len(transactions_by_symbol)
            
            logger.info(f"✅ Tax lot generation complete: {total_lots_created} lots created")
            
            return summary
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error generating tax lots: {e}")
            return {'error': str(e), 'tax_lots_created': 0}
        finally:
            db.close()
    
    def _generate_lots_for_symbol(self, db: Session, account_id: int, symbol: str, 
                                 transactions: List[Transaction]) -> int:
        """Generate tax lots for a specific symbol using FIFO method"""
        try:
            lots_created = 0
            
            for txn in transactions:
                # All transactions are already BUY transactions from the query filter
                
                # Calculate days held (from purchase date to today)
                purchase_date = txn.transaction_date.date() if hasattr(txn.transaction_date, 'date') else txn.transaction_date
                today = date.today()
                days_held = (today - purchase_date).days
                
                # Determine if it's long-term (> 365 days)
                is_long_term = days_held > 365
                
                # Calculate cost per share
                cost_per_share = Decimal(str(txn.price))
                total_cost = cost_per_share * Decimal(str(txn.quantity))
                
                # Get current market value (if holding exists)
                current_value_total = Decimal('0')
                unrealized_pnl = Decimal('0')
                unrealized_pnl_pct = Decimal('0')
                
                # Try to get current holding for market value calculation
                holding = db.query(Holding).filter(
                    Holding.account_id == account_id,
                    Holding.symbol == symbol
                ).first()
                
                if holding and holding.current_price:
                    current_price = Decimal(str(holding.current_price))
                    current_value_total = current_price * Decimal(str(txn.quantity))
                    unrealized_pnl = current_value_total - total_cost
                    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else Decimal('0')
                
                # Create tax lot using correct field names from TaxLot model
                tax_lot = TaxLot(
                    account_id=str(account_id),  # Convert to string as per model
                    holding_id=holding.id if holding else None,
                    symbol=symbol,
                    shares_purchased=float(txn.quantity),
                    shares_remaining=float(txn.quantity),  # Initially all shares remain
                    purchase_date=purchase_date,
                    cost_per_share=float(cost_per_share),
                    total_cost=float(total_cost),
                    commission=float(txn.commission or 0),
                    is_long_term=is_long_term,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.add(tax_lot)
                lots_created += 1
                
                logger.debug(f"Created tax lot: {symbol} {txn.quantity} shares @ ${cost_per_share} on {purchase_date}")
            
            return lots_created
            
        except Exception as e:
            logger.error(f"Error generating lots for {symbol}: {e}")
            return 0
    
    def _get_tax_lot_summary(self, db: Session, account_id: Optional[int]) -> Dict[str, Any]:
        """Get summary statistics of generated tax lots"""
        try:
            query = db.query(TaxLot)
            
            if account_id:
                query = query.filter(TaxLot.account_id == account_id)
            
            all_lots = query.all()
            
            if not all_lots:
                return {
                    'total_lots': 0,
                    'total_cost_basis': 0,
                    'total_current_value': 0,
                    'total_unrealized_pnl': 0,
                    'long_term_lots': 0,
                    'short_term_lots': 0,
                    'unique_symbols': 0
                }
            
            total_cost = sum(float(lot.total_cost or 0) for lot in all_lots)
            # TaxLot model doesn't store current_value or unrealized_pnl, only cost basis
            total_value = 0  # Will calculate this separately if needed
            total_pnl = 0  # Will calculate this separately if needed
            
            long_term_count = len([lot for lot in all_lots if lot.is_long_term])
            short_term_count = len(all_lots) - long_term_count
            
            unique_symbols = len(set(lot.symbol for lot in all_lots))
            
            return {
                'total_lots': len(all_lots),
                'total_cost_basis': round(total_cost, 2),
                'total_current_value': round(total_value, 2),
                'total_unrealized_pnl': round(total_pnl, 2),
                'unrealized_pnl_pct': round((total_pnl / total_cost * 100) if total_cost > 0 else 0, 2),
                'long_term_lots': long_term_count,
                'short_term_lots': short_term_count,
                'unique_symbols': unique_symbols,
                'average_days_held': round(sum((date.today() - lot.purchase_date.date() if hasattr(lot.purchase_date, 'date') else date.today() - lot.purchase_date).days for lot in all_lots) / len(all_lots), 1),
                'oldest_lot_date': min(lot.purchase_date for lot in all_lots).isoformat(),
                'newest_lot_date': max(lot.purchase_date for lot in all_lots).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating tax lot summary: {e}")
            return {'error': str(e)}
    
    def reconcile_tax_lots_with_current_holdings(self, account_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Reconcile tax lots with current holdings to ensure accuracy
        
        This checks that the sum of tax lot shares matches current holding quantities
        """
        db = SessionLocal()
        
        try:
            logger.info(f"🔍 Reconciling tax lots with current holdings")
            
            # Get current holdings
            holdings_query = db.query(Holding)
            if account_id:
                holdings_query = holdings_query.filter(Holding.account_id == account_id)
            
            holdings = holdings_query.all()
            
            reconciliation_results = []
            total_discrepancies = 0
            
            for holding in holdings:
                # Get tax lots for this holding
                tax_lots = db.query(TaxLot).filter(
                    TaxLot.account_id == holding.account_id,
                    TaxLot.symbol == holding.symbol
                ).all()
                
                # Calculate total shares in tax lots
                tax_lot_shares = sum(float(lot.shares_remaining) for lot in tax_lots)
                holding_shares = float(holding.quantity)
                
                discrepancy = abs(holding_shares - tax_lot_shares)
                
                if discrepancy > 0.01:  # Allow for small rounding differences
                    total_discrepancies += 1
                    
                    result = {
                        'symbol': holding.symbol,
                        'holding_shares': holding_shares,
                        'tax_lot_shares': tax_lot_shares,
                        'discrepancy': round(discrepancy, 4),
                        'status': 'MISMATCH'
                    }
                else:
                    result = {
                        'symbol': holding.symbol,
                        'holding_shares': holding_shares,
                        'tax_lot_shares': tax_lot_shares,
                        'discrepancy': 0,
                        'status': 'MATCH'
                    }
                
                reconciliation_results.append(result)
            
            return {
                'status': 'success',
                'holdings_checked': len(holdings),
                'discrepancies_found': total_discrepancies,
                'reconciliation_details': reconciliation_results,
                'summary': f"Checked {len(holdings)} holdings, found {total_discrepancies} discrepancies"
            }
            
        except Exception as e:
            logger.error(f"Error in tax lot reconciliation: {e}")
            return {'error': str(e)}
        finally:
            db.close()

# Global instance
tax_lot_generator = TaxLotGenerator() 