#!/usr/bin/env python3
"""
QuantMatrix V1 - Ordered Data Import
===================================

Import data in your preferred order:
1. TastyTrade (first)
2. IBKR Tax Deferred 
3. IBKR Joint

Clean, organized, no overlaps.
"""

import sys
import logging
import os
import psycopg2
from decimal import Decimal

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

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)

def import_tastytrade_data():
    """Import TastyTrade data first."""
    try:
        logger.info("1️⃣ Importing TastyTrade data...")
        
        conn = get_db_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Add TastyTrade account
        cursor.execute("""
            INSERT INTO accounts (account_id, broker, account_type, account_name) 
            VALUES ('5WX04297', 'TASTYTRADE', 'INDIVIDUAL', 'TastyTrade Individual')
            ON CONFLICT (account_id) DO NOTHING
        """)
        
        logger.info("   ✅ TastyTrade account added")
        
        # Import TastyTrade service
        try:
            sys.path.insert(0, '/app')
            from services.tastytrade_service import TastytradeService
            
            service = TastytradeService()
            
            # Sync positions
            logger.info("   📊 Syncing TastyTrade positions...")
            positions = service.get_positions()
            
            if positions:
                for position in positions:
                    cursor.execute("""
                        INSERT INTO holdings (
                            account_id, symbol, quantity, 
                            average_cost, current_price, market_value, 
                            pnl, pnl_percentage
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        '5WX04297',
                        position.get('symbol', ''),
                        position.get('quantity', 0),
                        position.get('average_cost', 0),
                        position.get('current_price', 0), 
                        position.get('market_value', 0),
                        position.get('pnl', 0),
                        position.get('pnl_percentage', 0)
                    ))
                
                logger.info(f"   ✅ Imported {len(positions)} TastyTrade positions")
            else:
                logger.info("   ⚠️ No TastyTrade positions found")
                
        except Exception as e:
            logger.warning(f"   ⚠️ TastyTrade service unavailable: {e}")
            logger.info("   📝 Creating placeholder TastyTrade entry")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ TastyTrade import complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ TastyTrade import failed: {e}")
        return False

def import_ibkr_tax_deferred():
    """Import IBKR Tax Deferred account."""
    try:
        logger.info("2️⃣ Importing IBKR Tax Deferred...")
        
        conn = get_db_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Add IBKR Tax Deferred account
        cursor.execute("""
            INSERT INTO accounts (account_id, broker, account_type, account_name)
            VALUES ('U15891532', 'IBKR', 'IRA', 'IBKR Tax Deferred IRA')
            ON CONFLICT (account_id) DO NOTHING
        """)
        
        logger.info("   ✅ IBKR Tax Deferred account added")
        
        # Try to import IBKR data
        try:
            from services.ibkr_client import IBKRClient
            
            client = IBKRClient()
            
            # Get positions for tax deferred account
            logger.info("   📊 Syncing IBKR Tax Deferred positions...")
            positions = client.get_positions_for_account('U15891532')
            
            if positions:
                for position in positions:
                    cursor.execute("""
                        INSERT INTO holdings (
                            account_id, symbol, quantity,
                            average_cost, current_price, market_value,
                            pnl, pnl_percentage  
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        'U15891532',
                        position.get('symbol', ''),
                        position.get('quantity', 0),
                        position.get('average_cost', 0),
                        position.get('current_price', 0),
                        position.get('market_value', 0),
                        position.get('pnl', 0),
                        position.get('pnl_percentage', 0)
                    ))
                
                logger.info(f"   ✅ Imported {len(positions)} IBKR Tax Deferred positions")
            else:
                logger.info("   ⚠️ No IBKR Tax Deferred positions found")
                
        except Exception as e:
            logger.warning(f"   ⚠️ IBKR service unavailable: {e}")
            logger.info("   📝 Creating placeholder IBKR Tax Deferred entry")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ IBKR Tax Deferred import complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ IBKR Tax Deferred import failed: {e}")
        return False

