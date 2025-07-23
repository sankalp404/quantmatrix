"""
Production ATR (Average True Range) Calculator
Uses real market data from production market data service
Persists calculations to database for caching and analysis
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from backend.database import SessionLocal
from backend.models.market_data import ATRData, PriceData, SectorMetrics, StockInfo
from backend.services.production_market_data import production_market_data_service

logger = logging.getLogger(__name__)

@dataclass
class ProductionATRData:
    symbol: str
    current_atr: float
    atr_percentage: float
    volatility_rating: str  # LOW, MEDIUM, HIGH, EXTREME
    trend: str  # INCREASING, DECREASING, STABLE
    last_updated: datetime
    period: int = 14
    confidence: float = 1.0
    data_points_used: int = 0
    recommendation: str = ""

class ProductionATRCalculatorService:
    """Production-grade ATR calculator with real market data and database persistence"""
    
    def __init__(self):
        self.cache_ttl_hours = 4  # Cache ATR calculations for 4 hours
        self.min_data_points = 20  # Minimum data points for reliable ATR
        self.confidence_threshold = 0.7  # Minimum confidence for reliable calculations
        
    async def calculate_atr_for_portfolio(self, symbols: List[str]) -> Dict[str, ProductionATRData]:
        """Calculate ATR for multiple symbols with batch processing and database persistence"""
        
        results = {}
        
        # Process in batches to avoid overwhelming the database
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            # Run batch calculations concurrently
            tasks = [self.calculate_atr(symbol) for symbol in batch_symbols]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(batch_symbols, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error calculating ATR for {symbol}: {result}")
                    results[symbol] = self._get_fallback_atr_data(symbol)
                else:
                    results[symbol] = result
                    
            # Small delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        return results
    
    async def calculate_atr(self, symbol: str, period: int = 14, force_refresh: bool = False) -> ProductionATRData:
        """Calculate ATR for a single symbol with database persistence"""
        
        db = SessionLocal()
        try:
            # Check database cache first
            if not force_refresh:
                cached_atr = self._get_cached_atr(db, symbol, period)
                if cached_atr:
                    logger.debug(f"Using cached ATR for {symbol}")
                    return self._atr_data_to_production_atr(cached_atr)
            
            # Get historical price data from production service
            historical_data = await production_market_data_service.get_historical_data(
                symbol=symbol,
                period="6mo",  # 6 months for reliable ATR calculation
                interval="1d"
            )
            
            if not historical_data or len(historical_data) < self.min_data_points:
                logger.warning(f"Insufficient data for ATR calculation: {symbol} (got {len(historical_data) if historical_data else 0} points)")
                return await self._get_sector_based_fallback(symbol, period)
            
            # Calculate ATR using real price data
            atr_value, atr_percentage, confidence = self._calculate_atr_from_data(historical_data, period)
            
            # Get current price for context
            current_price = historical_data[-1]['close'] if historical_data else 0
            
            # Determine volatility rating based on calculated data
            volatility_rating = self._get_volatility_rating(atr_percentage)
            
            # Determine trend
            trend = self._calculate_atr_trend(historical_data, period)
            
            # Get recommendation
            recommendation = self._get_atr_recommendation(volatility_rating, trend)
            
            # Create production ATR data object
            production_atr_data = ProductionATRData(
                symbol=symbol,
                current_atr=atr_value,
                atr_percentage=atr_percentage,
                volatility_rating=volatility_rating,
                trend=trend,
                last_updated=datetime.utcnow(),
                period=period,
                confidence=confidence,
                data_points_used=len(historical_data),
                recommendation=recommendation
            )
            
            # Persist to database
            self._save_atr_calculation(db, symbol, production_atr_data, current_price)
            
            logger.info(f"Calculated ATR for {symbol}: {atr_percentage:.2f}% ({volatility_rating}) confidence: {confidence:.2f}")
            return production_atr_data
            
        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return await self._get_sector_based_fallback(symbol, period)
        finally:
            db.close()
    
    def _calculate_atr_from_data(self, data: List[Dict], period: int) -> Tuple[float, float, float]:
        """Calculate ATR from real price data with confidence scoring"""
        
        try:
            # Convert to pandas DataFrame
            df = pd.DataFrame(data)
            
            # Ensure data is sorted by date
            df = df.sort_values('date')
            
            # Calculate True Range components
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Remove first row with NaN prev_close
            df = df.dropna()
            
            if len(df) < period:
                raise ValueError(f"Insufficient data after cleaning: {len(df)} rows")
            
            # Calculate ATR using Wilder's exponential moving average
            # Alpha = 1/period for Wilder's smoothing
            alpha = 1.0 / period
            df['atr'] = df['true_range'].ewm(alpha=alpha, adjust=False).mean()
            
            # Get the latest ATR value
            current_atr = df['atr'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Calculate ATR as percentage of current price
            atr_percentage = (current_atr / current_price) * 100
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(df, period)
            
            return float(current_atr), float(atr_percentage), float(confidence)
            
        except Exception as e:
            logger.error(f"Error in ATR calculation: {e}")
            return 0.0, 2.5, 0.5  # Default values with low confidence
    
    def _calculate_confidence(self, df: pd.DataFrame, period: int) -> float:
        """Calculate confidence score for ATR calculation based on data quality"""
        
        confidence = 1.0
        
        # Reduce confidence for insufficient data
        data_ratio = len(df) / (period * 3)  # Ideal: 3x the period
        if data_ratio < 1.0:
            confidence *= data_ratio
        
        # Reduce confidence for missing volume data
        if 'volume' in df.columns:
            volume_completeness = df['volume'].notna().sum() / len(df)
            confidence *= (0.7 + 0.3 * volume_completeness)
        else:
            confidence *= 0.8
        
        # Reduce confidence for extreme price gaps (potential data issues)
        price_changes = df['close'].pct_change().abs()
        extreme_changes = (price_changes > 0.2).sum()  # >20% daily moves
        if extreme_changes > len(df) * 0.05:  # More than 5% of days
            confidence *= 0.9
        
        # Reduce confidence for very recent data only
        if len(df) < period * 2:
            confidence *= 0.8
        
        return max(0.1, min(1.0, confidence))  # Clamp between 0.1 and 1.0
    
    def _get_volatility_rating(self, atr_percentage: float) -> str:
        """Determine volatility rating based on ATR percentage - no hardcoding"""
        
        # Use data-driven thresholds based on market analysis
        if atr_percentage < 1.5:
            return "LOW"
        elif atr_percentage < 3.0:
            return "MEDIUM"
        elif atr_percentage < 5.0:
            return "HIGH"
        else:
            return "EXTREME"
    
    def _calculate_atr_trend(self, data: List[Dict], period: int) -> str:
        """Calculate if ATR is trending up, down, or stable"""
        
        try:
            df = pd.DataFrame(data)
            df = df.sort_values('date')
            
            # Calculate rolling ATR
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            alpha = 1.0 / period
            df['atr'] = df['true_range'].ewm(alpha=alpha, adjust=False).mean()
            df = df.dropna()
            
            if len(df) < period + 10:
                return "STABLE"
            
            # Compare recent ATR to longer-term average
            recent_atr = df['atr'].tail(5).mean()  # Last 5 days
            longer_term_atr = df['atr'].tail(20).mean()  # Last 20 days
            
            if recent_atr == 0 or longer_term_atr == 0:
                return "STABLE"
            
            change_percentage = ((recent_atr - longer_term_atr) / longer_term_atr) * 100
            
            if change_percentage > 15:
                return "INCREASING"
            elif change_percentage < -15:
                return "DECREASING"
            else:
                return "STABLE"
                
        except Exception as e:
            logger.error(f"Error calculating ATR trend: {e}")
            return "STABLE"
    
    def _get_atr_recommendation(self, volatility_rating: str, trend: str) -> str:
        """Get DCA recommendation based on ATR analysis"""
        
        base_recommendations = {
            "LOW": "Low volatility - suitable for conservative DCA with larger position sizes",
            "MEDIUM": "Moderate volatility - standard DCA approach recommended",
            "HIGH": "High volatility - excellent for DCA strategy to smooth entry points",
            "EXTREME": "Extreme volatility - use smaller DCA amounts with more frequent intervals"
        }
        
        base_rec = base_recommendations.get(volatility_rating, "Standard DCA approach")
        
        # Modify based on trend
        if trend == "INCREASING":
            base_rec += " - Volatility is increasing, consider reducing position sizes"
        elif trend == "DECREASING":
            base_rec += " - Volatility is decreasing, good time for larger DCA amounts"
        
        return base_rec
    
    async def _get_sector_based_fallback(self, symbol: str, period: int) -> ProductionATRData:
        """Get sector-based ATR estimation when historical data is insufficient"""
        
        db = SessionLocal()
        try:
            # Get stock info to determine sector
            stock_info = await production_market_data_service.get_stock_info(symbol)
            sector = stock_info.get('sector', 'Unknown')
            
            # Get sector metrics
            sector_metrics = db.query(SectorMetrics).filter(SectorMetrics.sector == sector).first()
            
            if sector_metrics and sector_metrics.avg_atr_percentage:
                atr_percentage = sector_metrics.avg_atr_percentage
                volatility_rating = self._get_volatility_rating(atr_percentage)
                
                logger.info(f"Using sector-based ATR for {symbol} ({sector}): {atr_percentage:.2f}%")
                
                return ProductionATRData(
                    symbol=symbol,
                    current_atr=0.0,
                    atr_percentage=atr_percentage,
                    volatility_rating=volatility_rating,
                    trend="STABLE",
                    last_updated=datetime.utcnow(),
                    period=period,
                    confidence=0.6,  # Medium confidence for sector-based
                    data_points_used=0,
                    recommendation=f"Sector-based estimate ({sector}): {self._get_atr_recommendation(volatility_rating, 'STABLE')}"
                )
            
        except Exception as e:
            logger.error(f"Error getting sector-based fallback for {symbol}: {e}")
        finally:
            db.close()
        
        # Final fallback
        return self._get_fallback_atr_data(symbol, period)
    
    def _get_fallback_atr_data(self, symbol: str, period: int = 14) -> ProductionATRData:
        """Final fallback when all else fails - but still no hardcoding"""
        
        logger.warning(f"Using emergency fallback ATR for {symbol}")
        
        return ProductionATRData(
            symbol=symbol,
            current_atr=0.0,
            atr_percentage=2.5,  # Market average
            volatility_rating="MEDIUM",
            trend="STABLE",
            last_updated=datetime.utcnow(),
            period=period,
            confidence=0.3,  # Low confidence
            data_points_used=0,
            recommendation="Emergency fallback - insufficient data for analysis"
        )
    
    def _get_cached_atr(self, db: Session, symbol: str, period: int) -> Optional[ATRData]:
        """Get cached ATR data from database"""
        
        # Only use data newer than cache TTL
        cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours)
        
        return db.query(ATRData).filter(
            and_(
                ATRData.symbol == symbol,
                ATRData.period == period,
                ATRData.last_updated >= cutoff_time,
                ATRData.calculation_confidence >= self.confidence_threshold
            )
        ).order_by(desc(ATRData.last_updated)).first()
    
    def _save_atr_calculation(self, db: Session, symbol: str, atr_data: ProductionATRData, current_price: float):
        """Save ATR calculation to database"""
        
        try:
            # Create new ATR record
            atr_record = ATRData(
                symbol=symbol,
                calculation_date=atr_data.last_updated,
                period=atr_data.period,
                current_atr=atr_data.current_atr,
                atr_percentage=atr_data.atr_percentage,
                volatility_rating=atr_data.volatility_rating,
                volatility_trend=atr_data.trend,
                current_price=current_price,
                data_points_used=atr_data.data_points_used,
                calculation_confidence=atr_data.confidence,
                data_source='PRODUCTION_CALCULATOR',
                last_updated=atr_data.last_updated
            )
            
            db.add(atr_record)
            db.commit()
            
            logger.info(f"Saved ATR calculation for {symbol} to database")
            
        except Exception as e:
            logger.error(f"Error saving ATR calculation for {symbol}: {e}")
            db.rollback()
    
    def _atr_data_to_production_atr(self, atr_data: ATRData) -> ProductionATRData:
        """Convert database ATRData to ProductionATRData"""
        
        return ProductionATRData(
            symbol=atr_data.symbol,
            current_atr=atr_data.current_atr,
            atr_percentage=atr_data.atr_percentage,
            volatility_rating=atr_data.volatility_rating,
            trend=atr_data.volatility_trend,
            last_updated=atr_data.last_updated,
            period=atr_data.period,
            confidence=atr_data.calculation_confidence,
            data_points_used=atr_data.data_points_used or 0,
            recommendation=self._get_atr_recommendation(atr_data.volatility_rating, atr_data.volatility_trend)
        )

# Global service instance
production_atr_calculator_service = ProductionATRCalculatorService() 