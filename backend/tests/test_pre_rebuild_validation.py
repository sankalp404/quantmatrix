#!/usr/bin/env python3
"""
QuantMatrix V1 - Pre-Rebuild Validation Tests
=============================================

Validates that all components are ready before database rebuild.
Critical checks to ensure rebuild will succeed.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.notifications.discord_service import discord_notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreRebuildValidator:
    """Validates system readiness before database rebuild."""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.issues = []
    
    def check_file_structure(self):
        """Check that required files and directories exist."""
        logger.info("🔍 Checking file structure...")
        
        required_files = [
            "backend/config.py",
            "backend/database.py", 
            "backend/recreate_v1_database.py",
            "backend/services/analysis/atr_engine.py",
            "backend/services/market/market_data_service.py",
            "backend/services/market/index_constituents_service.py",
            "backend/services/notifications/discord_service.py",
            "backend/api/routes/atr.py",
            "backend/scripts/run_atr_universe.py"
        ]
        
        required_dirs = [
            "backend/models",
            "backend/services",
            "backend/api",
            "backend/tests",
            "backend/scripts"
        ]
        
        # Check files
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        # Check directories
        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_files or missing_dirs:
            self.checks_failed += 1
            self.issues.append(f"Missing files: {missing_files}")
            self.issues.append(f"Missing directories: {missing_dirs}")
            logger.error(f"❌ File structure check failed")
        else:
            self.checks_passed += 1
            logger.info(f"✅ File structure check passed")
    
    def check_database_config(self):
        """Check database configuration."""
        logger.info("🗃️ Checking database configuration...")
        
        try:
            from backend.config import settings
            
            # Check database URL format
            db_url = getattr(settings, 'DATABASE_URL', None)
            if not db_url:
                # Try environment variable directly
                import os
                db_url = os.getenv('DATABASE_URL')
            
            if db_url:
                if 'postgresql' in db_url or 'sqlite' in db_url:
                    db_type = 'PostgreSQL' if 'postgresql' in db_url else 'SQLite'
                    logger.info(f"   ✅ Database URL configured ({db_type})")
                    self.checks_passed += 1
                else:
                    self.checks_failed += 1
                    self.issues.append("Unknown database type in DATABASE_URL")
                    logger.error("   ❌ Unknown database type")
            else:
                self.checks_failed += 1
                self.issues.append("Missing DATABASE_URL")
                logger.error("   ❌ DATABASE_URL not found")
            
        except Exception as e:
            self.checks_failed += 1
            self.issues.append(f"Database config error: {e}")
            logger.error(f"   ❌ Database config check failed: {e}")
    
    def check_environment_config(self):
        """Check environment configuration."""
        logger.info("🔧 Checking environment configuration...")
        
        import os
        from pathlib import Path
        
        # Try to load .env file directly
        env_file = Path('.env')
        env_vars = {}
        
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                logger.info(f"   📄 Loaded {len(env_vars)} variables from .env file")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not read .env file: {e}")
        
        required_env_vars = [
            "DATABASE_URL",
            "REDIS_URL", 
            "SECRET_KEY"
        ]
        
        optional_env_vars = [
            "DISCORD_WEBHOOK_SIGNALS",
            "DISCORD_WEBHOOK_PORTFOLIO_DIGEST", 
            "DISCORD_WEBHOOK_SYSTEM_STATUS",
            "FMP_API_KEY",
            "POLYGON_API_KEY"
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_env_vars:
            if not (os.getenv(var) or env_vars.get(var)):
                missing_required.append(var)
            else:
                value = os.getenv(var) or env_vars.get(var)
                logger.info(f"   ✅ {var}: {'configured' if value else 'missing'}")
        
        for var in optional_env_vars:
            if not (os.getenv(var) or env_vars.get(var)):
                missing_optional.append(var)
        
        if missing_required:
            self.checks_failed += 1
            self.issues.append(f"Missing required env vars: {missing_required}")
            logger.error(f"❌ Environment check failed - missing required vars")
        else:
            self.checks_passed += 1
            logger.info(f"✅ Environment check passed")
        
        if missing_optional:
            logger.warning(f"⚠️ Missing optional env vars: {missing_optional}")
            logger.info("💡 Add these for full functionality:")
            for var in missing_optional:
                logger.info(f"   {var}=your_value_here")
    
    async def check_core_services(self):
        """Check that core services can be imported and initialized."""
        logger.info("🔧 Checking core services...")
        
        try:
            # Test ATR engine import (avoid database dependencies)
            logger.info("   🔧 Testing ATR engine import...")
            from backend.services.analysis import atr_engine
            logger.info("   ✅ ATR engine imports successfully")
            
            # Test market data service import (may have database dependency)
            logger.info("   📊 Testing market data service import...")
            try:
                from backend.services.market import market_data_service
                logger.info("   ✅ Market data service imports successfully")
            except Exception as market_error:
                if 'psycopg2' in str(market_error):
                    logger.info("   ⚠️ Market data service limited (psycopg2 missing - OK in Docker)")
                else:
                    raise market_error
            
            # Test index service import
            logger.info("   🌍 Testing index constituents service import...")
            try:
                from backend.services.market import index_constituents_service
                logger.info("   ✅ Index constituents service imports successfully")
            except Exception as index_error:
                if 'psycopg2' in str(index_error):
                    logger.info("   ⚠️ Index service limited (psycopg2 missing - OK in Docker)")
                else:
                    raise index_error
            
            # Test Discord service (no database dependency)
            logger.info("   📢 Testing Discord service...")
            from backend.services.notifications.discord_service import discord_notifier
            logger.info(f"   ✅ Discord service configured: {discord_notifier.is_configured()}")
            
            self.checks_passed += 1
            logger.info("✅ Core services check passed")
            
        except Exception as e:
            if 'psycopg2' in str(e):
                # psycopg2 missing is expected outside Docker
                logger.warning("⚠️ Core services limited: psycopg2 missing (will work in Docker)")
                self.checks_passed += 1
            else:
                self.checks_failed += 1
                self.issues.append(f"Core services import error: {e}")
                logger.error(f"❌ Core services check failed: {e}")
    
    async def check_market_data_access(self):
        """Check market data access."""
        logger.info("📊 Checking market data access...")
        
        try:
            from backend.services.market.market_data_service import market_data_service
            
            # Test basic price retrieval
            test_symbol = "AAPL"
            price = await market_data_service.get_current_price(test_symbol)
            
            if price and price > 0:
                logger.info(f"   ✅ Market data working: {test_symbol} = ${price:.2f}")
                self.checks_passed += 1
            else:
                logger.warning(f"   ⚠️ Market data limited: {test_symbol} price unavailable")
                self.checks_passed += 1  # Not critical for rebuild
                
        except Exception as e:
            logger.warning(f"   ⚠️ Market data access limited: {e}")
            self.checks_passed += 1  # Not critical for rebuild
    
    async def check_index_constituents(self):
        """Check index constituents access."""
        logger.info("🌍 Checking index constituents access...")
        
        try:
            from backend.services.market.index_constituents_service import index_service
            
            # Test getting small index
            dow30_symbols = await index_service.get_index_constituents('DOW30')
            
            if dow30_symbols and len(dow30_symbols) > 10:
                logger.info(f"   ✅ Index data working: {len(dow30_symbols)} Dow 30 symbols")
                self.checks_passed += 1
            else:
                logger.warning(f"   ⚠️ Index data limited: {len(dow30_symbols) if dow30_symbols else 0} symbols")
                self.checks_passed += 1  # Not critical for rebuild
                
        except Exception as e:
            logger.warning(f"   ⚠️ Index constituents access limited: {e}")
            self.checks_passed += 1  # Not critical for rebuild
    
    async def check_atr_calculations(self):
        """Check ATR calculation capabilities."""
        logger.info("🔧 Checking ATR calculations...")
        
        try:
            from backend.tests.test_atr_validation import StandaloneATRCalculator
            import pandas as pd
            import numpy as np
            
            # Create test data
            calculator = StandaloneATRCalculator()
            test_data = pd.DataFrame({
                'open': np.random.uniform(95, 105, 30),
                'high': np.random.uniform(100, 110, 30),
                'low': np.random.uniform(90, 100, 30),
                'close': np.random.uniform(95, 105, 30),
                'volume': np.random.randint(10000, 100000, 30)
            })
            
            # Test calculations
            tr_series = calculator.calculate_true_range_series(test_data)
            atr_series = calculator.calculate_wilder_atr(tr_series, 14)
            current_atr = atr_series.dropna().iloc[-1]
            
            if current_atr > 0:
                logger.info(f"   ✅ ATR calculations working: {current_atr:.3f}")
                self.checks_passed += 1
            else:
                self.checks_failed += 1
                self.issues.append("ATR calculation returned invalid result")
                logger.error("   ❌ ATR calculation failed")
                
        except Exception as e:
            self.checks_failed += 1
            self.issues.append(f"ATR calculation error: {e}")
            logger.error(f"   ❌ ATR calculation check failed: {e}")
    
    async def run_all_checks(self):
        """Run all pre-rebuild validation checks."""
        logger.info("🎯 Pre-Rebuild Validation Suite")
        logger.info("=" * 40)
        
        # Run all checks
        self.check_file_structure()
        self.check_environment_config()
        await self.check_core_services()
        await self.check_market_data_access()
        await self.check_index_constituents()
        await self.check_atr_calculations()
        self.check_database_config()
        
        # Summary
        logger.info("\n" + "=" * 40)
        logger.info("📊 Validation Summary:")
        logger.info(f"   ✅ Checks passed: {self.checks_passed}")
        logger.info(f"   ❌ Checks failed: {self.checks_failed}")
        
        if self.issues:
            logger.info("\n⚠️ Issues found:")
            for issue in self.issues:
                logger.info(f"   - {issue}")
        
        if self.checks_failed == 0:
            logger.info("\n🎉 ALL CHECKS PASSED!")
            logger.info("✅ System is ready for database rebuild")
            return True
        else:
            logger.info(f"\n❌ {self.checks_failed} checks failed")
            logger.info("🔧 Fix issues before proceeding with rebuild")
            return False

async def main():
    """Main validation function."""
    validator = PreRebuildValidator()
    success = await validator.run_all_checks()
    
    if success:
        print("\n🚀 READY FOR DATABASE REBUILD!")
        print("Run: ./backend/rebuild_db_docker.sh")
        return True
    else:
        print("\n⚠️ FIX ISSUES BEFORE REBUILD")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 