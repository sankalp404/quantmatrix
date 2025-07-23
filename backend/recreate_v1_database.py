#!/usr/bin/env python3
"""
QuantMatrix V1 - Database Recreation Script
==========================================

Drops all old tables and creates fresh database structure.
Run this before importing CSV files to ensure clean models.

USAGE:
    python backend/recreate_v1_database.py

⚠️ WARNING: This will DELETE ALL existing data! 
    Make sure to backup any important data first.
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# imports
from backend.database import engine, SessionLocal, DATABASE_URL

# Define Base locally to avoid circular imports
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# Import models from the package (gets all models through __init__.py)
from backend.models import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def confirm_database_recreation():
    """Ask user to confirm database recreation."""
    print("\n" + "="*60)
    print("🚨 QUANTMATRIX DATABASE RECREATION")
    print("="*60)
    print()
    print("⚠️  WARNING: This will PERMANENTLY DELETE all existing data!")
    print("    - All old tables will be dropped")
    print("    - Fresh models will be created")
    print("    - User accounts, positions, transactions will be LOST")
    print()
    print("📊 What will be created:")
    print("    ✅ Users and authentication")
    print("    ✅ Broker accounts (IBKR, TastyTrade)")
    print("    ✅ Tax lots with proper cost basis")
    print("    ✅ Positions and transactions")
    print("    ✅ CSV import system")
    print("    ✅ Strategy execution tracking")
    print()
    print("🎯 Ready for:")
    print("    - Your 3 IBKR CSV files import")
    print("    - Clean services integration")
    print("    - Strategy execution via StrategiesManager.tsx")
    print()
    
    response = input("Type 'YES DELETE ALL DATA' to proceed: ")
    
    if response != "YES DELETE ALL DATA":
        print("\n❌ Database recreation cancelled.")
        print("   No changes made to database.")
        sys.exit(0)
    
    print("\n✅ Confirmed. Starting database recreation...")

def drop_all_tables():
    """Drop all existing tables."""
    try:
        logger.info("🗑️  Dropping all existing tables...")
        
        # Connect to database
        meta = MetaData()
        meta.reflect(bind=engine)
        
        # Drop all tables
        meta.drop_all(bind=engine)
        
        logger.info("✅ All old tables dropped successfully")
        
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {e}")
        raise

def create_v1_tables():
    """Create all tables."""
    try:
        logger.info("🏗️  Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ tables created successfully")
        
        # Log the tables that were created
        table_names = list(Base.metadata.tables.keys())
        logger.info(f"📊 Created {len(table_names)} tables:")
        for table_name in sorted(table_names):
            logger.info(f"   ✅ {table_name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise

def create_default_user():
    """Create a default admin user for testing."""
    try:
        logger.info("👤 Creating default admin user...")
        
        session = SessionLocal()
        
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == "admin").first()
        if existing_user:
            logger.info("   ℹ️  Admin user already exists")
            session.close()
            return
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@quantmatrix.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        # Set password (in production, this should be hashed properly)
        admin_user.set_password("admin123")  # Default password
        
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        
        logger.info(f"✅ Created admin user: {admin_user.username} (ID: {admin_user.id})")
        logger.info("   📝 Login: admin / admin123")
        
        session.close()
        
        return admin_user.id
        
    except Exception as e:
        logger.error(f"❌ Error creating default user: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        raise

def setup_user_accounts(user_id: int):
    """Set up the user's IBKR accounts for CSV import."""
    try:
        logger.info("🏦 Setting up user's IBKR accounts...")
        
        session = SessionLocal()
        
        # Create taxable IBKR account (U19490886)
        taxable_account = BrokerAccount(
            user_id=user_id,
            broker=BrokerType.IBKR,
            account_number="U19490886",
            account_name="IBKR Taxable Account",
            account_type=AccountType.TAXABLE,
            is_primary=True,
            currency="USD"
        )
        
        # Create IRA IBKR account (U15891532)
        ira_account = BrokerAccount(
            user_id=user_id,
            broker=BrokerType.IBKR,
            account_number="U15891532", 
            account_name="IBKR IRA Account",
            account_type=AccountType.IRA,
            currency="USD"
        )
        
        session.add(taxable_account)
        session.add(ira_account)
        session.commit()
        
        logger.info(f"✅ Created taxable account: {taxable_account.account_number}")
        logger.info(f"✅ Created IRA account: {ira_account.account_number}")
        logger.info("   🎯 Ready for your 3 CSV files import!")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Error setting up user accounts: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        raise

def verify_v1_structure():
    """Verify that database structure is correct."""
    try:
        logger.info("🔍 Verifying database structure...")
        
        session = SessionLocal()
        
        # Test basic queries on each model
        tests = [
            ("Users", session.query(User).count()),
            ("Broker Accounts", session.query(BrokerAccount).count()),
            ("Tax Lots", session.query(TaxLot).count()),
            ("Positions", session.query(Position).count()),
            ("Transactions", session.query(Transaction).count()),
            ("Instruments", session.query(Instrument).count()),
        ]
        
        logger.info("📊 Database verification:")
        for table_name, count in tests:
            logger.info(f"   ✅ {table_name}: {count} records")
        
        session.close()
        
        logger.info("✅ database structure verified!")
        
    except Exception as e:
        logger.error(f"❌ Error verifying structure: {e}")
        if 'session' in locals():
            session.close()
        raise

def main():
    """Main recreation process."""
    print("🚀 QuantMatrix V1 Database Recreation")
    print(f"📍 Database: {DATABASE_URL}")
    print()
    
    try:
        # Confirm with user
        confirm_database_recreation()
        
        # Step 1: Drop all old tables
        drop_all_tables()
        
        # Step 2: Create tables
        create_v1_tables()
        
        # Step 3: Create default user
        user_id = create_default_user()
        
        # Step 4: Set up user accounts for CSV import
        setup_user_accounts(user_id)
        
        # Step 5: Verify structure
        verify_v1_structure()
        
        # Success message
        print("\n" + "="*60)
        print("🎉 DATABASE RECREATION COMPLETE!")
        print("="*60)
        print()
        print("✅ What's ready now:")
        print("   🏗️  Fresh database structure")
        print("   👤 Admin user (admin / admin123)")
        print("   🏦 IBKR accounts (U19490886 taxable, U15891532 IRA)")
        print("   📊 Ready for your 3 CSV files import")
        print("   🚀 Ready for services integration")
        print()
        print("🎯 Next steps:")
        print("   1. Run CSV import: python -m backend.services.portfolio.csv_import_service")
        print("   2. Test services integration")
        print("   3. Execute strategies via StrategiesManager.tsx")
        print()
        print("💰 Ready for production trading with clean architecture!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Database recreation failed: {e}")
        print(f"\n❌ FAILED: {e}")
        print("   Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 