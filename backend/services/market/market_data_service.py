import yfinance as yf
import finnhub
import fmpsdk
from twelvedata import TDClient
import pandas as pd
import numpy as np
import redis
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
import time
import aiohttp
from enum import Enum

from backend.config import settings

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    FINNHUB = "finnhub"
    TWELVE_DATA = "twelve_data"
    FMP = "fmp"
    YFINANCE = "yfinance"


class MarketDataService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.cache_ttl = getattr(
            settings, "MARKET_DATA_CACHE_TTL", 300
        )  # Default 5 minutes
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize API clients
        self._init_api_clients()

        # Rate limiting trackers for each API
        self.rate_limits = {
            APIProvider.FINNHUB: {"calls": [], "max_per_minute": 60},
            APIProvider.TWELVE_DATA: {
                "calls": [],
                "max_per_day": 800,
                "daily_count": 0,
                "last_reset": datetime.now().date(),
            },
            APIProvider.FMP: {
                "calls": [],
                "max_per_day": 250,
                "daily_count": 0,
                "last_reset": datetime.now().date(),
            },
            APIProvider.YFINANCE: {
                "calls": [],
                "max_per_minute": 2000,
            },  # Very generous limit
        }

    def _init_api_clients(self):
        """Initialize all API clients."""
        # Finnhub client
        if settings.FINNHUB_API_KEY:
            self.finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
            logger.info("Finnhub API client initialized")
        else:
            self.finnhub_client = None
            logger.warning("Finnhub API key not configured")

        # Twelve Data client
        if settings.TWELVE_DATA_API_KEY:
            self.twelve_data_client = TDClient(apikey=settings.TWELVE_DATA_API_KEY)
            logger.info("Twelve Data API client initialized")
        else:
            self.twelve_data_client = None
            logger.warning("Twelve Data API key not configured")

        # FMP doesn't need client initialization
        if settings.FMP_API_KEY:
            logger.info("FMP API key configured")
        else:
            logger.warning("FMP API key not configured")

        logger.info("yfinance available as fallback (no API key required)")

    def _check_rate_limit(self, provider: APIProvider) -> bool:
        """Check if we can make a call to the specified provider."""
        now = time.time()
        today = datetime.now().date()
        limits = self.rate_limits[provider]

        # Reset daily counters if needed
        if provider in [APIProvider.TWELVE_DATA, APIProvider.FMP]:
            if limits["last_reset"] != today:
                limits["daily_count"] = 0
                limits["last_reset"] = today

        # Clean old calls for minute-based limits
        if "max_per_minute" in limits:
            limits["calls"] = [
                call_time for call_time in limits["calls"] if now - call_time < 60
            ]
            if len(limits["calls"]) >= limits["max_per_minute"]:
                return False

        # Check daily limits
        if "max_per_day" in limits:
            if limits["daily_count"] >= limits["max_per_day"]:
                return False

        return True

    def _record_api_call(self, provider: APIProvider):
        """Record an API call for rate limiting."""
        now = time.time()
        limits = self.rate_limits[provider]

        if "max_per_minute" in limits:
            limits["calls"].append(now)

        if "max_per_day" in limits:
            limits["daily_count"] += 1

    async def _get_best_provider_for_data_type(self, data_type: str) -> APIProvider:
        """Determine the best API provider for a specific data type."""

        # Priority routing based on API strengths and availability
        if data_type == "real_time_quote":
            for provider in [
                APIProvider.FINNHUB,
                APIProvider.FMP,
                APIProvider.YFINANCE,
            ]:
                if self._check_rate_limit(provider) and self._is_provider_available(
                    provider
                ):
                    return provider

        elif data_type == "technical_indicators":
            for provider in [
                APIProvider.TWELVE_DATA,
                APIProvider.FMP,
                APIProvider.YFINANCE,
            ]:
                if self._check_rate_limit(provider) and self._is_provider_available(
                    provider
                ):
                    return provider

        elif data_type == "historical_data":
            for provider in [
                APIProvider.YFINANCE,
                APIProvider.TWELVE_DATA,
                APIProvider.FMP,
                APIProvider.FINNHUB,
            ]:
                if self._check_rate_limit(provider) and self._is_provider_available(
                    provider
                ):
                    return provider

        elif data_type == "company_info":
            for provider in [
                APIProvider.FMP,
                APIProvider.YFINANCE,
                APIProvider.FINNHUB,
            ]:
                if self._check_rate_limit(provider) and self._is_provider_available(
                    provider
                ):
                    return provider

        # Fallback to yfinance if available
        if self._check_rate_limit(APIProvider.YFINANCE):
            return APIProvider.YFINANCE

        # Last resort - return first available
        for provider in APIProvider:
            if self._check_rate_limit(provider) and self._is_provider_available(
                provider
            ):
                return provider

        raise Exception("No API providers available")

    def _is_provider_available(self, provider: APIProvider) -> bool:
        """Check if the API provider is properly configured."""
        if provider == APIProvider.FINNHUB:
            return self.finnhub_client is not None
        elif provider == APIProvider.TWELVE_DATA:
            return self.twelve_data_client is not None
        elif provider == APIProvider.FMP:
            return settings.FMP_API_KEY is not None
        elif provider == APIProvider.YFINANCE:
            return True
        return False

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price using the best available API."""
        cache_key = f"price:{symbol}"

        # Check cache first
        cached_price = self.redis_client.get(cache_key)
        if cached_price:
            try:
                return float(cached_price)
            except:
                pass

        try:
            provider = await self._get_best_provider_for_data_type("real_time_quote")
            self._record_api_call(provider)

            price = None

            if provider == APIProvider.FINNHUB:
                price = await self._get_price_finnhub(symbol)
            elif provider == APIProvider.FMP:
                price = await self._get_price_fmp(symbol)
            elif provider == APIProvider.YFINANCE:
                price = await self._get_price_yfinance(symbol)

            if price:
                # Cache for 1 minute
                self.redis_client.setex(cache_key, 60, str(price))
                return price

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")

        return None

    async def _get_price_finnhub(self, symbol: str) -> Optional[float]:
        """Get current price from Finnhub."""
        try:
            quote = self.finnhub_client.quote(symbol)
            return quote.get("c")  # Current price
        except Exception as e:
            logger.error(f"Finnhub price error for {symbol}: {e}")
            return None

    async def _get_price_fmp(self, symbol: str) -> Optional[float]:
        """Get current price from FMP."""
        try:
            quote = fmpsdk.quote(apikey=settings.FMP_API_KEY, symbol=symbol)
            if quote and len(quote) > 0:
                return quote[0].get("price")
        except Exception as e:
            logger.error(f"FMP price error for {symbol}: {e}")
            return None

    async def _get_price_yfinance(self, symbol: str) -> Optional[float]:
        """Get current price from yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.error(f"yfinance price error for {symbol}: {e}")
            return None

    async def get_historical_data(
        self, symbol: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Get historical data using the best available API."""
        cache_key = f"historical:{symbol}:{period}:{interval}"

        # Check cache first
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            try:
                return pd.read_json(cached_data, orient="index")
            except:
                pass

        try:
            provider = await self._get_best_provider_for_data_type("historical_data")
            self._record_api_call(provider)

            data = None

            if provider == APIProvider.YFINANCE:
                data = await self._get_historical_yfinance(symbol, period, interval)
            elif provider == APIProvider.TWELVE_DATA:
                data = await self._get_historical_twelve_data(symbol, period, interval)
            elif provider == APIProvider.FMP:
                data = await self._get_historical_fmp(symbol, period, interval)

            if data is not None and not data.empty:
                # Cache based on interval (shorter intervals = shorter cache)
                cache_seconds = 300 if interval in ["1m", "5m"] else 3600
                self.redis_client.setex(
                    cache_key, cache_seconds, data.to_json(orient="index")
                )
                return data

        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")

        return None

    async def _get_historical_yfinance(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        """Get historical data from yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            if not data.empty:
                # Keep only OHLCV columns to ensure consistency
                required_cols = ["Open", "High", "Low", "Close", "Volume"]
                available_cols = [col for col in required_cols if col in data.columns]

                if len(available_cols) >= 4:  # Need at least OHLC
                    data = data[available_cols]
                    # Fill missing Volume column if needed
                    if "Volume" not in data.columns:
                        data["Volume"] = 0
                    return data.sort_index(ascending=False)
                else:
                    logger.error(f"yfinance data for {symbol} missing required columns")
                    return None
        except Exception as e:
            logger.error(f"yfinance historical error for {symbol}: {e}")
            return None

    async def _get_historical_twelve_data(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        """Get historical data from Twelve Data."""
        try:
            # Convert period and interval to Twelve Data format
            td_interval = self._convert_interval_to_td(interval)
            td_outputsize = "5000"  # Get plenty of data

            ts = self.twelve_data_client.time_series(
                symbol=symbol, interval=td_interval, outputsize=td_outputsize
            )

            if ts.status == "ok":
                df = ts.as_pandas()
                if not df.empty:
                    # Rename columns to match our standard
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    return df.sort_index(ascending=False)
        except Exception as e:
            logger.error(f"Twelve Data historical error for {symbol}: {e}")
            return None

    async def _get_historical_fmp(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        """Get historical data from FMP."""
        try:
            if interval == "1d":
                # Daily data
                data = fmpsdk.historical_price_full(
                    apikey=settings.FMP_API_KEY, symbol=symbol
                )
                if data and "historical" in data:
                    df = pd.DataFrame(data["historical"])
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df = df[["open", "high", "low", "close", "volume"]]
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    return df.sort_index(ascending=False)
        except Exception as e:
            logger.error(f"FMP historical error for {symbol}: {e}")
            return None

    def _convert_interval_to_td(self, interval: str) -> str:
        """Convert interval to Twelve Data format."""
        mapping = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1h",
            "1d": "1day",
            "1wk": "1week",
            "1mo": "1month",
        }
        return mapping.get(interval, "1day")

    async def get_technical_analysis(self, symbol: str) -> Dict:
        """Get comprehensive technical analysis using multiple APIs."""
        cache_key = f"technical:{symbol}"

        # Check cache first
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except:
                pass

        # Get historical data first
        data = await self.get_historical_data(symbol, period="1y", interval="1d")
        if data is None or data.empty:
            logger.warning(f"No historical data available for {symbol}")
            return {}

        try:
            indicators = {}

            # Data is already sorted with newest first from get_historical_data
            # For technical analysis, we need oldest first
            data_for_ta = data.iloc[::-1].copy()  # Reverse to oldest first

            # Basic price data - use most recent (newest) data for current price
            current_close = float(data["Close"].iloc[0])  # Most recent close
            indicators["close"] = current_close
            indicators["current_price"] = current_close

            logger.debug(
                f"Processing {symbol}: Current price=${current_close:.2f}, Data points={len(data)}"
            )

            # Get technical indicators from best provider
            tech_indicators = await self._get_technical_indicators(symbol, data_for_ta)
            indicators.update(tech_indicators)

            # If API indicators failed, use local calculations
            if not tech_indicators or len(tech_indicators) < 3:
                logger.info(
                    f"API indicators failed for {symbol}, using local calculations"
                )
                local_indicators = self._calculate_indicators_locally(data_for_ta)
                indicators.update(local_indicators)

            # Calculate ATR Matrix specific metrics
            atr_metrics = self._calculate_atr_matrix_metrics(data_for_ta, indicators)
            indicators.update(atr_metrics)

            # Ensure we have minimum required indicators for ATR Matrix
            required_indicators = ["sma_50", "atr", "sma_20", "ema_10"]
            missing_indicators = [
                ind for ind in required_indicators if indicators.get(ind) is None
            ]

            if missing_indicators:
                logger.warning(
                    f"Missing critical indicators for {symbol}: {missing_indicators}"
                )
                # Try manual calculations for missing indicators
                fallback_indicators = self._manual_indicator_calculations(data_for_ta)
                for missing_ind in missing_indicators:
                    if missing_ind in fallback_indicators:
                        indicators[missing_ind] = fallback_indicators[missing_ind]

            # Cache for 5 minutes
            self.redis_client.setex(cache_key, 300, json.dumps(indicators, default=str))

            logger.debug(
                f"Successfully calculated indicators for {symbol}: {list(indicators.keys())}"
            )
            return indicators

        except Exception as e:
            logger.error(
                f"Error in technical analysis for {symbol}: {e}", exc_info=True
            )
            # Return minimal data at least
            try:
                current_close = float(data["Close"].iloc[0])
                return {
                    "close": current_close,
                    "current_price": current_close,
                    "error": str(e),
                }
            except:
                return {"error": str(e)}

    async def _get_technical_indicators(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Get technical indicators from the best available API."""
        try:
            provider = await self._get_best_provider_for_data_type(
                "technical_indicators"
            )

            if provider == APIProvider.TWELVE_DATA and self.twelve_data_client:
                return await self._get_indicators_twelve_data(symbol)
            elif provider == APIProvider.FMP and settings.FMP_API_KEY:
                return await self._get_indicators_fmp(symbol)
            else:
                # Fallback to our own calculations using pandas-ta
                return self._calculate_indicators_locally(data)

        except Exception as e:
            logger.error(f"Error getting technical indicators for {symbol}: {e}")
            # Always fallback to local calculations
            return self._calculate_indicators_locally(data)

    async def _get_indicators_twelve_data(self, symbol: str) -> Dict:
        """Get technical indicators from Twelve Data."""
        indicators = {}
        try:
            self._record_api_call(APIProvider.TWELVE_DATA)

            # RSI
            rsi = self.twelve_data_client.rsi(
                symbol=symbol, interval="1day", time_period=14
            )
            if rsi.status == "ok":
                rsi_df = rsi.as_pandas()
                if not rsi_df.empty:
                    indicators["rsi"] = float(rsi_df.iloc[-1])

            # ATR
            atr = self.twelve_data_client.atr(
                symbol=symbol, interval="1day", time_period=14
            )
            if atr.status == "ok":
                atr_df = atr.as_pandas()
                if not atr_df.empty:
                    indicators["atr"] = float(atr_df.iloc[-1])

            # Moving averages
            for period in [10, 20, 50, 100, 200]:
                ma_type = "ema" if period == 10 else "sma"
                ma = (
                    self.twelve_data_client.ema(
                        symbol=symbol, interval="1day", time_period=period
                    )
                    if ma_type == "ema"
                    else self.twelve_data_client.sma(
                        symbol=symbol, interval="1day", time_period=period
                    )
                )

                if ma.status == "ok":
                    ma_df = ma.as_pandas()
                    if not ma_df.empty:
                        indicators[f"{ma_type}_{period}"] = float(ma_df.iloc[-1])

            # MACD
            macd = self.twelve_data_client.macd(symbol=symbol, interval="1day")
            if macd.status == "ok":
                macd_df = macd.as_pandas()
                if not macd_df.empty:
                    indicators["macd"] = float(macd_df["macd"].iloc[-1])
                    indicators["macd_signal"] = float(macd_df["macd_signal"].iloc[-1])
                    indicators["macd_histogram"] = float(macd_df["macd_hist"].iloc[-1])

            # ADX
            adx = self.twelve_data_client.adx(
                symbol=symbol, interval="1day", time_period=14
            )
            if adx.status == "ok":
                adx_df = adx.as_pandas()
                if not adx_df.empty:
                    indicators["adx"] = float(adx_df["adx"].iloc[-1])
                    indicators["plus_di"] = float(adx_df["plus_di"].iloc[-1])
                    indicators["minus_di"] = float(adx_df["minus_di"].iloc[-1])

        except Exception as e:
            logger.error(f"Twelve Data indicators error for {symbol}: {e}")

        return indicators

    async def _get_indicators_fmp(self, symbol: str) -> Dict:
        """Get technical indicators from FMP."""
        indicators = {}
        try:
            self._record_api_call(APIProvider.FMP)

            # FMP provides some indicators
            # RSI
            rsi_data = fmpsdk.rsi(
                apikey=settings.FMP_API_KEY, symbol=symbol, period=14, datatype="json"
            )
            if rsi_data and len(rsi_data) > 0:
                indicators["rsi"] = rsi_data[0].get("rsi")

            # SMA
            for period in [20, 50, 100, 200]:
                sma_data = fmpsdk.sma(
                    apikey=settings.FMP_API_KEY,
                    symbol=symbol,
                    period=period,
                    datatype="json",
                )
                if sma_data and len(sma_data) > 0:
                    indicators[f"sma_{period}"] = sma_data[0].get("sma")

            # EMA
            ema_data = fmpsdk.ema(
                apikey=settings.FMP_API_KEY, symbol=symbol, period=10, datatype="json"
            )
            if ema_data and len(ema_data) > 0:
                indicators["ema_10"] = ema_data[0].get("ema")

        except Exception as e:
            logger.error(f"FMP indicators error for {symbol}: {e}")

        return indicators

    def _calculate_indicators_locally(self, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators locally using pandas-ta."""
        indicators = {}

        try:
            import pandas_ta as ta

            # Calculate indicators individually instead of using AllStrategy
            # RSI - use most recent value (last row)
            rsi = ta.rsi(data["Close"], length=14)
            if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                indicators["rsi"] = float(rsi.iloc[-1])

            # ATR - use most recent value
            atr = ta.atr(data["High"], data["Low"], data["Close"], length=14)
            if not atr.empty and not pd.isna(atr.iloc[-1]):
                indicators["atr"] = float(atr.iloc[-1])

            # Moving averages - use most recent values
            sma_20 = ta.sma(data["Close"], length=20)
            if not sma_20.empty and not pd.isna(sma_20.iloc[-1]):
                indicators["sma_20"] = float(sma_20.iloc[-1])

            sma_50 = ta.sma(data["Close"], length=50)
            if not sma_50.empty and not pd.isna(sma_50.iloc[-1]):
                indicators["sma_50"] = float(sma_50.iloc[-1])

            sma_100 = ta.sma(data["Close"], length=100)
            if not sma_100.empty and not pd.isna(sma_100.iloc[-1]):
                indicators["sma_100"] = float(sma_100.iloc[-1])

            sma_200 = ta.sma(data["Close"], length=200)
            if not sma_200.empty and not pd.isna(sma_200.iloc[-1]):
                indicators["sma_200"] = float(sma_200.iloc[-1])

            ema_10 = ta.ema(data["Close"], length=10)
            if not ema_10.empty and not pd.isna(ema_10.iloc[-1]):
                indicators["ema_10"] = float(ema_10.iloc[-1])

            # MACD - use most recent values
            macd_data = ta.macd(data["Close"])
            if not macd_data.empty:
                if not pd.isna(macd_data["MACD_12_26_9"].iloc[-1]):
                    indicators["macd"] = float(macd_data["MACD_12_26_9"].iloc[-1])
                if not pd.isna(macd_data["MACDs_12_26_9"].iloc[-1]):
                    indicators["macd_signal"] = float(
                        macd_data["MACDs_12_26_9"].iloc[-1]
                    )
                if not pd.isna(macd_data["MACDh_12_26_9"].iloc[-1]):
                    indicators["macd_histogram"] = float(
                        macd_data["MACDh_12_26_9"].iloc[-1]
                    )

            # ADX - use most recent values
            adx_data = ta.adx(data["High"], data["Low"], data["Close"], length=14)
            if not adx_data.empty:
                if not pd.isna(adx_data["ADX_14"].iloc[-1]):
                    indicators["adx"] = float(adx_data["ADX_14"].iloc[-1])
                if not pd.isna(adx_data["DMP_14"].iloc[-1]):
                    indicators["plus_di"] = float(adx_data["DMP_14"].iloc[-1])
                if not pd.isna(adx_data["DMN_14"].iloc[-1]):
                    indicators["minus_di"] = float(adx_data["DMN_14"].iloc[-1])

        except Exception as e:
            logger.error(f"Local indicator calculation error: {e}")
            # Fallback to manual calculations
            indicators.update(self._manual_indicator_calculations(data))

        return indicators

    def _manual_indicator_calculations(self, data: pd.DataFrame) -> Dict:
        """Manual calculation of key indicators as ultimate fallback."""
        indicators = {}

        try:
            logger.info(
                f"Using manual calculations for indicators, data length: {len(data)}"
            )

            # Simple moving averages - use most recent values (last row in oldest-first data)
            for period in [20, 50, 100, 200]:
                if len(data) >= period:
                    sma = data["Close"].rolling(window=period).mean()
                    if not sma.empty and not pd.isna(sma.iloc[-1]):
                        indicators[f"sma_{period}"] = float(sma.iloc[-1])
                        logger.debug(
                            f"Calculated SMA_{period}: {indicators[f'sma_{period}']:.2f}"
                        )

            # EMA 10 - use most recent value
            if len(data) >= 10:
                ema_10 = data["Close"].ewm(span=10).mean()
                if not ema_10.empty and not pd.isna(ema_10.iloc[-1]):
                    indicators["ema_10"] = float(ema_10.iloc[-1])
                    logger.debug(f"Calculated EMA_10: {indicators['ema_10']:.2f}")

            # ATR - Critical for ATR Matrix strategy
            if len(data) >= 14:
                atr = self.calculate_atr(data, 14)
                if atr is not None:
                    indicators["atr"] = atr
                    logger.debug(f"Calculated ATR: {atr:.4f}")

            # RSI - Important technical indicator
            if len(data) >= 14:
                rsi = self.calculate_rsi(data, 14)
                if rsi is not None:
                    indicators["rsi"] = rsi
                    logger.debug(f"Calculated RSI: {rsi:.2f}")

            # Basic price levels
            if len(data) > 0:
                current_price = float(data["Close"].iloc[-1])
                indicators["close"] = current_price
                if "current_price" not in indicators:
                    indicators["current_price"] = current_price

        except Exception as e:
            logger.error(f"Manual calculation error: {e}", exc_info=True)

        logger.info(
            f"Manual calculations completed. Indicators: {list(indicators.keys())}"
        )
        return indicators

    def _calculate_atr_matrix_metrics(
        self, data: pd.DataFrame, indicators: Dict
    ) -> Dict:
        """Calculate ATR Matrix specific metrics."""
        metrics = {}

        try:
            current_price = indicators.get("current_price") or indicators.get("close")
            if not current_price and len(data) > 0:
                current_price = float(data["Close"].iloc[-1])  # Most recent price

            sma_50 = indicators.get("sma_50")
            atr = indicators.get("atr")

            logger.debug(
                f"ATR Matrix calculation - Price: {current_price}, SMA50: {sma_50}, ATR: {atr}"
            )

            if current_price and sma_50 and atr and atr > 0:
                # ATR distance from SMA50 - core of ATR Matrix strategy
                atr_distance = (current_price - sma_50) / atr
                metrics["atr_distance"] = atr_distance

                # ATR as percentage of price - volatility measure
                atr_percent = (atr / current_price) * 100
                metrics["atr_percent"] = atr_percent

                logger.debug(
                    f"ATR distance: {atr_distance:.2f}, ATR percent: {atr_percent:.2f}%"
                )
            else:
                logger.warning(
                    f"Missing critical data for ATR Matrix: price={current_price}, sma50={sma_50}, atr={atr}"
                )

            # MA alignment check - trend confirmation
            ema_10 = indicators.get("ema_10")
            sma_20 = indicators.get("sma_20")
            sma_100 = indicators.get("sma_100")
            sma_200 = indicators.get("sma_200")

            mas = [ema_10, sma_20, sma_50, sma_100, sma_200]
            ma_names = ["EMA10", "SMA20", "SMA50", "SMA100", "SMA200"]

            if all(ma is not None for ma in mas):
                ma_aligned = all(mas[i] >= mas[i + 1] for i in range(len(mas) - 1))
                metrics["ma_aligned"] = ma_aligned
                metrics["ma_alignment"] = ma_aligned  # Both keys for compatibility
                logger.debug(
                    f"MA alignment: {ma_aligned} ({ma_names} = {[f'{ma:.2f}' if ma else 'None' for ma in mas]})"
                )
            else:
                logger.warning(
                    f"Missing MAs for alignment check: {dict(zip(ma_names, mas))}"
                )

            # 20-day price position - momentum indicator
            if len(data) >= 20:
                # For oldest-first data, use rolling window on last 20 periods
                recent_data = data.tail(20)
                high_20 = recent_data["High"].max()
                low_20 = recent_data["Low"].min()

                if high_20 > low_20:
                    price_position = (current_price - low_20) / (high_20 - low_20) * 100
                    metrics["price_position_20d"] = price_position
                    logger.debug(
                        f"20D price position: {price_position:.1f}% (H:{high_20:.2f}, L:{low_20:.2f})"
                    )

        except Exception as e:
            logger.error(f"ATR matrix calculation error: {e}", exc_info=True)

        return metrics

    async def get_stock_info(self, symbol: str) -> Dict:
        """Get basic stock information using the best available API."""
        cache_key = f"stock_info:{symbol}"

        # Check cache first
        cached_info = self.redis_client.get(cache_key)
        if cached_info:
            try:
                return json.loads(cached_info)
            except:
                pass

        try:
            provider = await self._get_best_provider_for_data_type("company_info")
            self._record_api_call(provider)

            info = {}

            if provider == APIProvider.FMP:
                info = await self._get_stock_info_fmp(symbol)
            elif provider == APIProvider.YFINANCE:
                info = await self._get_stock_info_yfinance(symbol)
            elif provider == APIProvider.FINNHUB:
                info = await self._get_stock_info_finnhub(symbol)

            if info:
                # Cache for 1 hour
                self.redis_client.setex(cache_key, 3600, json.dumps(info, default=str))
                return info

        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")

        return {"symbol": symbol, "company_name": symbol}

    async def _get_stock_info_fmp(self, symbol: str) -> Dict:
        """Get stock info from FMP."""
        try:
            profile = fmpsdk.company_profile(apikey=settings.FMP_API_KEY, symbol=symbol)
            if profile and len(profile) > 0:
                data = profile[0]
                return {
                    "symbol": symbol,
                    "company_name": data.get("companyName", symbol),
                    "sector": data.get("sector"),
                    "industry": data.get("industry"),
                    "market_cap": data.get("mktCap"),
                    "price": data.get("price"),
                }
        except Exception as e:
            logger.error(f"FMP stock info error for {symbol}: {e}")
            return {}

    async def _get_stock_info_yfinance(self, symbol: str) -> Dict:
        """Get stock info from yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "company_name": info.get("longName", symbol),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "price": info.get("currentPrice"),
            }
        except Exception as e:
            logger.error(f"yfinance stock info error for {symbol}: {e}")
            return {}

    async def _get_stock_info_finnhub(self, symbol: str) -> Dict:
        """Get stock info from Finnhub."""
        try:
            profile = self.finnhub_client.company_profile2(symbol=symbol)
            return {
                "symbol": symbol,
                "company_name": profile.get("name", symbol),
                "sector": profile.get("finnhubIndustry"),
                "industry": profile.get("finnhubIndustry"),
                "market_cap": profile.get("marketCapitalization"),
                "country": profile.get("country"),
            }
        except Exception as e:
            logger.error(f"Finnhub stock info error for {symbol}: {e}")
            return {}

    # Helper methods for manual calculations (keeping existing implementations)
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        try:
            delta = data["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return None

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Average True Range."""
        try:
            high_low = data["High"] - data["Low"]
            high_close = np.abs(data["High"] - data["Close"].shift())
            low_close = np.abs(data["Low"] - data["Close"].shift())

            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()

            return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
        except Exception as e:
            logger.error(f"ATR calculation error: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if at least one market data API is working."""
        test_symbol = "AAPL"

        for provider in APIProvider:
            if not self._is_provider_available(provider):
                continue

            try:
                if provider == APIProvider.YFINANCE:
                    ticker = yf.Ticker(test_symbol)
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        logger.info(f"Health check passed for {provider.value}")
                        return True
                elif provider == APIProvider.FINNHUB and self.finnhub_client:
                    quote = self.finnhub_client.quote(test_symbol)
                    if quote and "c" in quote:
                        logger.info(f"Health check passed for {provider.value}")
                        return True
                elif provider == APIProvider.FMP and settings.FMP_API_KEY:
                    quote = fmpsdk.quote(
                        apikey=settings.FMP_API_KEY, symbol=test_symbol
                    )
                    if quote and len(quote) > 0:
                        logger.info(f"Health check passed for {provider.value}")
                        return True
                elif provider == APIProvider.TWELVE_DATA and self.twelve_data_client:
                    quote = self.twelve_data_client.quote(symbol=test_symbol)
                    if quote.status == "ok":
                        logger.info(f"Health check passed for {provider.value}")
                        return True
            except Exception as e:
                logger.warning(f"Health check failed for {provider.value}: {e}")
                continue

        logger.error("All API health checks failed")
        return False

    # ----------------------------
    # Moving Averages & Buckets
    # ----------------------------
    async def get_moving_averages(self, symbol: str) -> Dict[str, float]:
        """Return SMA and EMA for 5,8,21,50,100,200 using last 200 closes."""
        df = await self.get_historical_data(symbol, period="1y", interval="1d")
        if df is None or df.empty:
            return {}
        closes = df.iloc[::-1]["Close"]  # oldest->newest
        out: Dict[str, float] = {}
        periods = [5, 8, 21, 50, 100, 200]
        for n in periods:
            if len(closes) >= n:
                out[f"sma_{n}"] = float(closes.rolling(n).mean().iloc[-1])
                out[f"ema_{n}"] = float(
                    closes.ewm(span=n, adjust=False).mean().iloc[-1]
                )
        out["price"] = float(df["Close"].iloc[0])
        return out

    async def classify_ma_bucket(self, symbol: str) -> Dict[str, Any]:
        """Classify as LEADING if price > 5 > 8 > 21 > 50 > 100 > 200; LAGGING if strictly opposite."""
        ma = await self.get_moving_averages(symbol)
        if not ma:
            return {"symbol": symbol, "bucket": "UNKNOWN", "data": {}}
        seq = [
            ma.get("price"),
            ma.get("sma_5"),
            ma.get("sma_8"),
            ma.get("sma_21"),
            ma.get("sma_50"),
            ma.get("sma_100"),
            ma.get("sma_200"),
        ]
        if all(isinstance(x, float) for x in seq):
            strictly_desc = all(seq[i] > seq[i + 1] for i in range(len(seq) - 1))
            strictly_asc = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
            bucket = (
                "LEADING"
                if strictly_desc
                else ("LAGGING" if strictly_asc else "NEUTRAL")
            )
        else:
            bucket = "UNKNOWN"
        return {"symbol": symbol, "bucket": bucket, "data": ma}

    # ----------------------------
    # Stage Analysis (Mark Minervini-inspired simplification)
    # ----------------------------
    async def get_stage_analysis(self, symbol: str) -> Dict[str, Any]:
        """Deprecated: replaced by get_weinstein_stage (weekly 30W SMA + RS)."""
        return await self.get_weinstein_stage(symbol)

    def _weekly_from_daily(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """Convert daily OHLCV (newest-first DataFrame) to weekly (oldest->newest)."""
        if df_daily is None or df_daily.empty:
            return pd.DataFrame()
        daily = df_daily.iloc[::-1].copy()  # oldest->newest
        weekly = pd.DataFrame()
        weekly["Open"] = daily["Open"].resample("W-FRI").first()
        weekly["High"] = daily["High"].resample("W-FRI").max()
        weekly["Low"] = daily["Low"].resample("W-FRI").min()
        weekly["Close"] = daily["Close"].resample("W-FRI").last()
        weekly["Volume"] = daily["Volume"].resample("W-FRI").sum()
        weekly = weekly.dropna()
        return weekly

    async def get_weinstein_stage(
        self, symbol: str, benchmark: str = "SPY"
    ) -> Dict[str, Any]:
        """Stan Weinstein Stage Analysis (weekly):
        - Weekly bars, 30-week SMA, its slope
        - Relative Strength vs benchmark and its slope
        - Volume vs 50-week average
        Classification:
        - Stage 2: price > SMA30w, SMA30w rising, RS rising
        - Stage 4: price < SMA30w, SMA30w falling, RS falling
        - Stage 1: SMA30w flat (|slope| small) and price near SMA30w
        - Stage 3: otherwise
        """
        daily_sym = await self.get_historical_data(symbol, period="5y", interval="1d")
        if daily_sym is None or daily_sym.empty:
            return {"symbol": symbol, "stage": "UNKNOWN"}
        daily_bm = await self.get_historical_data(benchmark, period="5y", interval="1d")
        if daily_bm is None or daily_bm.empty:
            return {"symbol": symbol, "stage": "UNKNOWN"}

        w_sym = self._weekly_from_daily(daily_sym)
        w_bm = self._weekly_from_daily(daily_bm)
        if w_sym.empty or w_bm.empty:
            return {"symbol": symbol, "stage": "UNKNOWN"}

        # Align indexes
        idx = w_sym.index.intersection(w_bm.index)
        w_sym = w_sym.loc[idx]
        w_bm = w_bm.loc[idx]
        if len(w_sym) < 60:  # need enough weeks
            return {"symbol": symbol, "stage": "UNKNOWN"}

        close = w_sym["Close"]
        sma30 = close.rolling(30).mean()
        vol50 = w_sym["Volume"].rolling(50).mean()

        # RS vs benchmark
        rs = close / w_bm["Close"].replace(0, pd.NA)
        rs = rs.dropna()

        def slope(series: pd.Series, window: int = 10) -> float:
            last = series.tail(window)
            if len(last) < 2:
                return 0.0
            return float(last.iloc[-1] - last.iloc[0]) / max(1.0, len(last) - 1)

        price = float(close.iloc[-1])
        sma30_now = float(sma30.iloc[-1]) if not pd.isna(sma30.iloc[-1]) else None
        sma30_slope = slope(sma30)
        rs_slope = slope(rs)
        vol_ratio = None
        if not pd.isna(vol50.iloc[-1]) and vol50.iloc[-1] > 0:
            vol_ratio = float(w_sym["Volume"].iloc[-1] / vol50.iloc[-1])

        # Classify
        stage = "UNKNOWN"
        if sma30_now:
            up = price > sma30_now and sma30_slope > 0 and rs_slope > 0
            down = price < sma30_now and sma30_slope < 0 and rs_slope < 0
            if up:
                stage = "STAGE_2_UPTREND"
            elif down:
                stage = "STAGE_4_DOWNTREND"
            else:
                flat = abs(sma30_slope) <= max(1e-6, sma30_now * 0.0001)
                near = abs(price - sma30_now) <= sma30_now * 0.03
                stage = "STAGE_1_BASE" if flat and near else "STAGE_3_DISTRIBUTION"

        return {
            "symbol": symbol,
            "benchmark": benchmark,
            "stage": stage,
            "price": price,
            "sma30w": sma30_now,
            "sma30w_slope": sma30_slope,
            "rs_slope": rs_slope,
            "vol_ratio_50w": vol_ratio,
            "as_of": idx[-1].isoformat(),
        }


# Popular stocks list for scanning
POPULAR_STOCKS = [
    # Tech Giants
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "NVDA",
    "NFLX",
    "CRM",
    "ORCL",
    # Financial
    "JPM",
    "BAC",
    "WFC",
    "GS",
    "MS",
    "C",
    "BLK",
    "AXP",
    "V",
    "MA",
    # Healthcare
    "JNJ",
    "PFE",
    "UNH",
    "MRK",
    "ABBV",
    "TMO",
    "MDT",
    "BMY",
    "AMGN",
    "GILD",
    # Consumer
    "KO",
    "PEP",
    "WMT",
    "TGT",
    "HD",
    "LOW",
    "MCD",
    "SBUX",
    "NKE",
    "DIS",
    # Industrial
    "BA",
    "CAT",
    "GE",
    "MMM",
    "UPS",
    "FDX",
    "HON",
    "LMT",
    "RTX",
    "DE",
    # Energy
    "XOM",
    "CVX",
    "COP",
    "EOG",
    "SLB",
    "PSX",
    "VLO",
    "MPC",
    "OXY",
    "HAL",
    # Communications
    "VZ",
    "T",
    "CMCSA",
    "CHTR",
    "TMUS",
    "DISH",
    # Real Estate
    "AMT",
    "PLD",
    "CCI",
    "EQIX",
    "SPG",
    "O",
    "WELL",
    "AVB",
    "EQR",
    "BXP",
    # Utilities
    "NEE",
    "DUK",
    "SO",
    "D",
    "AEP",
    "EXC",
    "XEL",
    "ED",
    "ETR",
    "ES",
    # Materials
    "LIN",
    "APD",
    "SHW",
    "ECL",
    "FCX",
    "NEM",
    "DOW",
    "DD",
    "PPG",
    "IFF",
    # Technology
    "ADBE",
    "INTC",
    "CSCO",
    "IBM",
    "QCOM",
    "TXN",
    "AVGO",
    "MU",
    "AMD",
    "NOW",
]

# Global instance
market_data_service = MarketDataService()

logger = logging.getLogger(__name__)


class FreeMarketDataService:
    """
    Comprehensive FREE market data service using multiple sources:
    - Yahoo Finance (FREE, real-time)
    - Alpha Vantage (FREE tier: 500 requests/day)
    - TastyTrade (already connected, real-time options)
    - Fallback to cached IBKR data
    """

    def __init__(self):
        self.yahoo_base_url = "https://query1.finance.yahoo.com"
        self.alpha_vantage_api_key = "demo"  # Replace with real key for production
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes

    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from multiple FREE sources"""
        try:
            # Try Yahoo Finance first (most reliable and free)
            price = await self._get_yahoo_price(symbol)
            if price:
                logger.info(f"✅ Yahoo Finance price for {symbol}: ${price}")
                return price

            # Fallback to Alpha Vantage
            price = await self._get_alpha_vantage_price(symbol)
            if price:
                logger.info(f"✅ Alpha Vantage price for {symbol}: ${price}")
                return price

            logger.warning(
                f"❌ Could not get real-time price for {symbol} from free sources"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting real-time price for {symbol}: {e}")
            return None

    async def _get_yahoo_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from Yahoo Finance (FREE)"""
        try:
            url = (
                f"{self.yahoo_base_url}/v8/finance/chart/{symbol}?range=1d&interval=1m"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("chart", {}).get("result"):
                            result = data["chart"]["result"][0]
                            price = result.get("meta", {}).get("regularMarketPrice")

                            if price:
                                return float(price)

        except Exception as e:
            logger.debug(f"Yahoo Finance failed for {symbol}: {e}")

        return None

    async def _get_alpha_vantage_price(self, symbol: str) -> Optional[float]:
        """Get real-time price from Alpha Vantage (FREE tier)"""
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.alpha_vantage_api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        global_quote = data.get("Global Quote", {})
                        price = global_quote.get("05. price")

                        if price:
                            return float(price)

        except Exception as e:
            logger.debug(f"Alpha Vantage failed for {symbol}: {e}")

        return None

    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get real-time prices for multiple symbols efficiently"""
        try:
            # Create tasks for concurrent requests
            tasks = [self.get_real_time_price(symbol) for symbol in symbols]
            prices = await asyncio.gather(*tasks, return_exceptions=True)

            result = {}
            for symbol, price in zip(symbols, prices):
                if isinstance(price, float) and price > 0:
                    result[symbol] = price
                else:
                    logger.warning(f"Failed to get price for {symbol}")

            return result

        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            return {}

    async def get_options_chain_from_tastytrade(self, symbol: str) -> Dict[str, Any]:
        """Get real-time options data from TastyTrade (already connected)"""
        try:
            from backend.services.tastytrade_client import tastytrade_client

            # Get options chain from TastyTrade
            options_data = await tastytrade_client.get_options_chain(symbol)

            if options_data:
                logger.info(
                    f"✅ TastyTrade options data for {symbol}: {len(options_data)} contracts"
                )
                return options_data

        except Exception as e:
            logger.error(f"Error getting TastyTrade options for {symbol}: {e}")

        return {}

    async def update_portfolio_with_real_time_prices(
        self, holdings: List[Any]
    ) -> List[Dict[str, Any]]:
        """Update portfolio holdings with real-time prices from FREE sources"""
        try:
            # Extract unique symbols
            symbols = list(set([h.symbol for h in holdings if h.symbol]))

            # Get real-time prices
            real_time_prices = await self.get_multiple_prices(symbols)

            updated_holdings = []

            for holding in holdings:
                holding_dict = {
                    "symbol": holding.symbol,
                    "quantity": holding.quantity,
                    "average_cost": holding.average_cost,
                    "market_value": holding.market_value,
                    "unrealized_pnl": holding.unrealized_pnl,
                    "contract_type": holding.contract_type,
                    "sector": holding.sector,
                }

                # Update with real-time price if available
                if holding.symbol in real_time_prices:
                    real_time_price = real_time_prices[holding.symbol]
                    real_time_market_value = abs(holding.quantity) * real_time_price

                    # Calculate real-time P&L
                    cost_basis = abs(holding.quantity) * holding.average_cost
                    real_time_pnl = real_time_market_value - cost_basis
                    real_time_pnl_pct = (
                        (real_time_pnl / cost_basis * 100) if cost_basis > 0 else 0
                    )

                    holding_dict.update(
                        {
                            "current_price": real_time_price,
                            "market_value": real_time_market_value,
                            "unrealized_pnl": real_time_pnl,
                            "unrealized_pnl_pct": real_time_pnl_pct,
                            "data_source": "free_real_time",
                        }
                    )
                else:
                    holding_dict.update(
                        {
                            "current_price": holding.current_price,
                            "data_source": "cached",
                        }
                    )

                updated_holdings.append(holding_dict)

            logger.info(
                f"✅ Updated {len(updated_holdings)} holdings with real-time data from FREE sources"
            )
            return updated_holdings

        except Exception as e:
            logger.error(f"Error updating portfolio with real-time prices: {e}")
            return []


# Create global instance
free_market_data_service = FreeMarketDataService()
