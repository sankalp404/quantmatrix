"""
QuantMatrix V1 - Clean FastAPI Application
Replaces the massive monolithic API routes with focused, organized endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

# Route imports - TEMPORARY: Only core routes for FlexQuery sync stabilization
from backend.api.routes import (
    auth,
    portfolio,
    portfolio_live,
    portfolio_dashboard,
    portfolio_stocks,
    portfolio_statements,
    portfolio_options,
    portfolio_dividends,
    # strategies,      # DISABLED: Causing import errors with strategy_manager
    market_data,
    # notifications,   # DISABLED: Non-essential for FlexQuery sync
    # admin           # DISABLED: Non-essential for FlexQuery sync
)

# Import new account management routes
from backend.api.routes import account_management

# Model imports
from backend.models import Base
from backend.database import engine, SessionLocal
from backend.config import settings
from backend.models.broker_account import (
    BrokerAccount,
    BrokerType,
    AccountType,
    AccountStatus,
    SyncStatus,
)
from backend.services.clients.tastytrade_client import (
    TastyTradeClient,
    TASTYTRADE_AVAILABLE,
)
from backend.services.portfolio.account_config_service import account_config_service

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="QuantMatrix V1 API",
    description="Professional Trading Platform API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quantmatrix.com",
        "https://staging.quantmatrix.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create database tables
@app.on_event("startup")
async def startup_event():
    """Initialize database and services."""
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ database tables created/verified")

        # Initialize services
        logger.info("🚀 QuantMatrix V1 API starting up...")
        # Seed default user and broker accounts from .env for dev convenience
        try:
            seeding = account_config_service.seed_broker_accounts(user_id=1)
            logger.info(f"🌱 Account seeding: {seeding}")
        except Exception as se:
            logger.warning(f"Account seeding skipped/failed: {se}")

        # Optional: auto-discover TastyTrade accounts when only username/password are provided
        try:
            if (
                TASTYTRADE_AVAILABLE
                and getattr(settings, "TASTYTRADE_USERNAME", None)
                and getattr(settings, "TASTYTRADE_PASSWORD", None)
            ):
                client = TastyTradeClient()
                ok = await client.connect_with_retry()
                if ok:
                    accounts = await client.get_accounts()
                    if accounts:
                        db = SessionLocal()
                        created = 0
                        updated = 0
                        for acc in accounts:
                            acct_num = acc.get("account_number") or acc.get("account")
                            if not acct_num:
                                continue
                            existing = (
                                db.query(BrokerAccount)
                                .filter(
                                    BrokerAccount.user_id == 1,
                                    BrokerAccount.broker == BrokerType.TASTYTRADE,
                                    BrokerAccount.account_number == acct_num,
                                )
                                .first()
                            )
                            if existing:
                                existing.account_name = (
                                    acc.get("nickname")
                                    or existing.account_name
                                    or f"TastyTrade ({acct_num})"
                                )
                                existing.account_type = AccountType.TAXABLE
                                updated += 1
                            else:
                                new_acc = BrokerAccount(
                                    user_id=1,
                                    broker=BrokerType.TASTYTRADE,
                                    account_number=acct_num,
                                    account_name=acc.get("nickname")
                                    or f"TastyTrade ({acct_num})",
                                    account_type=AccountType.TAXABLE,
                                    status=AccountStatus.ACTIVE,
                                    is_enabled=True,
                                    sync_status=SyncStatus.NEVER_SYNCED,
                                    currency="USD",
                                )
                                db.add(new_acc)
                                created += 1
                        db.commit()
                        db.close()
                        logger.info(
                            f"🔎 TastyTrade autodiscovery: {created} created, {updated} updated"
                        )
                await client.disconnect()
        except Exception as e:
            logger.warning(f"TastyTrade autodiscovery skipped: {e}")

    except Exception as e:
        logger.error(f"❌ Startup error: {e}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "api": "QuantMatrix V1",
    }


# API root
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "QuantMatrix V1 - Professional Trading Platform API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_base": "/api/v1",
    }


# Include route modules - TEMPORARY: Only core routes for FlexQuery sync stabilization
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(
    portfolio_live.router, prefix="/api/v1/portfolio", tags=["Portfolio"]
)
app.include_router(
    portfolio_dividends.router, prefix="/api/v1/portfolio", tags=["Portfolio"]
)
app.include_router(
    portfolio_dashboard.router, prefix="/api/v1/portfolio", tags=["Portfolio"]
)
app.include_router(
    portfolio_stocks.router, prefix="/api/v1/portfolio", tags=["Portfolio"]
)
app.include_router(
    portfolio_statements.router, prefix="/api/v1/portfolio", tags=["Portfolio"]
)
app.include_router(
    portfolio_options.router, prefix="/api/v1/portfolio/options", tags=["Portfolio"]
)
# app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["Strategies"])  # DISABLED: Import errors
app.include_router(
    market_data.router, prefix="/api/v1/market-data", tags=["Market Data"]
)
# app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])  # DISABLED: Non-essential
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])  # DISABLED: Non-essential
app.include_router(account_management.router)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for better error responses."""
    logger.error(f"❌ Global exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
