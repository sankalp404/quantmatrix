#!/usr/bin/env python3
"""
Comprehensive Tests for TastyTrade Client
=========================================

Tests all functionality of the TastyTradeClient including:
- Authentication and connection
- Account enumeration
- Position retrieval
- Transaction history
- Error handling and retry logic
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

try:
    from backend.services.clients.tastytrade_client import (
        TastyTradeClient,
        TASTYTRADE_AVAILABLE,
    )
except ImportError:
    TASTYTRADE_AVAILABLE = False


class TestTastyTradeClient:
    """Test suite for TastyTradeClient."""

    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        if not TASTYTRADE_AVAILABLE:
            pytest.skip("TastyTrade SDK not available")
        return TastyTradeClient()

    def test_client_initialization(self, client):
        """Test that client initializes correctly."""
        assert client.session is None
        assert client.accounts == []
        assert not client.connected
        assert client.max_retries == 3
        assert client.base_retry_delay == 2
        assert client.connection_health["status"] == "disconnected"

    def test_client_singleton_pattern(self):
        """Test that TastyTradeClient follows singleton pattern."""
        if not TASTYTRADE_AVAILABLE:
            pytest.skip("TastyTrade SDK not available")

        client1 = TastyTradeClient()
        client2 = TastyTradeClient()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """Test successful connection to TastyTrade."""
        mock_session = Mock()
        mock_account = Mock()
        import os

        mock_account.account_number = os.getenv(
            "TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT"
        )
        mock_account.nickname = "Test Account"
        mock_account.account_type_name = "Individual"

        with (
            patch(
                "backend.services.clients.tastytrade_client.Session",
                return_value=mock_session,
            ),
            patch(
                "backend.services.clients.tastytrade_client.Account.get",
                return_value=[mock_account],
            ),
            patch.object(client, "_verify_connection", return_value=True),
            patch(
                "backend.services.clients.tastytrade_client.settings"
            ) as mock_settings,
        ):

            mock_settings.TASTYTRADE_USERNAME = "test_user"
            mock_settings.TASTYTRADE_PASSWORD = "test_pass"
            mock_settings.TASTYTRADE_IS_TEST = True
            mock_settings.TASTYTRADE_ACCOUNT_NUMBER = "TEST_ACCOUNT"

            success = await client.connect_with_retry()

            assert success is True
            assert client.connected is True
            assert client.session == mock_session
            assert len(client.accounts) == 1
            assert client.accounts[0].account_number == "5WZ21096"

    @pytest.mark.asyncio
    async def test_connect_no_credentials(self, client):
        """Test connection failure when credentials not configured."""
        with patch(
            "backend.services.clients.tastytrade_client.settings"
        ) as mock_settings:
            mock_settings.TASTYTRADE_USERNAME = None
            mock_settings.TASTYTRADE_PASSWORD = None

            success = await client.connect_with_retry()
            assert success is False

    @pytest.mark.asyncio
    async def test_connect_with_retry_logic(self, client):
        """Test connection retry logic."""
        mock_session = Mock()

        with (
            patch(
                "backend.services.clients.tastytrade_client.Session"
            ) as mock_session_class,
            patch(
                "backend.services.clients.tastytrade_client.Account.get"
            ) as mock_account_get,
            patch.object(client, "_verify_connection", return_value=True),
            patch(
                "backend.services.clients.tastytrade_client.settings"
            ) as mock_settings,
            patch("asyncio.sleep"),
        ):  # Speed up test

            mock_settings.TASTYTRADE_USERNAME = "test_user"
            mock_settings.TASTYTRADE_PASSWORD = "test_pass"

            # First attempt fails, second succeeds
            mock_session_class.side_effect = [
                Exception("Connection failed"),
                mock_session,
            ]
            mock_account_get.return_value = []

            success = await client.connect_with_retry(max_attempts=2)
            assert success is True
            assert client.retry_count == 0  # Reset after success

    @pytest.mark.asyncio
    async def test_verify_connection(self, client):
        """Test connection verification."""
        # Mock successful verification
        result = await client._verify_connection()
        # Verify that it returns without error (basic implementation)
        assert result is not False

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test disconnection."""
        mock_session = Mock()
        client.session = mock_session
        client.connected = True
        client.accounts = [Mock()]

        await client.disconnect()

        assert client.session is None
        assert client.connected is False
        assert client.accounts == []
        assert client.connection_health["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_get_accounts_success(self, client):
        """Test successful account retrieval."""
        mock_account1 = Mock()
        mock_account1.account_number = "5WZ21096"
        mock_account1.nickname = "Primary"
        mock_account1.account_type_name = "Individual"
        mock_account1.is_closed = False

        mock_account2 = Mock()
        mock_account2.account_number = "5WZ21097"
        mock_account2.nickname = "IRA"
        mock_account2.account_type_name = "Traditional IRA"
        mock_account2.is_closed = False

        client.connected = True
        client.accounts = [mock_account1, mock_account2]

        accounts = await client.get_accounts()

        assert len(accounts) == 2
        assert accounts[0]["account_number"] == "5WZ21096"
        assert accounts[0]["nickname"] == "Primary"
        assert accounts[0]["account_type"] == "Individual"
        assert accounts[1]["account_number"] == "5WZ21097"

    @pytest.mark.asyncio
    async def test_get_accounts_not_connected(self, client):
        """Test account retrieval when not connected."""
        client.connected = False

        accounts = await client.get_accounts()
        assert accounts == []

    @pytest.mark.asyncio
    async def test_get_current_positions_success(self, client):
        """Test successful position retrieval."""
        mock_account = Mock()
        import os

        mock_account.account_number = os.getenv(
            "TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT"
        )

        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.instrument_type = "Equity"
        mock_position.quantity = 100.0
        mock_position.quantity_direction = "Long"
        mock_position.close_price = 150.0
        mock_position.average_open_price = 149.0
        mock_position.average_yearly_market_close_price = 148.0
        mock_position.average_daily_market_close_price = 151.0
        mock_position.multiplier = 1.0
        mock_position.cost_effect = "Debit"
        mock_position.is_suppressed = False
        mock_position.is_frozen = False
        mock_position.realized_day_gain = 100.0
        mock_position.realized_day_gain_effect = "Credit"
        mock_position.realized_day_gain_date = "2024-01-15"
        mock_position.realized_today = 50.0
        mock_position.created_at = datetime.now()
        mock_position.updated_at = datetime.now()
        mock_position.mark = 150.5
        mock_position.mark_value = 15050.0
        mock_position.restricted_quantity = 0.0
        mock_position.expired_quantity = 0.0
        mock_position.expiring_quantity = 0.0
        mock_position.right_quantity = 0.0
        mock_position.pending_quantity = 0.0

        # Mock instrument
        mock_instrument = Mock()
        mock_instrument.underlying_symbol = ""
        mock_instrument.product_code = "AAPL"
        mock_instrument.exchange = "NASDAQ"
        mock_instrument.listed_market = "NASDAQ"
        mock_instrument.description = "Apple Inc."
        mock_instrument.is_closing_only = False
        mock_instrument.active = True

        mock_position.instrument = mock_instrument

        mock_account.get_positions.return_value = [mock_position]

        client.connected = True
        client.accounts = [mock_account]

        positions = await client.get_current_positions(
            os.getenv("TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT")
        )

        assert len(positions) == 1
        position = positions[0]
        assert position["symbol"] == "AAPL"
        assert position["instrument_type"] == "Equity"
        assert position["quantity"] == 100.0
        assert position["mark_value"] == 15050.0
        assert position["account_number"] == "5WZ21096"
        assert position["underlying_symbol"] == ""
        assert position["exchange"] == "NASDAQ"

    @pytest.mark.asyncio
    async def test_get_current_positions_options(self, client):
        """Test position retrieval for options."""
        mock_account = Mock()
        import os

        mock_account.account_number = os.getenv(
            "TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT"
        )

        mock_option_position = Mock()
        mock_option_position.symbol = "AAPL 240315C150"
        mock_option_position.instrument_type = "Equity Option"
        mock_option_position.quantity = 5.0
        mock_option_position.quantity_direction = "Long"
        mock_option_position.close_price = 2.50
        mock_option_position.average_open_price = 2.00
        mock_option_position.average_yearly_market_close_price = 2.25
        mock_option_position.average_daily_market_close_price = 2.60
        mock_option_position.multiplier = 100.0
        mock_option_position.cost_effect = "Debit"
        mock_option_position.is_suppressed = False
        mock_option_position.is_frozen = False
        mock_option_position.realized_day_gain = 250.0
        mock_option_position.realized_day_gain_effect = "Credit"
        mock_option_position.realized_day_gain_date = "2024-01-15"
        mock_option_position.realized_today = 125.0
        mock_option_position.created_at = datetime.now()
        mock_option_position.updated_at = datetime.now()
        mock_option_position.mark = 2.75
        mock_option_position.mark_value = 1375.0
        mock_option_position.restricted_quantity = 0.0
        mock_option_position.expired_quantity = 0.0
        mock_option_position.expiring_quantity = 0.0
        mock_option_position.right_quantity = 0.0
        mock_option_position.pending_quantity = 0.0

        # Mock option instrument
        mock_option_instrument = Mock()
        mock_option_instrument.underlying_symbol = "AAPL"
        mock_option_instrument.product_code = "AAPL"
        mock_option_instrument.exchange = "CBOE"
        mock_option_instrument.listed_market = "CBOE"
        mock_option_instrument.description = "AAPL Mar 15 '24 $150 Call"
        mock_option_instrument.is_closing_only = False
        mock_option_instrument.active = True
        mock_option_instrument.option_type = "C"
        mock_option_instrument.strike_price = 150.0
        mock_option_instrument.expiration_date = "2024-03-15"
        mock_option_instrument.days_to_expiration = 60
        mock_option_instrument.delta = 0.75
        mock_option_instrument.gamma = 0.05
        mock_option_instrument.theta = -0.02
        mock_option_instrument.vega = 0.25

        mock_option_position.instrument = mock_option_instrument

        mock_account.get_positions.return_value = [mock_option_position]

        client.connected = True
        client.accounts = [mock_account]

        import os

        positions = await client.get_current_positions(
            os.getenv("TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT")
        )

        assert len(positions) == 1
        position = positions[0]
        assert position["symbol"] == "AAPL 240315C150"
        assert position["instrument_type"] == "Equity Option"
        assert position["underlying_symbol"] == "AAPL"
        assert position["option_type"] == "C"
        assert position["strike_price"] == 150.0
        assert position["expiration_date"] == "2024-03-15"
        assert position["delta"] == 0.75
        assert position["gamma"] == 0.05
        assert position["theta"] == -0.02
        assert position["vega"] == 0.25

    @pytest.mark.asyncio
    async def test_get_current_positions_account_not_found(self, client):
        """Test position retrieval for non-existent account."""
        client.connected = True
        client.accounts = []

        positions = await client.get_current_positions("NONEXISTENT")
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_current_positions_not_connected(self, client):
        """Test position retrieval when not connected."""
        client.connected = False

        positions = await client.get_current_positions("5WZ21096")
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_transaction_history_success(self, client):
        """Test successful transaction history retrieval."""
        mock_account = Mock()
        import os

        mock_account.account_number = os.getenv(
            "TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT"
        )

        mock_transaction = Mock()
        mock_transaction.id = "TXN123456"
        mock_transaction.symbol = "AAPL"
        mock_transaction.instrument_type = "Equity"
        mock_transaction.underlying_symbol = ""
        mock_transaction.transaction_type = "Trade"
        mock_transaction.action = "Buy to Open"
        mock_transaction.quantity = 100.0
        mock_transaction.price = 149.0
        mock_transaction.executed_at = datetime.now()
        mock_transaction.transaction_date = "2024-01-15"
        mock_transaction.value = 14900.0
        mock_transaction.value_effect = "Debit"
        mock_transaction.net_value = 14901.0
        mock_transaction.net_value_effect = "Debit"
        mock_transaction.is_estimated_fee = False
        mock_transaction.order_id = "ORD123"
        mock_transaction.ext_global_order_number = 789
        mock_transaction.ext_group_id = "GRP456"
        mock_transaction.ext_group_fill_id = "FILL789"
        mock_transaction.ext_exec_id = "EXEC123"
        mock_transaction.commission = 1.0
        mock_transaction.commission_effect = "Debit"
        mock_transaction.clearing_fees = 0.1
        mock_transaction.clearing_fees_effect = "Debit"
        mock_transaction.proprietary_index_option_fees = 0.0
        mock_transaction.proprietary_index_option_fees_effect = "None"
        mock_transaction.regulatory_fees = 0.05
        mock_transaction.regulatory_fees_effect = "Debit"

        mock_account.get_history.return_value = [mock_transaction]

        client.connected = True
        client.accounts = [mock_account]

        import os

        transactions = await client.get_transaction_history(
            os.getenv("TASTYTRADE_ACCOUNT_NUMBER", "TEST_ACCOUNT"), days=30
        )

        assert len(transactions) == 1
        transaction = transactions[0]
        assert transaction["id"] == "TXN123456"
        assert transaction["account_number"] == "5WZ21096"
        assert transaction["symbol"] == "AAPL"
        assert transaction["action"] == "Buy to Open"
        assert transaction["quantity"] == 100.0
        assert transaction["price"] == 149.0
        assert transaction["commission"] == 1.0

    @pytest.mark.asyncio
    async def test_get_transaction_history_account_not_found(self, client):
        """Test transaction history for non-existent account."""
        client.connected = True
        client.accounts = []

        transactions = await client.get_transaction_history("NONEXISTENT")
        assert transactions == []

    @pytest.mark.asyncio
    async def test_get_transaction_history_not_connected(self, client):
        """Test transaction history when not connected."""
        client.connected = False

        transactions = await client.get_transaction_history("5WZ21096")
        assert transactions == []

    @pytest.mark.asyncio
    async def test_error_handling_in_positions(self, client):
        """Test error handling in get_current_positions."""
        mock_account = Mock()
        mock_account.account_number = "5WZ21096"
        mock_account.get_positions.side_effect = Exception("API Error")

        client.connected = True
        client.accounts = [mock_account]

        positions = await client.get_current_positions("5WZ21096")
        assert positions == []

    @pytest.mark.asyncio
    async def test_error_handling_in_transactions(self, client):
        """Test error handling in get_transaction_history."""
        mock_account = Mock()
        mock_account.account_number = "5WZ21096"
        mock_account.get_history.side_effect = Exception("API Error")

        client.connected = True
        client.accounts = [mock_account]

        transactions = await client.get_transaction_history("5WZ21096")
        assert transactions == []


class TestTastyTradeClientIntegration:
    """Integration tests for TastyTrade client (require real credentials)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_tastytrade_connection(self):
        """Test real TastyTrade connection (requires valid credentials)."""
        if not TASTYTRADE_AVAILABLE:
            pytest.skip("TastyTrade SDK not available")

        client = TastyTradeClient()

        # Try to connect
        success = await client.connect_with_retry()

        if success:
            assert client.connected is True
            assert client.session is not None
            assert len(client.accounts) > 0

            # Test getting accounts
            accounts = await client.get_accounts()
            assert isinstance(accounts, list)
            assert len(accounts) > 0

            # Test getting positions
            first_account = accounts[0]
            positions = await client.get_current_positions(
                first_account["account_number"]
            )
            assert isinstance(positions, list)

            # Clean up
            await client.disconnect()
        else:
            pytest.skip("TastyTrade credentials not configured or invalid")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_position_data_structure(self):
        """Test real position data has expected structure."""
        if not TASTYTRADE_AVAILABLE:
            pytest.skip("TastyTrade SDK not available")

        client = TastyTradeClient()

        success = await client.connect_with_retry()
        if not success:
            pytest.skip("TastyTrade connection failed")

        try:
            accounts = await client.get_accounts()
            if not accounts:
                pytest.skip("No TastyTrade accounts found")

            positions = await client.get_current_positions(
                accounts[0]["account_number"]
            )

            if positions:
                # Verify structure of real position data
                position = positions[0]
                required_fields = [
                    "symbol",
                    "instrument_type",
                    "quantity",
                    "mark_value",
                    "account_number",
                ]

                for field in required_fields:
                    assert field in position, f"Missing field: {field}"

                # Verify data types
                assert isinstance(position["quantity"], float)
                assert isinstance(position["mark_value"], float)

        finally:
            await client.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
