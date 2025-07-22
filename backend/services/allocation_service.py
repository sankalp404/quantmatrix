from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from backend.models.portfolio import Account, Holding, Category
from backend.models import get_db
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class AllocationService:
    """Service for managing target allocations and rebalancing recommendations"""
    
    def __init__(self):
        self.db: Session = next(get_db())
    
    async def set_target_allocation(
        self,
        account_id: str,
        category_id: int,
        target_percentage: float
    ) -> Dict:
        """Set target allocation for a category"""
        try:
            category = self.db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise ValueError(f"Category {category_id} not found")
            
            # Update target allocation
            category.target_allocation = target_percentage
            
            # Validate total allocations don't exceed 100%
            account = self.db.query(Account).filter(Account.account_id == account_id).first()
            if account:
                total_target = sum(
                    cat.target_allocation or 0 
                    for cat in account.categories
                )
                
                if total_target > 100:
                    raise ValueError(f"Total target allocations exceed 100%: {total_target}%")
            
            self.db.commit()
            logger.info(f"Set target allocation for {category.name}: {target_percentage}%")
            
            return {
                'category_id': category_id,
                'category_name': category.name,
                'target_percentage': target_percentage,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error setting target allocation: {e}")
            self.db.rollback()
            raise
    
    async def get_current_allocation(self, account_id: str) -> Dict:
        """Calculate current portfolio allocation by category"""
        try:
            # Get account
            account = self.db.query(Account).filter(Account.account_id == account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Get all holdings with current values
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            total_value = 0
            category_values = {}
            uncategorized_value = 0
            
            for holding in holdings:
                # Update current price
                current_price = await market_data_service.get_current_price(holding.symbol)
                if current_price:
                    holding.current_price = current_price
                    holding.market_value = holding.shares * current_price
                    
                market_value = holding.market_value or 0
                total_value += market_value
                
                # Categorize holding
                if holding.categories:
                    for category in holding.categories:
                        if category.id not in category_values:
                            category_values[category.id] = {
                                'name': category.name,
                                'current_value': 0,
                                'target_percentage': category.target_allocation or 0,
                                'holdings': []
                            }
                        category_values[category.id]['current_value'] += market_value
                        category_values[category.id]['holdings'].append({
                            'symbol': holding.symbol,
                            'value': market_value,
                            'percentage': 0  # Will calculate after
                        })
                else:
                    uncategorized_value += market_value
            
            # Calculate percentages
            allocation_data = {}
            for cat_id, data in category_values.items():
                current_percentage = (data['current_value'] / total_value * 100) if total_value > 0 else 0
                
                # Update holding percentages within category
                for holding in data['holdings']:
                    holding['percentage'] = (holding['value'] / data['current_value'] * 100) if data['current_value'] > 0 else 0
                
                allocation_data[cat_id] = {
                    'name': data['name'],
                    'current_value': data['current_value'],
                    'current_percentage': current_percentage,
                    'target_percentage': data['target_percentage'],
                    'difference': current_percentage - data['target_percentage'],
                    'holdings': data['holdings']
                }
            
            # Add uncategorized if any
            if uncategorized_value > 0:
                allocation_data['uncategorized'] = {
                    'name': 'Uncategorized',
                    'current_value': uncategorized_value,
                    'current_percentage': (uncategorized_value / total_value * 100) if total_value > 0 else 0,
                    'target_percentage': 0,
                    'difference': (uncategorized_value / total_value * 100) if total_value > 0 else 0,
                    'holdings': []
                }
            
            return {
                'account_id': account_id,
                'total_value': total_value,
                'allocations': allocation_data,
                'last_updated': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error calculating current allocation: {e}")
            return {}
    
    async def generate_rebalancing_recommendations(self, account_id: str, min_threshold: float = 5.0) -> Dict:
        """Generate rebalancing recommendations based on target vs current allocations"""
        try:
            current_allocation = await self.get_current_allocation(account_id)
            
            if not current_allocation:
                return {'error': 'Unable to calculate current allocation'}
            
            total_value = current_allocation['total_value']
            allocations = current_allocation['allocations']
            
            recommendations = []
            total_trades_value = 0
            
            for cat_id, data in allocations.items():
                if cat_id == 'uncategorized':
                    continue
                    
                difference = data['difference']
                
                # Only recommend if difference exceeds threshold
                if abs(difference) >= min_threshold:
                    target_value = total_value * (data['target_percentage'] / 100)
                    current_value = data['current_value']
                    trade_amount = target_value - current_value
                    
                    action = 'buy' if trade_amount > 0 else 'sell'
                    
                    recommendation = {
                        'category': data['name'],
                        'category_id': cat_id,
                        'action': action,
                        'current_percentage': data['current_percentage'],
                        'target_percentage': data['target_percentage'],
                        'difference': difference,
                        'trade_amount': abs(trade_amount),
                        'priority': abs(difference),  # Higher difference = higher priority
                        'holdings_to_trade': self._suggest_holdings_to_trade(data['holdings'], action, abs(trade_amount))
                    }
                    
                    recommendations.append(recommendation)
                    total_trades_value += abs(trade_amount)
            
            # Sort by priority (largest differences first)
            recommendations.sort(key=lambda x: x['priority'], reverse=True)
            
            # Calculate impact metrics
            impact_metrics = {
                'total_trades_value': total_trades_value,
                'percentage_of_portfolio': (total_trades_value / total_value * 100) if total_value > 0 else 0,
                'number_of_categories': len(recommendations),
                'estimated_commission': len(recommendations) * 1.0,  # Assume $1 per trade
            }
            
            return {
                'account_id': account_id,
                'total_value': total_value,
                'min_threshold': min_threshold,
                'recommendations': recommendations,
                'impact_metrics': impact_metrics,
                'generated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating rebalancing recommendations: {e}")
            return {}
    
    def _suggest_holdings_to_trade(self, holdings: List[Dict], action: str, target_amount: float) -> List[Dict]:
        """Suggest specific holdings to trade for rebalancing"""
        if action == 'sell':
            # For selling, prioritize holdings with largest gains or smallest positions
            sorted_holdings = sorted(holdings, key=lambda x: x['value'], reverse=True)
        else:
            # For buying, suggest existing holdings to add to
            sorted_holdings = sorted(holdings, key=lambda x: x['percentage'], reverse=True)
        
        suggestions = []
        remaining_amount = target_amount
        
        for holding in sorted_holdings:
            if remaining_amount <= 0:
                break
                
            # Suggest trading a portion based on remaining amount
            suggested_amount = min(remaining_amount, holding['value'] * 0.5)  # Don't suggest more than 50% of position
            
            if suggested_amount > 100:  # Only suggest trades over $100
                suggestions.append({
                    'symbol': holding['symbol'],
                    'current_value': holding['value'],
                    'suggested_amount': suggested_amount,
                    'action': action
                })
                remaining_amount -= suggested_amount
        
        return suggestions
    
    async def create_rebalancing_orders(self, account_id: str, recommendations: List[Dict]) -> Dict:
        """Create actual rebalancing orders (simulation for now)"""
        try:
            orders = []
            
            for rec in recommendations:
                for holding in rec['holdings_to_trade']:
                    # Get current price
                    current_price = await market_data_service.get_current_price(holding['symbol'])
                    if not current_price:
                        continue
                    
                    shares = holding['suggested_amount'] / current_price
                    
                    order = {
                        'symbol': holding['symbol'],
                        'action': holding['action'],
                        'shares': round(shares, 2),
                        'estimated_price': current_price,
                        'estimated_value': holding['suggested_amount'],
                        'order_type': 'market',
                        'category': rec['category'],
                        'reason': f"Rebalancing {rec['category']} from {rec['current_percentage']:.1f}% to {rec['target_percentage']:.1f}%"
                    }
                    
                    orders.append(order)
            
            return {
                'account_id': account_id,
                'orders': orders,
                'total_orders': len(orders),
                'estimated_total_value': sum(order['estimated_value'] for order in orders),
                'status': 'simulated',  # Would be 'pending' in real implementation
                'created_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error creating rebalancing orders: {e}")
            return {}
    
    async def analyze_drift(self, account_id: str, days: int = 30) -> Dict:
        """Analyze allocation drift over time"""
        try:
            # This would need historical data to implement properly
            # For now, return current allocation analysis
            current_allocation = await self.get_current_allocation(account_id)
            
            if not current_allocation:
                return {'error': 'Unable to analyze drift'}
            
            drift_analysis = {
                'account_id': account_id,
                'analysis_period_days': days,
                'categories': {}
            }
            
            for cat_id, data in current_allocation['allocations'].items():
                if cat_id == 'uncategorized':
                    continue
                    
                # Calculate drift metrics
                drift_analysis['categories'][cat_id] = {
                    'name': data['name'],
                    'current_drift': data['difference'],
                    'drift_severity': self._categorize_drift(abs(data['difference'])),
                    'rebalance_urgency': 'high' if abs(data['difference']) > 10 else 'medium' if abs(data['difference']) > 5 else 'low'
                }
            
            return drift_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing drift: {e}")
            return {}
    
    def _categorize_drift(self, drift_amount: float) -> str:
        """Categorize drift severity"""
        if drift_amount < 2:
            return 'minimal'
        elif drift_amount < 5:
            return 'low'
        elif drift_amount < 10:
            return 'moderate'
        elif drift_amount < 20:
            return 'high'
        else:
            return 'severe'
    
    async def get_allocation_history(self, account_id: str, months: int = 12) -> Dict:
        """Get allocation history over time (placeholder for future implementation)"""
        try:
            # This would require historical snapshots
            # For now, return current state as baseline
            current = await self.get_current_allocation(account_id)
            
            return {
                'account_id': account_id,
                'months': months,
                'current_allocation': current,
                'historical_data': [],  # Would be populated with actual historical data
                'note': 'Historical tracking not yet implemented'
            }
            
        except Exception as e:
            logger.error(f"Error getting allocation history: {e}")
            return {}

# Create global instance
allocation_service = AllocationService() 