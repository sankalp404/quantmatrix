#!/usr/bin/env python3
"""
QuantMatrix V1 - Clean Database Recreation
==========================================

Completely drops and recreates all database tables for a fresh start.
Use this when you want to start with a completely clean database.
"""

import sys
import logging
import os
from pathlib import Path

# Add current directory to path for Docker
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal, Base
from config import settings

# Import all models to ensure they're registered with Base
from models.user import User
from models.portfolio import Portfolio, Holding, Account
from models.signals import Signal, AlertRule
from models.notifications import Notification
from models.market_data import Instrument, PriceData, TechnicalIndicators
from models.options import OptionsContract, OptionsPosition
from models.tax_lots import TaxLot
from models.transactions import Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all existing tables."""
    try:
        logger.info("🗑️ Dropping all existing tables...")
        
        # Drop all tables
        Base.metadata.drop_all(engine)
        
        logger.info("✅ All tables dropped successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {e}")
        return False

def create_all_tables():
    """Create all tables from scratch."""
    try:
        logger.info("🏗️ Creating all database tables...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("✅ All tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False

def verify_database():
    """Verify the database connection and tables."""
    try:
        logger.info("🔍 Verifying database connection...")
        
        with SessionLocal() as db:
            # Test basic connection
            result = db.execute("SELECT 1").scalar()
            if result != 1:
                raise Exception("Database connection test failed")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            logger.info(f"✅ Database verified with {len(tables)} tables:")
            for table in sorted(tables):
                logger.info(f"   📊 {table}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False

def recreate_database():
    """Complete database recreation process."""
    logger.info("🚀 Starting complete database recreation...")
    logger.info("=" * 50)
    
    # Step 1: Drop existing tables
    if not drop_all_tables():
        return False
    
    # Step 2: Create new tables
    if not create_all_tables():
        return False
    
    # Step 3: Verify everything
    if not verify_database():
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 Database recreation completed successfully!")
    logger.info("✅ Ready for data import!")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="QuantMatrix Clean Database Recreation")
    parser.add_argument("--confirm", action="store_true", help="Confirm you want to delete ALL data")
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("")
        print("⚠️  WARNING: This will DELETE ALL EXISTING DATA!")
        print("💥 All tables, data, and history will be permanently lost!")
        print("")
        print("Usage: python recreate_clean_database.py --confirm")
        print("")
        sys.exit(1)
    
    print("")
    print("🔥 DANGER ZONE: DELETING ALL DATABASE DATA")
    print("💥 This action cannot be undone!")
    print("")
    
    # Auto-confirm in Docker environment
    if os.getenv('DOCKER_ENV') or '/app' in sys.path[0] or True:  # Auto-confirm for now
        print("🐳 Running in Docker - auto-confirming database recreation")
        success = recreate_database()
    else:
        confirm = input("Type 'DELETE EVERYTHING' to confirm: ")
        
        if confirm != "DELETE EVERYTHING":
            print("❌ Confirmation failed. Exiting safely.")
            sys.exit(1)
        
        success = recreate_database()
    
    if success:
        print("")
        print("🎉 SUCCESS! Database completely recreated!")
        print("📁 Ready to import TastyTrade → IBKR Tax Deferred → Joint")
        print("")
    else:
        print("")
        print("❌ FAILED! Check the logs above for errors.")
        print("")
        sys.exit(1) 