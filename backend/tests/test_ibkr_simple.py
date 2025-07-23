#!/usr/bin/env python3

import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, AccountValue, Position, Trade
    IBKR_AVAILABLE = True
    print("✅ ib_insync library available")
except ImportError as e:
    print(f"❌ ib_insync not available: {e}")
    IBKR_AVAILABLE = False

def test_ibkr_connection():
    """Test IBKR connection step by step."""
    if not IBKR_AVAILABLE:
        print("❌ Cannot test - ib_insync not available")
        return
    
    print("\n🔍 Testing IBKR Gateway connection...")
    
    # Connection settings
    IBKR_HOST = "host.docker.internal"  # For Docker
    IBKR_PORT = 7497
    IBKR_CLIENT_ID = 2  # Use different client ID to avoid conflicts
    
    print(f"Host: {IBKR_HOST}")
    print(f"Port: {IBKR_PORT}")
    print(f"Client ID: {IBKR_CLIENT_ID}")
    
    ib = IB()
    
    try:
        print("\n📡 Attempting connection...")
        ib.connect(host=IBKR_HOST, port=IBKR_PORT, clientId=IBKR_CLIENT_ID, timeout=15)
        print("✅ Connected successfully!")
        
        # Wait a moment for connection to stabilize
        time.sleep(2)
        
        # Test 1: Check if connected
        print(f"\n🔗 Connection status: {ib.isConnected()}")
        print(f"📱 Client ID: {ib.client.clientId}")
        
        # Test 2: Get managed accounts  
        print("\n👤 Getting managed accounts...")
        managed_accounts = ib.managedAccounts()
        print(f"Managed accounts: {managed_accounts}")
        
        # Test 3: Request account values for specific account
        if managed_accounts:
            target_account = managed_accounts[0]
            print(f"\n💰 Getting account values for account: {target_account}")
            
            # Try multiple methods to get account data
            
            # Method 1: accountValues()
            account_values = ib.accountValues(account=target_account)
            print(f"Account values returned: {len(account_values)}")
            
            if account_values:
                print("\n📊 All account values:")
                for av in account_values[:20]:  # Show first 20
                    print(f"  {av.tag}: {av.value} {av.currency}")
            
            # Method 2: accountSummary()
            print(f"\n📋 Getting account summary for {target_account}...")
            try:
                summary_tags = "NetLiquidation,TotalCashValue,StockMarketValue,UnrealizedPnL,RealizedPnL,GrossPositionValue,AvailableFunds,BuyingPower"
                account_summary = ib.accountSummary(account=target_account, tags=summary_tags)
                
                print(f"Account summary items: {len(account_summary)}")
                for item in account_summary:
                    print(f"  📊 {item.tag}: {item.value} {item.currency}")
                    
            except Exception as e:
                print(f"❌ Account summary error: {e}")
        
        else:
            print("❌ No managed accounts found!")
        
        # Test 4: Get positions
        print("\n📈 Getting positions...")
        positions = ib.positions()
        print(f"Total positions: {len(positions)}")
        
        if positions:
            print("Current positions:")
            for pos in positions:
                print(f"  📊 {pos.contract.symbol}: {pos.position} shares @ ${pos.avgCost:.2f} (Account: {pos.account})")
        else:
            print("  📭 No positions (normal for new/empty account)")
        
        print("\n✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            if ib.isConnected():
                ib.disconnect()
                print("🔌 Disconnected from IBKR")
        except:
            pass

if __name__ == "__main__":
    test_ibkr_connection() 