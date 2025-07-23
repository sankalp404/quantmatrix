import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiohttp
import json
from backend.config import settings
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class NewsService:
    """Service for fetching financial news from multiple sources."""
    
    def __init__(self):
        self.session = None
        
    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_holdings_news(self, symbols: List[str], max_articles: int = 20) -> List[Dict]:
        """Get news for specific holdings/symbols."""
        all_news = []
        
        # Get news from multiple sources
        news_sources = [
            self._get_finnhub_news(symbols),
            self._get_fmp_news(symbols),
            self._get_general_market_news()
        ]
        
        try:
            results = await asyncio.gather(*news_sources, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"News source error: {result}")
                    continue
                if isinstance(result, list):
                    all_news.extend(result)
            
            # Sort by date and relevance, return top articles
            sorted_news = sorted(all_news, key=lambda x: x.get('published_at', ''), reverse=True)
            return sorted_news[:max_articles]
            
        except Exception as e:
            logger.error(f"Error fetching holdings news: {e}")
            return []
    
    async def _get_finnhub_news(self, symbols: List[str]) -> List[Dict]:
        """Fetch news from Finnhub API."""
        if not settings.FINNHUB_API_KEY:
            return []
        
        session = await self._get_session()
        news_items = []
        
        try:
            # Get company news for each symbol
            for symbol in symbols[:5]:  # Limit to prevent rate limiting
                url = f"https://finnhub.io/api/v1/company-news"
                params = {
                    'symbol': symbol,
                    'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'to': datetime.now().strftime('%Y-%m-%d'),
                    'token': settings.FINNHUB_API_KEY
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data[:3]:  # Top 3 per symbol
                            news_items.append({
                                'symbol': symbol,
                                'headline': item.get('headline', ''),
                                'summary': item.get('summary', ''),
                                'url': item.get('url', ''),
                                'published_at': datetime.fromtimestamp(item.get('datetime', 0)).isoformat(),
                                'source': 'Finnhub',
                                'category': item.get('category', 'company'),
                                'sentiment': self._analyze_sentiment(item.get('headline', '') + ' ' + item.get('summary', ''))
                            })
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Finnhub news error: {e}")
        
        return news_items
    
    async def _get_fmp_news(self, symbols: List[str]) -> List[Dict]:
        """Fetch news from Financial Modeling Prep API."""
        if not settings.FMP_API_KEY:
            return []
        
        session = await self._get_session()
        news_items = []
        
        try:
            for symbol in symbols[:5]:  # Limit to prevent rate limiting
                url = f"https://financialmodelingprep.com/api/v3/stock_news"
                params = {
                    'tickers': symbol,
                    'limit': 5,
                    'apikey': settings.FMP_API_KEY
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data:
                            news_items.append({
                                'symbol': symbol,
                                'headline': item.get('title', ''),
                                'summary': item.get('text', '')[:200] + '...' if len(item.get('text', '')) > 200 else item.get('text', ''),
                                'url': item.get('url', ''),
                                'published_at': item.get('publishedDate', ''),
                                'source': 'FMP',
                                'category': 'company',
                                'sentiment': self._analyze_sentiment(item.get('title', '') + ' ' + item.get('text', ''))
                            })
                
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"FMP news error: {e}")
        
        return news_items
    
    async def _get_general_market_news(self) -> List[Dict]:
        """Get general market news from reliable sources."""
        session = await self._get_session()
        news_items = []
        
        try:
            # General market news from Finnhub
            if settings.FINNHUB_API_KEY:
                url = "https://finnhub.io/api/v1/news"
                params = {
                    'category': 'general',
                    'token': settings.FINNHUB_API_KEY
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data[:5]:  # Top 5 general news
                            news_items.append({
                                'symbol': 'MARKET',
                                'headline': item.get('headline', ''),
                                'summary': item.get('summary', ''),
                                'url': item.get('url', ''),
                                'published_at': datetime.fromtimestamp(item.get('datetime', 0)).isoformat(),
                                'source': 'Finnhub',
                                'category': 'market',
                                'sentiment': self._analyze_sentiment(item.get('headline', '') + ' ' + item.get('summary', ''))
                            })
                            
        except Exception as e:
            logger.error(f"General news error: {e}")
        
        return news_items
    
    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis based on keywords."""
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        
        positive_words = ['beat', 'exceed', 'growth', 'profit', 'gain', 'rise', 'surge', 'strong', 'robust', 'positive', 'upgrade', 'buy', 'bullish', 'rally', 'breakthrough', 'success']
        negative_words = ['miss', 'loss', 'decline', 'fall', 'drop', 'weak', 'concern', 'downgrade', 'sell', 'bearish', 'crash', 'fail', 'struggle', 'challenge', 'risk']
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            return 'positive'
        elif negative_score > positive_score:
            return 'negative'
        else:
            return 'neutral'
    
    async def get_company_profile(self, symbol: str) -> Dict:
        """Get comprehensive company profile for signals."""
        try:
            # Try multiple sources for company info
            profile_sources = [
                self._get_fmp_company_profile(symbol),
                self._get_finnhub_company_profile(symbol),
                self._get_basic_company_info(symbol)
            ]
            
            results = await asyncio.gather(*profile_sources, return_exceptions=True)
            
            # Combine results from different sources
            combined_profile = {}
            for result in results:
                if isinstance(result, dict) and result:
                    combined_profile.update(result)
                    break  # Use first successful result
            
            # Ensure we have basic info
            if not combined_profile.get('name'):
                combined_profile = await self._get_basic_company_info(symbol)
            
            return combined_profile
            
        except Exception as e:
            logger.error(f"Error getting company profile for {symbol}: {e}")
            return {'symbol': symbol, 'name': symbol, 'description': 'Company information not available'}
    
    async def _get_fmp_company_profile(self, symbol: str) -> Dict:
        """Get company profile from FMP."""
        if not settings.FMP_API_KEY:
            return {}
        
        session = await self._get_session()
        
        try:
            url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
            params = {'apikey': settings.FMP_API_KEY}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        company = data[0]
                        return {
                            'symbol': symbol,
                            'name': company.get('companyName', ''),
                            'description': company.get('description', ''),
                            'industry': company.get('industry', ''),
                            'sector': company.get('sector', ''),
                            'market_cap': company.get('mktCap', 0),
                            'employees': company.get('fullTimeEmployees', 0),
                            'website': company.get('website', ''),
                            'ceo': company.get('ceo', ''),
                            'exchange': company.get('exchangeShortName', ''),
                            'country': company.get('country', ''),
                            'ipo_date': company.get('ipoDate', ''),
                            'beta': company.get('beta', 0)
                        }
        except Exception as e:
            logger.error(f"FMP company profile error for {symbol}: {e}")
        
        return {}
    
    async def _get_finnhub_company_profile(self, symbol: str) -> Dict:
        """Get company profile from Finnhub."""
        if not settings.FINNHUB_API_KEY:
            return {}
        
        session = await self._get_session()
        
        try:
            url = "https://finnhub.io/api/v1/stock/profile2"
            params = {
                'symbol': symbol,
                'token': settings.FINNHUB_API_KEY
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return {
                            'symbol': symbol,
                            'name': data.get('name', ''),
                            'description': f"{data.get('name', '')} operates in the {data.get('finnhubIndustry', 'N/A')} industry.",
                            'industry': data.get('finnhubIndustry', ''),
                            'market_cap': data.get('marketCapitalization', 0) * 1000000 if data.get('marketCapitalization') else 0,
                            'employees': data.get('employeeTotal', 0),
                            'website': data.get('weburl', ''),
                            'exchange': data.get('exchange', ''),
                            'country': data.get('country', ''),
                            'ipo_date': data.get('ipo', ''),
                            'logo': data.get('logo', '')
                        }
        except Exception as e:
            logger.error(f"Finnhub company profile error for {symbol}: {e}")
        
        return {}
    
    async def _get_basic_company_info(self, symbol: str) -> Dict:
        """Get basic company info as fallback."""
        try:
            # Use our existing market data service
            info = await market_data_service.get_stock_info(symbol)
            return {
                'symbol': symbol,
                'name': info.get('company_name', symbol),
                'description': f"Stock symbol {symbol}",
                'industry': info.get('industry', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'market_cap': info.get('market_cap', 0)
            }
        except Exception as e:
            logger.error(f"Basic company info error for {symbol}: {e}")
            return {'symbol': symbol, 'name': symbol, 'description': 'Company information not available'}
    
    def create_company_synopsis(self, company_profile: Dict, stock_info: Dict) -> str:
        """Create a comprehensive company synopsis for signals."""
        name = company_profile.get('name', 'Company')
        sector = company_profile.get('sector', 'N/A')
        industry = company_profile.get('industry', 'N/A')
        market_cap = company_profile.get('market_cap', 0)
        employees = company_profile.get('employees', 0)
        description = company_profile.get('description', '')
        
        market_cap_category = self._categorize_market_cap(market_cap)
        
        # Create concise but informative synopsis
        synopsis_parts = []
        
        # Core business description
        if description and len(description) > 50:
            synopsis_parts.append(description[:120] + "...")
        else:
            synopsis_parts.append(f"{name} operates in the {sector} sector, specifically in {industry}.")
        
        # Market position info
        if market_cap > 0:
            market_cap_billions = market_cap / 1_000_000_000
            synopsis_parts.append(f"{market_cap_category} company with ${market_cap_billions:.1f}B market cap.")
        
        if employees > 0:
            synopsis_parts.append(f"Employs {employees:,} people globally.")
        
        return " ".join(synopsis_parts)
    
    def calculate_time_horizon(self, atr_value: float, current_price: float, target_price: float) -> str:
        """Calculate expected time horizon for reaching target."""
        if not atr_value or not current_price or not target_price:
            return "3-7 days"
        
        # Simple heuristic based on ATR movement
        price_move_needed = abs(target_price - current_price)
        daily_atr_movement = atr_value * 0.7  # Assume 70% of ATR daily movement
        
        if daily_atr_movement > 0:
            days_to_target = price_move_needed / daily_atr_movement
            
            if days_to_target <= 3:
                return "1-3 days"
            elif days_to_target <= 7:
                return "3-7 days" 
            elif days_to_target <= 14:
                return "1-2 weeks"
            else:
                return "2+ weeks"
        
        return "3-7 days"
    
    def categorize_market_cap(self, market_cap: float) -> str:
        """Categorize stocks by market cap."""
        if market_cap > 200_000_000_000:  # >200B
            return "Mega Cap"
        elif market_cap > 10_000_000_000:  # >10B
            return "Large Cap"
        elif market_cap > 2_000_000_000:   # >2B
            return "Mid Cap"
        elif market_cap > 300_000_000:     # >300M
            return "Small Cap"
        else:
            return "Micro Cap"
    
    def _categorize_market_cap(self, market_cap: float) -> str:
        """Private method for internal use."""
        return self.categorize_market_cap(market_cap)

    async def get_enhanced_company_synopsis(self, symbol: str, company_profile: Dict, stock_info: Dict) -> str:
        """Create enhanced company synopsis with analyst ratings, price targets, and outlook."""
        name = company_profile.get('name', symbol)
        sector = company_profile.get('sector', 'N/A')
        industry = company_profile.get('industry', 'N/A')
        market_cap = company_profile.get('market_cap', 0)
        description = company_profile.get('description', '')
        
        # Start with basic company info
        synopsis_parts = []
        
        # Business description
        if description and len(description) > 50:
            business_desc = description[:150].strip()
            if not business_desc.endswith('.'):
                business_desc += "..."
            synopsis_parts.append(f"**Business**: {business_desc}")
        else:
            synopsis_parts.append(f"**Business**: {name} operates in {sector} sector, {industry} industry.")
        
        # Market position and fundamentals
        if market_cap > 0:
            market_cap_billions = market_cap / 1_000_000_000
            market_cap_category = self._categorize_market_cap(market_cap)
            synopsis_parts.append(f"**Market Cap**: ${market_cap_billions:.1f}B ({market_cap_category})")
        
        # Try to get analyst data and price targets
        analyst_info = await self._get_analyst_recommendations(symbol)
        if analyst_info:
            synopsis_parts.append(analyst_info)
        
        # Get recent earnings and guidance info
        earnings_info = await self._get_earnings_outlook(symbol)
        if earnings_info:
            synopsis_parts.append(earnings_info)
        
        # Get recent news sentiment for outlook
        recent_sentiment = await self._get_recent_sentiment_outlook(symbol)
        if recent_sentiment:
            synopsis_parts.append(recent_sentiment)
        
        return " ".join(synopsis_parts)
    
    async def _get_analyst_recommendations(self, symbol: str) -> str:
        """Get analyst recommendations and price targets."""
        try:
            # Try FMP for analyst recommendations
            if settings.FMP_API_KEY:
                session = await self._get_session()
                url = f"https://financialmodelingprep.com/api/v3/analyst-stock-recommendations/{symbol}"
                params = {'apikey': settings.FMP_API_KEY}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            # Get most recent recommendation
                            latest = data[0]
                            
                            # Get consensus data
                            url_consensus = f"https://financialmodelingprep.com/api/v3/price-target-consensus/{symbol}"
                            async with session.get(url_consensus, params=params) as consensus_response:
                                if consensus_response.status == 200:
                                    consensus_data = await consensus_response.json()
                                    if consensus_data and len(consensus_data) > 0:
                                        consensus = consensus_data[0]
                                        target_high = consensus.get('targetHigh', 0)
                                        target_mean = consensus.get('targetMean', 0)
                                        target_low = consensus.get('targetLow', 0)
                                        
                                        if target_mean > 0:
                                            return f"**Analyst Target**: ${target_mean:.0f} (Range: ${target_low:.0f}-${target_high:.0f})"
                            
                            # Fallback to basic recommendation if no price target
                            analyst_grade = latest.get('analystRatingstrength', latest.get('newGrade', 'N/A'))
                            if analyst_grade and analyst_grade != 'N/A':
                                return f"**Analyst Rating**: {analyst_grade}"
        except Exception as e:
            logger.error(f"Error getting analyst data for {symbol}: {e}")
        
        return ""
    
    async def _get_earnings_outlook(self, symbol: str) -> str:
        """Get earnings outlook and guidance."""
        try:
            if settings.FMP_API_KEY:
                session = await self._get_session()
                # Get earnings estimates
                url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{symbol}"
                params = {'apikey': settings.FMP_API_KEY, 'limit': 1}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            estimate = data[0]
                            estimated_revenue_avg = estimate.get('estimatedRevenueAvg', 0)
                            estimated_eps_avg = estimate.get('estimatedEpsAvg', 0)
                            
                            if estimated_revenue_avg > 0 or estimated_eps_avg > 0:
                                outlook_parts = []
                                if estimated_eps_avg > 0:
                                    outlook_parts.append(f"EPS Est: ${estimated_eps_avg:.2f}")
                                if estimated_revenue_avg > 0:
                                    revenue_billions = estimated_revenue_avg / 1_000_000_000
                                    outlook_parts.append(f"Rev Est: ${revenue_billions:.1f}B")
                                
                                if outlook_parts:
                                    return f"**Earnings Outlook**: {', '.join(outlook_parts)}"
        except Exception as e:
            logger.error(f"Error getting earnings outlook for {symbol}: {e}")
        
        return ""
    
    async def _get_recent_sentiment_outlook(self, symbol: str) -> str:
        """Get recent sentiment and business outlook from news."""
        try:
            # Get recent news for the symbol
            recent_news = await self.get_holdings_news([symbol], max_articles=5)
            
            if recent_news:
                positive_count = sum(1 for news in recent_news if news.get('sentiment') == 'positive')
                negative_count = sum(1 for news in recent_news if news.get('sentiment') == 'negative')
                
                if positive_count > negative_count + 1:
                    return "**Recent Outlook**: Positive news sentiment"
                elif negative_count > positive_count + 1:
                    return "**Recent Outlook**: Cautious due to negative news"
                else:
                    return "**Recent Outlook**: Mixed news sentiment"
        except Exception as e:
            logger.error(f"Error getting sentiment outlook for {symbol}: {e}")
        
        return ""

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()

# Global instance
news_service = NewsService() 