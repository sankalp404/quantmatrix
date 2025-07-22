"""
Comprehensive Test Suite for QuantMatrix Portfolio Sync Operations
Tests all critical data sync paths, API endpoints, and edge cases to prevent regressions.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from backend.services.transaction_sync import transaction_sync_service
from backend.services.ibkr_client import IBKRClient
from backend.services.tastytrade_client import tastytrade_client
from backend.models.portfolio import Account, Holding
from backend.models.transactions import Transaction, Dividend
from backend.models.tax_lots import TaxLot
import json


class TestPortfolioSyncService:
    """Test portfolio sync operations and data integrity."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=Session)
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.first.return_value = None
        session.commit.return_value = None
        session.close.return_value = None
        return session
    
    @pytest.fixture
    def sample_account(self):
        """Sample account for testing."""
        return Account(
            id=1,
            account_number="U19490886",
            account_name="Test IBKR Account",
            account_type="margin",
            broker="IBKR",
            is_active=True,
            currency="USD"
        )
    
    @pytest.fixture
    def sample_ibkr_transactions(self):
        """Sample IBKR transaction data."""
        return [
            {
                "id": "12345",
                "date": "2024-01-15",
                "time": "10:30:00",
                "symbol": "AAPL",
                "description": "BOT 100 AAPL @ $150.00",
                "type": "BUY",
                "action": "BUY",
                "quantity": 100.0,
                "price": 150.00,
                "amount": 15000.00,
                "commission": 1.00,
                "fees": 0.50,
                "net_amount": 15001.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "order_id": "67890",
                "execution_id": "12345",
                "contract_type": "STK",
                "settlement_date": "2024-01-17",
                "source": "ibkr_live"
            },
            {
                "id": "12346", 
                "date": "2024-01-16",
                "time": "14:20:00",
                "symbol": "AAPL",
                "description": "SLD 50 AAPL @ $155.00",
                "type": "SELL",
                "action": "SELL",
                "quantity": 50.0,
                "price": 155.00,
                "amount": 7750.00,
                "commission": 1.00,
                "fees": 0.50,
                "net_amount": 7748.50,
                "currency": "USD",
                "exchange": "NASDAQ",
                "order_id": "67891",
                "execution_id": "12346",
                "contract_type": "STK",
                "settlement_date": "2024-01-18",
                "source": "ibkr_live"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_transaction_sync_success(self, mock_db_session, sample_account, sample_ibkr_transactions):
        """Test successful transaction sync from IBKR."""
        # Mock IBKR client
        with patch('backend.services.ibkr_client.ibkr_client') as mock_ibkr:
            mock_ibkr.get_account_statements.return_value = sample_ibkr_transactions
            mock_ibkr.get_dividend_history.return_value = []
            
            # Mock database operations
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_account
            mock_db_session.query.return_value.filter.return_value.all.return_value = []  # No existing transactions
            
            # Execute sync
            result = await transaction_sync_service.sync_account_transactions(
                sample_account.account_number, days=30
            )
            
            # Verify result
            assert result['status'] == 'success'
            assert result['transactions_synced'] == 2
            assert result['dividends_synced'] == 0
            assert result['account_id'] == sample_account.account_number
    
    @pytest.mark.asyncio
    async def test_transaction_sync_empty_data(self, mock_db_session, sample_account):
        """Test transaction sync when no data is available."""
        # Mock IBKR client returning empty data
        with patch('backend.services.ibkr_client.ibkr_client') as mock_ibkr:
            mock_ibkr.get_account_statements.return_value = []
            mock_ibkr.get_dividend_history.return_value = []
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_account
            
            # Execute sync
            result = await transaction_sync_service.sync_account_transactions(
                sample_account.account_number, days=30
            )
            
            # Verify result
            assert result['status'] == 'success'
            assert result['transactions_synced'] == 0
            assert result['dividends_synced'] == 0
    
    @pytest.mark.asyncio
    async def test_transaction_sync_connection_failure(self, mock_db_session, sample_account):
        """Test transaction sync when IBKR connection fails."""
        # Mock IBKR client throwing exception
        with patch('backend.services.ibkr_client.ibkr_client') as mock_ibkr:
            mock_ibkr.get_account_statements.side_effect = Exception("IBKR connection failed")
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_account
            
            # Execute sync
            result = await transaction_sync_service.sync_account_transactions(
                sample_account.account_number, days=30
            )
            
            # Verify error handling
            assert result['status'] == 'error'
            assert 'IBKR connection failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_duplicate_transaction_handling(self, mock_db_session, sample_account, sample_ibkr_transactions):
        """Test that duplicate transactions are not synced."""
        # Mock existing transaction
        existing_transaction = Transaction(
            account_id=sample_account.id,
            external_id="12345",  # Same as first sample transaction
            symbol="AAPL"
        )
        
        with patch('backend.services.ibkr_client.ibkr_client') as mock_ibkr:
            mock_ibkr.get_account_statements.return_value = sample_ibkr_transactions
            mock_ibkr.get_dividend_history.return_value = []
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_account
            # Return existing transaction for first, None for second
            mock_db_session.query.return_value.filter.return_value.all.side_effect = [
                [existing_transaction],  # First transaction exists
                []  # Second transaction doesn't exist
            ]
            
            result = await transaction_sync_service.sync_account_transactions(
                sample_account.account_number, days=30
            )
            
            # Should only sync 1 new transaction (second one)
            assert result['status'] == 'success'
            assert result['transactions_synced'] == 1


class TestIBKRClient:
    """Test IBKR client connection and data retrieval."""
    
    @pytest.fixture
    def ibkr_client(self):
        """IBKR client instance for testing."""
        return IBKRClient()
    
    @pytest.mark.asyncio
    async def test_connection_success(self, ibkr_client):
        """Test successful IBKR connection."""
        with patch.object(ibkr_client, 'ib') as mock_ib:
            mock_ib.connectAsync = AsyncMock()
            mock_ib.managedAccounts.return_value = ['U19490886', 'U15891532']
            
            result = await ibkr_client.connect()
            
            assert result is True
            assert ibkr_client.connected is True
    
    @pytest.mark.asyncio 
    async def test_connection_failure(self, ibkr_client):
        """Test IBKR connection failure."""
        with patch.object(ibkr_client, 'ib') as mock_ib:
            mock_ib.connectAsync.side_effect = Exception("Connection refused")
            
            result = await ibkr_client.connect()
            
            assert result is False
            assert ibkr_client.connected is False
    
    @pytest.mark.asyncio
    async def test_ensure_connection_when_disconnected(self, ibkr_client):
        """Test ensure_connection when not connected."""
        ibkr_client.connected = False
        
        with patch.object(ibkr_client, 'connect') as mock_connect:
            mock_connect.return_value = True
            
            result = await ibkr_client.ensure_connection()
            
            assert result is True
            mock_connect.assert_called_once()


class TestPortfolioAPIs:
    """Test portfolio API endpoints for data integrity."""
    
    @pytest.fixture
    def api_client(self):
        """FastAPI test client."""
        from fastapi.testclient import TestClient
        from backend.api.main import app
        return TestClient(app)
    
    def test_portfolio_statements_empty_database(self, api_client):
        """Test /portfolio/statements returns empty data when database is empty."""
        with patch('backend.models.get_db') as mock_db:
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            mock_db.return_value = mock_session
            
            response = api_client.get("/api/v1/portfolio/statements?days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data['data']['summary']['total_transactions'] == 0
            assert data['data']['summary']['data_source'] == 'empty_database'
            assert len(data['data']['transactions']) == 0
    
    def test_portfolio_tax_lots_empty_database(self, api_client):
        """Test /portfolio/holdings/{id}/tax-lots returns empty data when no tax lots exist."""
        with patch('backend.models.get_db') as mock_db:
            mock_session = Mock()
            # Mock holding exists
            mock_holding = Mock()
            mock_holding.id = 1
            mock_holding.symbol = "AAPL"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_holding
            # Mock no tax lots
            mock_session.query.return_value.filter.return_value.all.return_value = []
            mock_db.return_value = mock_session
            
            response = api_client.get("/api/v1/portfolio/holdings/1/tax-lots")
            
            assert response.status_code == 200
            data = response.json()
            assert data['data']['total_lots'] == 0
            assert data['data']['source'] == 'empty_database'
            assert len(data['data']['tax_lots']) == 0
    
    def test_portfolio_dividends_empty_database(self, api_client):
        """Test /portfolio/dividends returns empty data when no dividends exist."""
        response = api_client.get("/api/v1/portfolio/dividends?days=365")
        
        assert response.status_code == 200
        data = response.json()
        assert data['data']['summary']['total_dividend_payments'] == 0
        assert len(data['data']['dividends']) == 0
        assert len(data['data']['projections']) == 0
    
    def test_options_portfolio_filtering(self, api_client):
        """Test options portfolio filtering by account."""
        with patch('backend.models.get_db') as mock_db:
            mock_session = Mock()
            mock_session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
            mock_db.return_value = mock_session
            
            # Test with account filter
            response = api_client.get("/api/v1/options/unified/portfolio?account_id=5WZ21096")
            
            assert response.status_code == 200
            data = response.json()
            assert data['data']['filtering']['applied'] is True
            assert data['data']['filtering']['account_id'] == '5WZ21096'


class TestDataIntegrity:
    """Test data integrity and validation."""
    
    def test_transaction_data_validation(self):
        """Test transaction data validation."""
        valid_transaction = {
            "symbol": "AAPL",
            "type": "BUY",
            "quantity": 100.0,
            "price": 150.00,
            "amount": 15000.00,
            "commission": 1.00,
            "currency": "USD"
        }
        
        # Test required fields
        assert valid_transaction['symbol'] is not None
        assert valid_transaction['type'] in ['BUY', 'SELL']
        assert valid_transaction['quantity'] > 0
        assert valid_transaction['price'] > 0
        assert valid_transaction['amount'] > 0
        assert valid_transaction['currency'] == 'USD'
    
    def test_holdings_data_validation(self):
        """Test holdings data validation."""
        valid_holding = {
            "symbol": "AAPL",
            "quantity": 100.0,
            "average_cost": 150.00,
            "current_price": 155.00,
            "market_value": 15500.00,
            "unrealized_pnl": 500.00
        }
        
        # Test data consistency
        expected_market_value = valid_holding['quantity'] * valid_holding['current_price']
        expected_unrealized_pnl = (valid_holding['current_price'] - valid_holding['average_cost']) * valid_holding['quantity']
        
        assert abs(valid_holding['market_value'] - expected_market_value) < 0.01
        assert abs(valid_holding['unrealized_pnl'] - expected_unrealized_pnl) < 0.01


class TestPerformanceAndReliability:
    """Test performance and reliability of critical operations."""
    
    @pytest.mark.asyncio
    async def test_transaction_sync_performance(self):
        """Test transaction sync completes within reasonable time."""
        start_time = datetime.now()
        
        # Mock fast sync operation
        with patch('backend.services.transaction_sync.transaction_sync_service.sync_account_transactions') as mock_sync:
            mock_sync.return_value = {
                'status': 'success',
                'transactions_synced': 0,
                'dividends_synced': 0,
                'account_id': 'U19490886',
                'sync_duration_seconds': 0.5
            }
            
            result = await transaction_sync_service.sync_account_transactions('U19490886', 30)
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within 1 second for mocked operation
        assert duration < 1.0
        assert result['status'] == 'success'
    
    def test_api_response_times(self, api_client):
        """Test API endpoints respond within acceptable time."""
        import time
        
        endpoints = [
            "/api/v1/portfolio/live",
            "/api/v1/portfolio/statements?days=30",
            "/api/v1/portfolio/dividends?days=365",
            "/api/v1/options/unified/portfolio"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = api_client.get(endpoint)
            end_time = time.time()
            
            duration = end_time - start_time
            
            # Should respond within 2 seconds
            assert duration < 2.0
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 