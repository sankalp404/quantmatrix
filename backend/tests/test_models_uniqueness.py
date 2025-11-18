import pytest
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal, Base, engine
from backend.models import BrokerAccount, User
from backend.models.broker_account import BrokerType, AccountType, AccountStatus
from backend.models.trade import Trade
from backend.models.transaction import Transaction, TransactionType
from backend.models.options import Option
from datetime import datetime, date


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def broker_account(db):
    # ensure user exists to satisfy FK
    user = db.query(User).filter_by(id=1).first()
    if not user:
        user = User(id=1, username="testuser", email="test@example.com", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    ba = BrokerAccount(
        user_id=1,
        broker=BrokerType.IBKR,
        account_number="TEST_ACC",
        account_name="Test Account",
        account_type=AccountType.TAXABLE,
        status=AccountStatus.ACTIVE,
        is_enabled=True,
        currency="USD",
    )
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return ba


def test_trade_unique_account_execution(db, broker_account):
    t1 = Trade(
        account_id=broker_account.id,
        symbol="AAPL",
        side="BUY",
        quantity=1,
        price=100.0,
        execution_id="exec-1",
    )
    db.add(t1)
    db.commit()

    t2 = Trade(
        account_id=broker_account.id,
        symbol="AAPL",
        side="BUY",
        quantity=1,
        price=100.0,
        execution_id="exec-1",
    )
    db.add(t2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_trade_unique_account_order(db, broker_account):
    t1 = Trade(
        account_id=broker_account.id,
        symbol="MSFT",
        side="BUY",
        quantity=1,
        price=100.0,
        order_id="ord-1",
    )
    db.add(t1)
    db.commit()

    t2 = Trade(
        account_id=broker_account.id,
        symbol="MSFT",
        side="BUY",
        quantity=1,
        price=100.0,
        order_id="ord-1",
    )
    db.add(t2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_transaction_unique_external_and_execution(db, broker_account):
    tx1 = Transaction(
        account_id=broker_account.id,
        symbol="AAPL",
        external_id="ext-1",
        execution_id="",
        transaction_type=TransactionType.BUY,
        amount=1.0,
        net_amount=1.0,
        currency="USD",
        transaction_date=datetime.utcnow(),
    )
    db.add(tx1)
    db.commit()

    tx2 = Transaction(
        account_id=broker_account.id,
        symbol="AAPL",
        external_id="ext-1",
        execution_id="",
        transaction_type=TransactionType.BUY,
        amount=1.0,
        net_amount=1.0,
        currency="USD",
        transaction_date=datetime.utcnow(),
    )
    db.add(tx2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    tx3 = Transaction(
        account_id=broker_account.id,
        symbol="AAPL",
        external_id="ext-2",
        execution_id="exec-1",
        transaction_type=TransactionType.BUY,
        amount=1.0,
        net_amount=1.0,
        currency="USD",
        transaction_date=datetime.utcnow(),
    )
    db.add(tx3)
    db.commit()

    tx4 = Transaction(
        account_id=broker_account.id,
        symbol="AAPL",
        external_id="ext-3",
        execution_id="exec-1",
        transaction_type=TransactionType.BUY,
        amount=1.0,
        net_amount=1.0,
        currency="USD",
        transaction_date=datetime.utcnow(),
    )
    db.add(tx4)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_option_position_unique_contract(db, broker_account):
    op1 = Option(
        user_id=1,
        account_id=broker_account.id,
        symbol="AAPL 2025-01-17 C 200",
        underlying_symbol="AAPL",
        strike_price=200.0,
        expiry_date=date(2025, 1, 17),
        option_type="CALL",
        open_quantity=1,
        multiplier=100,
    )
    db.add(op1)
    db.commit()

    op2 = Option(
        user_id=1,
        account_id=broker_account.id,
        symbol="AAPL 2025-01-17 C 200",
        underlying_symbol="AAPL",
        strike_price=200.0,
        expiry_date=date(2025, 1, 17),
        option_type="CALL",
        open_quantity=1,
        multiplier=100,
    )
    db.add(op2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
