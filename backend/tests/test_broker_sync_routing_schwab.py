import asyncio
import uuid
import pytest

from backend.services.portfolio.broker_sync_service import broker_sync_service
from backend.models.broker_account import BrokerAccount, BrokerType, AccountType


def _ensure_account(session) -> BrokerAccount:
    from backend.models.user import User

    user = session.query(User).filter(User.username == "route_tester").first()
    if not user:
        user = User(username="route_tester", email="route_tester@example.com", password_hash="x", is_active=True)
        session.add(user)
        session.commit()
        session.refresh(user)
    acct = BrokerAccount(
        user_id=user.id,
        broker=BrokerType.SCHWAB,
        account_number=f"S{uuid.uuid4().hex[:6]}",
        account_name="Route Schwab",
        account_type=AccountType.TAXABLE,
        currency="USD",
    )
    session.add(acct)
    session.commit()
    session.refresh(acct)
    return acct


def test_broker_sync_routes_to_schwab(monkeypatch, db_session):
    calls = {"count": 0}

    class DummyService:
        async def sync_account_comprehensive(self, account_number, session):
            calls["count"] += 1
            return {"status": "success", "account_number": account_number}

    # Patch the SchwabSyncService used inside the router
    import backend.services.portfolio.schwab_sync_service as schwab_module

    monkeypatch.setattr(schwab_module, "SchwabSyncService", lambda: DummyService())

    acct = _ensure_account(db_session)
    result = broker_sync_service.sync_account(account_id=acct.account_number, db=db_session, sync_type="comprehensive")
    assert result["status"] == "success"
    assert calls["count"] == 1


