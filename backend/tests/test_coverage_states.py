from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json
import pytest
from sqlalchemy.exc import OperationalError
from backend.api.main import app
from backend.api.routes.market_data import get_market_data_viewer
from backend.database import SessionLocal
from backend.models.market_data import PriceData
from backend.models.user import UserRole
from backend.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def allow_market_data_viewer():
    class _DummyUser:
        role = UserRole.ADMIN
        is_active = True
        email = "admin@example.com"

    app.dependency_overrides[get_market_data_viewer] = lambda: _DummyUser()
    yield
    app.dependency_overrides.pop(get_market_data_viewer, None)


def test_coverage_endpoint_buckets(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_DATA_SECTION_PUBLIC", True)
    try:
        db = SessionLocal()
    except OperationalError:
        pytest.skip("Database unavailable for coverage test")
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
    except OperationalError:
        db.rollback()
        pytest.skip("Database unavailable for coverage test")
    finally:
        db.close()

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
    assert "status" in data
    assert "history" in data


def test_coverage_prefers_cached_snapshot(monkeypatch):
    from backend.api.routes import market_data as routes

    monkeypatch.setattr(settings, "MARKET_DATA_SECTION_PUBLIC", True)
    cached_snapshot = {
        "generated_at": "2025-01-01T00:00:00",
        "symbols": 2,
        "tracked_count": 2,
        "daily": {"count": 2, "stale": []},
        "m5": {"count": 1, "stale": []},
    }
    cached_status = {
        "label": "ok",
        "summary": "Cached snapshot",
        "daily_pct": 100,
        "m5_pct": 50,
        "stale_daily": 0,
        "stale_m5": 0,
    }
    payload = {"snapshot": cached_snapshot, "updated_at": "2025-01-01T00:00:00", "status": cached_status}

    class _RedisStub:
        def get(self, key):
            if key == "coverage:health:last":
                return json.dumps(payload)
            return None

        def lrange(self, key, start, end):
            return [
                json.dumps(
                    {
                        "ts": "2025-01-01T00:00:00",
                        "daily_pct": 100,
                        "m5_pct": 50,
                        "stale_daily": 0,
                        "stale_m5": 0,
                        "label": "ok",
                    }
                )
            ]

    class _StubService:
        def __init__(self):
            self.redis_client = _RedisStub()

        def coverage_snapshot(self, db):
            raise AssertionError("Should not hit DB when cache is present")

    monkeypatch.setattr(routes, "MarketDataService", _StubService)

    resp = client.get("/api/v1/market-data/coverage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["source"] == "cache"
    assert body["status"]["label"].lower() == "ok"
    assert body["history"]



