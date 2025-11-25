from fastapi.testclient import TestClient
from backend.api.main import app
from backend.database import SessionLocal
from backend.models.index_constituent import IndexConstituent
from backend.tasks.market_data_tasks import refresh_index_constituents


def test_refresh_index_constituents_records_counters(monkeypatch):
    # Monkeypatch service to return a small set deterministically
    from backend.services.market.market_data_service import market_data_service

    async def fake_get_index_constituents(name: str):
        if name == "SP500":
            return ["AAPL", "MSFT"]
        if name == "NASDAQ100":
            return ["AAPL", "MSFT", "NVDA"]
        if name == "DOW30":
            return ["AAPL"]
        return []

    monkeypatch.setattr(market_data_service, "get_index_constituents", fake_get_index_constituents)

    # Clean existing
    db = SessionLocal()
    try:
        db.query(IndexConstituent).delete()
        db.commit()
    finally:
        db.close()

    res = refresh_index_constituents()
    assert res["status"] == "ok"
    idx = res["indices"]
    # Ensure keys present
    for k in ["SP500", "NASDAQ100", "DOW30"]:
        assert "fetched" in idx[k]
        assert "inserted" in idx[k]
        assert "inactivated" in idx[k]

    # Verify rows written
    db = SessionLocal()
    try:
        count = db.query(IndexConstituent).count()
        assert count > 0
    finally:
        db.close()



