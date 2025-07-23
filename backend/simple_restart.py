#!/usr/bin/env python3
"""
QuantMatrix V1 - Simple Fresh Restart
====================================

Clean restart process with ordered data import:
1. TastyTrade (first)
2. IBKR Tax Deferred 
3. IBKR Joint

No JWT, no complications - just clean data import.
"""

import sys
import logging
import os
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    'host': 'postgres',
    'port': '5432', 
    'database': 'quantmatrix',
    'user': 'quantmatrix',
    'password': 'password'
}

def clean_database():
    """Drop all tables and start fresh."""
    try:
        logger.info("🧹 Cleaning database completely...")
        
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop all tables
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        tables = cursor.fetchall()
        logger.info(f"Dropping {len(tables)} existing tables...")
        
        for (table_name,) in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            logger.info(f"   🗑️ Dropped: {table_name}")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Database completely cleaned!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database clean failed: {e}")
        return False

def create_basic_tables():
    """Create only the essential tables we need."""
    try:
        logger.info("🏗️ Creating basic tables...")
        
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create accounts table
        cursor.execute("""
            CREATE TABLE accounts (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) UNIQUE NOT NULL,
                broker VARCHAR(20) NOT NULL,
                account_type VARCHAR(20) NOT NULL,
                account_name VARCHAR(100),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create holdings table
        cursor.execute("""
            CREATE TABLE holdings (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                average_cost DECIMAL(12,4),
                current_price DECIMAL(12,4),
                market_value DECIMAL(15,2),
                pnl DECIMAL(15,2),
                pnl_percentage DECIMAL(8,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create transactions table
        cursor.execute("""
            CREATE TABLE transactions (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                price DECIMAL(12,4),
                amount DECIMAL(15,2),
                transaction_date DATE NOT NULL,
                settlement_date DATE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Basic tables created!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        return False

def verify_fresh_setup():
    """Verify we have a clean setup."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM accounts")
        account_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM holdings") 
        holdings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        transaction_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Fresh setup verified:")
        logger.info(f"   📊 Accounts: {account_count}")
        logger.info(f"   📈 Holdings: {holdings_count}")
        logger.info(f"   💰 Transactions: {transaction_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def fresh_restart():
    """Complete fresh restart process."""
    logger.info("🚀 QUANTMATRIX FRESH RESTART")
    logger.info("=" * 50)
    
    # Step 1: Clean database
    if not clean_database():
        return False
    
    # Step 2: Create basic tables
    if not create_basic_tables():
        return False
    
    # Step 3: Verify setup
    if not verify_fresh_setup():
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 FRESH RESTART COMPLETE!")
    logger.info("")
    logger.info("📋 Ready for ordered data import:")
    logger.info("   1️⃣ TastyTrade (first)")
    logger.info("   2️⃣ IBKR Tax Deferred")
    logger.info("   3️⃣ IBKR Joint")
    logger.info("")
    
    return True

if __name__ == "__main__":
    success = fresh_restart()
    
    if success:
        print("🎉 SUCCESS! Ready for data import!")
    else:
        print("❌ FAILED! Check logs above.")
        sys.exit(1) 