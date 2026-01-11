def test_coverage_snapshot_uses_snapshot_history(db_session, monkeypatch):
    """Regression: snapshot_fill_by_date should come from MarketSnapshotHistory (ledger), not MarketSnapshot (latest-only)."""
    from datetime import datetime, timezone

    from backend.services.market.market_data_service import MarketDataService
    from backend.models.market_data import MarketSnapshotHistory

    # Ensure coverage_snapshot sees a stable universe
    svc = MarketDataService()
    monkeypatch.setattr(svc.redis_client, "get", lambda key: b'["AAA","BBB"]' if key == "tracked:all" else None)

    # Insert history for two dates
    d1 = datetime(2026, 1, 8, tzinfo=timezone.utc).replace(tzinfo=None)
    d2 = datetime(2026, 1, 9, tzinfo=timezone.utc).replace(tzinfo=None)
    db_session.add(
        MarketSnapshotHistory(
            symbol="AAA",
            analysis_type="technical_snapshot",
            as_of_date=d1,
            analysis_payload={"current_price": 1, "as_of_timestamp": "2026-01-08T00:00:00"},
        )
    )
    db_session.add(
        MarketSnapshotHistory(
            symbol="BBB",
            analysis_type="technical_snapshot",
            as_of_date=d2,
            analysis_payload={"current_price": 2, "as_of_timestamp": "2026-01-09T00:00:00"},
        )
    )
    db_session.commit()

    snap = svc.coverage_snapshot(db_session)
    series = (snap.get("daily") or {}).get("snapshot_fill_by_date") or []
    dates = {row.get("date") for row in series}

    assert "2026-01-08" in dates
    assert "2026-01-09" in dates


