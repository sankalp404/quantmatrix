from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from backend.api.main import app
from backend.database import SessionLocal
from backend.models.market_data import PriceData


def test_coverage_endpoint_buckets():
    db = SessionLocal()
    try:
        # Clean and insert two symbols: one fresh, one stale
        db.query(PriceData).delete()
        now = datetime.utcnow()
        rows = [
            PriceData(symbol="TESTF", date=now - timedelta(hours=2), open_price=1, high_price=1, low_price=1, close_price=1, adjusted_close=1, volume=100, interval="1d", is_adjusted=True, data_source="test"),
            PriceData(symbol="TESTS", date=now - timedelta(days=3), open_price=1, high_price=1, low_price=1, close_price=1, adjusted_close=1, volume=100, interval="1d", is_adjusted=True, data_source="test"),
        ]
        for r in rows:
            db.add(r)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get("/api/v1/market-data/coverage")
    assert resp.status_code == 200
    data = resp.json()
    assert "daily" in data
    assert "freshness" in data["daily"]
    # Buckets should exist
    buckets = data["daily"]["freshness"]
    assert all(k in buckets for k in ["<=24h", "24-48h", ">48h", "none"])
    # Sanity: counts sum to daily count
    assert sum(buckets.values()) == data["daily"]["count"]



