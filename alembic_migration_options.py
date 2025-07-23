#!/usr/bin/env python3
"""
QuantMatrix - Alembic Migration Options
======================================

Options for creating/migrating database tables with Alembic.
Handles options trading, strategies, and enhanced portfolio features.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.database import engine, SessionLocal, Base

# Import all models to ensure they're registered with Base
try:
    from backend.models.user import User
    from backend.models.portfolio import Portfolio, Holding, Account
    from backend.models.signals import Signal, AlertRule
    from backend.models.notifications import Notification
    from backend.models.market_data import Instrument, PriceData, TechnicalIndicators
    from backend.models.options import OptionsContract, OptionsPosition
    from backend.models.tax_lots import TaxLot
    from backend.models.transactions import Transaction
    print("✅ Core models imported successfully")
except ImportError as e:
    print(f"⚠️ Some models not available: {e}")

def create_options_tables():
    """Create all database tables for options trading."""
    try:
        print("🗃️ Creating QuantMatrix database tables...")
        
        # Create all tables using SQLAlchemy metadata
        # This automatically creates all tables defined in imported models
        Base.metadata.create_all(engine)
        
        print("✅ All database tables created successfully!")
        
        # Verify table creation
        with SessionLocal() as db:
            # Test database connection
            result = db.execute("SELECT 1").scalar()
            if result == 1:
                print("✅ Database connection verified")
            else:
                print("⚠️ Database connection issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def drop_all_tables():
    """Drop all database tables (use with caution!)."""
    try:
        print("🗑️ Dropping all database tables...")
        
        Base.metadata.drop_all(engine)
        
        print("✅ All tables dropped successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="QuantMatrix Database Migration Options")
    parser.add_argument("--create", action="store_true", help="Create all tables")
    parser.add_argument("--drop", action="store_true", help="Drop all tables")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate all tables")
    
    args = parser.parse_args()
    
    if args.drop or args.recreate:
        if drop_all_tables():
            print("🗑️ Tables dropped successfully")
    
    if args.create or args.recreate:
        if create_options_tables():
            print("🎉 Database setup complete!")
    
    if not any([args.create, args.drop, args.recreate]):
        print("Usage: python alembic_migration_options.py --create|--drop|--recreate")
        print("  --create: Create all tables")
        print("  --drop: Drop all tables")  
        print("  --recreate: Drop and recreate all tables") 