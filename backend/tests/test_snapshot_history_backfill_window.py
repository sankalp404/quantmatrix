def test_backfill_snapshot_history_last_n_days_writes_rows(db_session, monkeypatch):
    """Smoke test: backfill_snapshot_history_last_n_days writes ledger rows for last N SPY trading days."""
    from datetime import datetime

    from backend.tasks import market_data_tasks

    # Force tasks to use the pytest db session (never dev DB).
    monkeypatch.setattr(market_data_tasks, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(market_data_tasks, "_set_task_status", lambda *args, **kwargs: None)

    # Stable tracked universe
    monkeypatch.setattr(
        market_data_tasks.market_data_service.redis_client,
        "get",
        lambda key: b'["AAA"]' if key == "tracked:all" else None,
    )

    from backend.models.market_data import PriceData, MarketSnapshotHistory

    # Create a tiny SPY calendar (5 days)
    spy_dates = [
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
        datetime(2026, 1, 3),
        datetime(2026, 1, 4),
        datetime(2026, 1, 5),
    ]
    for d in spy_dates:
        db_session.add(
            PriceData(
                symbol="SPY",
                interval="1d",
                date=d,
                open_price=100,
                high_price=101,
                low_price=99,
                close_price=100,
                adjusted_close=100,
                volume=0,
                data_source="test",
                is_adjusted=True,
            )
        )

    # Create AAA prices for same dates
    for i, d in enumerate(spy_dates):
        px = 10 + i
        db_session.add(
            PriceData(
                symbol="AAA",
                interval="1d",
                date=d,
                open_price=px,
                high_price=px + 1,
                low_price=px - 1,
                close_price=px,
                adjusted_close=px,
                volume=0,
                data_source="test",
                is_adjusted=True,
            )
        )
    db_session.commit()

    res = market_data_tasks.backfill_snapshot_history_last_n_days(days=5, batch_size=10)
    assert res["status"] == "ok"
    assert res["processed_symbols"] == 1
    assert res["written_rows"] >= 5

    rows = (
        db_session.query(MarketSnapshotHistory)
        .filter(MarketSnapshotHistory.symbol == "AAA", MarketSnapshotHistory.analysis_type == "technical_snapshot")
        .order_by(MarketSnapshotHistory.as_of_date.asc())
        .all()
    )
    assert len(rows) == 5
    # Wide/flat table: verify some computed fields landed on columns.
    assert rows[0].current_price is not None
    assert rows[-1].sma_5 is not None or rows[-1].sma_14 is not None or rows[-1].sma_21 is not None


