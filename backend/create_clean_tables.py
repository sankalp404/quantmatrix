#!/usr/bin/env python3
"""
QuantMatrix V1 - Create Clean Tables
===================================

Creates all database tables using the current models.
Use this after dropping all tables to get a fresh schema.
"""

import sys
import logging
import os

# Add paths for Docker
sys.path.insert(0, '/app')

# Import database components
from database import engine, SessionLocal, Base

# Import all models to register them
from models.user import User
from models.portfolio import Portfolio, Holding, Account
from models.notifications import Notification
from models.market_data import Instrument, PriceData, TechnicalIndicators
from models.options import OptionsContract, OptionsPosition
from models.tax_lots import TaxLot
from models.transactions import Transaction
from models.signals import Signal, AlertRule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create all tables using current models."""
    try:
        logger.info("🏗️ Creating database tables...")
        
        # Create all tables
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
        
        logger.info(f"✅ Successfully created {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"   📊 {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("🚀 Creating clean database tables...")
    
    success = create_tables()
    
    if success:
        print("🎉 SUCCESS! Clean tables created!")
        print("📁 Ready for data import:")
        print("   1. TastyTrade")
        print("   2. IBKR Tax Deferred")
        print("   3. IBKR Joint")
    else:
        print("❌ FAILED! Check logs above.")
        sys.exit(1) 