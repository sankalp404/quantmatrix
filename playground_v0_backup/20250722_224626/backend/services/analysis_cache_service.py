"""
Analysis Cache Service for Production-Level Market Analysis
Manages caching of heavy analysis results to avoid re-computation.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models import SessionLocal
from backend.models.market_analysis import (
    MarketAnalysisCache, 
    StockUniverse, 
    ScanHistory, 
    PolygonApiUsage, 
    MarketDataProvider
)

logger = logging.getLogger(__name__)

class AnalysisCacheService:
    """Production-grade caching service for market analysis results."""
    
    def __init__(self):
        self.cache_durations = {
            'atr_matrix': timedelta(minutes=30),      # ATR analysis valid for 30 min
            'company_profile': timedelta(hours=24),   # Company info valid for 1 day
            'technical_analysis': timedelta(minutes=15), # Technical data valid for 15 min
            'news_sentiment': timedelta(hours=6),     # News sentiment valid for 6 hours
            'market_sentiment': timedelta(hours=4),   # Market sentiment valid for 4 hours
        }
    
    def get_cached_analysis(self, symbol: str, analysis_type: str, db: Session) -> Optional[Dict]:
        """Get cached analysis if valid and not expired."""
        try:
            now = datetime.utcnow()
            
            # Query for valid cached analysis
            cached = db.query(MarketAnalysisCache).filter(
                and_(
                    MarketAnalysisCache.symbol == symbol.upper(),
                    MarketAnalysisCache.analysis_type == analysis_type,
                    MarketAnalysisCache.expiry_timestamp > now,
                    MarketAnalysisCache.is_valid == True
                )
            ).order_by(MarketAnalysisCache.analysis_timestamp.desc()).first()
            
            if cached:
                logger.info(f"✅ Cache HIT for {symbol} {analysis_type} (age: {(now - cached.analysis_timestamp).total_seconds():.1f}s)")
                
                # Return comprehensive cached data
                return {
                    'symbol': cached.symbol,
                    'analysis_type': cached.analysis_type,
                    'cache_timestamp': cached.analysis_timestamp,
                    'expiry_timestamp': cached.expiry_timestamp,
                    'current_price': cached.current_price,
                    'market_cap': cached.market_cap,
                    'sector': cached.sector,
                    'industry': cached.industry,
                    'fund_membership': cached.fund_membership,
                    'atr_value': cached.atr_value,
                    'atr_distance': cached.atr_distance,
                    'atr_percent': cached.atr_percent,
                    'rsi': cached.rsi,
                    'ma_alignment': cached.ma_alignment,
                    'confidence_score': cached.confidence_score,
                    'entry_signal': cached.entry_signal,
                    'stop_loss_price': cached.stop_loss_price,
                    'target_prices': cached.target_prices,
                    'risk_reward_ratio': cached.risk_reward_ratio,
                    'company_synopsis': cached.company_synopsis,
                    'analyst_rating': cached.analyst_rating,
                    'analyst_target': cached.analyst_target,
                    'news_sentiment': cached.news_sentiment,
                    'raw_analysis': cached.raw_analysis,
                    'cache_hit': True
                }
            
            logger.info(f"❌ Cache MISS for {symbol} {analysis_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for {symbol}: {e}")
            return None
    
    def cache_analysis(self, symbol: str, analysis_type: str, analysis_data: Dict, db: Session) -> bool:
        """Cache comprehensive analysis results for future use."""
        try:
            now = datetime.utcnow()
            expiry = now + self.cache_durations.get(analysis_type, timedelta(hours=1))
            
            # Create cache record
            cache_record = MarketAnalysisCache(
                symbol=symbol.upper(),
                analysis_type=analysis_type,
                analysis_timestamp=now,
                expiry_timestamp=expiry,
                current_price=analysis_data.get('current_price'),
                market_cap=analysis_data.get('market_cap'),
                sector=analysis_data.get('sector'),
                industry=analysis_data.get('industry'),
                fund_membership=analysis_data.get('fund_membership'),
                atr_value=analysis_data.get('atr_value'),
                atr_distance=analysis_data.get('atr_distance'),
                atr_percent=analysis_data.get('atr_percent'),
                rsi=analysis_data.get('rsi'),
                ma_alignment=analysis_data.get('ma_alignment'),
                confidence_score=analysis_data.get('confidence_score'),
                entry_signal=analysis_data.get('entry_signal', False),
                stop_loss_price=analysis_data.get('stop_loss_price'),
                target_prices=analysis_data.get('target_prices'),
                risk_reward_ratio=analysis_data.get('risk_reward_ratio'),
                company_synopsis=analysis_data.get('company_synopsis'),
                analyst_rating=analysis_data.get('analyst_rating'),
                analyst_target=analysis_data.get('analyst_target'),
                news_sentiment=analysis_data.get('news_sentiment'),
                raw_analysis=analysis_data.get('raw_analysis'),
                is_valid=True
            )
            
            db.add(cache_record)
            db.commit()
            
            logger.info(f"💾 Cached {analysis_type} analysis for {symbol} (expires in {self.cache_durations.get(analysis_type)})")
            return True
            
        except Exception as e:
            logger.error(f"Error caching analysis for {symbol}: {e}")
            db.rollback()
            return False
    
    def invalidate_cache(self, symbol: str, analysis_type: str = None, db: Session = None) -> bool:
        """Invalidate cached analysis for a symbol."""
        try:
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            query = db.query(MarketAnalysisCache).filter(
                MarketAnalysisCache.symbol == symbol.upper()
            )
            
            if analysis_type:
                query = query.filter(MarketAnalysisCache.analysis_type == analysis_type)
            
            updated = query.update({'is_valid': False})
            db.commit()
            
            logger.info(f"🗑️ Invalidated {updated} cache entries for {symbol}")
            
            if should_close:
                db.close()
                
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache for {symbol}: {e}")
            if db:
                db.rollback()
            return False
    
    def cleanup_expired_cache(self, db: Session = None) -> int:
        """Clean up expired cache entries."""
        try:
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            now = datetime.utcnow()
            
            # Delete expired entries
            deleted = db.query(MarketAnalysisCache).filter(
                MarketAnalysisCache.expiry_timestamp < now
            ).delete()
            
            db.commit()
            
            logger.info(f"🧹 Cleaned up {deleted} expired cache entries")
            
            if should_close:
                db.close()
                
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            if db:
                db.rollback()
            return 0
    
    def get_cache_stats(self, db: Session = None) -> Dict:
        """Get comprehensive cache statistics."""
        try:
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            now = datetime.utcnow()
            
            # Total cache entries
            total_entries = db.query(MarketAnalysisCache).count()
            
            # Valid entries
            valid_entries = db.query(MarketAnalysisCache).filter(
                and_(
                    MarketAnalysisCache.expiry_timestamp > now,
                    MarketAnalysisCache.is_valid == True
                )
            ).count()
            
            # Expired entries
            expired_entries = db.query(MarketAnalysisCache).filter(
                MarketAnalysisCache.expiry_timestamp <= now
            ).count()
            
            # Cache by analysis type
            analysis_breakdown = {}
            for analysis_type in ['atr_matrix', 'company_profile', 'technical_analysis', 'news_sentiment']:
                count = db.query(MarketAnalysisCache).filter(
                    and_(
                        MarketAnalysisCache.analysis_type == analysis_type,
                        MarketAnalysisCache.expiry_timestamp > now,
                        MarketAnalysisCache.is_valid == True
                    )
                ).count()
                analysis_breakdown[analysis_type] = count
            
            stats = {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'cache_hit_rate': (valid_entries / max(total_entries, 1)) * 100,
                'analysis_breakdown': analysis_breakdown,
                'cache_durations': {k: str(v) for k, v in self.cache_durations.items()},
                'last_updated': now.isoformat()
            }
            
            if should_close:
                db.close()
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def get_stock_universe(self, limit: int = 1000, filters: Dict = None, db: Session = None) -> List[Dict]:
        """Get comprehensive stock universe for scanning."""
        try:
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            query = db.query(StockUniverse).filter(StockUniverse.is_active == True)
            
            # Apply filters
            if filters:
                if filters.get('market_cap_min'):
                    query = query.filter(StockUniverse.market_cap >= filters['market_cap_min'])
                if filters.get('market_cap_max'):
                    query = query.filter(StockUniverse.market_cap <= filters['market_cap_max'])
                if filters.get('sector'):
                    query = query.filter(StockUniverse.sector == filters['sector'])
                if filters.get('is_sp500'):
                    query = query.filter(StockUniverse.is_sp500 == True)
                if filters.get('min_priority'):
                    query = query.filter(StockUniverse.scan_priority >= filters['min_priority'])
            
            # Order by scan priority and limit
            symbols = query.order_by(StockUniverse.scan_priority.desc()).limit(limit).all()
            
            result = [
                {
                    'symbol': s.symbol,
                    'name': s.name,
                    'sector': s.sector,
                    'industry': s.industry,
                    'market_cap': s.market_cap,
                    'market_cap_category': s.market_cap_category,
                    'scan_priority': s.scan_priority,
                    'polygon_available': s.polygon_available,
                    'last_scanned': s.last_scanned
                }
                for s in symbols
            ]
            
            if should_close:
                db.close()
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting stock universe: {e}")
            return []
    
    def log_scan_history(self, scan_type: str, scan_params: Dict, results: Dict, db: Session = None) -> bool:
        """Log comprehensive scan history for analytics."""
        try:
            if db is None:
                db = SessionLocal()
                should_close = True
            else:
                should_close = False
            
            scan_record = ScanHistory(
                scan_type=scan_type,
                total_symbols_scanned=results.get('total_scanned', 0),
                symbols_with_data=results.get('symbols_with_data', 0),
                analysis_duration_seconds=results.get('scan_time', 0),
                opportunities_found=results.get('opportunities_found', 0),
                signals_sent=results.get('signals_sent', 0),
                errors_encountered=results.get('errors_encountered', 0),
                scan_parameters=scan_params,
                top_results=results.get('top_results', []),
                error_log=results.get('errors', []),
                discord_sent=results.get('discord_sent', False)
            )
            
            db.add(scan_record)
            db.commit()
            
            logger.info(f"📊 Logged scan history: {scan_type} - {results.get('opportunities_found', 0)} opportunities")
            
            if should_close:
                db.close()
                
            return True
            
        except Exception as e:
            logger.error(f"Error logging scan history: {e}")
            if db:
                db.rollback()
            return False

# Global cache service instance
analysis_cache_service = AnalysisCacheService() 