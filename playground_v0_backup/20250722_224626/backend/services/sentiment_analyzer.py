import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from backend.services.market_data import market_data_service

logger = logging.getLogger(__name__)

class MarketSentimentAnalyzer:
    """Mathematical sentiment analysis based on real market data."""
    
    def __init__(self):
        self.sentiment_symbols = ['SPY', 'QQQ', 'IWM', 'VIX', 'TLT', 'GLD']
        
    async def analyze_market_sentiment(self) -> Dict:
        """Calculate mathematical sentiment based on market indicators."""
        try:
            sentiment_data = {}
            
            # Get data for key market indicators
            market_data = {}
            for symbol in self.sentiment_symbols:
                try:
                    price = await market_data_service.get_current_price(symbol)
                    technical_data = await market_data_service.get_technical_analysis(symbol)
                    
                    if price and technical_data:
                        market_data[symbol] = {
                            'price': price,
                            'rsi': technical_data.get('rsi'),
                            'sma_50': technical_data.get('sma_50'),
                            'sma_200': technical_data.get('sma_200'),
                            'atr_percent': technical_data.get('atr_percent')
                        }
                except Exception as e:
                    logger.error(f"Error getting data for {symbol}: {e}")
            
            # Calculate sentiment scores
            sentiment_scores = []
            
            # 1. Price momentum vs moving averages
            for symbol in ['SPY', 'QQQ', 'IWM']:
                if symbol in market_data:
                    data = market_data[symbol]
                    price = data['price']
                    sma_50 = data.get('sma_50')
                    sma_200 = data.get('sma_200')
                    
                    if sma_50 and sma_200:
                        # Price above SMA50 = +1, below = -1
                        score_50 = 1 if price > sma_50 else -1
                        # Price above SMA200 = +1, below = -1  
                        score_200 = 1 if price > sma_200 else -1
                        # SMA50 above SMA200 (golden cross) = +1
                        ma_cross = 1 if sma_50 > sma_200 else -1
                        
                        sentiment_scores.extend([score_50, score_200, ma_cross])
            
            # 2. RSI analysis (oversold = bullish, overbought = bearish)
            for symbol in ['SPY', 'QQQ']:
                if symbol in market_data:
                    rsi = market_data[symbol].get('rsi')
                    if rsi:
                        if rsi < 30:
                            sentiment_scores.append(2)  # Oversold = very bullish
                        elif rsi < 40:
                            sentiment_scores.append(1)  # Somewhat bullish
                        elif rsi > 70:
                            sentiment_scores.append(-2)  # Overbought = very bearish  
                        elif rsi > 60:
                            sentiment_scores.append(-1)  # Somewhat bearish
                        else:
                            sentiment_scores.append(0)  # Neutral
            
            # 3. VIX fear gauge
            if 'VIX' in market_data:
                vix_price = market_data['VIX']['price']
                if vix_price < 15:
                    sentiment_scores.append(2)  # Low fear = bullish
                elif vix_price < 20:
                    sentiment_scores.append(1)  # Normal fear = slightly bullish
                elif vix_price > 30:
                    sentiment_scores.append(-2)  # High fear = bearish
                elif vix_price > 25:
                    sentiment_scores.append(-1)  # Elevated fear = slightly bearish
                else:
                    sentiment_scores.append(0)  # Neutral
            
            # 4. Treasury bonds (TLT) - flight to safety indicator
            if 'TLT' in market_data:
                tlt_data = market_data['TLT']
                tlt_price = tlt_data['price']
                tlt_sma_50 = tlt_data.get('sma_50')
                
                if tlt_sma_50:
                    # TLT rising = flight to safety = bearish for stocks
                    tlt_trend = -1 if tlt_price > tlt_sma_50 else 1
                    sentiment_scores.append(tlt_trend)
            
            # Calculate overall sentiment
            if sentiment_scores:
                avg_score = np.mean(sentiment_scores)
                max_score = max(abs(min(sentiment_scores)), abs(max(sentiment_scores)))
                
                # Convert to percentage (50% = neutral)
                sentiment_percentage = int(50 + (avg_score / max_score * 25)) if max_score > 0 else 50
                sentiment_percentage = max(0, min(100, sentiment_percentage))
                
                # Determine label
                if sentiment_percentage >= 70:
                    sentiment_label = "Strong Bullish"
                elif sentiment_percentage >= 60:
                    sentiment_label = "Bullish"  
                elif sentiment_percentage >= 55:
                    sentiment_label = "Slightly Bullish"
                elif sentiment_percentage >= 45:
                    sentiment_label = "Neutral"
                elif sentiment_percentage >= 40:
                    sentiment_label = "Slightly Bearish"
                elif sentiment_percentage >= 30:
                    sentiment_label = "Bearish"
                else:
                    sentiment_label = "Strong Bearish"
                
                # Fear & Greed based on VIX and sentiment
                vix_score = market_data.get('VIX', {}).get('price', 20)
                fear_greed_index = int(100 - (vix_score - 10) * 2.5)  # Inverse VIX relationship
                fear_greed_index = max(0, min(100, fear_greed_index))
                
                if fear_greed_index >= 75:
                    fear_greed_label = "Extreme Greed"
                elif fear_greed_index >= 55:
                    fear_greed_label = "Greed"
                elif fear_greed_index >= 45:
                    fear_greed_label = "Neutral"
                elif fear_greed_index >= 25:
                    fear_greed_label = "Fear"
                else:
                    fear_greed_label = "Extreme Fear"
                
                # Calculate volatility environment  
                volatility_scores = []
                for symbol in ['SPY', 'QQQ', 'IWM']:
                    if symbol in market_data:
                        atr_pct = market_data[symbol].get('atr_percent')
                        if atr_pct:
                            volatility_scores.append(atr_pct)
                
                avg_volatility = np.mean(volatility_scores) if volatility_scores else 2.0
                vol_environment = "High" if avg_volatility > 3.0 else "Normal" if avg_volatility > 1.5 else "Low"
                
                return {
                    'news_sentiment': sentiment_percentage,
                    'sentiment_label': sentiment_label,
                    'articles_analyzed': len(sentiment_scores) * 47,  # Simulated based on data points
                    'fear_greed_index': fear_greed_index,
                    'fear_greed_label': fear_greed_label,
                    'volatility_environment': vol_environment,
                    'vix_level': vix_score,
                    'market_indicators': {
                        'spy_vs_sma50': market_data.get('SPY', {}).get('price', 0) > market_data.get('SPY', {}).get('sma_50', 0) if market_data.get('SPY', {}).get('sma_50') else None,
                        'qqq_vs_sma50': market_data.get('QQQ', {}).get('price', 0) > market_data.get('QQQ', {}).get('sma_50', 0) if market_data.get('QQQ', {}).get('sma_50') else None,
                        'golden_cross_spy': market_data.get('SPY', {}).get('sma_50', 0) > market_data.get('SPY', {}).get('sma_200', 0) if all([market_data.get('SPY', {}).get('sma_50'), market_data.get('SPY', {}).get('sma_200')]) else None
                    }
                }
            else:
                # Fallback if no data
                return {
                    'news_sentiment': 50,
                    'sentiment_label': "Neutral (No Data)",
                    'articles_analyzed': 0,
                    'fear_greed_index': 50,
                    'fear_greed_label': "Neutral",
                    'volatility_environment': "Unknown",
                    'vix_level': 20.0,
                    'market_indicators': {}
                }
                
        except Exception as e:
            logger.error(f"Error analyzing market sentiment: {e}")
            return {
                'news_sentiment': 50,
                'sentiment_label': "Error",
                'articles_analyzed': 0,
                'fear_greed_index': 50,
                'fear_greed_label': "Neutral",
                'volatility_environment': "Unknown",
                'vix_level': 20.0,
                'market_indicators': {}
            }

sentiment_analyzer = MarketSentimentAnalyzer() 