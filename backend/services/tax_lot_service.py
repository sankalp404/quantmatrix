from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from backend.models.tax_lots import TaxLot, TaxLotSale, TaxStrategy, TaxReport, TaxLotMethod
from backend.models.portfolio import Holding, Account
from backend.models import get_db
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class TaxLotService:
    """Service for managing tax lots, cost basis, and tax optimization"""
    
    def __init__(self):
        self.db: Session = next(get_db())
    
    async def create_tax_lot(
        self,
        holding_id: int,
        symbol: str,
        account_id: str,
        purchase_date: datetime,
        shares: float,
        cost_per_share: float,
        commission: float = 0.0
    ) -> TaxLot:
        """Create a new tax lot for a purchase"""
        try:
            total_cost = (shares * cost_per_share) + commission
            
            tax_lot = TaxLot(
                holding_id=holding_id,
                symbol=symbol,
                account_id=account_id,
                purchase_date=purchase_date,
                shares_purchased=shares,
                cost_per_share=cost_per_share,
                total_cost=total_cost,
                commission=commission,
                shares_remaining=shares,
                shares_sold=0.0
            )
            
            # Determine if long-term (> 1 year)
            days_held = (datetime.utcnow() - purchase_date).days
            tax_lot.is_long_term = days_held >= 365
            
            self.db.add(tax_lot)
            self.db.commit()
            self.db.refresh(tax_lot)
            
            logger.info(f"Created tax lot for {symbol}: {shares} shares at ${cost_per_share}")
            return tax_lot
            
        except Exception as e:
            logger.error(f"Error creating tax lot: {e}")
            self.db.rollback()
            raise
    
    async def get_tax_lots_for_holding(self, holding_id: int) -> List[TaxLot]:
        """Get all tax lots for a specific holding"""
        return self.db.query(TaxLot).filter(
            and_(
                TaxLot.holding_id == holding_id,
                TaxLot.shares_remaining > 0
            )
        ).order_by(TaxLot.purchase_date).all()
    
    async def get_tax_lots_for_symbol(self, symbol: str, account_id: str) -> List[TaxLot]:
        """Get all tax lots for a symbol in an account"""
        return self.db.query(TaxLot).filter(
            and_(
                TaxLot.symbol == symbol,
                TaxLot.account_id == account_id,
                TaxLot.shares_remaining > 0
            )
        ).order_by(TaxLot.purchase_date).all()
    
    async def calculate_cost_basis(self, symbol: str, account_id: str) -> Dict:
        """Calculate detailed cost basis for a position"""
        tax_lots = await self.get_tax_lots_for_symbol(symbol, account_id)
        
        if not tax_lots:
            return {
                'total_shares': 0,
                'total_cost_basis': 0,
                'average_cost': 0,
                'tax_lots': []
            }
        
        total_shares = sum(lot.shares_remaining for lot in tax_lots)
        total_cost_basis = sum(lot.shares_remaining * lot.cost_per_share for lot in tax_lots)
        average_cost = total_cost_basis / total_shares if total_shares > 0 else 0
        
        # Get current price for unrealized calculations
        current_price = await market_data_service.get_current_price(symbol)
        
        lot_details = []
        for lot in tax_lots:
            current_value = lot.shares_remaining * current_price if current_price else 0
            unrealized_pnl = current_value - (lot.shares_remaining * lot.cost_per_share)
            
            lot_details.append({
                'id': lot.id,
                'purchase_date': lot.purchase_date,
                'shares': lot.shares_remaining,
                'cost_per_share': lot.cost_per_share,
                'cost_basis': lot.shares_remaining * lot.cost_per_share,
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': lot.unrealized_gain_loss_pct,
                'days_held': lot.holding_period_days,
                'tax_status': lot.tax_status,
                'is_wash_sale': lot.is_wash_sale
            })
        
        return {
            'symbol': symbol,
            'total_shares': total_shares,
            'total_cost_basis': total_cost_basis,
            'average_cost': average_cost,
            'current_price': current_price,
            'total_current_value': total_shares * current_price if current_price else 0,
            'total_unrealized_pnl': sum(lot['unrealized_pnl'] for lot in lot_details),
            'tax_lots': lot_details
        }
    
    async def simulate_sale(
        self,
        symbol: str,
        account_id: str,
        shares_to_sell: float,
        sale_price: float,
        lot_method: TaxLotMethod = TaxLotMethod.FIFO
    ) -> Dict:
        """Simulate a sale to show tax impact before execution"""
        tax_lots = await self.get_tax_lots_for_symbol(symbol, account_id)
        
        if not tax_lots:
            raise ValueError(f"No tax lots found for {symbol}")
        
        # Sort lots based on method
        if lot_method == TaxLotMethod.FIFO:
            tax_lots.sort(key=lambda x: x.purchase_date)
        elif lot_method == TaxLotMethod.LIFO:
            tax_lots.sort(key=lambda x: x.purchase_date, reverse=True)
        elif lot_method == TaxLotMethod.HIFO:
            tax_lots.sort(key=lambda x: x.cost_per_share, reverse=True)
        
        remaining_to_sell = shares_to_sell
        affected_lots = []
        total_cost_basis = 0
        total_proceeds = shares_to_sell * sale_price
        
        for lot in tax_lots:
            if remaining_to_sell <= 0:
                break
            
            shares_from_lot = min(remaining_to_sell, lot.shares_remaining)
            cost_basis = shares_from_lot * lot.cost_per_share
            proceeds = shares_from_lot * sale_price
            realized_pnl = proceeds - cost_basis
            
            affected_lots.append({
                'lot_id': lot.id,
                'purchase_date': lot.purchase_date,
                'shares_sold': shares_from_lot,
                'cost_per_share': lot.cost_per_share,
                'cost_basis': cost_basis,
                'proceeds': proceeds,
                'realized_pnl': realized_pnl,
                'is_long_term': lot.holding_period_days >= 365,
                'days_held': lot.holding_period_days
            })
            
            total_cost_basis += cost_basis
            remaining_to_sell -= shares_from_lot
        
        if remaining_to_sell > 0:
            raise ValueError(f"Not enough shares to sell. Need {shares_to_sell}, available {shares_to_sell - remaining_to_sell}")
        
        total_realized_pnl = total_proceeds - total_cost_basis
        short_term_pnl = sum(lot['realized_pnl'] for lot in affected_lots if not lot['is_long_term'])
        long_term_pnl = sum(lot['realized_pnl'] for lot in affected_lots if lot['is_long_term'])
        
        return {
            'symbol': symbol,
            'shares_sold': shares_to_sell,
            'sale_price': sale_price,
            'total_proceeds': total_proceeds,
            'total_cost_basis': total_cost_basis,
            'total_realized_pnl': total_realized_pnl,
            'short_term_pnl': short_term_pnl,
            'long_term_pnl': long_term_pnl,
            'lot_method': lot_method.value,
            'affected_lots': affected_lots,
            'estimated_tax_impact': self._estimate_tax_impact(short_term_pnl, long_term_pnl)
        }
    
    async def execute_sale(
        self,
        symbol: str,
        account_id: str,
        shares_to_sell: float,
        sale_price: float,
        sale_date: datetime,
        lot_method: TaxLotMethod = TaxLotMethod.FIFO,
        commission: float = 0.0
    ) -> List[TaxLotSale]:
        """Execute a sale and record tax lot sales"""
        try:
            # First simulate to validate
            simulation = await self.simulate_sale(symbol, account_id, shares_to_sell, sale_price, lot_method)
            
            tax_lots = await self.get_tax_lots_for_symbol(symbol, account_id)
            
            # Sort based on method (same as simulation)
            if lot_method == TaxLotMethod.FIFO:
                tax_lots.sort(key=lambda x: x.purchase_date)
            elif lot_method == TaxLotMethod.LIFO:
                tax_lots.sort(key=lambda x: x.purchase_date, reverse=True)
            elif lot_method == TaxLotMethod.HIFO:
                tax_lots.sort(key=lambda x: x.cost_per_share, reverse=True)
            
            remaining_to_sell = shares_to_sell
            sales_records = []
            
            for lot in tax_lots:
                if remaining_to_sell <= 0:
                    break
                
                shares_from_lot = min(remaining_to_sell, lot.shares_remaining)
                cost_basis = shares_from_lot * lot.cost_per_share
                proceeds = shares_from_lot * sale_price
                realized_pnl = proceeds - cost_basis - commission
                
                # Create sale record
                sale_record = TaxLotSale(
                    tax_lot_id=lot.id,
                    sale_date=sale_date,
                    shares_sold=shares_from_lot,
                    sale_price_per_share=sale_price,
                    total_proceeds=proceeds,
                    commission=commission,
                    cost_basis=cost_basis,
                    realized_gain_loss=realized_pnl,
                    is_long_term=lot.holding_period_days >= 365,
                    lot_method=lot_method
                )
                
                # Update tax lot
                lot.shares_remaining -= shares_from_lot
                lot.shares_sold += shares_from_lot
                
                self.db.add(sale_record)
                sales_records.append(sale_record)
                remaining_to_sell -= shares_from_lot
            
            self.db.commit()
            logger.info(f"Executed sale of {shares_to_sell} shares of {symbol}")
            return sales_records
            
        except Exception as e:
            logger.error(f"Error executing sale: {e}")
            self.db.rollback()
            raise
    
    async def analyze_tax_loss_harvesting(self, account_id: str) -> List[Dict]:
        """Analyze positions for tax loss harvesting opportunities"""
        try:
            # Get all holdings with unrealized losses
            query = self.db.query(TaxLot).filter(
                and_(
                    TaxLot.account_id == account_id,
                    TaxLot.shares_remaining > 0
                )
            ).all()
            
            opportunities = []
            for lot in query:
                # Get current price
                current_price = await market_data_service.get_current_price(lot.symbol)
                if not current_price:
                    continue
                
                unrealized_pnl = lot.unrealized_gain_loss
                
                # Only consider losses
                if unrealized_pnl < 0:
                    # Calculate potential tax savings (assume 30% tax rate for simplicity)
                    tax_savings = abs(unrealized_pnl) * 0.30 if lot.is_long_term else abs(unrealized_pnl) * 0.37
                    
                    opportunities.append({
                        'symbol': lot.symbol,
                        'shares': lot.shares_remaining,
                        'cost_basis': lot.shares_remaining * lot.cost_per_share,
                        'current_value': lot.current_value,
                        'unrealized_loss': unrealized_pnl,
                        'tax_savings': tax_savings,
                        'is_long_term': lot.is_long_term,
                        'days_held': lot.holding_period_days,
                        'purchase_date': lot.purchase_date,
                        'lot_id': lot.id
                    })
            
            # Sort by tax savings potential
            opportunities.sort(key=lambda x: x['tax_savings'], reverse=True)
            return opportunities
            
        except Exception as e:
            logger.error(f"Error analyzing tax loss harvesting: {e}")
            return []
    
    async def generate_tax_report(self, account_id: str, tax_year: int) -> Dict:
        """Generate comprehensive tax report for a year"""
        try:
            # Get all sales for the tax year
            start_date = datetime(tax_year, 1, 1)
            end_date = datetime(tax_year, 12, 31, 23, 59, 59)
            
            sales = self.db.query(TaxLotSale).join(TaxLot).filter(
                and_(
                    TaxLot.account_id == account_id,
                    TaxLotSale.sale_date >= start_date,
                    TaxLotSale.sale_date <= end_date
                )
            ).all()
            
            # Calculate totals
            short_term_gains = sum(sale.realized_gain_loss for sale in sales 
                                 if not sale.is_long_term and sale.realized_gain_loss > 0)
            short_term_losses = sum(sale.realized_gain_loss for sale in sales 
                                  if not sale.is_long_term and sale.realized_gain_loss < 0)
            long_term_gains = sum(sale.realized_gain_loss for sale in sales 
                                if sale.is_long_term and sale.realized_gain_loss > 0)
            long_term_losses = sum(sale.realized_gain_loss for sale in sales 
                                 if sale.is_long_term and sale.realized_gain_loss < 0)
            
            net_short_term = short_term_gains + short_term_losses
            net_long_term = long_term_gains + long_term_losses
            total_net = net_short_term + net_long_term
            
            # Get unrealized positions
            current_lots = self.db.query(TaxLot).filter(
                and_(
                    TaxLot.account_id == account_id,
                    TaxLot.shares_remaining > 0
                )
            ).all()
            
            unrealized_gains = 0
            unrealized_losses = 0
            
            for lot in current_lots:
                current_price = await market_data_service.get_current_price(lot.symbol)
                if current_price:
                    pnl = lot.unrealized_gain_loss
                    if pnl > 0:
                        unrealized_gains += pnl
                    else:
                        unrealized_losses += pnl
            
            return {
                'account_id': account_id,
                'tax_year': tax_year,
                'realized_gains_losses': {
                    'short_term_gains': short_term_gains,
                    'short_term_losses': short_term_losses,
                    'net_short_term': net_short_term,
                    'long_term_gains': long_term_gains,
                    'long_term_losses': long_term_losses,
                    'net_long_term': net_long_term,
                    'total_net': total_net
                },
                'unrealized_positions': {
                    'unrealized_gains': unrealized_gains,
                    'unrealized_losses': unrealized_losses,
                    'net_unrealized': unrealized_gains + unrealized_losses
                },
                'tax_efficiency_metrics': {
                    'loss_harvesting_potential': abs(unrealized_losses),
                    'long_term_percentage': (long_term_gains + abs(long_term_losses)) / 
                                          (short_term_gains + abs(short_term_losses) + long_term_gains + abs(long_term_losses)) * 100
                                          if (short_term_gains + abs(short_term_losses) + long_term_gains + abs(long_term_losses)) > 0 else 0
                },
                'sales_count': len(sales),
                'generated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating tax report: {e}")
            return {}
    
    def _estimate_tax_impact(self, short_term_pnl: float, long_term_pnl: float) -> Dict:
        """Estimate tax impact (simplified calculation)"""
        # Simplified tax rates
        short_term_rate = 0.37  # Assume highest bracket for short-term
        long_term_rate = 0.20   # Long-term capital gains rate
        
        short_term_tax = max(0, short_term_pnl * short_term_rate)
        long_term_tax = max(0, long_term_pnl * long_term_rate)
        
        return {
            'short_term_tax': short_term_tax,
            'long_term_tax': long_term_tax,
            'total_estimated_tax': short_term_tax + long_term_tax,
            'assumptions': {
                'short_term_rate': short_term_rate,
                'long_term_rate': long_term_rate,
                'note': 'Simplified calculation - consult tax professional'
            }
        }

# Create global instance
tax_lot_service = TaxLotService() 