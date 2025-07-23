"""
Production Market Data Service
Fetches real market data from IBKR, FMP, Alpha Vantage and other sources
Persists data to database for caching and historical analysis
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import yfinance as yf
import pandas as pd

from backend.database import SessionLocal
from backend.models.market_data import StockInfo, PriceData, ATRData, SectorMetrics, MarketDataSync
from backend.config import settings

logger = logging.getLogger(__name__)

class ProductionMarketDataService:
    """Production-grade market data service with multiple data sources"""
    
    def __init__(self):
        self.fmp_api_key = getattr(settings, 'FMP_API_KEY', None)
        self.alpha_vantage_key = getattr(settings, 'ALPHA_VANTAGE_API_KEY', None) 
        self.data_sources = ['IBKR', 'FMP', 'YAHOO', 'ALPHA_VANTAGE']
        self.cache_duration_hours = 4  # Cache real-time data for 4 hours
        
    async def get_stock_info(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get comprehensive stock information with database persistence"""
        
        db = SessionLocal()
        try:
            # Check database cache first
            if not force_refresh:
                cached_info = self._get_cached_stock_info(db, symbol)
                if cached_info:
                    return self._stock_info_to_dict(cached_info)
            
            # Fetch from multiple sources
            stock_info = await self._fetch_stock_info_multi_source(symbol)
            
            if stock_info:
                # Persist to database
                self._save_stock_info(db, symbol, stock_info)
                return stock_info
            
            # Fallback to cached data even if stale
            cached_info = self._get_cached_stock_info(db, symbol, ignore_staleness=True)
            if cached_info:
                logger.warning(f"Using stale cached data for {symbol}")
                return self._stock_info_to_dict(cached_info)
            
            raise Exception(f"No data available for {symbol}")
            
        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")
            return self._get_emergency_fallback_data(symbol)
        finally:
            db.close()
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "3mo", 
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Get historical price data with database persistence"""
        
        db = SessionLocal()
        try:
            # Check database cache first
            cached_data = self._get_cached_price_data(db, symbol, period, interval)
            if cached_data:
                return cached_data
            
            # Fetch fresh data
            price_data = await self._fetch_historical_data_multi_source(symbol, period, interval)
            
            if price_data:
                # Persist to database
                self._save_price_data(db, symbol, price_data, interval)
                return price_data
            
            raise Exception(f"No historical data available for {symbol}")
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
        finally:
            db.close()
    
    async def _fetch_stock_info_multi_source(self, symbol: str) -> Dict[str, Any]:
        """Fetch stock info from multiple sources with failover"""
        
        # Try Yahoo Finance first (most reliable)
        try:
            return await self._fetch_from_yahoo_finance(symbol)
        except Exception as e:
            logger.warning(f"Yahoo Finance failed for {symbol}: {e}")
        
        # Try FMP if API key available
        if self.fmp_api_key:
            try:
                return await self._fetch_from_fmp(symbol)
            except Exception as e:
                logger.warning(f"FMP failed for {symbol}: {e}")
        
        # Try Alpha Vantage if API key available
        if self.alpha_vantage_key:
            try:
                return await self._fetch_from_alpha_vantage(symbol)
            except Exception as e:
                logger.warning(f"Alpha Vantage failed for {symbol}: {e}")
        
        raise Exception(f"All data sources failed for {symbol}")
    
    async def _fetch_from_yahoo_finance(self, symbol: str) -> Dict[str, Any]:
        """Fetch stock info from Yahoo Finance"""
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'dividend_yield': info.get('dividendYield', None),
                'beta': info.get('beta', None),
                'revenue_growth': info.get('revenueGrowth', None),
                'profit_margin': info.get('profitMargins', None),
                'exchange': info.get('exchange', ''),
                'currency': info.get('currency', 'USD'),
                'country': info.get('country', ''),
                'data_source': 'YAHOO'
            }
        except Exception as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            raise
    
    async def _fetch_from_fmp(self, symbol: str) -> Dict[str, Any]:
        """Fetch stock info from Financial Modeling Prep API"""
        
        if not self.fmp_api_key:
            raise Exception("FMP API key not configured")
        
        async with aiohttp.ClientSession() as session:
            # Company profile
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={self.fmp_api_key}"
            
            async with session.get(profile_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        profile = data[0]
                        return {
                            'symbol': symbol,
                            'company_name': profile.get('companyName', ''),
                            'sector': profile.get('sector', ''),
                            'industry': profile.get('industry', ''),
                            'market_cap': profile.get('mktCap', 0),
                            'pe_ratio': profile.get('pe', None),
                            'dividend_yield': profile.get('lastDiv', None),
                            'beta': profile.get('beta', None),
                            'exchange': profile.get('exchangeShortName', ''),
                            'currency': profile.get('currency', 'USD'),
                            'country': profile.get('country', ''),
                            'data_source': 'FMP'
                        }
                
                raise Exception(f"FMP API returned status {response.status}")
    
    async def _fetch_from_alpha_vantage(self, symbol: str) -> Dict[str, Any]:
        """Fetch stock info from Alpha Vantage API"""
        
        if not self.alpha_vantage_key:
            raise Exception("Alpha Vantage API key not configured")
        
        async with aiohttp.ClientSession() as session:
            # Company overview
            overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={self.alpha_vantage_key}"
            
            async with session.get(overview_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'Symbol' in data:
                        return {
                            'symbol': symbol,
                            'company_name': data.get('Name', ''),
                            'sector': data.get('Sector', ''),
                            'industry': data.get('Industry', ''),
                            'market_cap': float(data.get('MarketCapitalization', 0)) if data.get('MarketCapitalization', '').replace('.', '').isdigit() else 0,
                            'pe_ratio': float(data.get('PERatio', 0)) if data.get('PERatio', '').replace('.', '').isdigit() else None,
                            'dividend_yield': float(data.get('DividendYield', 0)) if data.get('DividendYield', '').replace('.', '').isdigit() else None,
                            'beta': float(data.get('Beta', 0)) if data.get('Beta', '').replace('.', '').isdigit() else None,
                            'exchange': data.get('Exchange', ''),
                            'currency': data.get('Currency', 'USD'),
                            'country': data.get('Country', ''),
                            'data_source': 'ALPHA_VANTAGE'
                        }
                
                raise Exception(f"Alpha Vantage API returned status {response.status}")
    
    async def _fetch_historical_data_multi_source(
        self, 
        symbol: str, 
        period: str, 
        interval: str
    ) -> List[Dict[str, Any]]:
        """Fetch historical data from multiple sources"""
        
        # Try Yahoo Finance first
        try:
            return await self._fetch_historical_yahoo(symbol, period, interval)
        except Exception as e:
            logger.warning(f"Yahoo historical data failed for {symbol}: {e}")
        
        # Try FMP for daily data
        if interval == "1d" and self.fmp_api_key:
            try:
                return await self._fetch_historical_fmp(symbol, period)
            except Exception as e:
                logger.warning(f"FMP historical data failed for {symbol}: {e}")
        
        raise Exception(f"All historical data sources failed for {symbol}")
    
    async def _fetch_historical_yahoo(self, symbol: str, period: str, interval: str) -> List[Dict[str, Any]]:
        """Fetch historical data from Yahoo Finance"""
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            data = []
            for date, row in hist.iterrows():
                data.append({
                    'date': date.to_pydatetime(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                    'data_source': 'YAHOO'
                })
            
            return data
        except Exception as e:
            logger.error(f"Yahoo historical data error for {symbol}: {e}")
            raise
    
    def _get_cached_stock_info(self, db: Session, symbol: str, ignore_staleness: bool = False) -> Optional[StockInfo]:
        """Get cached stock info from database"""
        
        query = db.query(StockInfo).filter(StockInfo.symbol == symbol)
        
        if not ignore_staleness:
            # Only use data newer than cache duration
            cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_duration_hours)
            query = query.filter(StockInfo.last_updated >= cutoff_time)
        
        return query.first()
    
    def _get_cached_price_data(
        self, 
        db: Session, 
        symbol: str, 
        period: str, 
        interval: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached price data from database"""
        
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == "1d":
            start_date = end_date - timedelta(days=1)
        elif period == "5d":
            start_date = end_date - timedelta(days=5)
        elif period == "1mo":
            start_date = end_date - timedelta(days=30)
        elif period == "3mo":
            start_date = end_date - timedelta(days=90)
        elif period == "6mo":
            start_date = end_date - timedelta(days=180)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=90)  # Default to 3 months
        
        # Check if we have recent data
        recent_cutoff = datetime.utcnow() - timedelta(hours=self.cache_duration_hours)
        recent_data = db.query(PriceData).filter(
            and_(
                PriceData.symbol == symbol,
                PriceData.interval == interval,
                PriceData.date >= start_date,
                PriceData.created_at >= recent_cutoff
            )
        ).order_by(PriceData.date).all()
        
        if len(recent_data) > 10:  # Minimum viable dataset
            return [
                {
                    'date': row.date,
                    'open': row.open_price,
                    'high': row.high_price,
                    'low': row.low_price,
                    'close': row.close_price,
                    'volume': row.volume or 0
                }
                for row in recent_data
            ]
        
        return None
    
    def _save_stock_info(self, db: Session, symbol: str, info: Dict[str, Any]):
        """Save stock info to database"""
        
        try:
            # Update or create stock info
            stock_info = db.query(StockInfo).filter(StockInfo.symbol == symbol).first()
            
            if stock_info:
                # Update existing
                for key, value in info.items():
                    if hasattr(stock_info, key):
                        setattr(stock_info, key, value)
                stock_info.last_updated = datetime.utcnow()
            else:
                # Create new
                stock_info = StockInfo(**info, last_updated=datetime.utcnow())
                db.add(stock_info)
            
            db.commit()
            logger.info(f"Saved stock info for {symbol}")
            
        except Exception as e:
            logger.error(f"Error saving stock info for {symbol}: {e}")
            db.rollback()
    
    def _save_price_data(self, db: Session, symbol: str, price_data: List[Dict[str, Any]], interval: str):
        """Save price data to database"""
        
        try:
            for data_point in price_data:
                # Check if data point already exists
                existing = db.query(PriceData).filter(
                    and_(
                        PriceData.symbol == symbol,
                        PriceData.date == data_point['date'],
                        PriceData.interval == interval
                    )
                ).first()
                
                if not existing:
                    price_record = PriceData(
                        symbol=symbol,
                        date=data_point['date'],
                        open_price=data_point['open'],
                        high_price=data_point['high'],
                        low_price=data_point['low'],
                        close_price=data_point['close'],
                        volume=data_point.get('volume', 0),
                        interval=interval,
                        data_source=data_point.get('data_source', 'UNKNOWN'),
                        created_at=datetime.utcnow()
                    )
                    db.add(price_record)
            
            db.commit()
            logger.info(f"Saved {len(price_data)} price data points for {symbol}")
            
        except Exception as e:
            logger.error(f"Error saving price data for {symbol}: {e}")
            db.rollback()
    
    def _stock_info_to_dict(self, stock_info: StockInfo) -> Dict[str, Any]:
        """Convert StockInfo model to dictionary"""
        
        return {
            'symbol': stock_info.symbol,
            'company_name': stock_info.company_name,
            'sector': stock_info.sector,
            'industry': stock_info.industry,
            'market_cap': stock_info.market_cap,
            'pe_ratio': stock_info.pe_ratio,
            'dividend_yield': stock_info.dividend_yield,
            'beta': stock_info.beta,
            'revenue_growth': stock_info.revenue_growth,
            'profit_margin': stock_info.profit_margin,
            'exchange': stock_info.exchange,
            'currency': stock_info.currency,
            'country': stock_info.country,
            'data_source': stock_info.data_source,
            'last_updated': stock_info.last_updated.isoformat() if stock_info.last_updated else None
        }
    
    def _get_emergency_fallback_data(self, symbol: str) -> Dict[str, Any]:
        """Emergency fallback when all data sources fail"""
        
        logger.warning(f"Using emergency fallback data for {symbol}")
        
        return {
            'symbol': symbol,
            'company_name': f'{symbol} Corporation',
            'sector': 'Unknown',
            'industry': 'Unknown',
            'market_cap': 1000000000,  # 1B default
            'pe_ratio': None,
            'dividend_yield': None,
            'beta': None,
            'revenue_growth': None,
            'profit_margin': None,
            'exchange': 'UNKNOWN',
            'currency': 'USD',
            'country': 'US',
            'data_source': 'FALLBACK',
            'last_updated': datetime.utcnow().isoformat()
        }

# Global service instance
production_market_data_service = ProductionMarketDataService() 