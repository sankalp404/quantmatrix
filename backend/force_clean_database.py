#!/usr/bin/env python3
"""
QuantMatrix V1 - Force Clean Database
====================================

Uses raw SQL to completely drop all tables and recreate them fresh.
This bypasses any SQLAlchemy model conflicts.
"""

import sys
import logging
import os
import psycopg2
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection details
DB_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'postgres'),
    'port': os.getenv('DATABASE_PORT', '5432'),
    'database': os.getenv('DATABASE_NAME', 'quantmatrix'),
    'user': os.getenv('DATABASE_USER', 'quantmatrix'),
    'password': os.getenv('DATABASE_PASSWORD', 'password')
}

def get_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return None

def drop_all_tables():
    """Drop all tables using raw SQL."""
    try:
        conn = get_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        logger.info("🗑️ Dropping all tables with CASCADE...")
        
        # Get all table names
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%' 
            AND tablename NOT LIKE 'sql_%'
        """)
        
        tables = cursor.fetchall()
        logger.info(f"Found {len(tables)} tables to drop")
        
        # Drop all tables
        for (table_name,) in tables:
            logger.info(f"   🗑️ Dropping table: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        
        # Also drop any remaining sequences
        cursor.execute("""
            SELECT sequence_name FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        
        sequences = cursor.fetchall()
        for (seq_name,) in sequences:
            logger.info(f"   🗑️ Dropping sequence: {seq_name}")
            cursor.execute(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ All tables and sequences dropped successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {e}")
        return False

def create_fresh_tables():
    """Create tables using SQLAlchemy after cleanup."""
    try:
        logger.info("🏗️ Creating fresh tables...")
        
        # Now import SQLAlchemy after cleanup
        sys.path.insert(0, '/app')
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Clear any cached modules
        modules_to_clear = [key for key in sys.modules.keys() if 'models' in key or 'database' in key]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        from database import engine, Base
        
        # Import models one by one to avoid conflicts
        from models.user import User
        from models.portfolio import Portfolio, Holding, Account
        from models.notifications import Notification
        from models.market_data import Instrument, PriceData, TechnicalIndicators
        from models.options import OptionsContract, OptionsPosition
        from models.tax_lots import TaxLot
        from models.transactions import Transaction
        
        # Import signals last (seems to have conflicts)
        try:
            from models.signals import Signal, AlertRule
        except Exception as e:
            logger.warning(f"⚠️ Signals model had issues: {e}")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        logger.info("✅ Fresh tables created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_fresh_database():
    """Verify the fresh database."""
    try:
        conn = get_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """)
        
        tables = cursor.fetchall()
        logger.info(f"✅ Fresh database verified with {len(tables)} tables:")
        
        for (table_name,) in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"   📊 {table_name}: {count} rows")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def force_clean_database():
    """Complete force clean process."""
    logger.info("🚀 Starting FORCE CLEAN database recreation...")
    logger.info("=" * 60)
    
    # Step 1: Force drop all tables
    if not drop_all_tables():
        return False
    
    # Step 2: Create fresh tables
    if not create_fresh_tables():
        return False
    
    # Step 3: Verify
    if not verify_fresh_database():
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 FORCE CLEAN completed successfully!")
    logger.info("✅ Database is completely fresh and ready!")
    
    return True

if __name__ == "__main__":
    logger.info("🔥 FORCE CLEAN DATABASE - NUCLEAR OPTION")
    logger.info("💥 This will DESTROY ALL DATA!")
    
    success = force_clean_database()
    
    if success:
        print("")
        print("🎉 SUCCESS! Database is completely fresh!")
        print("📁 Ready for ordered import:")
        print("   1. TastyTrade")
        print("   2. IBKR Tax Deferred") 
        print("   3. IBKR Joint")
        print("")
    else:
        print("")
        print("❌ FAILED! Check the logs above.")
        print("")
        sys.exit(1) 