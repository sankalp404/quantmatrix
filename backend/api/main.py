"""
QuantMatrix V1 - Clean FastAPI Application
Replaces the massive monolithic API routes with focused, organized endpoints.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
from typing import Dict, Any

# Route imports
from backend.api.routes import (
    auth,
    portfolio, 
    strategies,
    market_data,
    notifications,
    admin
)

# Model imports
from backend.models import Base
from backend.database import engine

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="QuantMatrix V1 API",
    description="Professional Trading Platform API with Architecture",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://quantmatrix.com", "https://staging.quantmatrix.com"],
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
        "api": "QuantMatrix V1"
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
        "api_base": "/api/v1"
    }

# Include route modules (focused and clean)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["Strategies"])
app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["Market Data"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

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
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 