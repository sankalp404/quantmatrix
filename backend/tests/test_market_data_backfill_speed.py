import asyncio
import pandas as pd
from datetime import datetime, timedelta

import pytest

from backend.services.market.market_data_service import MarketDataService, market_data_service


def _make_df(days: int = 5) -> pd.DataFrame:
    now = datetime.utcnow().replace(microsecond=0)
    dates = [now - timedelta(days=i) for i in range(days)][::-1]
    df = pd.DataFrame(
        [{"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1} for _ in dates],
        index=pd.DatetimeIndex(dates),
    )
    return df


@pytest.mark.asyncio
async def test_call_blocking_with_retries_backoff_on_429(monkeypatch):
    svc = MarketDataService()
    sleeps: list[float] = []

    async def fake_sleep(delay: float):
        sleeps.append(float(delay))

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    class RateLimitExc(Exception):
        status_code = 429

    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitExc("429")
        return "ok"

    out = await svc._call_blocking_with_retries(flaky, attempts=5, max_delay_seconds=1.0)
    assert out == "ok"
    assert calls["n"] == 3
    # Should have backed off at least once
    assert len(sleeps) >= 2


def test_persist_price_bars_bulk_upsert_still_delta_only(db_session):
    sym = "BULKTEST"
    df = _make_df(days=3)
    inserted_1 = market_data_service.persist_price_bars(
        db_session, sym, df.iloc[:1], interval="1d", data_source="unit_test", is_adjusted=True
    )
    assert inserted_1 == 1
    from backend.models import PriceData

    last_date = (
        db_session.query(PriceData.date)
        .filter(PriceData.symbol == sym, PriceData.interval == "1d")
        .order_by(PriceData.date.desc())
        .limit(1)
        .scalar()
    )
    assert last_date is not None
    inserted_2 = market_data_service.persist_price_bars(
        db_session, sym, df, interval="1d", data_source="unit_test", is_adjusted=True, delta_after=last_date
    )
    assert inserted_2 == 2


