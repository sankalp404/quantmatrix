#!/usr/bin/env python3
"""
Debug Tax Lots and IBKR Connection
Helps diagnose why tax lots aren't being synced
"""

import asyncio
import json
from datetime import datetime
from services.enhanced_ibkr_client import enhanced_ibkr_client
from models import SessionLocal
from models.portfolio import Account, Holding

async def debug_ibkr_connection():
    """Debug enhanced IBKR connection and account access."""
    print("🔍 Debugging Enhanced IBKR Connection")
    print("=" * 50)
    
    # Test enhanced connection
    print("1️⃣ Testing enhanced IBKR connection...")
    try:
        connected = await enhanced_ibkr_client.connect_with_retry(max_attempts=3)
        if connected:
            print("✅ Enhanced IBKR connected successfully")
            
            # Show connection status
            status = enhanced_ibkr_client.get_connection_status()
            print(f"📊 Connection Status: {status}")
        else:
            print("❌ Enhanced IBKR connection failed")
            return
    except Exception as e:
        print(f"❌ Enhanced IBKR connection error: {e}")
        return
    
    # Test managed accounts
    print("\n2️⃣ Testing managed accounts...")
    try:
        accounts = enhanced_ibkr_client.managed_accounts
        if accounts:
            print(f"✅ Found {len(accounts)} managed accounts: {accounts}")
        else:
            print("❌ No managed accounts found")
    except Exception as e:
        print(f"❌ Error getting managed accounts: {e}")
        return
    
    # Test enhanced transactions and tax lots
    print("\n3️⃣ Testing enhanced transactions and tax lots...")
    for account_id in accounts:
        print(f"\n📊 Account {account_id}:")
        
        try:
            # Test enhanced transactions
            print("  🔄 Testing enhanced transaction sync...")
            transactions = await enhanced_ibkr_client.get_enhanced_account_statements(account_id, days=90)
            print(f"  ✅ Retrieved {len(transactions)} transactions")
            
            if transactions:
                print(f"  📝 Sample transactions:")
                for tx in transactions[:3]:  # Show first 3
                    print(f"    - {tx['symbol']}: {tx['action']} {tx['quantity']} @ ${tx['price']} on {tx['date']}")
            
            # Test enhanced tax lots
            print("  📊 Testing enhanced tax lot sync...")
            tax_lots = await enhanced_ibkr_client.get_enhanced_tax_lots(account_id)
            print(f"  ✅ Retrieved {len(tax_lots)} tax lots")
            
            if tax_lots:
                print(f"  📋 Sample tax lots:")
                for lot in tax_lots[:3]:  # Show first 3
                    print(f"    - {lot['symbol']}: {lot['quantity']} shares @ ${lot['cost_per_share']} ({lot['acquisition_date']})")
                    print(f"      P&L: ${lot['unrealized_pnl']:.2f} ({lot['unrealized_pnl_pct']:.1f}%)")
            
        except Exception as e:
            print(f"  ❌ Error testing account {account_id}: {e}")
        
        # Get holdings from database for comparison
        db = SessionLocal()
        try:
            account = db.query(Account).filter(Account.account_number == account_id).first()
            if account:
                holdings = db.query(Holding).filter(
                    Holding.account_id == account.id,
                    Holding.quantity > 0,
                    Holding.contract_type == 'STK'  # Only stocks for tax lots
                ).limit(3).all()
                
                print(f"  📈 Database comparison: {len(holdings)} stock holdings in database")
            else:
                print(f"  ❌ Account {account_id} not found in database")
        finally:
            db.close()

async def debug_tax_lot_sync():
    """Debug the tax lot sync process."""
    print("\n4️⃣ Testing tax lot sync process...")
    
    # Check if we have any tax lots in the database
    db = SessionLocal()
    try:
        from models.tax_lots import TaxLot
        tax_lots_count = db.query(TaxLot).count()
        print(f"  📊 Tax lots in database: {tax_lots_count}")
        
        if tax_lots_count > 0:
            recent_lot = db.query(TaxLot).order_by(TaxLot.id.desc()).first()
            print(f"  📅 Most recent: {recent_lot.symbol} on {recent_lot.purchase_date}")
        
        # Check holdings that could have tax lots
        stock_holdings = db.query(Holding).filter(
            Holding.quantity > 0,
            Holding.contract_type == 'STK'
        ).count()
        print(f"  📈 Stock holdings that could have tax lots: {stock_holdings}")
        
    except Exception as e:
        print(f"  ❌ Error checking database: {e}")
    finally:
        db.close()

def main():
    """Main debug function."""
    print("🧪 QuantMatrix Tax Lots Debug")
    print(f"⏰ Started at: {datetime.now()}")
    print()
    
    asyncio.run(debug_ibkr_connection())
    asyncio.run(debug_tax_lot_sync())
    
    print("\n" + "=" * 50)
    print("🏁 Debug complete!")
    print()
    print("💡 To fix tax lot issues:")
    print("  1. Ensure IBKR TWS is running on port 7497")
    print("  2. Check that API is enabled in TWS settings")
    print("  3. Add 127.0.0.1 to trusted IPs in TWS")
    print("  4. Make sure account has transaction history from May 9, 2024")

if __name__ == "__main__":
    main() 