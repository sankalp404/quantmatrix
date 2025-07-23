#!/usr/bin/env python3
"""
QuantMatrix V2 - Proper Database Creation
========================================

Creates database using YOUR sophisticated models, not amateur basic tables.
Based on our MODELS_V2_ANALYSIS.md planning.
"""

import sys
import logging
import os

# Add paths for Docker
sys.path.insert(0, '/app')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_v2_database():
    """Create database using your sophisticated V2 models."""
    try:
        logger.info("🚀 Creating QuantMatrix V2 Database")
        logger.info("Using YOUR sophisticated enterprise models!")
        logger.info("=" * 60)
        
        # Import database components
        from database import engine, SessionLocal, Base
        
        logger.info("📦 Importing your sophisticated models...")
        
        # Import all your sophisticated models
        from models.users import User
        from models.accounts import Account
        from models.instruments import Instrument
        from models.positions import Position
        from models.transactions import Transaction
        from models.tax_lots import TaxLot
        from models.portfolio import Portfolio
        from models.market_data import MarketData, PriceData, TechnicalIndicators
        from models.strategies import Strategy, StrategyRun
        from models.signals import Signal, AlertRule
        from models.notifications import Notification
        from models.options import OptionsContract, OptionsPosition
        from models.audit import AuditLog
        
        logger.info("✅ All sophisticated models imported!")
        
        # Create all tables using your sophisticated models
        logger.info("🏗️ Creating sophisticated database schema...")
        Base.metadata.create_all(engine)
        
        # Verify creation
        with SessionLocal() as db:
            result = db.execute("SELECT 1").scalar()
            if result != 1:
                raise Exception("Database connection test failed")
        
        # Count tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info("=" * 60)
        logger.info(f"✅ Created {len(tables)} sophisticated tables:")
        
        # Categorize tables
        core_tables = []
        trading_tables = []
        system_tables = []
        
        for table in sorted(tables):
            if any(x in table for x in ['user', 'account', 'instrument', 'position']):
                core_tables.append(table)
            elif any(x in table for x in ['transaction', 'tax', 'signal', 'strategy', 'option']):
                trading_tables.append(table)
            else:
                system_tables.append(table)
        
        logger.info("📊 Core Tables:")
        for table in core_tables:
            logger.info(f"   ✅ {table}")
            
        logger.info("💰 Trading Tables:")
        for table in trading_tables:
            logger.info(f"   ✅ {table}")
            
        logger.info("🔧 System Tables:")
        for table in system_tables:
            logger.info(f"   ✅ {table}")
        
        logger.info("=" * 60)
        logger.info("🎉 V2 DATABASE CREATED SUCCESSFULLY!")
        logger.info("✅ Using YOUR sophisticated enterprise models")
        logger.info("✅ Ready for ordered data import:")
        logger.info("   1️⃣ TastyTrade → accounts & positions tables")
        logger.info("   2️⃣ IBKR Tax Deferred → accounts & positions tables") 
        logger.info("   3️⃣ IBKR Joint → accounts & positions tables")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ V2 database creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_v2_database()
    
    if success:
        print("")
        print("🎉 SUCCESS! V2 Database with YOUR sophisticated models!")
        print("📋 No more amateur 'holdings' - proper 'positions' & 'instruments'!")
        print("🚀 Ready for your preferred import order!")
    else:
        print("")
        print("❌ FAILED! Check logs above.")
        sys.exit(1) 