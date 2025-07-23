# V2 Test Suite - Test-Driven Development Plan 🧪

## 🎯 **WHY TDD FOR TRADING PLATFORM**

### **Critical Importance:**
- 💰 **Financial Accuracy** - Bugs cost real money
- 🔒 **Risk Management** - Position sizing, stop losses must work
- 📊 **Data Integrity** - Tax lots, P&L calculations must be precise
- 🚀 **Strategy Reliability** - Automated trading requires bulletproof logic
- 👥 **Multi-User Safety** - User isolation critical
- 📈 **Performance** - High-frequency operations need optimization

---

## ✅ **V2 TEST ARCHITECTURE**

### **Test Structure Organization:**
```
backend/tests_v2/
├── unit/                          # Fast, isolated tests
│   ├── models/                    # V2 model tests
│   │   ├── test_users.py
│   │   ├── test_market_data.py
│   │   ├── test_strategies.py
│   │   ├── test_signals.py
│   │   └── test_csv_import.py
│   ├── services/                  # Service layer tests
│   │   ├── clients/
│   │   │   ├── test_ibkr_client.py
│   │   │   └── test_tastytrade_client.py
│   │   ├── analysis/
│   │   │   └── test_atr_calculator.py    # SINGLE ATR tests
│   │   ├── strategies/
│   │   │   ├── test_atr_matrix_service.py
│   │   │   └── test_dca_service.py
│   │   ├── portfolio/
│   │   │   ├── test_sync_service.py
│   │   │   ├── test_tax_lot_service.py
│   │   │   └── test_csv_import_service.py
│   │   └── notifications/
│   │       └── test_discord_service.py
│   └── utils/
│       ├── test_calculations.py
│       └── test_validations.py
├── integration/                   # Component interaction tests
│   ├── test_strategy_execution.py
│   ├── test_csv_import_flow.py
│   ├── test_portfolio_sync.py
│   ├── test_notification_pipeline.py
│   └── test_multi_user_isolation.py
├── api/                          # API endpoint tests
│   ├── test_auth_endpoints.py
│   ├── test_portfolio_endpoints.py
│   ├── test_strategy_endpoints.py
│   ├── test_market_data_endpoints.py
│   └── test_notification_endpoints.py
├── performance/                  # Performance & load tests
│   ├── test_portfolio_sync_performance.py
│   ├── test_atr_calculation_performance.py
│   └── test_concurrent_users.py
├── fixtures/                     # Test data & utilities
│   ├── sample_data/
│   │   ├── ibkr_csv_samples/
│   │   ├── market_data_samples/
│   │   └── strategy_execution_samples/
│   ├── database_fixtures.py
│   ├── client_mocks.py
│   └── test_helpers.py
└── conftest.py                   # Pytest configuration
```

---

## 🧪 **TDD IMPLEMENTATION STRATEGY**

### **Phase 1: Core Models (RED-GREEN-REFACTOR)**

#### **Test-First Examples:**

**1. User Model Testing:**
```python
# tests_v2/unit/models/test_users.py
import pytest
from backend.models_v2.users import User, UserRole

class TestUserModel:
    def test_create_user_with_valid_data(self):
        """Test user creation with valid data"""
        # RED: Write failing test first
        user = User(
            username="testuser",
            email="test@example.com", 
            role=UserRole.TRADER
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.TRADER
        assert user.is_active is True
    
    def test_user_password_hashing(self):
        """Test password is properly hashed"""
        user = User(username="test", email="test@test.com")
        user.set_password("plaintext")
        
        assert user.password_hash != "plaintext"
        assert user.check_password("plaintext") is True
        assert user.check_password("wrong") is False
    
    def test_user_api_key_generation(self):
        """Test API key generation for strategies"""
        user = User(username="test", email="test@test.com")
        api_key = user.generate_api_key()
        
        assert api_key is not None
        assert len(api_key) >= 32
        assert user.verify_api_key(api_key) is True
```

