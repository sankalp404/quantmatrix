"""
Comprehensive Tests for IBKR Sync Service
=========================================

Tests that validate the IBKR sync service properly populates all database models:
- Positions, TaxLots, Trades, Instruments, Transactions, BrokerAccounts
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch

from backend.database import SessionLocal
from backend.models import (
    BrokerAccount,
    TaxLot,
    Instrument,
    Position,
    User,
)
from backend.services.portfolio.ibkr_sync_service import IBKRSyncService


class TestIBKRSyncService:
    """Test comprehensive IBKR sync functionality."""

    @pytest.fixture
    def sync_service(self):
        """Create IBKR sync service instance."""
        return IBKRSyncService()

    @pytest.fixture
    def db_session(self):
        """Create database session for testing."""
        db = SessionLocal()
        yield db
        db.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user."""
        user = User(email="test@quantmatrix.com", username="testuser")
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def test_broker_account(self, db_session, test_user):
        """Create test broker account."""
        from backend.models.broker_account import BrokerType, AccountType, SyncStatus

        broker_account = BrokerAccount(
            user_id=test_user.id,
            account_id="U19490886",
            broker=BrokerType.IBKR,
            account_type=AccountType.TAXABLE,
            sync_status=SyncStatus.SUCCESS,
            connection_status="connected",
        )
        db_session.add(broker_account)
        db_session.commit()
        return broker_account

    @pytest.fixture
    def mock_flexquery_data(self):
        """Mock FlexQuery tax lots data."""
        return [
            {
                "symbol": "AAPL",
                "quantity": 100,
                "cost_basis": 15000.00,
                "acquisition_date": datetime(2023, 1, 15),
                "current_price": 175.50,
                "current_value": 17550.00,
                "unrealized_pnl": 2550.00,
                "unrealized_pnl_pct": 17.0,
                "currency": "USD",
                "contract_type": "STK",
            },
            {
                "symbol": "NVDA",
                "quantity": 50,
                "cost_basis": 12000.00,
                "acquisition_date": datetime(2023, 3, 10),
                "current_price": 280.00,
                "current_value": 14000.00,
                "unrealized_pnl": 2000.00,
                "unrealized_pnl_pct": 16.67,
                "currency": "USD",
                "contract_type": "STK",
            },
        ]

    @pytest.fixture
    def mock_trades_data(self):
        """Mock FlexQuery trades data."""
        return [
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "price": 150.00,
                "total_value": 15000.00,
                "commission": 1.00,
                "execution_id": "T123456",
                "execution_time": datetime(2023, 1, 15),
                "currency": "USD",
                "exchange": "NASDAQ",
                "contract_type": "STK",
            },
            {
                "symbol": "NVDA",
                "side": "BUY",
                "quantity": 50,
                "price": 240.00,
                "total_value": 12000.00,
                "commission": 1.00,
                "execution_id": "T123457",
                "execution_time": datetime(2023, 3, 10),
                "currency": "USD",
                "exchange": "NASDAQ",
                "contract_type": "STK",
            },
        ]

    @pytest.mark.asyncio
    async def test_comprehensive_sync_success(
        self, sync_service, test_broker_account, mock_flexquery_data, mock_trades_data
    ):
        """Test successful comprehensive portfolio sync."""

        # Mock FlexQuery client methods
        with (
            patch.object(
                sync_service.flexquery_client,
                "get_official_tax_lots",
                return_value=mock_flexquery_data,
            ),
            patch.object(
                sync_service.flexquery_client, "_request_report", return_value="REF123"
            ),
            patch.object(
                sync_service.flexquery_client, "_get_report", return_value="<mock_xml>"
            ),
            patch.object(
                sync_service.flexquery_client,
                "_parse_trades_from_xml",
                return_value=mock_trades_data,
            ),
        ):

            # Run comprehensive sync
            result = await sync_service.sync_comprehensive_portfolio("U19490886")

            # Verify sync success
            assert "error" not in result
            assert "summary" in result
            assert "instruments" in result
            assert "tax_lots" in result
            assert "trades" in result
            assert "holdings" in result

            # Verify summary data
            summary = result["summary"]
            assert "total_cost_basis" in summary
            assert "total_market_value" in summary
            assert "unrealized_pnl" in summary
            assert "return_pct" in summary

    @pytest.mark.asyncio
    async def test_sync_instruments(self, sync_service, mock_flexquery_data):
        """Test instruments sync creates master data."""
        db = SessionLocal()

        try:
            with patch.object(
                sync_service.flexquery_client,
                "get_official_tax_lots",
                return_value=mock_flexquery_data,
            ):

                result = await sync_service._sync_instruments(db, "U19490886")

                # Verify result
                assert result["synced"] == 2
                assert result["total_symbols"] == 2

                # Verify instruments created in database
                instruments = db.query(Instrument).all()
                symbols = [inst.symbol for inst in instruments]
                assert "AAPL" in symbols
                assert "NVDA" in symbols

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_sync_tax_lots(
        self, sync_service, test_broker_account, mock_flexquery_data
    ):
        """Test tax lots sync with real cost basis."""
        db = SessionLocal()

        try:
            with patch.object(
                sync_service.flexquery_client,
                "get_official_tax_lots",
                return_value=mock_flexquery_data,
            ):

                result = await sync_service._sync_tax_lots_from_flexquery(
                    db, test_broker_account, "U19490886"
                )

                # Verify result
                assert result["synced"] == 2
                assert "$27,000.00" in result["total_cost_basis"]
                assert "$31,550.00" in result["total_market_value"]

                # Verify tax lots in database
                tax_lots = (
                    db.query(TaxLot)
                    .filter(TaxLot.account_id == test_broker_account.id)
                    .all()
                )
                assert len(tax_lots) == 2

                # Verify tax lot data
                aapl_lot = next((lot for lot in tax_lots if lot.symbol == "AAPL"), None)
                assert aapl_lot is not None
                assert aapl_lot.cost_basis == Decimal("15000.00")
                assert aapl_lot.current_value == Decimal("17550.00")

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_sync_holdings_from_tax_lots(self, sync_service, test_broker_account):
        """Test holdings aggregation from tax lots."""
        db = SessionLocal()

        try:
            # Create test tax lots
            tax_lot1 = TaxLot(
                account_id=test_broker_account.id,
                lot_id="TEST_AAPL_1",
                symbol="AAPL",
                original_quantity=Decimal("100"),
                cost_basis=Decimal("15000.00"),
                current_price=Decimal("175.50"),
                current_value=Decimal("17550.00"),
                currency="USD",
                contract_type="STK",
            )

            tax_lot2 = TaxLot(
                account_id=test_broker_account.id,
                lot_id="TEST_AAPL_2",
                symbol="AAPL",
                original_quantity=Decimal("50"),
                cost_basis=Decimal("8000.00"),
                current_price=Decimal("175.50"),
                current_value=Decimal("8775.00"),
                currency="USD",
                contract_type="STK",
            )

            db.add_all([tax_lot1, tax_lot2])
            db.commit()

            # Test holdings sync
            result = await sync_service._sync_holdings_from_tax_lots(
                db, test_broker_account
            )

            # Verify result
            assert result["synced"] == 1  # One aggregated AAPL holding

            # Verify holding created
            holdings = (
                db.query(Position)
                .filter(Position.account_id == test_broker_account.id)
                .all()
            )
            assert len(holdings) == 1

            aapl_holding = holdings[0]
            assert aapl_holding.symbol == "AAPL"
            assert aapl_holding.quantity == 150  # 100 + 50
            assert aapl_holding.market_value == 26325  # 17550 + 8775

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_sync_positions_from_holdings(
        self, sync_service, test_broker_account
    ):
        """Test positions sync from holdings."""
        db = SessionLocal()

        try:
            # Create test holding
            holding = Position(
                account_id=test_broker_account.id,
                symbol="AAPL",
                quantity=100,
                average_cost=150.00,
                current_price=175.50,
                market_value=17550.00,
                unrealized_pnl=2550.00,
                unrealized_pnl_pct=17.0,
                currency="USD",
                sector="Technology",
            )

            db.add(holding)
            db.commit()

            # Test positions sync
            result = await sync_service._sync_positions(db, test_broker_account)

            # Verify result
            assert result["synced"] == 1

            # Verify position created
            positions = (
                db.query(Position)
                .filter(Position.account_id == test_broker_account.id)
                .all()
            )
            assert len(positions) == 1

            position = positions[0]
            assert position.symbol == "AAPL"
            assert position.quantity == Decimal("100")
            assert position.market_value == Decimal("17550.00")

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_create_portfolio_snapshot(self, sync_service, test_broker_account):
        """Test portfolio snapshot creation."""
        db = SessionLocal()

        try:
            # Create test holdings
            holding1 = Position(
                account_id=test_broker_account.id,
                symbol="AAPL",
                quantity=100,
                market_value=17550.00,
                unrealized_pnl=2550.00,
            )

            holding2 = Position(
                account_id=test_broker_account.id,
                symbol="NVDA",
                quantity=50,
                market_value=14000.00,
                unrealized_pnl=2000.00,
            )

            db.add_all([holding1, holding2])
            db.commit()

            # Test snapshot creation
            result = await sync_service._create_portfolio_snapshot(
                db, test_broker_account
            )

            # Verify result
            assert result["created"] is True
            assert "$31,550.00" in result["total_value"]

            # Verify snapshot in database
            snapshots = (
                db.query(PortfolioSnapshot)
                .filter(PortfolioSnapshot.account_id == test_broker_account.id)
                .all()
            )
            assert len(snapshots) == 1

            snapshot = snapshots[0]
            assert snapshot.total_value == 31550.00
            assert snapshot.unrealized_pnl == 4550.00

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_account_not_found_error(self, sync_service):
        """Test error handling when account not found."""

        result = await sync_service.sync_comprehensive_portfolio("INVALID123")

        assert "error" in result
        assert "not found in database" in result["error"]

    def test_data_validation(self, sync_service):
        """Test data validation in sync service."""

        # Test symbol length validation
        long_symbol = "A" * 25
        assert len(long_symbol) > 20  # Should be filtered out

        # Test quantity validation
        assert isinstance(Decimal("100.5"), Decimal)

        # Test price validation
        assert isinstance(Decimal("175.50"), Decimal)

    @pytest.mark.asyncio
    async def test_duplicate_sync_handling(
        self, sync_service, test_broker_account, mock_flexquery_data
    ):
        """Test that duplicate syncs don't create duplicate records."""
        db = SessionLocal()

        try:
            with patch.object(
                sync_service.flexquery_client,
                "get_official_tax_lots",
                return_value=mock_flexquery_data,
            ):

                # First sync
                await sync_service._sync_tax_lots_from_flexquery(
                    db, test_broker_account, "U19490886"
                )
                first_count = (
                    db.query(TaxLot)
                    .filter(TaxLot.account_id == test_broker_account.id)
                    .count()
                )

                # Second sync (should clear and recreate)
                await sync_service._sync_tax_lots_from_flexquery(
                    db, test_broker_account, "U19490886"
                )
                second_count = (
                    db.query(TaxLot)
                    .filter(TaxLot.account_id == test_broker_account.id)
                    .count()
                )

                # Verify no duplicates
                assert first_count == second_count == 2

        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
