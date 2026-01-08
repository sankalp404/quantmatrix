from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import timedelta

import finnhub
import fmpsdk
import pandas as pd
import redis
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.config import settings
from backend.database import SessionLocal
from backend.models import MarketSnapshot
from backend.models.market_data import PriceData
from backend.models.index_constituent import IndexConstituent
from backend.services.market.indicator_engine import (
    calculate_performance_windows,
    classify_ma_bucket_from_ma,
    compute_atr_matrix_metrics,
    compute_core_indicators,
    compute_gap_counts,
    compute_td_sequential_counts,
    compute_trendline_counts,
    compute_weinstein_stage_from_daily,
)

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    FINNHUB = "finnhub"
    TWELVE_DATA = "twelve_data"
    FMP = "fmp"
    YFINANCE = "yfinance"


class MarketDataService:
    """Market data facade with a clean, policy-driven provider strategy.

    Responsibilities:
    - Provider routing (paid vs free) for quotes and historical OHLCV
    - Caching of quotes/series in Redis
    - Building technical snapshots from local DB first (fast path),
      falling back to provider fetch when needed (slow path)
    - Enriching snapshots with chart metrics and fundamentals
    - Persisting snapshots to MarketSnapshot

    Policy:
    - paid: prefer FMP for historical/quotes; yfinance fallback
    - free: FMP (if key) + yfinance + Twelve Data (if key) + finnhub
    """

    def __init__(self) -> None:
        self._redis_client = None
        self.cache_ttl_seconds = int(getattr(settings, "MARKET_DATA_CACHE_TTL", 300))

        # Optional API clients
        self.finnhub_client = (
            finnhub.Client(api_key=settings.FINNHUB_API_KEY)
            if settings.FINNHUB_API_KEY
            else None
        )

        self.twelve_data_client = None
        try:
            from twelvedata import TDClient  # lazy import
            if settings.TWELVE_DATA_API_KEY:
                self.twelve_data_client = TDClient(apikey=settings.TWELVE_DATA_API_KEY)
        except Exception:
            self.twelve_data_client = None

        if settings.FMP_API_KEY:
            logger.info("FMP API configured")

        # Index endpoints for constituents
        self.index_endpoints = {
            "SP500": {"fmp": "sp500_constituent"},
            "NASDAQ100": {"fmp": "nasdaq_constituent"},
            "DOW30": {"fmp": "dowjones_constituent"},
        }

    @property
    def redis_client(self) -> redis.Redis:
        if self._redis_client is None:
            url = getattr(settings, "REDIS_URL", None)
            if not url:
                raise RuntimeError("REDIS_URL is not configured")
            self._redis_client = redis.from_url(url)
        return self._redis_client

    # ---------------------- Internal helpers ----------------------
    def _visibility_scope(self) -> str:
        return "all_authenticated" if settings.MARKET_DATA_SECTION_PUBLIC else "admin_only"

    def _snapshot_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Common snapshot builder used by DB and provider flows."""
        if df is None or df.empty or "Close" not in df.columns:
            return {}

        price = float(df["Close"].iloc[0])
        data_for_ta = df.iloc[::-1].copy()
        indicators = compute_core_indicators(data_for_ta)
        indicators["current_price"] = price
        indicators.update(compute_atr_matrix_metrics(data_for_ta, indicators))
        indicators.update(calculate_performance_windows(df))

        sma_50 = indicators.get("sma_50")
        sma_200 = indicators.get("sma_200")
        ema_8 = indicators.get("ema_8")
        ema_21 = indicators.get("ema_21")
        ema_200 = indicators.get("ema_200")
        atr = indicators.get("atr")

        def pct_dist(val: Optional[float]) -> Optional[float]:
            return (price / val - 1.0) * 100.0 if (val and price) else None

        def atr_dist(val: Optional[float]) -> Optional[float]:
            return ((price - val) / atr) if (val and price and atr and atr != 0) else None

        ma_for_bucket = {
            "price": price,
            "sma_5": indicators.get("sma_5"),
            "sma_8": indicators.get("sma_8"),
            "sma_21": indicators.get("sma_21"),
            "sma_50": indicators.get("sma_50"),
            "sma_100": indicators.get("sma_100"),
            "sma_200": indicators.get("sma_200"),
        }
        bucket = classify_ma_bucket_from_ma(ma_for_bucket).get("bucket")

        snapshot: Dict[str, Any] = {
            "current_price": price,
            "rsi": indicators.get("rsi"),
            "atr_value": atr,
            "atr_percent": ((atr / price) * 100.0) if (atr and price) else None,
            "atr_distance": ((price - sma_50) / atr) if (price and sma_50 and atr) else None,
            "sma_20": indicators.get("sma_20"),
            "sma_50": sma_50,
            "sma_100": indicators.get("sma_100"),
            "sma_200": sma_200,
            "ema_10": indicators.get("ema_10"),
            "ema_8": ema_8,
            "ema_21": ema_21,
            "ema_200": ema_200,
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "perf_1d": indicators.get("perf_1d"),
            "perf_3d": indicators.get("perf_3d"),
            "perf_5d": indicators.get("perf_5d"),
            "perf_20d": indicators.get("perf_20d"),
            "perf_60d": indicators.get("perf_60d"),
            "perf_120d": indicators.get("perf_120d"),
            "perf_252d": indicators.get("perf_252d"),
            "perf_mtd": indicators.get("perf_mtd"),
            "perf_qtd": indicators.get("perf_qtd"),
            "perf_ytd": indicators.get("perf_ytd"),
            "ma_bucket": bucket,
            "pct_dist_ema8": pct_dist(ema_8),
            "pct_dist_ema21": pct_dist(ema_21),
            "pct_dist_ema200": pct_dist(ema_200 or sma_200),
            "atr_dist_ema8": atr_dist(ema_8),
            "atr_dist_ema21": atr_dist(ema_21),
            "atr_dist_ema200": atr_dist(ema_200 or sma_200),
        }

        # Chart metrics (TD Sequential, gaps, trendlines)
        try:
            df_newest = df.head(120).copy()
            if not df_newest.empty:
                td = compute_td_sequential_counts(df_newest["Close"].tolist())
                snapshot.update(td)
                snapshot.update(compute_gap_counts(df_newest))
                snapshot.update(compute_trendline_counts(df_newest.iloc[::-1].copy()))
        except Exception:
            pass
        for key in ("stage_label", "stage_slope_pct", "stage_dist_pct"):
            snapshot.setdefault(key, None)

        return snapshot

    @staticmethod
    def _needs_fundamentals(snapshot: Dict[str, Any]) -> bool:
        return (
            snapshot.get("sector") is None
            and snapshot.get("industry") is None
            and snapshot.get("market_cap") is None
        )


    # ---------------------- Provider selection ----------------------
    def _provider_priority(self, data_type: str) -> List[APIProvider]:
        """Return provider order based on MARKET_PROVIDER_POLICY and availability.

        data_type: "historical_data" | "real_time_quote" | "company_info"
        paid policy: [FMP, yfinance]
        free policy: [FMP?] + yfinance + [Twelve Data?] + finnhub
        """
        policy = str(getattr(settings, "MARKET_PROVIDER_POLICY", "paid")).lower()
        has_fmp = bool(settings.FMP_API_KEY)
        has_td = bool(settings.TWELVE_DATA_API_KEY)
        if data_type == "historical_data":
            if policy == "paid":
                # Prefer FMP; in paid mode use Twelve Data before yfinance to avoid CF issues
                if has_fmp and has_td:
                    return [APIProvider.FMP, APIProvider.TWELVE_DATA, APIProvider.YFINANCE]
                if has_fmp:
                    return [APIProvider.FMP, APIProvider.YFINANCE]
                if has_td:
                    return [APIProvider.TWELVE_DATA, APIProvider.YFINANCE]
                return [APIProvider.YFINANCE]
            order: List[APIProvider] = []
            if has_fmp:
                order.append(APIProvider.FMP)
            order.append(APIProvider.YFINANCE)
            if has_td:
                order.append(APIProvider.TWELVE_DATA)
            order.append(APIProvider.FINNHUB)
            return order
        if data_type == "real_time_quote":
            return [APIProvider.FMP, APIProvider.YFINANCE]
        if data_type == "company_info":
            return [APIProvider.FMP, APIProvider.YFINANCE]
        return [APIProvider.YFINANCE]

    def _is_provider_available(self, provider: APIProvider) -> bool:
        if provider == APIProvider.FMP:
            return bool(settings.FMP_API_KEY)
        if provider == APIProvider.TWELVE_DATA:
            return self.twelve_data_client is not None
        if provider == APIProvider.FINNHUB:
            return self.finnhub_client is not None
        if provider == APIProvider.YFINANCE:
            return True
        return False

    # ---------------------- Quotes and history ----------------------
    @staticmethod
    def _extract_http_status(exc: Exception) -> Optional[int]:
        """Best-effort extraction of HTTP status code from provider exceptions."""
        try:
            # requests/httpx style
            resp = getattr(exc, "response", None)
            if resp is not None:
                code = getattr(resp, "status_code", None)
                if isinstance(code, int):
                    return code
        except Exception:
            pass
        for attr in ("status_code", "status"):
            try:
                code = getattr(exc, attr, None)
                if isinstance(code, int):
                    return code
            except Exception:
                continue
        # Last resort: parse digits from message
        try:
            msg = str(exc)
            for needle in ("429", "500", "502", "503", "504"):
                if needle in msg:
                    return int(needle)
        except Exception:
            pass
        return None

    async def _call_blocking_with_retries(
        self,
        fn,
        *args,
        attempts: Optional[int] = None,
        max_delay_seconds: Optional[float] = None,
        **kwargs,
    ):
        """Run a blocking provider call in a thread with bounded exponential backoff.

        We use this to make provider calls concurrency-safe (they don't block the event loop),
        and resilient (429/5xx/backoff and continue).
        """
        n = int(attempts or int(getattr(settings, "MARKET_BACKFILL_RETRY_ATTEMPTS", 6)))
        max_delay = float(
            max_delay_seconds
            if max_delay_seconds is not None
            else float(getattr(settings, "MARKET_BACKFILL_RETRY_MAX_DELAY_SECONDS", 60.0))
        )
        last_exc: Optional[Exception] = None
        for i in range(max(1, n)):
            try:
                return await asyncio.to_thread(fn, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001 (provider libs raise wide exceptions)
                last_exc = exc
                status = self._extract_http_status(exc)
                # Backoff for rate limits and transient upstream errors; otherwise keep it short.
                is_rate_limited = status == 429 or "Too Many" in str(exc)
                is_transient = status in (429, 500, 502, 503, 504) or is_rate_limited
                if i >= n - 1:
                    break
                base = 0.8 if is_transient else 0.2
                delay = min(max_delay, base * (2**i))
                # jitter in [0.75x, 1.25x]
                delay = delay * (0.75 + random.random() * 0.5)
                await asyncio.sleep(delay)
        if last_exc:
            raise last_exc
        raise RuntimeError("provider call failed without exception")

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol with provider policy and 60s Redis cache."""
        cache_key = f"price:{symbol}"
        cached = self.redis_client.get(cache_key)
        if cached:
            try:
                return float(cached)
            except Exception:
                pass
        for provider in self._provider_priority("real_time_quote"):
            if not self._is_provider_available(provider):
                continue
            try:
                price = None
                if provider == APIProvider.FMP:
                    q = fmpsdk.quote(apikey=settings.FMP_API_KEY, symbol=symbol)
                    price = q and len(q) > 0 and q[0].get("price")
                elif provider == APIProvider.YFINANCE:
                    hist = yf.Ticker(symbol).history(period="1d", interval="1m")
                    price = float(hist["Close"].iloc[-1]) if not hist.empty else None
                if price is not None:
                    self.redis_client.setex(cache_key, 60, str(price))
                    return float(price)
            except Exception:
                continue
        return None

    def get_fundamentals_info(self, symbol: str) -> Dict[str, Any]:
        """Return fundamentals for a symbol using FMP first, then yfinance.

        Returns keys: name, sector, industry, sub_industry, market_cap when available.
        """
        info: Dict[str, Any] = {}
        try:
            if settings.FMP_API_KEY:
                prof = fmpsdk.company_profile(apikey=settings.FMP_API_KEY, symbol=symbol)
                if prof and len(prof) > 0 and isinstance(prof[0], dict):
                    d = prof[0]
                    info = {
                        "name": d.get("companyName") or d.get("company_name") or d.get("symbol"),
                        "sector": d.get("sector"),
                        "industry": d.get("industry"),
                        "sub_industry": d.get("subIndustry") or d.get("sub_industry"),
                        "market_cap": d.get("mktCap"),
                    }
        except Exception:
            pass
        if not info:
            try:
                y = yf.Ticker(symbol).info
                info = {
                    "name": y.get("shortName") or y.get("longName") or y.get("symbol"),
                    "sector": y.get("sector"),
                    "industry": y.get("industry"),
                    "sub_industry": y.get("subIndustry") or y.get("industry") or None,
                    "market_cap": y.get("marketCap"),
                }
            except Exception:
                info = {}
        return info

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        max_bars: Optional[int] = 270,
        return_provider: bool = False,
    ) -> Optional[pd.DataFrame] | tuple[Optional[pd.DataFrame], Optional[str]]:
        """Get OHLCV (newest->first index) with provider policy, returning provider when requested.

        - Trims to max_bars for interval==1d to bound downstream compute
        - Cache TTL: 300s for intraday; 3600s for daily+
        """
        cache_key = f"historical:{symbol}:{period}:{interval}"
        cached = self.redis_client.get(cache_key)
        if cached:
            try:
                df_cached = pd.read_json(cached, orient="index")
                if return_provider:
                    return df_cached, None
                return df_cached
            except Exception:
                pass

        provider_used: Optional[str] = None
        for provider in self._provider_priority("historical_data"):
            if not self._is_provider_available(provider):
                continue
            try:
                if provider == APIProvider.FMP:
                    # Support daily and intraday (5m) for FMP
                    if interval == "5m":
                        df = await self._call_blocking_with_retries(self._get_historical_fmp_5m_sync, symbol, period)
                    else:
                        df = await self._call_blocking_with_retries(self._get_historical_fmp_sync, symbol, period, interval)
                elif provider == APIProvider.TWELVE_DATA:
                    df = await self._call_blocking_with_retries(self._get_historical_twelve_data_sync, symbol, period, interval)
                elif provider == APIProvider.YFINANCE:
                    df = await self._call_blocking_with_retries(self._get_historical_yfinance_sync, symbol, period, interval)
                elif provider == APIProvider.FINNHUB:
                    df = None  # not implemented
                else:
                    df = None
                if df is not None and not df.empty:
                    provider_used = provider.value
                    if max_bars and interval == "1d":
                        df = df.head(max_bars)
                    ttl = 300 if interval in ("1m", "5m") else 3600
                    self.redis_client.setex(cache_key, ttl, df.to_json(orient="index"))
                    if return_provider:
                        return df, provider_used
                    return df
            except Exception:
                continue
        return (None, provider_used) if return_provider else None

    def _get_historical_yfinance_sync(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        try:
            data = yf.Ticker(symbol).history(period=period, interval=interval)
            if data is None or data.empty:
                return None
            required = ["Open", "High", "Low", "Close"]
            if not any(c in data.columns for c in required):
                return None
            if "Volume" not in data.columns:
                data["Volume"] = 0
            return data[[c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]].sort_index(ascending=False)
        except Exception:
            return None

    def _get_historical_fmp_5m_sync(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """Fetch intraday 5m bars from FMP historical_chart.

        FMP returns newest-first timestamps. `period` is best-effort: we trim using days.
        """
        try:
            # FMP supports intervals like '5min'
            data = fmpsdk.historical_chart(
                apikey=settings.FMP_API_KEY, symbol=symbol, interval="5min"
            )
            if not data or not isinstance(data, list):
                return None
            df = pd.DataFrame(data)
            # Normalize columns and index
            if df.empty or "date" not in df.columns:
                return None
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            cols = ["open", "high", "low", "close", "volume"]
            df = df[[c for c in cols if c in df.columns]]
            df.columns = ["Open", "High", "Low", "Close", "Volume"][: len(df.columns)]
            # Best-effort period trim (e.g., '5d', '30d', '60d')
            try:
                if isinstance(period, str) and period.endswith("d"):
                    days = int(period[:-1])
                    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=days)
                    df = df[df.index >= cutoff]
            except Exception:
                pass
            return df.sort_index(ascending=False)
        except Exception:
            return None

    def _get_historical_twelve_data_sync(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        if not self.twelve_data_client:
            return None
        try:
            td_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "1h",
                "1d": "1day",
                "1wk": "1week",
                "1mo": "1month",
            }
            ts = self.twelve_data_client.time_series(
                symbol=symbol, interval=td_map.get(interval, "1day"), outputsize="5000"
            )
            df = ts.as_pandas()
            if df is None or df.empty:
                return None
            out = pd.DataFrame(index=df.index)
            for src, dst in [("open", "Open"), ("high", "High"), ("low", "Low"), ("close", "Close"), ("volume", "Volume")]:
                if src in df.columns:
                    out[dst] = df[src]
                elif src.capitalize() in df.columns:
                    out[dst] = df[src.capitalize()]
            if "Close" not in out.columns:
                return None
            if "Volume" not in out.columns:
                out["Volume"] = 0
            return out.sort_index(ascending=False)
        except Exception:
            return None

    def _get_historical_fmp_sync(
        self, symbol: str, period: str, interval: str
    ) -> Optional[pd.DataFrame]:
        try:
            if interval != "1d":
                return None
            data = fmpsdk.historical_price_full(apikey=settings.FMP_API_KEY, symbol=symbol)
            # FMP can return either {"symbol": ..., "historical": [...]} or a plain list
            if isinstance(data, dict):
                data = data.get("historical")
            if not data or not isinstance(data, list):
                return None
            df = pd.DataFrame(data)
            if df.empty or "date" not in df.columns:
                return None
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            cols = ["open", "high", "low", "close", "volume"]
            df = df[[c for c in cols if c in df.columns]]
            df.columns = ["Open", "High", "Low", "Close", "Volume"][: len(df.columns)]
            return df.sort_index(ascending=False)
        except Exception:
            return None

    # ---------------------- Index Constituents ----------------------

    async def get_index_constituents(self, index_name: str) -> List[str]:
        """Return constituents for supported indices (SP500, NASDAQ100, DOW30).

        Strategy: Redis cache → FMP → Wikipedia fallback. Normalized to UPPER and '.'→'-'.
        """
        cache_key = f"index_constituents:{index_name}"
        # Redis cache
        cached = self.redis_client.get(cache_key)
        if cached:
            try:
                obj = json.loads(cached)
                if isinstance(obj, dict) and obj.get("symbols"):
                    return list(obj.get("symbols"))
            except Exception:
                pass
        idx = index_name.upper()
        ep = self.index_endpoints.get(idx, {}).get("fmp")
        symbols: List[str] = []
        # FMP
        if settings.FMP_API_KEY and ep:
            try:
                fn = getattr(fmpsdk, ep, None)
                data = fn(apikey=settings.FMP_API_KEY) if callable(fn) else []
            except Exception:
                data = []
            if isinstance(data, list):
                symbols = [str(d.get("symbol", "")).strip().upper().replace('.', '-') for d in data if d.get("symbol")]
        # Track which path we used
        provider_used = "fmp" if symbols else None
        # Wikipedia fallback
        if not symbols:
            import pandas as _pd
            try:
                if idx == "SP500":
                    tables = _pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
                    if tables:
                        df = tables[0]
                        if "Symbol" in df.columns:
                            symbols = [str(s).upper().replace('.', '-') for s in df["Symbol"].dropna().tolist()]
                elif idx == "NASDAQ100":
                    tables = _pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
                    for t in tables:
                        for col in ["Ticker", "Symbol", "Company", "Stock Symbol"]:
                            if col in t.columns:
                                symbols = [str(s).upper().replace('.', '-') for s in t[col].dropna().tolist()]
                                break
                        if symbols:
                            break
                elif idx == "DOW30":
                    tables = _pd.read_html("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
                    for t in tables:
                        if "Symbol" in t.columns and len(t) <= 40:
                            symbols = [str(s).upper().replace('.', '-') for s in t["Symbol"].dropna().tolist()]
                            break
            except Exception:
                symbols = []
        fallback_used = False if provider_used == "fmp" and symbols else (True if not provider_used else False)
        provider_used = provider_used or ("wikipedia" if symbols else "none")
        # Normalize and cache
        out = sorted(list({s for s in symbols if s and len(s) <= 5}))
        try:
            self.redis_client.setex(cache_key, 24 * 3600, json.dumps({"symbols": out}))
            # Store lightweight meta for observability
            meta_key = f"{cache_key}:meta"
            self.redis_client.setex(
                meta_key,
                24 * 3600,
                json.dumps({"provider_used": provider_used, "fallback_used": bool(fallback_used), "count": len(out)}),
            )
        except Exception:
            pass
        return out

    async def get_all_tradeable_symbols(self, indices: Optional[List[str]] = None) -> Dict[str, List[str]]:
        idxs = ["SP500", "NASDAQ100", "DOW30"] if not indices else [i.upper() for i in indices]
        result: Dict[str, List[str]] = {}
        for idx in idxs:
            try:
                result[idx] = await self.get_index_constituents(idx)
            except Exception:
                result[idx] = []
        return result


    # ---------------------- Snapshots ----------------------
    async def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Return the latest technical snapshot for a symbol.

        Flow:
        1) Try existing stored snapshot in MarketSnapshot (respect expiry)
        2) If not present/stale: build from local DB prices (fast path)
        3) If still missing: compute from provider OHLCV (slow path)
        4) Persist refreshed snapshot and return
        """
        session = SessionLocal()
        try:
            # 1) Try stored snapshot first
            snap = self.get_snapshot_from_store(session, symbol)
            # 2) Build and persist if missing/stale
            if not snap:
                snap = self.compute_snapshot_from_db(session, symbol)
            if not snap:
                snap = await self.compute_snapshot_from_providers(symbol)
            if snap:
                self.persist_snapshot(session, symbol, snap)
            return snap or {}
        finally:
            session.close()

    def get_snapshot_from_store(self, db: Session, symbol: str) -> Dict[str, Any]:
        """Fetch freshest snapshot from MarketSnapshot if not expired.

        Returns raw_analysis if available; otherwise rebuilds a dict from mapped columns.
        """
        now = datetime.utcnow()
        row = (
            db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.symbol == symbol,
                MarketSnapshot.analysis_type == "technical_snapshot",
            )
            .order_by(MarketSnapshot.analysis_timestamp.desc())
            .first()
        )
        if not row:
            return {}
        exp = row.expiry_timestamp
        try:
            if exp is not None and getattr(exp, 'tzinfo', None) is not None:
                exp = exp.replace(tzinfo=None)
        except Exception:
            pass
        if exp and exp < now:
            return {}
        try:
            if isinstance(row.raw_analysis, dict) and row.raw_analysis:
                return dict(row.raw_analysis)
        except Exception:
            pass
        # Fallback: minimal reconstruction from mapped columns
        out: Dict[str, Any] = {
            "current_price": getattr(row, "current_price", None),
            "rsi": getattr(row, "rsi", None),
            "atr_value": getattr(row, "atr_value", None),
            "sma_20": getattr(row, "sma_20", None),
            "sma_50": getattr(row, "sma_50", None),
            "sma_100": getattr(row, "sma_100", None),
            "sma_200": getattr(row, "sma_200", None),
            "ema_10": getattr(row, "ema_10", None),
            "ema_8": getattr(row, "ema_8", None),
            "ema_21": getattr(row, "ema_21", None),
            "ema_200": getattr(row, "ema_200", None),
            "macd": getattr(row, "macd", None),
            "macd_signal": getattr(row, "macd_signal", None),
            "perf_1d": getattr(row, "perf_1d", None),
            "perf_3d": getattr(row, "perf_3d", None),
            "perf_5d": getattr(row, "perf_5d", None),
            "perf_20d": getattr(row, "perf_20d", None),
            "perf_60d": getattr(row, "perf_60d", None),
            "perf_120d": getattr(row, "perf_120d", None),
            "perf_252d": getattr(row, "perf_252d", None),
            "perf_mtd": getattr(row, "perf_mtd", None),
            "perf_qtd": getattr(row, "perf_qtd", None),
            "perf_ytd": getattr(row, "perf_ytd", None),
            "ma_bucket": getattr(row, "ma_bucket", None),
            "pct_dist_ema8": getattr(row, "pct_dist_ema8", None),
            "pct_dist_ema21": getattr(row, "pct_dist_ema21", None),
            "pct_dist_ema200": getattr(row, "pct_dist_ema200", None),
            "atr_dist_ema8": getattr(row, "atr_dist_ema8", None),
            "atr_dist_ema21": getattr(row, "atr_dist_ema21", None),
            "atr_dist_ema200": getattr(row, "atr_dist_ema200", None),
            "td_buy_setup": getattr(row, "td_buy_setup", None),
            "td_sell_setup": getattr(row, "td_sell_setup", None),
            "gaps_unfilled_up": getattr(row, "gaps_unfilled_up", None),
            "gaps_unfilled_down": getattr(row, "gaps_unfilled_down", None),
            "trend_up_count": getattr(row, "trend_up_count", None),
            "trend_down_count": getattr(row, "trend_down_count", None),
            "stage_label": getattr(row, "stage_label", None),
            "stage_slope_pct": getattr(row, "stage_slope_pct", None),
            "stage_dist_pct": getattr(row, "stage_dist_pct", None),
            "sector": getattr(row, "sector", None),
            "industry": getattr(row, "industry", None),
            "market_cap": getattr(row, "market_cap", None),
        }
        return out

    def compute_snapshot_from_db(self, db: Session, symbol: str) -> Dict[str, Any]:
        """Compute a snapshot purely from local PriceData (and enrich it) for speed and consistency.

        - Reads the last ~270 daily bars (newest->first) from price_data
        - Computes indicators locally (no provider calls)
        - Also enriches with chart metrics and fundamentals before returning
        """
        from backend.models import PriceData

        rows = (
            db.query(
                PriceData.open_price,
                PriceData.high_price,
                PriceData.low_price,
                PriceData.close_price,
                PriceData.volume,
            )
            .filter(PriceData.symbol == symbol, PriceData.interval == "1d")
            .order_by(PriceData.date.desc())
            .limit(270)
            .all()
        )
        if not rows:
            return {}
        df = pd.DataFrame(
            {
                "Open": [float(r[0]) for r in rows],
                "High": [float(r[1]) for r in rows],
                "Low": [float(r[2]) for r in rows],
                "Close": [float(r[3]) for r in rows],
                "Volume": [int(r[4] or 0) for r in rows],
            }
        )
        snapshot = self._snapshot_from_dataframe(df)
        if not snapshot:
            return {}
        # Fundamentals enrichment (reuse from latest snapshot if present; otherwise fetch once)
        # Prefer fundamentals from the latest stored snapshot
        try:
            prev_row = (
                db.query(MarketSnapshot)
                .filter(
                    MarketSnapshot.symbol == symbol,
                    MarketSnapshot.analysis_type == "technical_snapshot",
                )
                .order_by(MarketSnapshot.analysis_timestamp.desc())
                .first()
            )
            if prev_row and (prev_row.sector or prev_row.industry or prev_row.market_cap):
                if prev_row.sector is not None:
                    snapshot["sector"] = prev_row.sector
                if prev_row.industry is not None:
                    snapshot["industry"] = prev_row.industry
                if prev_row.market_cap is not None:
                    snapshot["market_cap"] = prev_row.market_cap
        except Exception:
            pass

        if self._needs_fundamentals(snapshot):
            try:
                info = self.get_fundamentals_info(symbol)
                for k in ("sector", "industry", "market_cap"):
                    if info.get(k) is not None:
                        snapshot[k] = info.get(k)
            except Exception:
                pass
        # no broad except here; previous except already guarded
        return snapshot

    async def compute_snapshot_from_providers(self, symbol: str) -> Dict[str, Any]:
        """Compute a snapshot from provider OHLCV when DB path is missing (and enrich it).

        - Uses get_historical_data (policy-driven) to fetch ~1y daily bars
        - Computes indicators locally; no external indicator APIs are used
        - Intended as a slow-path fallback to bootstrap symbols not yet in DB
        """
        data = await self.get_historical_data(symbol, period="1y", interval="1d")
        if data is None or data.empty:
            price_only = await self.get_current_price(symbol)
            return {"current_price": float(price_only)} if price_only else {}

        snapshot = self._snapshot_from_dataframe(data)
        if not snapshot:
            return {}

        try:
            funda = self.get_fundamentals_info(symbol)
            if funda:
                for k in ("name", "sector", "industry", "sub_industry", "market_cap"):
                    if funda.get(k) is not None:
                        snapshot[k] = funda.get(k)
        except Exception:
            pass
        return snapshot


    def persist_snapshot(
        self,
        db: Session,
        symbol: str,
        snapshot: Dict[str, Any],
        analysis_type: str = "technical_snapshot",
        ttl_hours: int = 24,
        ) -> MarketSnapshot:
        """Upsert-like persistence for MarketSnapshot with mapped fields copied."""
        if not snapshot:
            raise ValueError("empty snapshot")
        now = datetime.utcnow()
        expiry = now + pd.Timedelta(hours=ttl_hours)
        row = (
            db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.symbol == symbol,
                MarketSnapshot.analysis_type == analysis_type,
            )
            .order_by(MarketSnapshot.analysis_timestamp.desc())
            .first()
        )
        if row is None:
            row = MarketSnapshot(
                symbol=symbol,
                analysis_type=analysis_type,
                expiry_timestamp=expiry,
                raw_analysis=snapshot,
            )
            for k, v in snapshot.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            db.add(row)
        else:
            row.expiry_timestamp = expiry
            row.raw_analysis = snapshot
            for k, v in snapshot.items():
                if hasattr(row, k):
                    setattr(row, k, v)
        db.flush()
        db.commit()
        return row

    # ---------------------- Persistence Helpers (OHLCV Backfill) ----------------------
    def persist_price_bars(
        self,
        db: Session,
        symbol: str,
        df: pd.DataFrame,
        *,
        interval: str = "1d",
        data_source: str = "provider",
        is_adjusted: bool = True,
        delta_after: Optional[datetime] = None,
    ) -> int:
        """Persist OHLCV bars into `price_data` with ON CONFLICT DO NOTHING.

        - Assumes df index are timestamps (newest->first or ascending; both ok)
        - Coalesces missing O/H/L/Volume to Close/0 to avoid NULLs
        - If delta_after is provided, only insert rows with ts > delta_after
        - Returns number of attempted inserts (not necessarily rows changed)
        """
        if df is None or df.empty:
            return 0
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from backend.models import PriceData
        except Exception as exc:
            raise RuntimeError("PostgreSQL dialect or models unavailable") from exc

        # Build rows in chronological order for clarity (and stable delta filtering).
        try:
            df_iter = df.sort_index(ascending=True).iterrows()
        except Exception:
            df_iter = df.iterrows()

        rows: list[dict[str, Any]] = []
        for ts, row in df_iter:
            try:
                pd_date = (
                    datetime.fromtimestamp(ts.timestamp())
                    if hasattr(ts, "timestamp")
                    else ts
                )
            except Exception:
                pd_date = ts
            if delta_after and pd_date <= delta_after:
                continue
            close_val = float(row.get("Close"))
            open_val = (
                float(row.get("Open"))
                if "Open" in row and row.get("Open") is not None
                else close_val
            )
            high_val = (
                float(row.get("High"))
                if "High" in row and row.get("High") is not None
                else close_val
            )
            low_val = (
                float(row.get("Low"))
                if "Low" in row and row.get("Low") is not None
                else close_val
            )
            vol_val = int(row.get("Volume") or 0) if "Volume" in row else 0
            rows.append(
                {
                    "symbol": symbol,
                    "date": pd_date,
                    "open_price": open_val,
                    "high_price": high_val,
                    "low_price": low_val,
                    "close_price": close_val,
                    "adjusted_close": close_val,
                    "volume": vol_val,
                    "interval": interval,
                    "data_source": data_source,
                    "is_adjusted": is_adjusted,
                }
            )

        if not rows:
            return 0

        stmt = pg_insert(PriceData).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_symbol_date_interval",
            set_={
                "data_source": data_source,
            },
            where=or_(
                PriceData.data_source.is_(None),
                PriceData.data_source.in_(["provider", "fmp_td_yf"]),
            ),
        )
        db.execute(stmt)
        db.commit()
        return len(rows)

    async def backfill_daily_bars(
        self,
        db: Session,
        symbol: str,
        *,
        lookback_period: str = "1y",
        max_bars: int = 270,
    ) -> Dict[str, Any]:
        """Delta backfill last ~270 daily bars for a single symbol using provider policy."""
        # Determine last stored date to do delta-only inserts
        last_date: Optional[datetime] = None
        try:
            from backend.models import PriceData
            last_date = (
                db.query(PriceData.date)
                .filter(PriceData.symbol == symbol.upper(), PriceData.interval == "1d")
                .order_by(PriceData.date.desc())
                .limit(1)
                .scalar()
            )
        except Exception:
            last_date = None
        df, provider_used = await self.get_historical_data(
            symbol=symbol.upper(),
            period=lookback_period,
            interval="1d",
            max_bars=None,
            return_provider=True,
        )
        if df is None or df.empty:
            return {
                "status": "empty",
                "symbol": symbol.upper(),
                "inserted": 0,
                "provider": provider_used,
            }
        # Trim to bounded size for downstream compute
        df = df.tail(max_bars) if max_bars else df
        inserted = self.persist_price_bars(
            db,
            symbol.upper(),
            df,
            interval="1d",
            data_source=provider_used or "unknown",
            is_adjusted=True,
            delta_after=last_date,
        )
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "inserted": inserted,
            "provider": provider_used,
        }

    async def backfill_intraday_5m(
        self,
        db: Session,
        symbol: str,
        *,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """Delta backfill last N days of 5m bars for a single symbol using provider policy."""
        from backend.models import PriceData
        sym = symbol.upper()
        # Last stored timestamp for 5m to do delta-only inserts
        last_ts: Optional[datetime] = (
            db.query(PriceData.date)
            .filter(PriceData.symbol == sym, PriceData.interval == "5m")
            .order_by(PriceData.date.desc())
            .limit(1)
            .scalar()
        )
        period = f"{max(1, int(lookback_days))}d"
        df, provider_used = await self.get_historical_data(
            symbol=sym,
            period=period,
            interval="5m",
            max_bars=None,
            return_provider=True,
        )
        if df is None or df.empty:
            return {"status": "empty", "symbol": sym, "inserted": 0, "provider": provider_used}
        inserted = self.persist_price_bars(
            db,
            sym,
            df,
            interval="5m",
            data_source=provider_used or "unknown",
            is_adjusted=True,
            delta_after=last_ts,
        )
        return {"status": "ok", "symbol": sym, "inserted": inserted, "provider": provider_used}

    def get_db_history(
        self,
        db: Session,
        symbol: str,
        *,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Read OHLCV from price_data (ascending by time) for API consumers."""
        from backend.models import PriceData
        q = (
            db.query(
                PriceData.date,
                PriceData.open_price,
                PriceData.high_price,
                PriceData.low_price,
                PriceData.close_price,
                PriceData.volume,
            )
            .filter(PriceData.symbol == symbol.upper(), PriceData.interval == interval)
        )
        if start:
            q = q.filter(PriceData.date >= start)
        if end:
            q = q.filter(PriceData.date <= end)
        q = q.order_by(PriceData.date.asc())
        if limit:
            q = q.limit(limit)
        rows = q.all()
        if not rows:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        df = pd.DataFrame(
            [
                {
                    "date": r[0],
                    "Open": float(r[1]) if r[1] is not None else float(r[4]),
                    "High": float(r[2]) if r[2] is not None else float(r[4]),
                    "Low": float(r[3]) if r[3] is not None else float(r[4]),
                    "Close": float(r[4]),
                    "Volume": int(r[5] or 0),
                }
                for r in rows
            ]
        )
        df.set_index("date", inplace=True)
        return df

    # ---------------------- High-level TA helpers for tests/integration ----------------------
    async def build_indicator_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Build a technical snapshot from provider OHLCV (newest->first) with indicators."""
        return await self.compute_snapshot_from_providers(symbol)

    async def get_weinstein_stage(self, symbol: str, benchmark: str = "SPY") -> Dict[str, Any]:
        """Compute Weinstein stage by fetching daily series for symbol and a benchmark."""
        sym_df = await self.get_historical_data(symbol, period="1y", interval="1d")
        bm_df = await self.get_historical_data(benchmark, period="1y", interval="1d")
        try:
            return compute_weinstein_stage_from_daily(sym_df, bm_df)
        except Exception:
            return {"stage": "UNKNOWN"}

    async def get_technical_analysis(self, symbol: str) -> Dict[str, Any]:
        """Compatibility wrapper expected by tests – returns the latest snapshot."""
        return await self.get_snapshot(symbol)

    # ---------------------- Coverage instrumentation ----------------------
    def _compute_interval_coverage_for_symbols(
        self,
        db: Session,
        *,
        symbols: List[str],
        interval: str,
        now_utc: datetime | None = None,
        stale_sample_limit: int | None = None,
        return_full_stale: bool = False,
    ) -> tuple[Dict[str, Any], List[str] | None]:
        """Compute freshness buckets and stale/missing sets for a given symbol universe.

        - Includes missing symbols (no bars) in the `none` bucket.
        - Returns a sampled `stale` list for UI, but can also return the full stale symbol list.
        """
        now = now_utc or datetime.utcnow()
        safe_symbols = sorted({str(s).upper() for s in (symbols or []) if s})
        sym_set = set(safe_symbols)
        if stale_sample_limit is None:
            stale_sample_limit = int(getattr(settings, "COVERAGE_STALE_SAMPLE", 50))

        last_dt: Dict[str, datetime | None] = {s: None for s in safe_symbols}
        if sym_set:
            rows = (
                db.query(PriceData.symbol, PriceData.date)
                .filter(PriceData.interval == interval, PriceData.symbol.in_(sym_set))
                .order_by(PriceData.symbol.asc(), PriceData.date.desc())
                .distinct(PriceData.symbol)
                .all()
            )
            for sym, dt in rows:
                if sym:
                    last_dt[str(sym).upper()] = dt

        def _bucketize(ts: datetime | None) -> str:
            if not ts:
                return "none"
            age = now - ts
            if age <= timedelta(hours=24):
                return "<=24h"
            if age <= timedelta(hours=48):
                return "24-48h"
            return ">48h"

        freshness = {"<=24h": 0, "24-48h": 0, ">48h": 0, "none": 0}
        stale_items: List[Dict[str, Any]] = []
        stale_full: List[str] = []

        for sym in safe_symbols:
            dt = last_dt.get(sym)
            bucket = _bucketize(dt)
            freshness[bucket] = int(freshness.get(bucket, 0)) + 1
            if bucket in (">48h", "none"):
                stale_items.append(
                    {"symbol": sym, "last": dt.isoformat() if dt else None, "bucket": bucket}
                )
                stale_full.append(sym)

        stale_items.sort(
            key=lambda item: (
                item.get("bucket") or "",
                item.get("last") or "",
                item.get("symbol") or "",
            )
        )
        stale_sample = stale_items[: max(0, int(stale_sample_limit))]

        fresh_24 = int(freshness["<=24h"])
        fresh_48 = int(freshness["24-48h"])
        stale_48h = int(freshness[">48h"])
        missing = int(freshness["none"])

        last_iso_map: Dict[str, str | None] = {s: (last_dt[s].isoformat() if last_dt[s] else None) for s in safe_symbols}

        section: Dict[str, Any] = {
            # Count = within freshness SLA (<=48h).
            "count": fresh_24 + fresh_48,
            "last": last_iso_map,
            "freshness": freshness,
            "stale": stale_sample,
            "fresh_24h": fresh_24,
            "fresh_48h": fresh_48,
            "fresh_gt48h": 0,
            "stale_48h": stale_48h,
            "missing": missing,
        }
        return section, (stale_full if return_full_stale else None)

    def coverage_snapshot(self, db: Session) -> Dict[str, Any]:
        """Compute coverage freshness, stale lists, and tracked stats for instrumentation/UI."""
        now = datetime.utcnow()

        idx_counts: Dict[str, int] = {}
        for idx in ("SP500", "NASDAQ100", "DOW30"):
            idx_counts[idx] = (
                db.query(IndexConstituent)
                .filter(IndexConstituent.index_name == idx, IndexConstituent.is_active.is_(True))
                .count()
            )

        tracked_symbols: List[str] = []
        tracked_from_redis = False
        try:
            raw = self.redis_client.get("tracked:all")
            tracked_symbols = json.loads(raw) if raw else []
        except Exception:
            tracked_symbols = []
        tracked_symbols = [str(s).upper() for s in tracked_symbols if s]
        tracked_from_redis = bool(tracked_symbols)
        tracked_total = len(set(tracked_symbols))
        if tracked_total:
            universe = sorted(set(tracked_symbols))
        else:
            universe = sorted({str(s).upper() for (s,) in db.query(PriceData.symbol).distinct().all() if s})
        total_symbols = len(universe)

        daily_section, _ = self._compute_interval_coverage_for_symbols(
            db,
            symbols=universe,
            interval="1d",
            now_utc=now,
            return_full_stale=False,
        )
        m5_section, _ = self._compute_interval_coverage_for_symbols(
            db,
            symbols=universe,
            interval="5m",
            now_utc=now,
            return_full_stale=False,
        )

        snapshot = {
            "generated_at": now.isoformat(),
            "symbols": total_symbols,
            "tracked_count": tracked_total if tracked_from_redis else total_symbols,
            "tracked_sample": tracked_symbols[:10],
            "indices": idx_counts,
            "daily": daily_section,
            "m5": m5_section,
        }
        snapshot["status"] = compute_coverage_status(snapshot)
        return snapshot

def compute_coverage_status(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Derive human-readable coverage state + KPI percentages from a raw snapshot."""
    total_symbols = int(snapshot.get("symbols") or 0)
    tracked = int(snapshot.get("tracked_count") or 0)

    daily = snapshot.get("daily", {}) or {}
    m5 = snapshot.get("m5", {}) or {}
    daily_count = int(daily.get("count") or 0)
    m5_count = int(m5.get("count") or 0)
    # Stale counts should reflect the full universe, not just the sampled `stale` lists.
    daily_freshness = daily.get("freshness") or {}
    m5_freshness = m5.get("freshness") or {}
    stale_daily = int(daily.get("stale_48h") or daily_freshness.get(">48h") or 0) + int(
        daily.get("missing") or daily_freshness.get("none") or 0
    )
    stale_m5 = int(m5.get("stale_48h") or m5_freshness.get(">48h") or 0) + int(
        m5.get("missing") or m5_freshness.get("none") or 0
    )
    # Fall back to list lengths only if no aggregate counts are available.
    if stale_daily == 0 and not daily_freshness and daily.get("stale"):
        stale_daily = len(daily.get("stale") or [])
    if stale_m5 == 0 and not m5_freshness and m5.get("stale"):
        stale_m5 = len(m5.get("stale") or [])

    # If 5m backfill is explicitly disabled, 5m coverage should be informational only
    # and must not drive degraded/warning states.
    meta = snapshot.get("meta", {}) or {}
    backfill_5m_enabled = meta.get("backfill_5m_enabled")
    if backfill_5m_enabled is None:
        backfill_5m_enabled = snapshot.get("backfill_5m_enabled")
    backfill_5m_enabled = True if backfill_5m_enabled is None else bool(backfill_5m_enabled)

    def pct(count: int) -> float:
        return round((count / total_symbols) * 100.0, 1) if total_symbols else 0.0

    daily_pct = pct(daily_count)
    m5_pct = pct(m5_count)

    label = "ok"
    summary = "Coverage healthy across daily + 5m intervals."
    if total_symbols == 0:
        label = "idle"
        summary = "No symbols discovered yet. Run refresh + tracked tasks."
    if total_symbols > 0 and daily_pct < 90:
        label = "degraded"
        summary = f"Daily coverage {daily_pct}% below 90% SLA."
    elif stale_daily:
        label = "degraded"
        none_n = int((daily.get("freshness") or {}).get("none") or daily.get("missing") or 0)
        summary = (
            f"{stale_daily} symbols have daily bars older than 48h."
            if none_n == 0
            else f"{stale_daily} symbols have daily bars older than 48h or missing."
        )
    elif backfill_5m_enabled:
        if m5_pct == 0 and total_symbols:
            label = "degraded"
            summary = "5m coverage is 0% – run intraday backfill."
        elif stale_m5:
            label = "warning"
            summary = f"{stale_m5} symbols missing 5m data."

    return {
        "label": label,
        "summary": summary,
        "daily_pct": daily_pct,
        "m5_pct": m5_pct,
        "stale_daily": stale_daily,
        "stale_m5": stale_m5,
        "symbols": total_symbols,
        "tracked_count": tracked,
        "thresholds": {
            "daily_pct": 90,
            "m5_expectation": ">=1 refresh/day" if backfill_5m_enabled else "ignored (disabled by admin)",
        },
    }


# Global instance
market_data_service = MarketDataService()