**2. ATR Calculator Testing (Critical!):**
```python
# tests_v2/unit/services/analysis/test_atr_calculator.py
import pytest
import pandas as pd
from backend.services_v2.analysis.atr_calculator import ATRCalculator

class TestATRCalculator:
    @pytest.fixture
    def sample_ohlc_data(self):
        """Provide sample OHLC data for testing"""
        return pd.DataFrame({
            'high': [110, 112, 108, 115, 113],
            'low': [105, 107, 102, 109, 110], 
            'close': [108, 111, 105, 114, 112]
        })
    
    def test_basic_atr_calculation(self, sample_ohlc_data):
        """Test basic ATR calculation accuracy"""
        calc = ATRCalculator()
        atr = calc.calculate_basic_atr(sample_ohlc_data, periods=3)
        
        # ATR should be positive
        assert atr > 0
        # ATR should be reasonable for sample data
        assert 0 < atr < 20
    
    def test_atr_consistency_across_methods(self, sample_ohlc_data):
        """Test all ATR methods give consistent results"""
        calc = ATRCalculator()
        
        basic_atr = calc.calculate_basic_atr(sample_ohlc_data)
        enhanced_atr = calc.calculate_enhanced_atr(sample_ohlc_data)
        
        # Results should be similar (within 5%)
        diff_pct = abs(basic_atr - enhanced_atr) / basic_atr * 100
        assert diff_pct < 5.0
    
    def test_atr_options_calculation(self):
        """Test ATR calculation for options strategies"""
        calc = ATRCalculator()
        result = calc.calculate_options_atr("AAPL")
        
        assert "atr_value" in result
        assert "volatility_level" in result
        assert result["volatility_level"] in ["LOW", "MEDIUM", "HIGH", "EXTREME"]
```

**3. CSV Import Testing (Your 3 Files!):**
```python
# tests_v2/unit/services/portfolio/test_csv_import_service.py
import pytest
from backend.models_v2.csv_import import IBKRCSVImporter, IBKR_CSV_IMPORT_CONFIGS

class TestCSVImportService:
    @pytest.fixture
    def sample_csv_data(self):
        """Sample IBKR CSV data for testing"""
        return """Date,Time,Symbol,Action,Quantity,Price,Amount,Commission
2025-01-15,10:30:00,AAPL,BUY,100,150.00,15000.00,1.00
2025-01-16,14:20:00,MSFT,BUY,50,300.00,15000.00,1.00"""
    
    def test_csv_parsing_accuracy(self, sample_csv_data, tmp_path):
        """Test CSV parsing produces correct data"""
        # Create temp CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(sample_csv_data)
        
        importer = IBKRCSVImporter()
        records = importer.parse_csv_file(str(csv_file))
        
        assert len(records) == 2
        assert records[0]["symbol"] == "AAPL"
        assert records[0]["quantity"] == 100
        assert records[0]["price"] == 150.00
    
    def test_taxable_vs_ira_configuration(self):
        """Test different configurations for taxable vs IRA"""
        taxable_config = IBKR_CSV_IMPORT_CONFIGS["U19490886_current"]
        ira_config = IBKR_CSV_IMPORT_CONFIGS["U15891532"]
        
        assert taxable_config["tax_treatment"] == "taxable"
        assert taxable_config["use_average_cost_basis"] is False
        
        assert ira_config["tax_treatment"] == "tax_deferred" 
        assert ira_config["use_average_cost_basis"] is True
    
    def test_tax_lot_calculation_accuracy(self):
        """Test tax lot calculations are correct"""
        # This is CRITICAL for tax reporting!
        pass  # Implementation coming
```

---

## 🔄 **TDD WORKFLOW**

### **Red-Green-Refactor Cycle:**

**1. 🔴 RED - Write Failing Test:**
```python
def test_strategy_execution_with_10k_capital():
    """Test strategy execution with $10k starting capital"""
    strategy = ATRMatrixStrategy(
        capital=10000,
        profit_target=0.20,
        reinvest_percentage=0.80
    )
    
    result = strategy.execute_trade("AAPL")
    
    assert result.position_size <= 10000
    assert result.stop_loss is not None
    assert result.profit_target == strategy.capital * 0.20
```

**2. 🟢 GREEN - Make Test Pass:**
```python
# Implement minimal code to make test pass
class ATRMatrixStrategy:
    def __init__(self, capital, profit_target, reinvest_percentage):
        self.capital = capital
        self.profit_target = profit_target
        self.reinvest_percentage = reinvest_percentage
    
    def execute_trade(self, symbol):
        # Minimal implementation
        return TradeResult(
            position_size=self.capital * 0.1,  # 10% position
            stop_loss=0.05,  # 5% stop
            profit_target=self.capital * self.profit_target
        )
```

**3. 🔵 REFACTOR - Improve Code:**
```python
# Refactor with proper ATR calculations, risk management, etc.
```

