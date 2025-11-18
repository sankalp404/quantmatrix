from __future__ import annotations

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


def compute_core_indicators(data_oldest_first: pd.DataFrame) -> Dict[str, Any]:
    """Compute core technical indicators using pandas/numpy only.

    Input must be oldest->newest DataFrame with columns: Close (required), High/Low (optional for ATR/ADX).
    """
    out: Dict[str, Any] = {}
    closes = data_oldest_first["Close"]

    # SMAs (include 5/8/21 for MA bucket + 20/50/100/200 for snapshots)
    for n in [5, 8, 21, 20, 50, 100, 200]:
        if len(closes) >= n:
            sma = closes.rolling(n).mean()
            if not sma.empty and not pd.isna(sma.iloc[-1]):
                out[f"sma_{n}"] = float(sma.iloc[-1])

    # EMAs (10 + pine parity 8/21/200)
    for n in [10, 8, 21, 200]:
        if len(closes) >= n:
            ema = closes.ewm(span=n, adjust=False).mean()
            if not ema.empty and not pd.isna(ema.iloc[-1]):
                key = "ema_10" if n == 10 else f"ema_{n}"
                out[key] = float(ema.iloc[-1])

    # RSI(14)
    if len(closes) >= 14:
        rsi = calculate_rsi_series(closes, 14)
        if rsi is not None and not pd.isna(rsi.iloc[-1]):
            out["rsi"] = float(rsi.iloc[-1])

    # ATR(14)
    if (
        set(["High", "Low", "Close"]).issubset(data_oldest_first.columns)
        and len(data_oldest_first) >= 14
    ):
        atr = calculate_atr_series(data_oldest_first, 14)
        if atr is not None and not pd.isna(atr.iloc[-1]):
            out["atr"] = float(atr.iloc[-1])

    # MACD (12,26,9)
    if len(closes) >= 26:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - signal
        if not macd_line.empty and not pd.isna(macd_line.iloc[-1]):
            out["macd"] = float(macd_line.iloc[-1])
        if not signal.empty and not pd.isna(signal.iloc[-1]):
            out["macd_signal"] = float(signal.iloc[-1])
        if not hist.empty and not pd.isna(hist.iloc[-1]):
            out["macd_histogram"] = float(hist.iloc[-1])

    # DI/ADX (approx)
    try:
        if set(["High", "Low", "Close"]).issubset(data_oldest_first.columns):
            period = 14
            up_move = data_oldest_first["High"].diff()
            down_move = -data_oldest_first["Low"].diff()
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
            tr1 = data_oldest_first["High"] - data_oldest_first["Low"]
            tr2 = (data_oldest_first["High"] - data_oldest_first["Close"].shift()).abs()
            tr3 = (data_oldest_first["Low"] - data_oldest_first["Close"].shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * pd.Series(plus_dm).rolling(window=period).sum() / atr
            minus_di = 100 * pd.Series(minus_dm).rolling(window=period).sum() / atr
            dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace(
                [np.inf, -np.inf], np.nan
            )
            adx = dx.rolling(window=period).mean()
            if not plus_di.empty and not pd.isna(plus_di.iloc[-1]):
                out["plus_di"] = float(plus_di.iloc[-1])
            if not minus_di.empty and not pd.isna(minus_di.iloc[-1]):
                out["minus_di"] = float(minus_di.iloc[-1])
            if not adx.empty and not pd.isna(adx.iloc[-1]):
                out["adx"] = float(adx.iloc[-1])
    except Exception:
        pass

    return out


def calculate_performance_windows(
    data_newest_first: pd.DataFrame,
) -> Dict[str, Optional[float]]:
    """Compute performance windows from newest-first DataFrame of OHLCV.
    Returns percentage moves for 1/3/5/20/60/120/252d and MTD/QTD/YTD.
    """
    out: Dict[str, Optional[float]] = {
        "perf_1d": None,
        "perf_3d": None,
        "perf_5d": None,
        "perf_20d": None,
        "perf_60d": None,
        "perf_120d": None,
        "perf_252d": None,
        "perf_mtd": None,
        "perf_qtd": None,
        "perf_ytd": None,
    }
    if (
        data_newest_first is None
        or data_newest_first.empty
        or "Close" not in data_newest_first.columns
    ):
        return out

    close = data_newest_first["Close"]

    def pct(n: int) -> Optional[float]:
        if len(close) > n and close.iloc[0] and close.iloc[n]:
            try:
                return float((close.iloc[0] / close.iloc[n] - 1.0) * 100.0)
            except Exception:
                return None
        return None

    out["perf_1d"] = pct(1)
    out["perf_3d"] = pct(3)
    out["perf_5d"] = pct(5)
    out["perf_20d"] = pct(20)
    out["perf_60d"] = pct(60)
    out["perf_120d"] = pct(120)
    out["perf_252d"] = pct(252)

    # MTD/QTD/YTD (approx using calendar boundaries)
    try:
        idx = data_newest_first.index
        ts0 = idx[0]
        # Month start
        mstart = ts0.replace(day=1)
        qstart_month = ((ts0.month - 1) // 3) * 3 + 1
        qstart = ts0.replace(month=qstart_month, day=1)
        ystart = ts0.replace(month=1, day=1)

        def nearest_close_on_or_after(target):
            matches = idx.get_indexer(
                [target], method="nearest", tolerance=pd.Timedelta(days=7)
            )
            pos = matches[0]
            return close.iloc[pos] if pos >= 0 else None

        for key, dt in [
            ("perf_mtd", mstart),
            ("perf_qtd", qstart),
            ("perf_ytd", ystart),
        ]:
            ref = nearest_close_on_or_after(dt)
            if ref and close.iloc[0]:
                out[key] = float((close.iloc[0] / ref - 1.0) * 100.0)
    except Exception:
        pass

    return out


def calculate_rsi_series(closes: pd.Series, period: int = 14) -> Optional[pd.Series]:
    try:
        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception:
        return None


def calculate_atr_series(df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
    try:
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    except Exception:
        return None


# ----------------------------
# Higher-level analyses
# ----------------------------
def compute_atr_matrix_metrics(
    data_oldest_first: pd.DataFrame, indicators: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute ATR Matrix-related metrics (atr_distance, atr_percent, ma_alignment, price_position_20d)."""
    metrics: Dict[str, Any] = {}
    try:
        current_price = indicators.get("current_price") or indicators.get("close")
        if not current_price and len(data_oldest_first) > 0:
            current_price = float(data_oldest_first["Close"].iloc[-1])

        sma_50 = indicators.get("sma_50")
        atr = indicators.get("atr")

        if current_price and sma_50 and atr and atr > 0:
            metrics["atr_distance"] = (current_price - sma_50) / atr
            metrics["atr_percent"] = (atr / current_price) * 100

        # MA alignment (EMA10 > SMA20 > SMA50 > SMA100 > SMA200)
        ema_10 = indicators.get("ema_10")
        sma_20 = indicators.get("sma_20")
        sma_100 = indicators.get("sma_100")
        sma_200 = indicators.get("sma_200")
        mas = [ema_10, sma_20, sma_50, sma_100, sma_200]
        if all(m is not None for m in mas):
            metrics["ma_aligned"] = all(
                mas[i] >= mas[i + 1] for i in range(len(mas) - 1)
            )
            metrics["ma_alignment"] = metrics["ma_aligned"]

        # 20-day price position
        if len(data_oldest_first) >= 20 and current_price is not None:
            recent = data_oldest_first.tail(20)
            hi = recent["High"].max()
            lo = recent["Low"].min()
            if hi > lo:
                metrics["price_position_20d"] = float(
                    (current_price - lo) / (hi - lo) * 100
                )
    except Exception:
        pass
    return metrics


def weekly_from_daily(df_daily_newest_first: pd.DataFrame) -> pd.DataFrame:
    """Convert daily OHLCV (newest->first index) to weekly (oldest->newest)."""
    if df_daily_newest_first is None or df_daily_newest_first.empty:
        return pd.DataFrame()
    daily = df_daily_newest_first.iloc[::-1].copy()  # oldest->newest
    weekly = pd.DataFrame()
    weekly["Open"] = daily["Open"].resample("W-FRI").first()
    weekly["High"] = daily["High"].resample("W-FRI").max()
    weekly["Low"] = daily["Low"].resample("W-FRI").min()
    weekly["Close"] = daily["Close"].resample("W-FRI").last()
    weekly["Volume"] = daily["Volume"].resample("W-FRI").sum()
    weekly = weekly.dropna()
    return weekly


def compute_weinstein_stage_from_daily(
    daily_sym_newest_first: pd.DataFrame,
    daily_bm_newest_first: pd.DataFrame,
) -> Dict[str, Any]:
    """Compute Weinstein stage from daily OHLCV of symbol and benchmark (both newest->first)."""
    if (
        daily_sym_newest_first is None
        or daily_sym_newest_first.empty
        or daily_bm_newest_first is None
        or daily_bm_newest_first.empty
    ):
        return {"stage": "UNKNOWN"}

    w_sym = weekly_from_daily(daily_sym_newest_first)
    w_bm = weekly_from_daily(daily_bm_newest_first)
    if w_sym.empty or w_bm.empty:
        return {"stage": "UNKNOWN"}

    # Align indexes
    idx = w_sym.index.intersection(w_bm.index)
    w_sym = w_sym.loc[idx]
    w_bm = w_bm.loc[idx]
    if len(w_sym) < 60:
        return {"stage": "UNKNOWN"}

    close = w_sym["Close"]
    sma30 = close.rolling(30).mean()
    vol50 = w_sym["Volume"].rolling(50).mean()

    # Relative strength vs benchmark
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
        "stage": stage,
        "price": price,
        "sma30w": sma30_now,
        "sma30w_slope": sma30_slope,
        "rs_slope": rs_slope,
        "vol_ratio_50w": vol_ratio,
        "as_of": idx[-1].isoformat() if len(idx) else None,
    }


def classify_ma_bucket_from_ma(ma: Dict[str, Any]) -> Dict[str, Any]:
    """Classify leading/lagging/neutral from moving averages dict (includes price)."""
    seq = [
        ma.get("price"),
        ma.get("sma_5"),
        ma.get("sma_8"),
        ma.get("sma_21"),
        ma.get("sma_50"),
        ma.get("sma_100"),
        ma.get("sma_200"),
    ]
    if all(isinstance(x, (int, float)) for x in seq):
        strictly_desc = all(seq[i] > seq[i + 1] for i in range(len(seq) - 1))
        strictly_asc = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
        bucket = (
            "LEADING" if strictly_desc else ("LAGGING" if strictly_asc else "NEUTRAL")
        )
    else:
        bucket = "UNKNOWN"
    return {"bucket": bucket, "data": ma}


# -------------------------------------------------------------
# Chart metrics (TD Sequential, gaps, trendlines)
# -------------------------------------------------------------
def compute_td_sequential_counts(closes: List[float]) -> Dict[str, Optional[int]]:
    """Compute simplified TD Sequential buy/sell setup counts from a close series.

    Expects newest-first closes; returns last observed setup counts.
    """
    if not closes or len(closes) < 5:
        return {"td_buy_setup": None, "td_sell_setup": None}
    buy_setup = 0
    sell_setup = 0
    # Iterate oldest->newest for stability
    for i in range(len(closes) - 1, -1, -1):
        j = i + 4
        if j >= len(closes):
            continue
        if closes[i] < closes[j]:
            buy_setup += 1
            sell_setup = 0
        elif closes[i] > closes[j]:
            sell_setup += 1
            buy_setup = 0
        else:
            buy_setup = 0
            sell_setup = 0
    return {
        "td_buy_setup": int(buy_setup) if buy_setup > 0 else None,
        "td_sell_setup": int(sell_setup) if sell_setup > 0 else None,
    }


def compute_gap_counts(
    data_newest_first: pd.DataFrame,
    min_gap_percent: float = 0.5,
) -> Dict[str, Optional[int]]:
    """Count unfilled gaps up/down over recent window.

    A gap up if Low[t] > High[t+1] and pct gap >= min_gap_percent.
    Consider a gap filled if subsequent bars cross the gap zone.
    """
    out = {"gaps_unfilled_up": None, "gaps_unfilled_down": None}
    if data_newest_first is None or data_newest_first.empty:
        return out
    if not set(["High", "Low"]).issubset(set(data_newest_first.columns)):
        return out
    hi = data_newest_first["High"].tolist()
    lo = data_newest_first["Low"].tolist()
    up_gaps = []  # list of tuples (top, bottom, start_idx)
    down_gaps = []
    pct = min_gap_percent / 100.0
    # iterate newest->older pairs
    for i in range(len(lo) - 1):
        # current bar = i, previous = i+1 (since newest-first ordering)
        # Up gap
        if lo[i] > hi[i + 1] and (lo[i] / hi[i + 1] - 1.0) >= pct:
            up_gaps.append((lo[i], hi[i + 1], i))
        # Down gap
        if hi[i] < lo[i + 1] and (1.0 - hi[i] / lo[i + 1]) >= pct:
            down_gaps.append((lo[i + 1], hi[i], i))

    # determine filled status scanning forward (towards older bars)
    def count_unfilled(gaps, direction: str) -> int:
        count = 0
        for top, bottom, start in gaps:
            filled = False
            for j in range(start + 1, len(lo)):
                if direction == "up":
                    if lo[j] <= bottom:
                        filled = True
                        break
                else:
                    if hi[j] >= top:
                        filled = True
                        break
            if not filled:
                count += 1
        return count

    out["gaps_unfilled_up"] = count_unfilled(up_gaps, "up")
    out["gaps_unfilled_down"] = count_unfilled(down_gaps, "down")
    return out


def compute_trendline_counts(
    data_oldest_first: pd.DataFrame,
    pivot_period: int = 20,
    max_lines: int = 3,
) -> Dict[str, Optional[int]]:
    """Simple trendline counts based on pivot highs/lows over a rolling window.

    Returns number of uptrend lines (connecting rising pivot lows) and
    downtrend lines (connecting falling pivot highs), capped by max_lines.
    """
    out = {"trend_up_count": None, "trend_down_count": None}
    if data_oldest_first is None or data_oldest_first.empty:
        return out
    if not set(["High", "Low"]).issubset(set(data_oldest_first.columns)):
        return out
    highs = data_oldest_first["High"].reset_index(drop=True)
    lows = data_oldest_first["Low"].reset_index(drop=True)
    n = len(highs)
    if n < pivot_period * 2:
        return out
    # find pivot highs/lows: local extrema over window [i-pivot, i+pivot]
    piv_hi = []
    piv_lo = []
    for i in range(pivot_period, n - pivot_period):
        h = highs.iloc[i]
        win_hi = highs.iloc[i - pivot_period : i + pivot_period + 1]
        if h == win_hi.max():
            piv_hi.append((i, float(h)))
        l = lows.iloc[i]
        win_lo = lows.iloc[i - pivot_period : i + pivot_period + 1]
        if l == win_lo.min():
            piv_lo.append((i, float(l)))
    # count lines with monotonic slope constraints
    up = 0
    for a in range(len(piv_lo)):
        for b in range(a + 1, min(a + 6, len(piv_lo))):
            if piv_lo[b][1] > piv_lo[a][1]:
                up += 1
                break
        if up >= max_lines:
            break
    down = 0
    for a in range(len(piv_hi)):
        for b in range(a + 1, min(a + 6, len(piv_hi))):
            if piv_hi[b][1] < piv_hi[a][1]:
                down += 1
                break
        if down >= max_lines:
            break
    out["trend_up_count"] = up
    out["trend_down_count"] = down
    return out
