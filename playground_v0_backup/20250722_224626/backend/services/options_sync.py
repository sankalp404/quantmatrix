"""
Unified Options Sync Service
Combines options data from IBKR and TastyTrade, syncs to database for performance
Follows the 3 rules: Backend does the work, frontend displays, real data only
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import json

from backend.models import SessionLocal
from backend.models.options import (
    OptionInstrument, OptionPosition, OptionType, TastytradeAccount
)
from backend.models.portfolio import Account, Holding
from backend.services.ibkr_client import ibkr_client
from backend.services.tastytrade_client import tastytrade_client

logger = logging.getLogger(__name__)

class UnifiedOptionsSync:
    """Unified options data sync from both IBKR and TastyTrade"""
    
    def __init__(self):
        self.db = None
    
    async def sync_all_options_positions(self) -> Dict[str, Any]:
        """Sync options positions from both IBKR and TastyTrade"""
        db = SessionLocal()
        self.db = db
        
        try:
            results = {
                'status': 'success',
                'ibkr_results': {},
                'tastytrade_results': {},
                'total_options_synced': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Sync IBKR options positions
            ibkr_results = await self._sync_ibkr_options(db)
            results['ibkr_results'] = ibkr_results
            results['total_options_synced'] += ibkr_results.get('options_synced', 0)
            
            # Sync TastyTrade options positions
            tastytrade_results = await self._sync_tastytrade_options(db)
            results['tastytrade_results'] = tastytrade_results
            results['total_options_synced'] += tastytrade_results.get('options_synced', 0)
            
            db.commit()
            
            logger.info(f"✅ Unified options sync complete: {results['total_options_synced']} total options")
            return results
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in unified options sync: {e}")
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
        finally:
            db.close()
    
    async def _sync_ibkr_options(self, db) -> Dict[str, Any]:
        """Sync options positions from IBKR using database holdings (since live API has connection issues)"""
        try:
            # Get IBKR accounts
            ibkr_accounts = db.query(Account).filter(
                Account.broker == 'IBKR',
                Account.is_active == True
            ).all()
            
            if not ibkr_accounts:
                return {'error': 'No active IBKR accounts found', 'options_synced': 0}
            
            total_options = 0
            account_results = {}
            
            for account in ibkr_accounts:
                try:
                    # Get options holdings from database instead of live API (due to connection issues)
                    options_holdings = db.query(Holding).filter(
                        Holding.account_id == account.id,
                        Holding.contract_type == 'OPT',
                        Holding.quantity != 0  # Only active positions
                    ).all()
                    
                    options_count = 0
                    for holding in options_holdings:
                        # Convert holding to position-like dict for parsing
                        position_data = {
                            'symbol': holding.symbol,
                            'contract_type': holding.contract_type,
                            'position': holding.quantity,
                            'average_cost': holding.average_cost,
                            'current_price': holding.current_price,
                            'market_value': holding.market_value,
                            'unrealized_pnl': holding.unrealized_pnl,
                            'account': account.account_number
                        }
                        
                        # Parse IBKR option details from the symbol
                        option_data = self._parse_ibkr_option_from_holding(holding)
                        if option_data:
                            # Create or update option instrument
                            option_instrument = await self._create_or_update_option_instrument(db, option_data)
                            
                            # Create or update option position
                            if option_instrument:
                                await self._create_or_update_ibkr_position(
                                    db, option_instrument, position_data, account
                                )
                                options_count += 1
                                logger.debug(f"IBKR option synced: {option_instrument.symbol}")
                    
                    account_results[account.account_number] = {
                        'options_synced': options_count,
                        'broker': 'IBKR'
                    }
                    total_options += options_count
                    
                except Exception as e:
                    logger.error(f"Error syncing IBKR options for {account.account_number}: {e}")
                    account_results[account.account_number] = {
                        'options_synced': 0,
                        'broker': 'IBKR',
                        'error': str(e)
                    }
            
            return {
                'status': 'success',
                'options_synced': total_options,
                'accounts_processed': len(ibkr_accounts),
                'account_results': account_results
            }
            
        except Exception as e:
            logger.error(f"Error syncing IBKR options: {e}")
            return {'error': str(e), 'options_synced': 0}
    
    async def _sync_tastytrade_options(self, db) -> Dict[str, Any]:
        """Sync options positions from TastyTrade"""
        try:
            # Get TastyTrade accounts
            tt_accounts = db.query(Account).filter(
                Account.broker == 'TASTYTRADE',
                Account.is_active == True
            ).all()
            
            if not tt_accounts:
                return {'error': 'No active TastyTrade accounts found', 'options_synced': 0}
            
            total_options = 0
            account_results = {}
            
            for account in tt_accounts:
                # Get positions directly from TastyTrade API
                positions = await tastytrade_client.get_positions(account.account_number)
                
                options_count = 0
                for position in positions:
                    # Only process options
                    if position.get('instrument_type') in ['Equity Option', 'Future Option']:
                        # Parse TastyTrade option details
                        option_data = self._parse_tastytrade_option(position)
                        if option_data:
                            # Create or update option instrument
                            option_instrument = await self._create_or_update_option_instrument(db, option_data)
                            
                            # Create or update option position
                            if option_instrument:
                                await self._create_or_update_tastytrade_position(
                                    db, option_instrument, position, account
                                )
                                options_count += 1
                
                account_results[account.account_number] = {
                    'options_synced': options_count,
                    'broker': 'TASTYTRADE'
                }
                total_options += options_count
            
            return {
                'status': 'success',
                'options_synced': total_options,
                'accounts_processed': len(tt_accounts),
                'account_results': account_results
            }
            
        except Exception as e:
            logger.error(f"Error syncing TastyTrade options: {e}")
            return {'error': str(e), 'options_synced': 0}
    
    def _parse_ibkr_option(self, holding: Holding) -> Optional[Dict[str, Any]]:
        """Parse IBKR option details from holding symbol"""
        try:
            symbol = holding.symbol
            
            # IBKR option symbols are typically like: AAPL250117C00225000
            if len(symbol) < 15:
                return None
            
            # Parse components
            underlying = symbol[:4].strip()  # First 4 chars typically
            if len(symbol) > 15:
                # Try 6-char underlying for indices like SPY
                underlying = symbol[:6].strip()
                date_part = symbol[6:12]
                option_type = symbol[12]
                strike_part = symbol[13:]
            else:
                date_part = symbol[4:10]
                option_type = symbol[10]
                strike_part = symbol[11:]
            
            # Parse expiration date (YYMMDD format)
            exp_date = datetime.strptime(f"20{date_part}", "%Y%m%d")
            
            # Parse strike price (in cents, convert to dollars)
            strike_price = float(strike_part) / 1000.0
            
            # Determine option type
            opt_type = OptionType.CALL if option_type.upper() == 'C' else OptionType.PUT
            
            return {
                'symbol': symbol,
                'underlying_symbol': underlying,
                'strike_price': Decimal(str(strike_price)),
                'expiration_date': exp_date,
                'option_type': opt_type,
                'multiplier': 100,
                'source': 'IBKR'
            }
            
        except Exception as e:
            logger.warning(f"Could not parse IBKR option symbol {holding.symbol}: {e}")
            return None
    
    def _parse_ibkr_option_from_position(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse IBKR option details from position data"""
        try:
            symbol = position.get('symbol', '')
            
            # IBKR option symbols are typically like: AAPL250117C00225000
            if len(symbol) < 15:
                return None
            
            # Try different parsing strategies based on symbol length
            if len(symbol) >= 18:  # Longer symbols like indices
                underlying = symbol[:5].strip()
                date_part = symbol[5:11]
                option_type = symbol[11]
                strike_part = symbol[12:]
            else:
                underlying = symbol[:4].strip()
                date_part = symbol[4:10]
                option_type = symbol[10]
                strike_part = symbol[11:]
            
            # Parse expiration date (YYMMDD format)
            try:
                exp_date = datetime.strptime(f"20{date_part}", "%Y%m%d")
            except:
                return None
            
            # Parse strike price (in cents, convert to dollars)
            try:
                strike_price = float(strike_part) / 1000.0
            except:
                return None
            
            # Determine option type
            opt_type = OptionType.CALL if option_type.upper() == 'C' else OptionType.PUT
            
            return {
                'symbol': symbol,
                'underlying_symbol': underlying,
                'strike_price': Decimal(str(strike_price)),
                'expiration_date': exp_date,
                'option_type': opt_type,
                'multiplier': 100,
                'source': 'IBKR'
            }
            
        except Exception as e:
            logger.warning(f"Could not parse IBKR option symbol {position.get('symbol', 'UNKNOWN')}: {e}")
            return None
    
    def _parse_tastytrade_option(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse TastyTrade option details from position data"""
        try:
            symbol = position.get('symbol', '')
            underlying = position.get('underlying_symbol', '')
            
            # TastyTrade provides structured data
            if position.get('strike_price') and position.get('expiration_date'):
                exp_date = datetime.fromisoformat(position['expiration_date'].replace('Z', '+00:00'))
                strike_price = Decimal(str(position['strike_price']))
                option_type = OptionType.CALL if position.get('option_type', '').upper() == 'CALL' else OptionType.PUT
                
                return {
                    'symbol': symbol,
                    'underlying_symbol': underlying,
                    'strike_price': strike_price,
                    'expiration_date': exp_date,
                    'option_type': option_type,
                    'multiplier': position.get('multiplier', 100),
                    'source': 'TASTYTRADE'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not parse TastyTrade option {position.get('symbol', 'UNKNOWN')}: {e}")
            return None
    
    def _parse_ibkr_option_from_holding(self, holding: Holding) -> Optional[Dict[str, Any]]:
        """
        STOP GUESSING! Get real IBKR option data or return None.
        
        The previous implementation was creating FAKE option data by guessing 
        call vs put types and using placeholder strikes. This is completely wrong
        for a production trading system.
        """
        try:
            # CRITICAL: Only process if we have a real IBKR option symbol
            if not holding.symbol or holding.contract_type != 'OPT':
                logger.debug(f"Skipping non-option holding: {holding.symbol} ({holding.contract_type})")
                return None
                
            # Try to parse real IBKR option symbol format
            # IBKR option symbols are like: AAPL250117C00225000
            symbol = holding.symbol
            
            if len(symbol) < 15:
                logger.warning(f"IBKR option symbol too short: {symbol}")
                return None
            
            # Parse real option symbol components
            try:
                # Extract underlying (first 3-6 characters)
                if symbol[:3] in ['SPY', 'QQQ', 'IWM']:  # Common 3-char symbols
                    underlying = symbol[:3]
                    date_start = 3
                elif symbol[:4] in ['AAPL', 'MSFT', 'GOOGL']:  # Common 4-char symbols  
                    underlying = symbol[:4]
                    date_start = 4
                elif symbol[:5] in ['TSLA']:  # Some 5-char symbols
                    underlying = symbol[:5]
                    date_start = 5
                else:
                    # Default to 4 characters for most stocks
                    underlying = symbol[:4].rstrip()
                    date_start = len(underlying)
                
                # Parse expiration date (YYMMDD format)
                date_part = symbol[date_start:date_start+6]
                exp_date = datetime.strptime(f"20{date_part}", "%Y%m%d")
                
                # Parse option type (C or P)
                option_type_char = symbol[date_start+6]
                if option_type_char.upper() not in ['C', 'P']:
                    logger.warning(f"Invalid option type character: {option_type_char} in {symbol}")
                    return None
                    
                option_type = OptionType.CALL if option_type_char.upper() == 'C' else OptionType.PUT
                
                # Parse strike price (remaining digits in cents)
                strike_part = symbol[date_start+7:]
                if not strike_part.isdigit():
                    logger.warning(f"Invalid strike price format: {strike_part} in {symbol}")
                    return None
                    
                strike_price = Decimal(str(float(strike_part) / 1000.0))
                
                logger.info(f"✅ Parsed real IBKR option: {underlying} {option_type.value.upper()} ${strike_price} exp {exp_date.date()}")
                
                return {
                    'symbol': symbol,
                    'underlying_symbol': underlying,
                    'strike_price': strike_price,
                    'expiration_date': exp_date,
                    'option_type': option_type,
                    'multiplier': 100,
                    'source': 'IBKR_REAL'
                }
                
            except Exception as parse_error:
                logger.error(f"Failed to parse IBKR option symbol {symbol}: {parse_error}")
                return None
            
        except Exception as e:
            logger.warning(f"Could not parse IBKR option from holding {holding.symbol}: {e}")
            return None
    
    async def _create_or_update_option_instrument(self, db, option_data: Dict[str, Any]) -> Optional[OptionInstrument]:
        """Create or update option instrument in database"""
        try:
            # Check if instrument already exists
            existing = db.query(OptionInstrument).filter(
                OptionInstrument.symbol == option_data['symbol']
            ).first()
            
            if existing:
                # Update existing instrument with all fields
                existing.underlying_symbol = option_data['underlying_symbol']
                existing.strike_price = option_data['strike_price']
                existing.expiration_date = option_data['expiration_date']
                existing.option_type = option_data['option_type']
                existing.multiplier = option_data['multiplier']
                existing.updated_at = datetime.utcnow()
                return existing
            
            # Create new instrument
            instrument = OptionInstrument(
                symbol=option_data['symbol'],
                underlying_symbol=option_data['underlying_symbol'],
                strike_price=option_data['strike_price'],
                expiration_date=option_data['expiration_date'],
                option_type=option_data['option_type'],
                multiplier=option_data['multiplier'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(instrument)
            db.flush()  # Get the ID
            
            logger.debug(f"Created option instrument: {instrument.symbol}")
            return instrument
            
        except Exception as e:
            logger.error(f"Error creating option instrument: {e}")
            return None
    
    async def _create_or_update_option_position(self, db, instrument: OptionInstrument, 
                                               holding: Holding, account: Account, source: str):
        """Create or update option position from IBKR holding"""
        try:
            # Find or create TastyTrade account record if needed
            if source == 'IBKR':
                # For IBKR, we need to link to TastytradeAccount table or create a separate table
                # For now, let's use a placeholder approach
                # TODO: Create separate IBKRAccount table or modify OptionPosition to use generic Account
                return  # Skip for now, will implement after creating proper account linking
            
        except Exception as e:
            logger.error(f"Error creating option position: {e}")
    
    async def _create_or_update_ibkr_position(self, db, instrument: OptionInstrument,
                                                    position_data: Dict[str, Any], account: Account):
         """Create or update option position from IBKR data (using holding data)"""
         try:
             quantity = int(position_data.get('position', 0))
             
             # IBKR stores the total market value, extract the per-share option price
             market_value_total = float(position_data.get('market_value', 0))
             average_cost_total = float(position_data.get('average_cost', 0))
             
             # Calculate per-share prices for options
             if quantity != 0:
                 # Current price per share (market_value / quantity / multiplier)
                 current_price_per_share = market_value_total / (abs(quantity) * 100)
                 # Average cost per share (for options this should be cost per share, not per contract)
                 average_cost_per_share = average_cost_total / 100  # IBKR gives per-contract cost
             else:
                 current_price_per_share = 0
                 average_cost_per_share = 0
             
             # Calculate correct unrealized P&L for options
             # Cost basis = average_cost_per_share * quantity * multiplier
             cost_basis = average_cost_per_share * abs(quantity) * 100
             current_value = current_price_per_share * abs(quantity) * 100
             unrealized_pnl = current_value - cost_basis
             
             # Calculate percentage
             unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
             
             # Check if position already exists
             existing_position = db.query(OptionPosition).filter(
                 OptionPosition.account_id == account.id,
                 OptionPosition.option_id == instrument.id
             ).first()
             
             if existing_position:
                 # Update existing position with corrected values
                 existing_position.quantity = quantity
                 existing_position.average_open_price = Decimal(str(average_cost_per_share))
                 existing_position.current_price = Decimal(str(current_price_per_share))
                 existing_position.market_value = Decimal(str(current_value))
                 existing_position.unrealized_pnl = Decimal(str(unrealized_pnl))
                 existing_position.unrealized_pnl_pct = Decimal(str(unrealized_pnl_pct))
                 existing_position.position_cost = Decimal(str(cost_basis))
                 existing_position.last_updated = datetime.utcnow()
                 
                 logger.debug(f"Updated IBKR option: {instrument.symbol} P&L=${unrealized_pnl:.2f} ({unrealized_pnl_pct:.1f}%)")
                 return existing_position
             
             # Create new position with corrected values
             option_position = OptionPosition(
                 account_id=account.id,
                 option_id=instrument.id,
                 quantity=quantity,
                 average_open_price=Decimal(str(average_cost_per_share)),
                 current_price=Decimal(str(current_price_per_share)),
                 market_value=Decimal(str(current_value)),
                 unrealized_pnl=Decimal(str(unrealized_pnl)),
                 unrealized_pnl_pct=Decimal(str(unrealized_pnl_pct)),
                 day_pnl=Decimal(str(unrealized_pnl)),  # Use same as unrealized for now
                 position_cost=Decimal(str(cost_basis)),
                 opened_at=datetime.utcnow(),
                 last_updated=datetime.utcnow()
             )
             
             db.add(option_position)
             logger.debug(f"Created IBKR option: {instrument.symbol} qty={quantity} P&L=${unrealized_pnl:.2f}")
             
         except Exception as e:
             logger.error(f"Error creating IBKR option position: {e}")
    
    async def _create_or_update_tastytrade_position(self, db, instrument: OptionInstrument,
                                                   position: Dict[str, Any], account: Account):
        """Create or update option position from TastyTrade data"""
        try:
            quantity = int(position.get('quantity', 0))
            average_open_price = float(position.get('average_open_price', 0))
            current_price = float(position.get('close_price', 0))
            multiplier = int(position.get('multiplier', 100))
            
            # Calculate correct P&L for TastyTrade options
            # TastyTrade provides per-share prices, so we need to multiply by multiplier
            cost_basis = average_open_price * abs(quantity) * multiplier
            current_value = current_price * abs(quantity) * multiplier
            unrealized_pnl = current_value - cost_basis
            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            # Check if position already exists
            existing_position = db.query(OptionPosition).filter(
                OptionPosition.account_id == account.id,
                OptionPosition.option_id == instrument.id
            ).first()
            
            if existing_position:
                # Update existing position
                existing_position.quantity = quantity
                existing_position.average_open_price = Decimal(str(average_open_price))
                existing_position.current_price = Decimal(str(current_price))
                existing_position.market_value = Decimal(str(current_value))
                existing_position.unrealized_pnl = Decimal(str(unrealized_pnl))
                existing_position.unrealized_pnl_pct = Decimal(str(unrealized_pnl_pct))
                existing_position.position_cost = Decimal(str(cost_basis))
                existing_position.last_updated = datetime.utcnow()
                
                logger.debug(f"Updated TT option: {instrument.symbol} P&L=${unrealized_pnl:.2f} ({unrealized_pnl_pct:.1f}%)")
                return existing_position
            
            # Create new position
            option_position = OptionPosition(
                account_id=account.id,
                option_id=instrument.id,
                quantity=quantity,
                average_open_price=Decimal(str(average_open_price)),
                current_price=Decimal(str(current_price)),
                market_value=Decimal(str(current_value)),
                unrealized_pnl=Decimal(str(unrealized_pnl)),
                unrealized_pnl_pct=Decimal(str(unrealized_pnl_pct)),
                day_pnl=Decimal(str(unrealized_pnl)),  # Use same as unrealized for now
                position_cost=Decimal(str(cost_basis)),
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            
            db.add(option_position)
            logger.debug(f"Created TT option: {instrument.symbol} qty={quantity} P&L=${unrealized_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error creating TastyTrade option position: {e}")
    
    async def get_unified_options_portfolio(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get unified options portfolio from database"""
        db = SessionLocal()
        
        try:
            # Build base query
            query = db.query(OptionPosition).join(OptionInstrument).join(Account) # Changed from TastytradeAccount to Account
            
            if account_id:
                query = query.filter(Account.account_number == account_id) # Changed from TastytradeAccount to Account
            
            positions = query.all()
            
            # Process positions for frontend
            options_data = []
            total_market_value = Decimal('0')
            total_pnl = Decimal('0')
            
            for position in positions:
                option = position.option
                account = position.account
                
                position_data = {
                    'id': position.id,
                    'symbol': option.symbol,
                    'underlying_symbol': option.underlying_symbol,
                    'strike_price': float(option.strike_price),
                    'expiration_date': option.expiration_date.isoformat(),
                    'option_type': option.option_type.value,
                    'quantity': position.quantity,
                    'average_open_price': float(position.average_open_price),
                    'current_price': float(position.current_price or 0),
                    'market_value': float(position.market_value or 0),
                    'unrealized_pnl': float(position.unrealized_pnl or 0),
                    'unrealized_pnl_pct': float(position.unrealized_pnl_pct or 0),
                    'day_pnl': float(position.day_pnl or 0),
                    'account_number': account.account_number,
                    'days_to_expiration': (option.expiration_date.date() - datetime.now().date()).days,
                    'multiplier': option.multiplier,
                    'last_updated': position.last_updated.isoformat() if position.last_updated else None
                }
                
                options_data.append(position_data)
                total_market_value += position.market_value or Decimal('0')
                total_pnl += position.unrealized_pnl or Decimal('0')
            
            # Separate calls and puts
            calls = [pos for pos in options_data if pos['option_type'] == 'call']
            puts = [pos for pos in options_data if pos['option_type'] == 'put']
            
            # Group by underlying
            underlyings = {}
            for pos in options_data:
                underlying = pos['underlying_symbol']
                if underlying not in underlyings:
                    underlyings[underlying] = {'calls': [], 'puts': [], 'total_value': 0, 'total_pnl': 0}
                
                if pos['option_type'] == 'call':
                    underlyings[underlying]['calls'].append(pos)
                else:
                    underlyings[underlying]['puts'].append(pos)
                
                underlyings[underlying]['total_value'] += pos['market_value']
                underlyings[underlying]['total_pnl'] += pos['unrealized_pnl']
            
            return {
                'status': 'success',
                'data': {
                    'positions': options_data,
                    'calls': calls,
                    'puts': puts,
                    'underlyings': underlyings,
                    'summary': {
                        'total_positions': len(options_data),
                        'total_market_value': float(total_market_value),
                        'total_unrealized_pnl': float(total_pnl),
                        'calls_count': len(calls),
                        'puts_count': len(puts),
                        'underlyings_count': len(underlyings)
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting unified options portfolio: {e}")
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}
        finally:
            db.close()

# Global instance
unified_options_sync = UnifiedOptionsSync() 