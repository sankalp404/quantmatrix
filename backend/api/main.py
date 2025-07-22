from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
from contextlib import asynccontextmanager

from backend.config import settings, LOGGING_CONFIG
from backend.models import get_db, create_tables
from backend.services.market_data import market_data_service

# Import route modules
from backend.api.routes import (
    portfolio, 
    market_data, 
    strategies,
    trading,
    allocation, 
    tax_lots,
    alerts,
    tasks,
    screener,
    tastytrade,
    options
)

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle events."""
    # Startup
    logger.info("Starting QuantMatrix API...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    
    # Test market data service
    try:
        is_healthy = await market_data_service.health_check()
        if is_healthy:
            logger.info("Market data service is healthy")
        else:
            logger.warning("Market data service health check failed")
    except Exception as e:
        logger.error(f"Market data service error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down QuantMatrix API...")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A unified portfolio intelligence and automated trading platform",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - organized and cleaned up
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["market-data"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["trading"])
app.include_router(allocation.router, prefix="/api/v1/allocation", tags=["allocation"])
app.include_router(tax_lots.router, prefix="/api/v1/tax-lots", tags=["tax-lots"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(screener.router, prefix="/api/v1/screener", tags=["screener"])
app.include_router(tastytrade.router, prefix="/api/v1/tastytrade", tags=["tastytrade"])
app.include_router(options.router, prefix="/api/v1/options", tags=["options"])

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "QuantMatrix Trading Platform API",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Test market data service
    try:
        market_data_status = "healthy" if await market_data_service.health_check() else "unhealthy"
    except Exception:
        market_data_status = "unhealthy"
    
    overall_status = "healthy" if all([
        db_status == "healthy",
        market_data_status == "healthy"
    ]) else "unhealthy"
    
    return {
        "status": overall_status,
        "services": {
            "database": db_status,
            "market_data": market_data_status
        },
        "timestamp": "2024-01-01T00:00:00Z"  # Will be dynamic in real implementation
    }

@app.get("/api/v1/status")
async def api_status():
    """Detailed API status endpoint."""
    return {
        "api_version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "features": {
            "portfolio_tracking": True,
            "technical_analysis": True,
            "atr_matrix_strategy": True,
            "discord_notifications": bool(settings.DISCORD_WEBHOOK_URL),
            "ibkr_integration": True,
            "real_time_data": True
        },
        "limits": {
            "max_scanner_tickers": settings.MAX_SCANNER_TICKERS,
            "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
            "max_daily_trades": settings.MAX_DAILY_TRADES
        }
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error"
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    ) 