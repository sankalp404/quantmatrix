#!/usr/bin/env python3
"""
Migration script for Options Trading Tables
Run this to create the new options trading database tables.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from backend.config import settings
from backend.models.options import *
from backend.models import Base

def run_migration():
    """Create all options trading tables."""
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    print("Creating options trading tables...")
    
    try:
        # Create all tables defined in options models
        Base.metadata.create_all(engine, tables=[
            TastytradeAccount.__table__,
            OptionInstrument.__table__,
            OptionPosition.__table__,
            OptionGreeks.__table__,
            OptionPrice.__table__,
            OptionOrder.__table__,
            TradingStrategy.__table__,
            StrategySignal.__table__,
            StrategyPerformance.__table__,
            CapitalAllocation.__table__,
            RiskMetrics.__table__
        ])
        
        print("✅ Options trading tables created successfully!")
        print("\nNew Tables Created:")
        print("- tastytrade_accounts")
        print("- option_instruments") 
        print("- option_positions")
        print("- option_greeks")
        print("- option_prices")
        print("- option_orders")
        print("- trading_strategies")
        print("- strategy_signals")
        print("- strategy_performance")
        print("- capital_allocations")
        print("- risk_metrics")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n🎉 Migration completed! Your options trading system is ready.")
        print("\nNext steps:")
        print("1. Add your Tastytrade credentials to .env file")
        print("2. Initialize your first ATR Matrix strategy")
        print("3. Start automated trading!")
    else:
        print("\n💥 Migration failed. Please check the error above.")
        sys.exit(1) 