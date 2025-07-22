import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Configuration
    APP_NAME: str = "QuantMatrix Trading Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # Database Configuration - using SQLite for development  
    DATABASE_URL: str = "sqlite:///./quantmatrix.db"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # API Keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    TWELVE_DATA_API_KEY: Optional[str] = None
    FMP_API_KEY: Optional[str] = None
    
    # Tastytrade Configuration  
    TASTYTRADE_USERNAME: Optional[str] = None
    TASTYTRADE_PASSWORD: Optional[str] = None
    TASTYTRADE_IS_TEST: bool = True  # Match user's .env variable name
    
    # IBKR Configuration
    IBKR_HOST: str = "127.0.0.1"
    IBKR_PORT: int = 7497
    IBKR_CLIENT_ID: int = 1
    
    # Discord Configuration (5 separate webhooks for different purposes)
    DISCORD_WEBHOOK_SIGNALS: Optional[str] = None  # Entry/exit signals
    DISCORD_WEBHOOK_PORTFOLIO_DIGEST: Optional[str] = None  # Portfolio summaries
    DISCORD_WEBHOOK_MORNING_BREW: Optional[str] = None  # Daily scans & market updates  
    DISCORD_WEBHOOK_PLAYGROUND: Optional[str] = None  # Test notifications
    DISCORD_WEBHOOK_SYSTEM_STATUS: Optional[str] = None  # System status updates
    
    # Security Configuration
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Scanner Configuration
    MAX_SCANNER_TICKERS: int = 508  # Maximum tickers to scan in ATR Matrix
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env file
    }


# Global settings instance
settings = Settings()


# Market Data Configuration
MARKET_DATA_PROVIDERS = {
    "primary": "yfinance",
    "fallback": "alpha_vantage"
}

# Technical Indicators Configuration
INDICATORS_CONFIG = {
    "sma_periods": [10, 20, 50, 200],
    "ema_periods": [12, 26],
    "rsi_period": 14,
    "bollinger_period": 20,
    "bollinger_std": 2
}

# Portfolio Configuration
PORTFOLIO_CONFIG = {
    "default_currency": "USD",
    "risk_free_rate": 0.02,  # 2% risk-free rate
    "benchmark_symbol": "SPY"
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"]
    }
} 

# Tastytrade API Configuration
TASTYTRADE_USERNAME: str = os.getenv("TASTYTRADE_USERNAME", "")
TASTYTRADE_PASSWORD: str = os.getenv("TASTYTRADE_PASSWORD", "")
TASTYTRADE_IS_TEST: bool = os.getenv("TASTYTRADE_IS_TEST", "false").lower() == "true" 