import pandas as pd
from datetime import datetime, timedelta

from backend.services.market.market_data_service import market_data_service
from backend.models import PriceData, MarketSnapshot


def _make_df(dates: list[datetime], close: float = 100.0) -> pd.DataFrame:
    data = []
    for i, d in enumerate(dates):
        c = close + i
        data.append(
            {
                "Open": c,
                "High": c,
                "Low": c,
                "Close": c,
                "Volume": 1000 + i,
            }
        )
    df = pd.DataFrame(data)
    df.index = pd.DatetimeIndex(dates)
    return df


def test_persist_price_bars_delta_only(db_session):
    sym = "TEST"
    now = datetime.utcnow().replace(microsecond=0)
    yesterday = now - timedelta(days=1)
    df = _make_df([yesterday, now], close=50.0)

    # First insert yesterday
    inserted_1 = market_data_service.persist_price_bars(
        db_session, sym, df.iloc[:1], interval="1d", data_source="unit_test", is_adjusted=True
    )
    assert inserted_1 == 1
    # Delta insert should skip yesterday and insert only today
    last_date = (
        db_session.query(PriceData.date)
        .filter(PriceData.symbol == sym, PriceData.interval == "1d")
        .order_by(PriceData.date.desc())
        .limit(1)
        .scalar()
    )
    assert last_date is not None
    inserted_2 = market_data_service.persist_price_bars(
        db_session,
        sym,
        df,
        interval="1d",
        data_source="unit_test",
        is_adjusted=True,
        delta_after=last_date,
    )
    assert inserted_2 == 1
    # Verify two rows exist
    count = db_session.query(PriceData).filter(PriceData.symbol == sym).count()
    assert count == 2


def test_compute_snapshot_from_db_uses_existing_fundamentals(db_session):
    sym = "TESTF"
    # Seed 120 days of prices to enable indicator computation
    start = datetime.utcnow().replace(microsecond=0) - timedelta(days=130)
    dates = [start + timedelta(days=i) for i in range(120)]
    df = _make_df(dates, close=100.0)
    market_data_service.persist_price_bars(
        db_session, sym, df, interval="1d", data_source="unit_test", is_adjusted=True
    )
    # Seed a previous snapshot with fundamentals
    prev = MarketSnapshot(
        symbol=sym,
        analysis_type="technical_snapshot",
        expiry_timestamp=datetime.utcnow() + timedelta(hours=12),
        sector="Technology",
        industry="Software",
        market_cap=123456789.0,
        raw_analysis={"sector": "Technology", "industry": "Software", "market_cap": 123456789.0},
    )
    db_session.add(prev)
    db_session.commit()

    snap = market_data_service.compute_snapshot_from_db(db_session, sym)
    assert snap
    assert snap.get("sector") == "Technology"
    assert snap.get("industry") == "Software"
    assert snap.get("market_cap") == 123456789.0

