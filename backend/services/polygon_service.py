"""
Polygon.io Premium Market Data Service
Production-grade integration with comprehensive API usage tracking.
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import json
from decimal import Decimal

from backend.config import settings
from backend.models import SessionLocal
from backend.models.market_analysis import PolygonApiUsage, MarketDataProvider

logger = logging.getLogger(__name__)

class PolygonService:
    """Production-grade Polygon.io service with comprehensive tracking."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'POLYGON_API_KEY', None)
        self.base_url = "https://api.polygon.io"
        self.is_premium = bool(self.api_key)
        self.session = None
        
        # Rate limiting for different plan tiers
        self.rate_limits = {
            'free': {'per_minute': 5, 'per_day': 500},
            'starter': {'per_minute': 100, 'per_day': 50000},
            'developer': {'per_minute': 500, 'per_day': 100000},
            'advanced': {'per_minute': 1000, 'per_day': 500000}
        }
        
        self.current_plan = 'advanced' if self.is_premium else 'free'
        self.usage_tracker = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'QuantMatrix/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        if not self.is_premium:
            return False  # Don't use Polygon on free tier
            
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        self.usage_tracker = {
            timestamp: endpoint for timestamp, endpoint in self.usage_tracker.items()
            if timestamp > minute_ago
        }
        
        # Check current minute usage
        current_minute_usage = len(self.usage_tracker)
        limit = self.rate_limits[self.current_plan]['per_minute']
        
        return current_minute_usage < limit
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Tuple[Dict, Dict]:
        """Make tracked API request to Polygon.io."""
        if not self.is_premium:
            raise ValueError("Polygon.io requires premium API key")
            
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded for Polygon.io")
            await asyncio.sleep(1)
            
        start_time = time.time()
        
        # Add API key to params
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                response_time = (time.time() - start_time) * 1000
                
                # Track usage
                self.usage_tracker[time.time()] = endpoint
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Log usage to database
                    await self._log_api_usage(
                        endpoint, 
                        response_time, 
                        response.status,
                        data.get('resultsCount', 0)
                    )
                    
                    return data, {
                        'status_code': response.status,
                        'response_time_ms': response_time,
                        'rate_limit_remaining': response.headers.get('X-RateLimit-Remaining'),
                        'success': True
                    }
                else:
                    logger.error(f"Polygon API error {response.status}: {await response.text()}")
                    return {}, {
                        'status_code': response.status,
                        'response_time_ms': response_time,
                        'success': False,
                        'error': await response.text()
                    }
                    
        except Exception as e:
            logger.error(f"Polygon API request failed: {e}")
            return {}, {
                'success': False,
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            }
    
    async def _log_api_usage(self, endpoint: str, response_time: float, status_code: int, data_points: int):
        """Log API usage for tracking and optimization."""
        try:
            db = SessionLocal()
            
            usage_record = PolygonApiUsage(
                endpoint=endpoint,
                response_time_ms=response_time,
                status_code=status_code,
                data_points_returned=data_points,
                data_quality_score=10.0 if status_code == 200 else 0.0
            )
            
            db.add(usage_record)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"Error logging API usage: {e}")
    
    async def get_real_time_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote data for a symbol."""
        if not self.is_premium:
            return None
            
        endpoint = f"/v2/last/trade/{symbol}"
        data, metadata = await self._make_request(endpoint)
        
        if metadata['success'] and data.get('results'):
            result = data['results']
            return {
                'symbol': symbol,
                'price': result.get('p'),
                'size': result.get('s'),
                'timestamp': result.get('t'),
                'exchange': result.get('x'),
                'conditions': result.get('c', []),
                'source': 'polygon_realtime'
            }
        return None
    
    async def get_aggregates(self, symbol: str, multiplier: int = 1, timespan: str = 'day', 
                           from_date: str = None, to_date: str = None, limit: int = 120) -> List[Dict]:
        """Get aggregate data (OHLCV) for a symbol."""
        if not self.is_premium:
            return []
            
        if not from_date:
            from_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
            
        endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        params = {
            'adjusted': 'true',
            'sort': 'desc',
            'limit': limit
        }
        
        data, metadata = await self._make_request(endpoint, params)
        
        if metadata['success'] and data.get('results'):
            return [
                {
                    'symbol': symbol,
                    'timestamp': result.get('t'),
                    'date': datetime.fromtimestamp(result.get('t', 0) / 1000).strftime('%Y-%m-%d'),
                    'open': result.get('o'),
                    'high': result.get('h'),
                    'low': result.get('l'),
                    'close': result.get('c'),
                    'volume': result.get('v'),
                    'vwap': result.get('vw'),
                    'transactions': result.get('n'),
                    'source': 'polygon_premium'
                }
                for result in data['results']
            ]
        return []
    
    async def get_ticker_details(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive ticker details."""
        if not self.is_premium:
            return None
            
        endpoint = f"/v3/reference/tickers/{symbol}"
        data, metadata = await self._make_request(endpoint)
        
        if metadata['success'] and data.get('results'):
            result = data['results']
            return {
                'symbol': result.get('ticker'),
                'name': result.get('name'),
                'market_cap': result.get('market_cap'),
                'sector': result.get('sic_description'),
                'industry': result.get('industry'),
                'description': result.get('description'),
                'homepage_url': result.get('homepage_url'),
                'total_employees': result.get('total_employees'),
                'list_date': result.get('list_date'),
                'currency': result.get('currency_name'),
                'source': 'polygon_premium'
            }
        return None
    
    async def get_technical_indicators(self, symbol: str, indicator: str = 'sma', 
                                     window: int = 50, limit: int = 120) -> List[Dict]:
        """Get technical indicators from Polygon."""
        if not self.is_premium:
            return []
            
        endpoint = f"/v1/indicators/{indicator}/{symbol}"
        
        params = {
            'timestamp.gte': (datetime.now() - timedelta(days=limit)).strftime('%Y-%m-%d'),
            'window': window,
            'series_type': 'close',
            'order': 'desc',
            'limit': limit
        }
        
        data, metadata = await self._make_request(endpoint, params)
        
        if metadata['success'] and data.get('results'):
            return [
                {
                    'symbol': symbol,
                    'timestamp': result.get('timestamp'),
                    'indicator': indicator,
                    'value': result.get('value'),
                    'window': window,
                    'source': 'polygon_premium'
                }
                for result in data.get('results', {}).get('values', [])
            ]
        return []
    
    async def get_options_chain(self, underlying_symbol: str, expiration_date: str = None) -> List[Dict]:
        """Get options chain data."""
        if not self.is_premium:
            return []
            
        endpoint = "/v3/reference/options/contracts"
        
        params = {
            'underlying_ticker': underlying_symbol,
            'limit': 1000
        }
        
        if expiration_date:
            params['expiration_date'] = expiration_date
            
        data, metadata = await self._make_request(endpoint, params)
        
        if metadata['success'] and data.get('results'):
            return [
                {
                    'symbol': result.get('ticker'),
                    'underlying_symbol': result.get('underlying_ticker'),
                    'contract_type': result.get('contract_type'),
                    'expiration_date': result.get('expiration_date'),
                    'strike_price': result.get('strike_price'),
                    'shares_per_contract': result.get('shares_per_contract'),
                    'source': 'polygon_premium'
                }
                for result in data['results']
            ]
        return []
    
    async def get_market_status(self) -> Dict:
        """Get current market status."""
        if not self.is_premium:
            return {}
            
        endpoint = "/v1/marketstatus/now"
        data, metadata = await self._make_request(endpoint)
        
        if metadata['success']:
            return {
                'market': data.get('market', 'unknown'),
                'serverTime': data.get('serverTime'),
                'exchanges': data.get('exchanges', {}),
                'currencies': data.get('currencies', {}),
                'source': 'polygon_premium'
            }
        return {}
    
    async def get_comprehensive_stock_data(self, symbol: str) -> Dict:
        """Get comprehensive stock data combining multiple endpoints."""
        if not self.is_premium:
            return {}
            
        logger.info(f"🔄 Fetching comprehensive Polygon data for {symbol}")
        
        # Run all requests concurrently
        tasks = [
            self.get_real_time_quote(symbol),
            self.get_ticker_details(symbol),
            self.get_aggregates(symbol, limit=60),
            self.get_technical_indicators(symbol, 'sma', 20),
            self.get_technical_indicators(symbol, 'sma', 50),
            self.get_technical_indicators(symbol, 'rsi', 14)
        ]
        
        try:
            quote, details, aggregates, sma20, sma50, rsi = await asyncio.gather(*tasks)
            
            # Combine all data
            comprehensive_data = {
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat(),
                'quote': quote,
                'details': details,
                'price_history': aggregates,
                'technical_indicators': {
                    'sma_20': sma20,
                    'sma_50': sma50,
                    'rsi_14': rsi
                },
                'data_quality': 'premium',
                'source': 'polygon_comprehensive'
            }
            
            logger.info(f"✅ Retrieved comprehensive Polygon data for {symbol}")
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive data for {symbol}: {e}")
            return {}
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics."""
        now = time.time()
        minute_ago = now - 60
        
        current_minute_usage = len([
            t for t in self.usage_tracker.keys() if t > minute_ago
        ])
        
        return {
            'is_premium': self.is_premium,
            'current_plan': self.current_plan,
            'usage_last_minute': current_minute_usage,
            'rate_limit_per_minute': self.rate_limits[self.current_plan]['per_minute'],
            'usage_percentage': (current_minute_usage / self.rate_limits[self.current_plan]['per_minute']) * 100,
            'api_key_configured': bool(self.api_key)
        }

# Global service instance
polygon_service = PolygonService() 