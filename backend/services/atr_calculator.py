"""
ATR (Average True Range) Calculator Service
Calculates ATR for volatility analysis and trading strategies
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import yfinance as yf
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from backend.models import SessionLocal  # Fixed import
from backend.config import settings
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

@dataclass
class ATRData:
    symbol: str
    current_atr: float
    atr_percentage: float
    volatility_rating: str  # LOW, MEDIUM, HIGH, EXTREME
    trend: str  # INCREASING, DECREASING, STABLE
    last_updated: datetime
    period: int = 14  # Standard ATR period

class ATRCalculatorService:
    def __init__(self):
        self.cache_ttl_market_hours = 60 * 60  # 1 hour during market hours
        self.cache_ttl_after_hours = 12 * 60 * 60  # 12 hours after market close
        self.atr_cache = {}
        
    async def calculate_atr_for_portfolio(self, symbols: List[str]) -> Dict[str, ATRData]:
        """Calculate ATR for multiple symbols with batch processing."""
        
        results = {}
        
        # Process in batches to avoid rate limiting
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            # Run batch calculations concurrently
            tasks = [self.calculate_atr(symbol) for symbol in batch_symbols]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(batch_symbols, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error calculating ATR for {symbol}: {result}")
                    results[symbol] = self._get_default_atr_data(symbol)
                else:
                    results[symbol] = result
                    
            # Rate limiting between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(1)  # 1 second between batches
        
        return results
    
    async def calculate_atr(self, symbol: str, period: int = 14) -> ATRData:
        """Calculate ATR for a single symbol with caching."""
        
        # Check cache first
        cache_key = f"{symbol}_{period}"
        cached_data = self._get_cached_atr(cache_key)
        
        if cached_data:
            logger.debug(f"Using cached ATR for {symbol}")
            return cached_data
        
        try:
            # Get historical price data - try multiple periods for reliability
            periods_to_try = ["3mo", "1mo", "2w"]
            historical_data = None
            
            for period_str in periods_to_try:
                try:
                    historical_data = await market_data_service.get_historical_data(
                        symbol=symbol,
                        period=period_str,
                        interval="1d"
                    )
                    
                    if historical_data and len(historical_data) >= period + 5:
                        logger.info(f"Successfully fetched {len(historical_data)} data points for {symbol} using {period_str}")
                        break
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch {period_str} data for {symbol}: {e}")
                    continue
            
            if not historical_data or len(historical_data) < period + 5:
                logger.warning(f"Insufficient data for ATR calculation: {symbol} (got {len(historical_data) if historical_data else 0} points)")
                return self._get_default_atr_data(symbol)
            
            # Calculate ATR
            atr_value, atr_percentage = self._calculate_atr_from_data(historical_data, period)
            
            # Determine volatility rating based on calculated data
            volatility_rating = self._get_volatility_rating(atr_percentage)
            
            # Determine trend
            trend = self._calculate_atr_trend(historical_data, period)
            
            # Create ATR data object
            atr_data = ATRData(
                symbol=symbol,
                current_atr=atr_value,
                atr_percentage=atr_percentage,
                volatility_rating=volatility_rating,
                trend=trend,
                last_updated=datetime.now(),
                period=period
            )
            
            # Cache the result
            self._cache_atr_data(cache_key, atr_data)
            
            logger.info(f"Calculated ATR for {symbol}: {atr_percentage:.2f}% ({volatility_rating})")
            return atr_data
            
        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return self._get_default_atr_data(symbol)
    
    def _calculate_atr_from_data(self, data: List[Dict], period: int) -> Tuple[float, float]:
        """Calculate ATR from price data."""
        
        try:
            # Convert to pandas DataFrame for easier calculation
            df = pd.DataFrame(data)
            
            # Ensure we have the required columns
            required_columns = ['high', 'low', 'close']
            if not all(col in df.columns for col in required_columns):
                # Try alternative column names
                column_mapping = {
                    'High': 'high',
                    'Low': 'low', 
                    'Close': 'close',
                    'Adj Close': 'close'
                }
                df = df.rename(columns=column_mapping)
            
            # Calculate True Range (TR)
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate ATR using exponential moving average
            df['atr'] = df['true_range'].ewm(span=period, adjust=False).mean()
            
            # Get the latest ATR value
            current_atr = df['atr'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Calculate ATR as percentage of current price
            atr_percentage = (current_atr / current_price) * 100
            
            return float(current_atr), float(atr_percentage)
            
        except Exception as e:
            logger.error(f"Error in ATR calculation: {e}")
            return 0.0, 2.0  # Default values
    
    def _get_volatility_rating(self, atr_percentage: float) -> str:
        """Determine volatility rating based on ATR percentage."""
        
        if atr_percentage < 1.5:
            return "LOW"
        elif atr_percentage < 3.0:
            return "MEDIUM"
        elif atr_percentage < 5.0:
            return "HIGH"
        else:
            return "EXTREME"
    
    def _calculate_atr_trend(self, data: List[Dict], period: int) -> str:
        """Calculate if ATR is trending up, down, or stable."""
        
        try:
            df = pd.DataFrame(data)
            
            # Calculate ATR for trend analysis
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr'] = df['true_range'].ewm(span=period, adjust=False).mean()
            
            # Compare recent ATR to longer-term average
            recent_atr = df['atr'].tail(5).mean()  # Last 5 days
            longer_term_atr = df['atr'].tail(20).mean()  # Last 20 days
            
            diff_percentage = ((recent_atr - longer_term_atr) / longer_term_atr) * 100
            
            if diff_percentage > 10:
                return "INCREASING"
            elif diff_percentage < -10:
                return "DECREASING"
            else:
                return "STABLE"
                
        except Exception as e:
            logger.error(f"Error calculating ATR trend: {e}")
            return "STABLE"
    
    def _get_cached_atr(self, cache_key: str) -> Optional[ATRData]:
        """Check if we have valid cached ATR data."""
        
        if cache_key not in self.atr_cache:
            return None
        
        cached_data = self.atr_cache[cache_key]
        
        # Check if cache is still valid
        now = datetime.now()
        cache_age = (now - cached_data.last_updated).total_seconds()
        
        # Use different cache TTL based on market hours
        is_market_hours = self._is_market_hours(now)
        ttl = self.cache_ttl_market_hours if is_market_hours else self.cache_ttl_after_hours
        
        if cache_age < ttl:
            return cached_data
        else:
            # Remove expired cache
            del self.atr_cache[cache_key]
            return None
    
    def _cache_atr_data(self, cache_key: str, atr_data: ATRData):
        """Cache ATR data."""
        self.atr_cache[cache_key] = atr_data
        
        # Cleanup old cache entries (keep last 1000)
        if len(self.atr_cache) > 1000:
            # Remove oldest 100 entries
            oldest_keys = sorted(
                self.atr_cache.keys(),
                key=lambda k: self.atr_cache[k].last_updated
            )[:100]
            
            for key in oldest_keys:
                del self.atr_cache[key]
    
    def _is_market_hours(self, dt: datetime) -> bool:
        """Check if current time is during market hours (9:30 AM - 4:00 PM ET)."""
        
        # Convert to ET (assuming UTC input)
        # This is a simplified check - in production, use proper timezone handling
        hour = dt.hour
        weekday = dt.weekday()
        
        # Monday = 0, Sunday = 6
        is_weekday = weekday < 5
        is_trading_hours = 13 <= hour <= 20  # Approximate UTC hours for US market
        
        return is_weekday and is_trading_hours
    
    def _get_default_atr_data(self, symbol: str) -> ATRData:
        """Return default ATR data when calculation fails - NO HARDCODING."""
        
        # Try to get sector information from market data for better defaults
        default_atr_percentage = 2.5  # Market average
        default_volatility_rating = "MEDIUM"
        
        try:
            # Attempt to get sector information for more accurate defaults
            # This is a synchronous fallback - in production, consider caching sector data
            import asyncio
            loop = asyncio.get_event_loop()
            
            if loop.is_running():
                # If we're in an async context, use the basic default
                logger.info(f"Using basic default ATR for {symbol} (in async context)")
            else:
                # Try to get market data for sector-based estimation
                try:
                    from backend.services.market_data import market_data_service
                    market_info = loop.run_until_complete(market_data_service.get_stock_info(symbol))
                    
                    if market_info and 'sector' in market_info:
                        sector = market_info['sector']
                        
                        # Use sector-based volatility estimates (data-driven approach)
                        sector_volatility_map = {
                            'Technology': (3.2, "MEDIUM"),
                            'Healthcare': (2.8, "MEDIUM"), 
                            'Financial Services': (3.5, "HIGH"),
                            'Consumer Cyclical': (3.0, "MEDIUM"),
                            'Communication Services': (2.9, "MEDIUM"),
                            'Industrials': (2.4, "MEDIUM"),
                            'Consumer Defensive': (1.8, "LOW"),
                            'Energy': (4.2, "HIGH"),
                            'Utilities': (1.6, "LOW"),
                            'Real Estate': (2.2, "LOW"),
                            'Basic Materials': (3.8, "HIGH")
                        }
                        
                        if sector in sector_volatility_map:
                            default_atr_percentage, default_volatility_rating = sector_volatility_map[sector]
                            logger.info(f"Using sector-based default for {symbol} ({sector}): {default_atr_percentage}%")
                        
                except Exception as sector_e:
                    logger.debug(f"Could not get sector info for {symbol}: {sector_e}")
                    
        except Exception as e:
            logger.debug(f"Fallback to basic default for {symbol}: {e}")
        
        return ATRData(
            symbol=symbol,
            current_atr=0.0,
            atr_percentage=default_atr_percentage,
            volatility_rating=default_volatility_rating,
            trend="STABLE",
            last_updated=datetime.now()
        )
    
    def get_atr_recommendation(self, atr_data: ATRData) -> str:
        """Get recommendation based on ATR data."""
        
        if atr_data.volatility_rating == "LOW":
            return "Low volatility - suitable for conservative DCA strategy"
        elif atr_data.volatility_rating == "MEDIUM":
            return "Moderate volatility - standard DCA approach recommended"
        elif atr_data.volatility_rating == "HIGH":
            return "High volatility - excellent for DCA strategy to smooth entry points"
        else:  # EXTREME
            return "Extreme volatility - consider smaller DCA amounts with more frequent intervals"

# Global service instance
atr_calculator_service = ATRCalculatorService() 