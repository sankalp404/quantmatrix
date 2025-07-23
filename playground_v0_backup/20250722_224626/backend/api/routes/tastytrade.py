"""
Tastytrade API Routes
Endpoints for portfolio management and options trading through Tastytrade
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import logging
from collections import defaultdict

from backend.services.tastytrade_service import tastytrade_service
from backend.services.transaction_sync import transaction_sync_service
from backend.models import get_db, SessionLocal
from backend.models.portfolio import Account, Holding, PortfolioSnapshot

router = APIRouter(tags=["tastytrade"])

logger = logging.getLogger(__name__)

class OptionOrderRequest(BaseModel):
    symbol: str
    action: str  # 'BUY_TO_OPEN', 'SELL_TO_CLOSE', etc.
    quantity: int
    order_type: str = 'LIMIT'
    price: Optional[float] = None

@router.get("/health")
async def tastytrade_health():
    """Check Tastytrade connection status"""
    try:
        is_connected = tastytrade_service.is_connected
        return {
            "status": "connected" if is_connected else "disconnected",
            "service": "tastytrade",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_tastytrade():
    """Connect to Tastytrade API"""
    try:
        success = await tastytrade_service.connect()
        if success:
            return {
                "success": True,
                "message": "Connected to Tastytrade successfully"
            }
        else:
            raise HTTPException(status_code=401, detail="Failed to connect to Tastytrade")
    except Exception as e:
        logger.error(f"TastyTrade connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/accounts/initialize")
async def initialize_tastytrade_accounts():
    """Initialize TastyTrade accounts in the database from API"""
    try:
        # Connect to TastyTrade if not connected
        if not tastytrade_service.is_connected:
            connection_success = await tastytrade_service.connect()
            if not connection_success:
                raise HTTPException(status_code=401, detail="Failed to connect to TastyTrade")
        
        # Get accounts from TastyTrade client (not service)
        from backend.services.tastytrade_client import tastytrade_client
        
        if not tastytrade_client.connected:
            connection_success = await tastytrade_client.connect()
            if not connection_success:
                raise HTTPException(status_code=401, detail="Failed to connect to TastyTrade client")
        
        logger.info(f"TastyTrade client connected with {len(tastytrade_client.accounts)} accounts")
        
        tt_accounts_data = await tastytrade_client.get_accounts()
        
        logger.info(f"TastyTrade get_accounts returned: {tt_accounts_data}")
        
        if 'error' in str(tt_accounts_data):
            raise HTTPException(status_code=400, detail=f"TastyTrade API error: {tt_accounts_data}")
        
        db = SessionLocal()
        accounts_created = 0
        
        try:
            accounts_list = tt_accounts_data
            
            # Handle both cases: accounts_data might be a list or a dict with 'accounts' key
            if isinstance(accounts_list, dict) and 'accounts' in accounts_list:
                accounts_list = accounts_list['accounts']
            elif not isinstance(accounts_list, list):
                accounts_list = []
            
            logger.info(f"Processing {len(accounts_list)} TastyTrade accounts")
            
            for account_data in accounts_list:
                logger.info(f"Processing account: {account_data}")
                account_number = account_data.get('account-number') or account_data.get('account_number') or account_data.get('account_id')
                
                if not account_number:
                    logger.warning(f"Skipping account with no account number: {account_data}")
                    continue
                
                # Check if account already exists
                existing_account = db.query(Account).filter(
                    Account.account_number == account_number,
                    Account.broker == 'TASTYTRADE'
                ).first()
                
                if not existing_account:
                    # Create new TastyTrade account
                    new_account = Account(
                        user_id=1,  # Default user for now
                        account_name=account_data.get('nickname', f"TastyTrade {account_number}"),
                        account_type=account_data.get('account-type', 'brokerage'),
                        account_number=account_number,
                        broker='TASTYTRADE',
                        is_active=True,
                        is_paper_trading=account_data.get('is-test-drive', False),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    db.add(new_account)
                    accounts_created += 1
                    logger.info(f"Created TastyTrade account: {account_number}")
            
            db.commit()
            
            return {
                "status": "success",
                "message": f"Initialized {accounts_created} TastyTrade accounts",
                "accounts_created": accounts_created,
                "total_accounts_found": len(accounts_list),
                "accounts_data": accounts_list,  # For debugging
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Error initializing TastyTrade accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize accounts: {str(e)}")

@router.post("/portfolio/sync")
async def sync_tastytrade_portfolio():
    """Sync TastyTrade portfolio data to database"""
    try:
        logger.info("Starting TastyTrade portfolio sync...")
        
        # Use the transaction sync service which handles TastyTrade portfolio sync
        sync_results = await transaction_sync_service.sync_tastytrade_portfolio()
        
        if 'error' in sync_results:
            raise HTTPException(status_code=503, detail=f"TastyTrade sync error: {sync_results['error']}")
        
        return {
            "status": "success",
            "message": "TastyTrade portfolio synced successfully",
            "results": sync_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error syncing TastyTrade portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/portfolio/live")
async def get_tastytrade_live_portfolio(account_id: Optional[str] = None):
    """Get TastyTrade portfolio data from database (synced from TastyTrade)"""
    try:
        start_time = datetime.now()
        db = SessionLocal()
        
        # Filter TastyTrade accounts
        accounts_query = db.query(Account).filter(
            Account.is_active == True,
            Account.broker == 'TASTYTRADE'
        )
        if account_id:
            accounts_query = accounts_query.filter(Account.account_number == account_id)
        
        accounts = accounts_query.all()
        
        if not accounts:
            db.close()
            return {
                "status": "success",
                "data": {
                    "accounts": {},
                    "managed_accounts": [],
                    "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                    "timestamp": datetime.now().isoformat(),
                    "source": "database_tastytrade"
                }
            }
        
        accounts_data = {}
        managed_accounts = []
        
        for account in accounts:
            managed_accounts.append(account.account_number)
            
            # Get current holdings
            holdings = db.query(Holding).filter(
                Holding.account_id == account.id,
                Holding.quantity != 0  # Only active positions
            ).all()
            
            # Get latest portfolio snapshot for cash and margin data
            latest_snapshot = db.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.account_id == account.id
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).first()
            
            # Convert holdings to positions format
            all_positions = []
            equity_positions = []
            options_positions = []
            
            for holding in holdings:
                position_data = {
                    'symbol': holding.symbol,
                    'quantity': holding.quantity,
                    'average_price': holding.average_cost,
                    'current_price': holding.current_price,
                    'market_value': holding.market_value,
                    'unrealized_pnl': holding.unrealized_pnl,
                    'unrealized_pnl_pct': holding.unrealized_pnl_pct,
                    'day_pnl': holding.day_pnl or 0,
                    'day_pnl_pct': holding.day_pnl_pct or 0,
                    'currency': holding.currency,
                    'exchange': holding.exchange,
                    'contract_type': holding.contract_type,
                    'sector': holding.sector,
                    'industry': holding.industry,
                    'account': account.account_number,
                    'account_id': account.account_number,
                    'source': 'database'
                }
                
                all_positions.append(position_data)
                
                # Separate equity and options
                if holding.contract_type == 'STK':
                    equity_positions.append(position_data)
                elif holding.contract_type in ['OPT', 'CALL', 'PUT']:
                    options_positions.append(position_data)
            
            # Calculate portfolio metrics
            total_equity_value = sum(h.market_value for h in holdings)
            total_unrealized_pnl = sum(h.unrealized_pnl for h in holdings)
            total_day_pnl = sum(h.day_pnl or 0 for h in holdings)
            
            # Get cash and margin from latest snapshot or use defaults
            total_cash = latest_snapshot.total_cash if latest_snapshot else 0.0
            buying_power = latest_snapshot.buying_power if latest_snapshot else total_cash
            margin_used = latest_snapshot.margin_used if latest_snapshot else 0.0
            margin_available = latest_snapshot.margin_available if latest_snapshot else 0.0
            
            # Account summary data
            account_summary = {
                'account_id': account.account_number,
                'account_name': account.account_name,
                'account_type': account.account_type,
                'broker': 'TASTYTRADE',
                'net_liquidation': total_equity_value + total_cash,
                'total_cash': total_cash,
                'available_funds': total_cash + margin_available,
                'buying_power': buying_power,
                'margin_used': margin_used,
                'margin_available': margin_available,
                'unrealized_pnl': total_unrealized_pnl,
                'day_pnl': total_day_pnl,
                'timestamp': datetime.now().isoformat()
            }
            
            # Portfolio metrics with options breakdown
            portfolio_metrics = {
                'total_positions': len(holdings),
                'equity_positions': len(equity_positions),
                'options_positions': len(options_positions),
                'total_equity_value': total_equity_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_day_pnl': total_day_pnl,
                'cash_percentage': (total_cash / (total_equity_value + total_cash) * 100) if (total_equity_value + total_cash) > 0 else 0
            }
            
            # Sector allocation (primarily for equities)
            sector_totals = defaultdict(float)
            for holding in holdings:
                if holding.contract_type == 'STK':
                    sector_totals[holding.sector or 'Other'] += holding.market_value
            
            sector_allocation = [
                {
                    'sector': sector,
                    'value': value,
                    'percentage': (value / total_equity_value * 100) if total_equity_value > 0 else 0
                }
                for sector, value in sector_totals.items()
            ]
            
            # Top performers and worst performers
            holdings_data = [
                {
                    'symbol': h.symbol,
                    'unrealized_pnl_pct': h.unrealized_pnl_pct,
                    'market_value': h.market_value,
                    'contract_type': h.contract_type
                }
                for h in holdings if h.unrealized_pnl_pct is not None
            ]
            
            top_performers = sorted(holdings_data, key=lambda x: x['unrealized_pnl_pct'], reverse=True)[:5]
            worst_performers = sorted(holdings_data, key=lambda x: x['unrealized_pnl_pct'])[:5]
            
            # Assemble account data
            accounts_data[account.account_number] = {
                'account_summary': account_summary,
                'all_positions': all_positions,
                'equity_positions': equity_positions,
                'options_positions': options_positions,
                'portfolio_metrics': portfolio_metrics,
                'sector_allocation': sector_allocation,
                'top_performers': top_performers,
                'worst_performers': worst_performers,
                'timestamp': datetime.now().isoformat()
            }
        
        db.close()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "success",
            "data": {
                "accounts": accounts_data,
                "managed_accounts": managed_accounts,
                "processing_time_seconds": processing_time,
                "timestamp": datetime.now().isoformat(),
                "source": "database_tastytrade"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting TastyTrade portfolio data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get TastyTrade portfolio data: {str(e)}")

@router.get("/debug/holdings")
async def debug_tastytrade_holdings():
    """Debug endpoint to see what TastyTrade holdings are in the database"""
    try:
        db = SessionLocal()
        
        # Get TastyTrade account
        account = db.query(Account).filter(
            Account.broker == 'TASTYTRADE',
            Account.is_active == True
        ).first()
        
        if not account:
            return {"error": "No TastyTrade account found"}
        
        # Get ALL holdings (no quantity filter)
        holdings = db.query(Holding).filter(Holding.account_id == account.id).all()
        
        holdings_data = []
        for holding in holdings:
            holdings_data.append({
                'symbol': holding.symbol,
                'quantity': holding.quantity,
                'average_cost': holding.average_cost,
                'current_price': holding.current_price,
                'market_value': holding.market_value,
                'contract_type': holding.contract_type,
                'last_updated': holding.last_updated.isoformat() if holding.last_updated else None
            })
        
        db.close()
        
        return {
            "account_id": account.account_number,
            "total_holdings": len(holdings_data),
            "holdings": holdings_data[:5],  # First 5 for debugging
            "zero_quantity_count": len([h for h in holdings_data if h['quantity'] == 0]),
            "non_zero_quantity_count": len([h for h in holdings_data if h['quantity'] != 0])
        }
        
    except Exception as e:
        logger.error(f"Error in debug holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoints (direct TastyTrade API calls - for comparison)
@router.get("/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary from Tastytrade"""
    try:
        summary = await tastytrade_service.get_portfolio_summary()
        if "error" in summary:
            raise HTTPException(status_code=400, detail=summary["error"])
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/positions")
async def get_positions():
    """Get all positions from Tastytrade"""
    try:
        positions = await tastytrade_service.get_positions()
        
        # Convert to serializable format
        positions_data = []
        for pos in positions:
            positions_data.append({
                "symbol": pos.symbol,
                "quantity": float(pos.quantity),
                "average_price": float(pos.average_price),
                "current_price": float(pos.current_price),
                "unrealized_pnl": float(pos.unrealized_pnl),
                "realized_pnl": float(pos.realized_pnl),
                "instrument_type": pos.instrument_type,
                "underlying_symbol": pos.underlying_symbol,
                "option_type": pos.option_type,
                "strike": float(pos.strike) if pos.strike else None,
                "expiration": pos.expiration.isoformat() if pos.expiration else None
            })
        
        return {
            "positions": positions_data,
            "count": len(positions_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/options/top-atr-stocks")
async def get_top_atr_stocks(limit: int = 20):
    """Get top high-ATR stocks for options trading"""
    try:
        stocks = await tastytrade_service.get_top_atr_stocks(limit)
        return {
            "stocks": stocks,
            "count": len(stocks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/options/chain/{symbol}")
async def get_option_chain(symbol: str, days_to_expiry: int = 45):
    """Get option chain for a symbol"""
    try:
        chain = await tastytrade_service.get_option_chain(symbol, days_to_expiry)
        
        if not chain:
            raise HTTPException(status_code=404, detail=f"Option chain not found for {symbol}")
        
        return {
            "underlying_symbol": chain.underlying_symbol,
            "expiration": chain.expiration.isoformat(),
            "underlying_price": float(chain.underlying_price),
            "calls": chain.calls,
            "puts": chain.puts,
            "calls_count": len(chain.calls),
            "puts_count": len(chain.puts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/options/order")
async def place_option_order(order_request: OptionOrderRequest):
    """Place an options order"""
    try:
        result = await tastytrade_service.place_option_order(
            symbol=order_request.symbol,
            action=order_request.action,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            price=order_request.price
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quotes/{symbol}")
async def get_live_quote(symbol: str):
    """Get live quote for a symbol"""
    try:
        quote = await tastytrade_service.get_live_quote(symbol)
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"Quote not available for {symbol}")
        
        return {
            "symbol": quote.symbol,
            "bid": float(quote.bid),
            "ask": float(quote.ask),
            "last": float(quote.last),
            "volume": quote.volume,
            "iv": float(quote.iv) if quote.iv else None,
            "delta": float(quote.delta) if quote.delta else None,
            "gamma": float(quote.gamma) if quote.gamma else None,
            "theta": float(quote.theta) if quote.theta else None,
            "vega": float(quote.vega) if quote.vega else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/streaming/start")
async def start_streaming(symbols: List[str]):
    """Start real-time data streaming for symbols"""
    try:
        success = await tastytrade_service.start_real_time_data(symbols)
        
        if success:
            return {
                "success": True,
                "message": f"Started streaming for {len(symbols)} symbols",
                "symbols": symbols
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start streaming")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect")
async def disconnect_tastytrade():
    """Disconnect from Tastytrade"""
    try:
        await tastytrade_service.disconnect()
        return {
            "success": True,
            "message": "Disconnected from Tastytrade"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/transactions/{account_id}")
async def get_tastytrade_transactions(account_id: str, days: int = 30):
    """Get TastyTrade transaction history for specific account."""
    try:
        if not tastytrade_service.is_connected():
            await tastytrade_service.connect()
            
        transactions = await tastytrade_service.get_transaction_history(account_id, days)
        
        # Calculate summary
        total_transactions = len(transactions)
        buy_transactions = [t for t in transactions if t['type'] == 'BUY']
        sell_transactions = [t for t in transactions if t['type'] == 'SELL']
        
        total_buy_amount = sum(t['amount'] for t in buy_transactions)
        total_sell_amount = sum(t['amount'] for t in sell_transactions)
        total_fees = sum(t['commission'] + t['fees'] for t in transactions)
        
        summary = {
            'total_transactions': total_transactions,
            'buy_transactions': len(buy_transactions),
            'sell_transactions': len(sell_transactions),
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
            'total_fees': total_fees,
            'net_trading_amount': total_sell_amount - total_buy_amount - total_fees
        }
        
        return {
            'status': 'success',
            'data': {
                'transactions': transactions,
                'summary': summary,
                'account_id': account_id,
                'period_days': days,
                'source': 'tastytrade_direct'
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting TastyTrade transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")

@router.get("/transactions")
async def get_all_tastytrade_transactions(days: int = 30):
    """Get TastyTrade transaction history for all accounts."""
    try:
        if not tastytrade_service.is_connected():
            await tastytrade_service.connect()
            
        all_transactions = await tastytrade_service.get_all_transactions(days)
        
        # Combine transactions from all accounts
        combined_transactions = []
        for account_id, transactions in all_transactions.items():
            combined_transactions.extend(transactions)
        
        # Sort by date (newest first)
        combined_transactions.sort(key=lambda x: f"{x['date']} {x['time']}", reverse=True)
        
        # Calculate combined summary
        total_transactions = len(combined_transactions)
        buy_transactions = [t for t in combined_transactions if t['type'] == 'BUY']
        sell_transactions = [t for t in combined_transactions if t['type'] == 'SELL']
        
        total_buy_amount = sum(t['amount'] for t in buy_transactions)
        total_sell_amount = sum(t['amount'] for t in sell_transactions)
        total_fees = sum(t['commission'] + t['fees'] for t in combined_transactions)
        
        summary = {
            'accounts_processed': len(all_transactions),
            'total_transactions': total_transactions,
            'buy_transactions': len(buy_transactions),
            'sell_transactions': len(sell_transactions),
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
            'total_fees': total_fees,
            'net_trading_amount': total_sell_amount - total_buy_amount - total_fees
        }
        
        return {
            'status': 'success',
            'data': {
                'transactions': combined_transactions,
                'by_account': all_transactions,
                'summary': summary,
                'period_days': days,
                'source': 'tastytrade_direct'
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting all TastyTrade transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")

@router.get("/dividends/{account_id}")
async def get_tastytrade_dividends(account_id: str, days: int = 365):
    """Get TastyTrade dividend history for specific account."""
    try:
        if not tastytrade_service.is_connected():
            await tastytrade_service.connect()
            
        dividends = await tastytrade_service.get_dividend_history(account_id, days)
        
        # Calculate summary
        total_dividends = sum(d['total_dividend'] for d in dividends)
        total_tax_withheld = sum(d['tax_withheld'] for d in dividends)
        net_dividends = sum(d['net_dividend'] for d in dividends)
        
        summary = {
            'total_dividend_payments': len(dividends),
            'total_gross_dividends': total_dividends,
            'total_tax_withheld': total_tax_withheld,
            'total_net_dividends': net_dividends,
            'average_dividend': total_dividends / len(dividends) if dividends else 0
        }
        
        return {
            'status': 'success',
            'data': {
                'dividends': dividends,
                'summary': summary,
                'account_id': account_id,
                'period_days': days,
                'source': 'tastytrade_direct'
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting TastyTrade dividends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dividends: {str(e)}") 