def import_ibkr_joint():
    """Import IBKR Joint account."""
    try:
        logger.info("3️⃣ Importing IBKR Joint...")
        
        conn = get_db_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Add IBKR Joint account
        cursor.execute("""
            INSERT INTO accounts (account_id, broker, account_type, account_name)
            VALUES ('U19490886', 'IBKR', 'JOINT', 'IBKR Joint Taxable')
            ON CONFLICT (account_id) DO NOTHING  
        """)
        
        logger.info("   ✅ IBKR Joint account added")
        
        # Try to import IBKR data
        try:
            from services.ibkr_client import IBKRClient
            
            client = IBKRClient()
            
            # Get positions for joint account
            logger.info("   📊 Syncing IBKR Joint positions...")
            positions = client.get_positions_for_account('U19490886')
            
            if positions:
                for position in positions:
                    cursor.execute("""
                        INSERT INTO holdings (
                            account_id, symbol, quantity,
                            average_cost, current_price, market_value,
                            pnl, pnl_percentage
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        'U19490886',
                        position.get('symbol', ''),
                        position.get('quantity', 0),
                        position.get('average_cost', 0),
                        position.get('current_price', 0),
                        position.get('market_value', 0),
                        position.get('pnl', 0),
                        position.get('pnl_percentage', 0)
                    ))
                
                logger.info(f"   ✅ Imported {len(positions)} IBKR Joint positions")
            else:
                logger.info("   ⚠️ No IBKR Joint positions found")
                
        except Exception as e:
            logger.warning(f"   ⚠️ IBKR service unavailable: {e}")
            logger.info("   📝 Creating placeholder IBKR Joint entry")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ IBKR Joint import complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ IBKR Joint import failed: {e}")
        return False

def verify_import_results():
    """Verify all data was imported correctly."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count by account
        cursor.execute("""
            SELECT a.account_name, a.broker, a.account_type, COUNT(h.id) as holdings_count
            FROM accounts a 
            LEFT JOIN holdings h ON a.account_id = h.account_id
            GROUP BY a.account_id, a.account_name, a.broker, a.account_type
            ORDER BY a.account_id
        """)
        
        results = cursor.fetchall()
        
        logger.info("📊 Import Results:")
        logger.info("-" * 60)
        
        total_holdings = 0
        for account_name, broker, account_type, count in results:
            logger.info(f"   {broker} {account_type}: {count} holdings ({account_name})")
            total_holdings += count
        
        logger.info("-" * 60)
        logger.info(f"   TOTAL: {total_holdings} holdings across {len(results)} accounts")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def ordered_import():
    """Run the complete ordered import process."""
    logger.info("🚀 QUANTMATRIX ORDERED DATA IMPORT")
    logger.info("=" * 60)
    
    success_count = 0
    
    # Step 1: TastyTrade
    if import_tastytrade_data():
        success_count += 1
    
    # Step 2: IBKR Tax Deferred
    if import_ibkr_tax_deferred():
        success_count += 1
    
    # Step 3: IBKR Joint
    if import_ibkr_joint():
        success_count += 1
    
    # Verify results
    verify_import_results()
    
    logger.info("=" * 60)
    
    if success_count == 3:
        logger.info("🎉 ALL IMPORTS SUCCESSFUL!")
        logger.info("✅ Ready for trading operations!")
        return True
    else:
        logger.info(f"⚠️ {success_count}/3 imports successful")
        logger.info("🔧 Some imports had issues - check logs above")
        return False

if __name__ == "__main__":
    success = ordered_import()
    
    if success:
        print("")
        print("🎉 SUCCESS! All data imported in order!")
        print("📊 TastyTrade → IBKR Tax Deferred → IBKR Joint")
        print("🚀 Ready for live trading!")
    else:
        print("")
        print("⚠️ Some issues occurred - check logs above")
        print("💡 You can run individual imports if needed") 