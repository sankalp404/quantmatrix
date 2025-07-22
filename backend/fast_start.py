"""
Fast Start Backend - Minimal Working Server with Tastytrade
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QuantMatrix API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "QuantMatrix API is running", "status": "ok"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "quantmatrix",
        "timestamp": "2025-01-19T15:05:00Z"
    }

@app.get("/api/v1/tastytrade/health")
async def tastytrade_health():
    """Check Tastytrade credentials"""
    username = os.getenv('TASTYTRADE_USERNAME')
    password = os.getenv('TASTYTRADE_PASSWORD')
    is_test = os.getenv('TASTYTRADE_IS_TEST', 'true').lower() == 'true'
    
    return {
        "status": "configured" if username and password else "missing_credentials",
        "username": username[:4] + "***" if username else None,
        "is_test": is_test,
        "timestamp": "2025-01-19T15:05:00Z"
    }

@app.post("/api/v1/tastytrade/connect")
async def connect_tastytrade():
    """Test Tastytrade connection"""
    try:
        import tastytrade
        from tastytrade import Session
        
        username = os.getenv('TASTYTRADE_USERNAME')
        password = os.getenv('TASTYTRADE_PASSWORD')
        is_test = os.getenv('TASTYTRADE_IS_TEST', 'true').lower() == 'true'
        
        if not username or not password:
            return {"success": False, "error": "Missing credentials"}
        
        logger.info(f"Connecting to Tastytrade with username: {username[:4]}*** (test: {is_test})")
        
        # Test connection
        session = Session(username, password, is_test=is_test)
        
        return {
            "success": True,
            "message": "Connected to Tastytrade successfully",
            "is_test": is_test
        }
        
    except Exception as e:
        logger.error(f"Tastytrade connection failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/tastytrade/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio summary from Tastytrade"""
    try:
        import tastytrade
        from tastytrade import Session, Account
        
        username = os.getenv('TASTYTRADE_USERNAME')
        password = os.getenv('TASTYTRADE_PASSWORD')
        is_test = os.getenv('TASTYTRADE_IS_TEST', 'true').lower() == 'true'
        
        if not username or not password:
            return {"error": "Missing credentials"}
        
        # Connect and get portfolio
        session = Session(username, password, is_test=is_test)
        accounts = Account.get(session)
        
        if not accounts:
            return {"error": "No accounts found"}
        
        account = accounts[0]
        balances = account.get_balances(session)
        positions = account.get_positions(session)
        
        return {
            "account_number": account.account_number,
            "total_equity": float(balances.net_liquidating_value),
            "buying_power": float(balances.cash_balance),
            "day_pnl": float(balances.realized_day_gain or 0),
            "positions_count": len(positions),
            "options_count": len([p for p in positions if p.instrument_type.value == 'Option']),
            "stocks_count": len([p for p in positions if p.instrument_type.value == 'Equity']),
            "last_updated": "2025-01-19T15:05:00Z"
        }
        
    except Exception as e:
        logger.error(f"Portfolio summary error: {e}")
        return {"error": str(e)}

@app.get("/api/v1/tastytrade/portfolio/positions")
async def get_positions():
    """Get all positions from Tastytrade"""
    try:
        import tastytrade
        from tastytrade import Session, Account
        
        username = os.getenv('TASTYTRADE_USERNAME')
        password = os.getenv('TASTYTRADE_PASSWORD')
        is_test = os.getenv('TASTYTRADE_IS_TEST', 'true').lower() == 'true'
        
        if not username or not password:
            return {"error": "Missing credentials"}
        
        # Connect and get positions
        session = Session(username, password, is_test=is_test)
        accounts = Account.get(session)
        
        if not accounts:
            return {"error": "No accounts found"}
        
        account = accounts[0]
        positions = account.get_positions(session)
        
        positions_data = []
        for pos in positions:
            positions_data.append({
                "symbol": pos.symbol,
                "quantity": float(pos.quantity),
                "average_price": float(pos.average_open_price or 0),
                "current_price": float(pos.mark_price or 0),
                "unrealized_pnl": float(pos.unrealized_day_gain or 0),
                "realized_pnl": float(pos.realized_day_gain or 0),
                "instrument_type": pos.instrument_type.value,
                "underlying_symbol": pos.underlying_symbol,
            })
        
        return {
            "positions": positions_data,
            "count": len(positions_data)
        }
        
    except Exception as e:
        logger.error(f"Positions error: {e}")
        return {"error": str(e)}

@app.get("/api/v1/tastytrade/options/top-atr-stocks")
async def get_top_atr_stocks(limit: int = 20):
    """Get top high-ATR stocks for options trading"""
    # Mock data for now - replace with real ATR calculation
    stocks = [
        {"symbol": "TSLA", "last_price": 850.0, "atr_percentage": 4.2, "iv_rank": 65},
        {"symbol": "NVDA", "last_price": 875.0, "atr_percentage": 3.8, "iv_rank": 72},
        {"symbol": "AMD", "last_price": 150.0, "atr_percentage": 3.5, "iv_rank": 68},
        {"symbol": "ARKK", "last_price": 52.0, "atr_percentage": 3.2, "iv_rank": 58},
        {"symbol": "SPY", "last_price": 595.0, "atr_percentage": 1.1, "iv_rank": 25},
        {"symbol": "QQQ", "last_price": 520.0, "atr_percentage": 1.8, "iv_rank": 35},
        {"symbol": "AAPL", "last_price": 230.0, "atr_percentage": 2.1, "iv_rank": 42},
        {"symbol": "GOOGL", "last_price": 190.0, "atr_percentage": 2.3, "iv_rank": 38},
        {"symbol": "META", "last_price": 580.0, "atr_percentage": 2.8, "iv_rank": 45},
        {"symbol": "NFLX", "last_price": 970.0, "atr_percentage": 3.1, "iv_rank": 52},
    ]
    
    return {
        "stocks": stocks[:limit],
        "count": len(stocks[:limit])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 