---

## 🛡️ **CRITICAL TEST CATEGORIES**

### **1. Financial Accuracy Tests:**
```python
class TestFinancialAccuracy:
    def test_pnl_calculations_precision(self):
        """P&L must be accurate to 2 decimal places"""
        
    def test_tax_lot_fifo_accuracy(self):
        """FIFO tax lot calculations must be correct"""
        
    def test_commission_calculations(self):
        """Commission calculations must be precise"""
        
    def test_position_sizing_limits(self):
        """Position sizing must respect capital limits"""
```

### **2. Multi-User Isolation Tests:**
```python
class TestMultiUserIsolation:
    def test_user_data_isolation(self):
        """Users cannot see each other's data"""
        
    def test_strategy_execution_isolation(self):
        """Strategy executions are isolated per user"""
        
    def test_portfolio_sync_isolation(self):
        """Portfolio syncs don't interfere between users"""
```

### **3. Performance Tests:**
```python
class TestPerformance:
    def test_portfolio_sync_performance(self):
        """Portfolio sync completes under 5 seconds"""
        
    def test_atr_calculation_performance(self):
        """ATR calculation for 1000 stocks under 1 second"""
        
    def test_concurrent_strategy_execution(self):
        """Multiple strategies can run concurrently"""
```

---

## 📊 **TEST COVERAGE TARGETS**

### **Coverage Requirements:**
- 🎯 **Models**: 95%+ coverage
- 🔧 **Services**: 90%+ coverage  
- 🌐 **API Endpoints**: 85%+ coverage
- 📈 **Critical Paths**: 100% coverage (CSV import, strategy execution, P&L)

### **Coverage Command:**
```bash
pytest --cov=backend/models_v2 --cov=backend/services_v2 --cov=backend/api_v2 --cov-report=html
```

---

## 🚀 **IMPLEMENTATION TIMELINE**

### **Week 1: Core Testing Foundation**
```
Day 1: Set up test structure + fixtures
Day 2: Test core models (users, market_data, strategies)
Day 3: Test SINGLE ATR calculator (critical!)
Day 4: Test CSV import (your 3 files)
Day 5: Test strategy services
```

### **Week 2: Integration & API Testing**
```
Day 1: Integration tests (strategy execution flow)
Day 2: API endpoint tests
Day 3: Multi-user isolation tests
Day 4: Performance tests
Day 5: Full test suite validation
```

### **Week 3: Advanced Testing**
```
Day 1: Load testing (concurrent users)
Day 2: Error handling & edge cases
Day 3: Mock external APIs (IBKR, TastyTrade)
Day 4: Production deployment testing
Day 5: Documentation & CI/CD setup
```

---

## 🎯 **IMMEDIATE ACTIONS**

### **Set Up Test Infrastructure:**
```bash
# Create test structure
mkdir -p backend/tests_v2/{unit/{models,services},integration,api,performance,fixtures}

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock factory-boy

# Create conftest.py with common fixtures
# Set up database fixtures for testing
# Create mock clients for external APIs
```

### **Start with Critical Tests:**
1. ✅ **ATR Calculator** - Single source of truth
2. ✅ **CSV Import** - Your 3 files accuracy
3. ✅ **Strategy Execution** - Money on the line
4. ✅ **User Isolation** - Multi-user safety
5. ✅ **P&L Calculations** - Financial accuracy

---

## 💡 **TDD BENEFITS FOR TRADING**

### **Immediate Benefits:**
- 🛡️ **Confidence** - Know your code works under all conditions
- 🚀 **Speed** - Catch bugs before they cost money
- 📖 **Documentation** - Tests document expected behavior
- 🔧 **Refactoring** - Safely improve code with test coverage

### **Long-term Benefits:**
- 💰 **Risk Reduction** - Prevent costly trading bugs
- 👥 **Team Scaling** - New developers can contribute safely
- 🏗️ **Architecture** - Tests enforce good design
- 📈 **Performance** - Identify bottlenecks early

---

## ✅ **RECOMMENDATION**

**IMPLEMENT TDD IMMEDIATELY WITH V2:**

This gives you:
- ✅ **Bulletproof trading platform** - Tests prevent money-losing bugs
- ✅ **Confident development** - Refactor without fear
- ✅ **Production readiness** - Comprehensive coverage
- ✅ **Team readiness** - New developers can contribute safely

**Ready to implement test-driven V2 development? 🧪🚀** 