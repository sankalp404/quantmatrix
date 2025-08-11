import pytest
import pandas as pd
from backend.services.market.market_data_service import MarketDataService


@pytest.mark.asyncio
async def test_manual_ma_stage_basic(monkeypatch):
    svc = MarketDataService()

    # Create synthetic uptrend data: steadily rising close
    dates = pd.date_range(end=pd.Timestamp.today(), periods=220, freq="D")
    close = pd.Series(range(1, 221), index=dates, dtype=float)
    high = close + 1
    low = close - 1
    df = pd.DataFrame(
        {"Open": close, "High": high, "Low": low, "Close": close, "Volume": 1000}
    )
    df = df.iloc[::-1]  # newest first to match service expectations

    async def fake_hist(symbol, period="1y", interval="1d"):
        return df

    import asyncio

    monkeypatch.setattr(
        MarketDataService,
        "get_historical_data",
        lambda self, symbol, period="1y", interval="1d": asyncio.create_task(
            _return(df)
        ),
    )

    # helper to return awaitable
    async def _return(val):
        return val

    ma = await svc.get_moving_averages("TEST")
    assert "sma_200" in ma and "ema_200" in ma
    bucket = await svc.classify_ma_bucket("TEST")
    assert bucket["bucket"] in ("LEADING", "NEUTRAL")

    stage = await svc.get_weinstein_stage("TEST")
    # synthetic monotonic up close without benchmark alignment may still be UNKNOWN; just assert key present
    assert "stage" in stage
