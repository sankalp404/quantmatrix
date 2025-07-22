# QuantMatrix Test Suite Guide

## 🧪 Comprehensive Testing Framework

This test suite prevents regressions in critical portfolio sync operations, API endpoints, and data integrity. Run these tests before deploying changes.

## 📋 **Test Categories**

### 1. **Portfolio Sync Tests**
- Transaction sync from IBKR and TastyTrade
- Duplicate transaction handling
- Connection failure scenarios
- Empty data handling

### 2. **IBKR Client Tests**
- Connection management
- Retry logic with dynamic client IDs
- Error handling and recovery

### 3. **API Endpoint Tests**
- Portfolio statements (empty database)
- Tax lots (empty database) 
- Dividends (empty database)
- Options portfolio filtering

### 4. **Data Integrity Tests**
- Transaction validation
- Holdings calculations
- P&L consistency checks

### 5. **Performance Tests**
- API response times (<2 seconds)
- Sync operation timing
- Database query performance

## 🚀 **Running Tests**

### **Prerequisites**
```bash
pip install pytest pytest-asyncio
```

### **Run All Tests**
```bash
# From backend directory
cd backend
python -m pytest test_portfolio_sync.py -v

# With detailed output
python -m pytest test_portfolio_sync.py -v --tb=long

# Run specific test class
python -m pytest test_portfolio_sync.py::TestPortfolioSyncService -v

# Run specific test
python -m pytest test_portfolio_sync.py::TestPortfolioSyncService::test_transaction_sync_success -v
```

### **Run Tests in Docker**
```bash
# Start test container
docker-compose exec backend python -m pytest test_portfolio_sync.py -v

# Run with coverage
docker-compose exec backend python -m pytest test_portfolio_sync.py --cov=backend --cov-report=html
```

## 📊 **Expected Test Results**

### **Passing Tests (All Should Pass)**
```
✅ test_transaction_sync_success - IBKR transaction sync works
✅ test_transaction_sync_empty_data - Handles empty data gracefully
✅ test_transaction_sync_connection_failure - Error handling works
✅ test_duplicate_transaction_handling - No duplicate data synced
✅ test_connection_success - IBKR client connects properly
✅ test_connection_failure - Connection failures handled
✅ test_portfolio_statements_empty_database - API returns empty data correctly
✅ test_portfolio_tax_lots_empty_database - Tax lots API works with empty DB
✅ test_options_portfolio_filtering - Account filtering works
✅ test_transaction_data_validation - Data integrity maintained
✅ test_api_response_times - Performance requirements met
```

## 🔧 **Common Test Scenarios**

### **Test 1: Verify No Fake Data**
```python
def test_no_fake_data_in_apis():
    response = client.get("/api/v1/portfolio/statements")
    data = response.json()
    
    # Should be empty or real data, never "realistic_sample"
    for transaction in data['data']['transactions']:
        assert transaction['source'] != 'realistic_sample'
        assert transaction['source'] != 'ibkr_sample'
```

### **Test 2: Account Filtering Works**
```python
def test_account_filtering():
    response = client.get("/api/v1/options/unified/portfolio?account_id=5WZ21096")
    data = response.json()
    
    assert data['data']['filtering']['applied'] is True
    assert data['data']['filtering']['account_id'] == '5WZ21096'
```

### **Test 3: IBKR Connection Management**
```python
async def test_ibkr_connection_cleanup():
    client = IBKRClient()
    
    # Should handle multiple connection attempts
    result1 = await client.connect()
    result2 = await client.connect()  # Should reuse or cleanup properly
    
    assert not (result1 and result2 and "connection conflicts")
```

## 🚨 **Critical Test Failures**

### **If Transaction Sync Tests Fail:**
1. Check IBKR TWS connection (port 7497)
2. Verify client ID conflicts resolved
3. Check database connection
4. Review transaction sync service logs

### **If API Tests Fail:**
1. Verify database is empty (no fake data)
2. Check API endpoint routing
3. Verify mock data setup
4. Check authentication/permissions

### **If Performance Tests Fail:**
1. Check database query optimization
2. Review API response caching
3. Check connection pooling
4. Monitor resource usage

## 📝 **Adding New Tests**

### **New API Endpoint Test**
```python
def test_new_endpoint(self, api_client):
    """Test new API endpoint functionality."""
    response = api_client.get("/api/v1/new/endpoint")
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    # Add specific assertions
```

### **New Data Validation Test**
```python
def test_new_data_validation(self):
    """Test new data validation rules."""
    valid_data = {
        "field1": "value1",
        "field2": 100.0
    }
    
    # Test required fields
    assert valid_data['field1'] is not None
    assert valid_data['field2'] > 0
```

## 🔄 **Continuous Integration**

### **Pre-commit Tests**
```bash
# Run before committing changes
python -m pytest test_portfolio_sync.py::TestDataIntegrity -v
python -m pytest test_portfolio_sync.py::TestPortfolioAPIs -v
```

### **Pre-deployment Tests**
```bash
# Run full suite before deployment
python -m pytest test_portfolio_sync.py -v
```

### **Regression Tests**
```bash
# Run after major changes
python -m pytest test_portfolio_sync.py --tb=short
```

## 🎯 **Test Coverage Goals**

- **Portfolio Sync**: 95%+ coverage
- **API Endpoints**: 90%+ coverage  
- **Data Validation**: 100% coverage
- **Error Handling**: 85%+ coverage

## 📋 **Test Maintenance**

### **Weekly Tasks**
- [ ] Run full test suite
- [ ] Update test data if needed
- [ ] Review test performance
- [ ] Check for new edge cases

### **After Major Changes**
- [ ] Add tests for new features
- [ ] Update existing tests if APIs change
- [ ] Verify test coverage maintained
- [ ] Document new test scenarios

---

**💡 Remember**: Tests should be run before every deployment and after any changes to portfolio sync or API endpoints! 