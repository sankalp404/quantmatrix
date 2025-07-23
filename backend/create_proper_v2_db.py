#!/usr/bin/env python3
"""
QuantMatrix V2 - Proper Database Creation (Avoiding Conflicts)
=============================================================

Creates YOUR sophisticated V2 database using MAIN models only.
Avoids duplicate table conflicts by importing selectively.
"""

import sys
import logging
import os

# Add paths for Docker
sys.path.insert(0, '/app')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_proper_v2_database():
    """Create your V2 database using main models only."""
    try:
        logger.info("🚀 QuantMatrix V2 - YOUR Sophisticated Database")
        logger.info("=" * 70)
        logger.info("📋 Following MODELS_V2_ANALYSIS.md planning")
        logger.info("🎯 Using YOUR enterprise-grade models (not amateur tables)")
        
        # Import database components first
        from database import engine, SessionLocal, Base
        
        logger.info("📦 Importing YOUR sophisticated models (avoiding conflicts)...")
        
        # Import MAIN models only (avoiding duplicates)
        
        # 1. Core User Management
        from models.users import User  # Main users table
        logger.info("   ✅ users (main)")
        
        # 2. Account Management - use the comprehensive one
        from models.accounts import BrokerAccount  # Comprehensive account model
        logger.info("   ✅ broker_accounts")
        
        # 3. Instruments & Positions (your sophisticated models)
        from models.instruments import Instrument, InstrumentAlias
        from models.positions import Position, PositionHistory
        logger.info("   ✅ instruments & positions (sophisticated)")
        
        # 4. Transactions & Tax Lots
        from models.transactions import Transaction, Dividend, TransactionSyncStatus
        from models.tax_lots import TaxLot, TaxLotSale, TaxStrategy, TaxReport
        logger.info("   ✅ transactions & tax_lots")
        
        # 5. Portfolio Management
        from models.portfolio import Holdings, Category, HoldingCategory, PortfolioSnapshot
        logger.info("   ✅ portfolio (holdings, categories)")
        
        # 6. Market Data (comprehensive)
        from models.market_data import StockInfo, PriceData, ATRData, SectorMetrics
        logger.info("   ✅ market_data (comprehensive)")
        
        # 7. Strategies (main strategies model)
        from models.strategies import Strategy, StrategyRun, StrategyPerformance, BacktestRun
        logger.info("   ✅ strategies (main)")
        
        # 8. Notifications (main notifications model)  
        from models.notifications import Notification, NotificationTemplate, NotificationPreference
        logger.info("   ✅ notifications (main)")
        
        # 9. Options Trading
        from models.options import TastytradeAccount, OptionInstrument, OptionPosition
        logger.info("   ✅ options")
        
        # 10. Alerts
        from models.alert import Alert, AlertCondition, AlertTemplate, AlertHistory
        logger.info("   ✅ alerts")
        
        # 11. Audit & CSV Import
        from models.audit import AuditLog, DataChangeLog, SecurityEvent
        from models.csv_import import CSVImport
        logger.info("   ✅ audit & csv_import")
        
        # 12. Market Analysis
        from models.market_analysis import MarketAnalysisCache, StockUniverse, ScanHistory
        logger.info("   ✅ market_analysis")
        
        logger.info("📊 Creating YOUR sophisticated database schema...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Verify creation
        with SessionLocal() as db:
            result = db.execute("SELECT 1").scalar()
            if result != 1:
                raise Exception("Database connection test failed")
        
        # Count and categorize tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info("=" * 70)
        logger.info(f"🎉 SUCCESS! Created {len(tables)} sophisticated tables:")
        logger.info("")
        
        # Show your sophisticated table structure
        user_tables = [t for t in tables if 'user' in t]
        account_tables = [t for t in tables if 'account' in t or 'broker' in t]
        trading_tables = [t for t in tables if any(x in t for x in ['position', 'transaction', 'tax', 'option', 'trade'])]
        strategy_tables = [t for t in tables if any(x in t for x in ['strategy', 'signal', 'alert'])]
        data_tables = [t for t in tables if any(x in t for x in ['market', 'price', 'instrument', 'atr'])]
        system_tables = [t for t in tables if any(x in t for x in ['notification', 'audit', 'csv', 'sync'])]
        
        if user_tables:
            logger.info("👤 User Management:")
            for table in sorted(user_tables):
                logger.info(f"   ✅ {table}")
        
        if account_tables:
            logger.info("🏦 Account Management:")
            for table in sorted(account_tables):
                logger.info(f"   ✅ {table}")
        
        if trading_tables:
            logger.info("💰 Trading & Positions:")
            for table in sorted(trading_tables):
                logger.info(f"   ✅ {table}")
        
        if strategy_tables:
            logger.info("📈 Strategies & Signals:")
            for table in sorted(strategy_tables):
                logger.info(f"   ✅ {table}")
        
        if data_tables:
            logger.info("📊 Market Data:")
            for table in sorted(data_tables):
                logger.info(f"   ✅ {table}")
        
        if system_tables:
            logger.info("🔧 System & Integration:")
            for table in sorted(system_tables):
                logger.info(f"   ✅ {table}")
        
        logger.info("=" * 70)
        logger.info("🎉 YOUR SOPHISTICATED V2 DATABASE IS READY!")
        logger.info("✅ No more amateur 'holdings' - proper enterprise models!")
        logger.info("✅ Ready for ordered data import:")
        logger.info("   1️⃣ TastyTrade → broker_accounts & positions")
        logger.info("   2️⃣ IBKR Tax Deferred → broker_accounts & positions")
        logger.info("   3️⃣ IBKR Joint → broker_accounts & positions")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ V2 database creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_proper_v2_database()
    
    if success:
        print("")
        print("🎉 SUCCESS! YOUR Sophisticated V2 Database Created!")
        print("🏆 Enterprise-grade models (following MODELS_V2_ANALYSIS.md)")
        print("🚀 Ready for your preferred data import order!")
    else:
        print("")
        print("❌ FAILED! Check logs for model conflicts.")
        sys.exit(1) 