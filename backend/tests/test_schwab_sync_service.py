import asyncio
from decimal import Decimal
from backend.services.portfolio.schwab_sync_service import SchwabSyncService
from backend.models.broker_account import BrokerAccount, BrokerType, AccountType
from backend.database import SessionLocal


class DummySchwabClient:
    async def connect(self):
        return True

    async def get_positions(self, account_number: str):
        return [
            {"symbol": "AAPL", "quantity": 10, "average_cost": 150.0, "total_cost_basis": 1500.0},
            {"symbol": "MSFT", "quantity": 0, "average_cost": 0.0, "total_cost_basis": 0.0},
        ]

    async def get_options_positions(self, account_number: str):
        # Minimal option record
        return [
            {
                "symbol": "AAPL 2025-01-17 200C",
                "underlying_symbol": "AAPL",
                "strike_price": 200.0,
                "expiry_date": "2025-01-17",
                "option_type": "CALL",
                "open_quantity": 2,
                "multiplier": 100,
            }
        ]

    async def get_corporate_actions(self, account_number: str):
        # 2-for-1 split on AAPL
        return [
            {"type": "split", "symbol": "AAPL", "numerator": 2, "denominator": 1},
        ]

def _create_account() -> BrokerAccount:
    session = SessionLocal()
    try:
        from backend.models.user import User

        user = session.query(User).filter(User.username == "sync_tester").first()
        if not user:
            user = User(username="sync_tester", email="sync_tester@example.com", password_hash="x", is_active=True)
            session.add(user)
            session.commit()
            session.refresh(user)
        acct = BrokerAccount(
            user_id=user.id,
            broker=BrokerType.SCHWAB,
            account_number="SCHWAB123",
            account_name="Schwab Test",
            account_type=AccountType.TAXABLE,
            currency="USD",
        )
        session.add(acct)
        session.commit()
        session.refresh(acct)
        return acct
    finally:
        session.close()


def test_schwab_sync_positions_only():
    account = _create_account()
    session = SessionLocal()
    try:
        service = SchwabSyncService(client=DummySchwabClient())
        result = asyncio.get_event_loop().run_until_complete(
            service.sync_account_comprehensive(account_number=account.account_number, session=session)
        )
        assert result["status"] == "success"
        from backend.models.position import Position, PositionStatus, PositionType

        aapl = session.query(Position).filter(Position.account_id == account.id, Position.symbol == "AAPL").first()
        assert aapl is not None
        # 10 from positions, then 2:1 split → 20
        assert Decimal(aapl.quantity) == Decimal("20")
        assert aapl.position_type == PositionType.LONG
        # average cost 150 becomes 75 after split
        assert Decimal(aapl.average_cost) == Decimal("75")
        msft = session.query(Position).filter(Position.account_id == account.id, Position.symbol == "MSFT").first()
        assert msft is not None
        assert msft.status == PositionStatus.CLOSED

        # Options created
        from backend.models.options import Option

        opt = (
            session.query(Option)
            .filter(Option.account_id == account.id, Option.underlying_symbol == "AAPL", Option.option_type == "CALL")
            .first()
        )
        assert opt is not None and opt.open_quantity == 2
    finally:
        session.close()


