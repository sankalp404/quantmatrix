#!/usr/bin/env python3

import asyncio
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, AccountValue, Position, Trade
    IBKR_AVAILABLE = True
    print("✅ ib_insync library available")
except ImportError as e:
    print(f"❌ ib_insync not available: {e}")
    IBKR_AVAILABLE = False

async def test_ibkr_connection():
    """Test IBKR connection step by step."""
    if not IBKR_AVAILABLE:
        print("❌ Cannot test - ib_insync not available")
        return
    
    print("\n🔍 Testing IBKR Gateway connection...")
    
    # Connection settings
    IBKR_HOST = "host.docker.internal"  # For Docker
    IBKR_PORT = 7497
    IBKR_CLIENT_ID = 1
    
    print(f"Host: {IBKR_HOST}")
    print(f"Port: {IBKR_PORT}")
    print(f"Client ID: {IBKR_CLIENT_ID}")
    
    ib = IB()
    
    try:
        print("\n📡 Attempting connection...")
        ib.connect(host=IBKR_HOST, port=IBKR_PORT, clientId=IBKR_CLIENT_ID, timeout=10)
        print("✅ Connected successfully!")
        
        # Test 1: Check if connected
        print(f"\n🔗 Connection status: {ib.isConnected()}")
        print(f"📱 Client ID: {ib.client.clientId}")
        
        # Test 2: Get managed accounts  
        print("\n👤 Getting managed accounts...")
        managed_accounts = ib.managedAccounts()
        print(f"Managed accounts: {managed_accounts}")
        
        # Test 3: Get account values (step by step)
        print("\n💰 Getting account values...")
        account_values = ib.accountValues()
        print(f"Total account values returned: {len(account_values)}")
        
        if account_values:
            print("\n📊 First 10 account values:")
            for i, av in enumerate(account_values[:10]):
                print(f"  {i+1}. Account: {av.account}, Tag: {av.tag}, Value: {av.value}, Currency: {av.currency}")
            
            # Look specifically for key values
            print("\n🎯 Looking for key account metrics:")
            key_tags = ['NetLiquidation', 'TotalCashValue', 'UnrealizedPnL', 'RealizedPnL', 'DayTradesRemaining', 'AvailableFunds', 'BuyingPower']
            
            for tag in key_tags:
                matching_values = [av for av in account_values if av.tag == tag]
                if matching_values:
                    for av in matching_values:
                        print(f"  ✅ {tag}: {av.value} {av.currency} (Account: {av.account})")
                else:
                    print(f"  ❌ {tag}: Not found")
        else:
            print("❌ No account values returned!")
        
        # Test 4: Get positions
        print("\n📈 Getting positions...")
        positions = ib.positions()
        print(f"Total positions: {len(positions)}")
        
        if positions:
            print("Current positions:")
            for pos in positions[:5]:  # Show first 5
                print(f"  📊 {pos.contract.symbol}: {pos.position} shares @ ${pos.avgCost:.2f}")
        else:
            print("  📭 No positions (normal for new/empty account)")
        
        # Test 5: Account summary
        print("\n📋 Getting account summary...")
        try:
            # Request account summary with specific tags
            summary_tags = "NetLiquidation,TotalCashValue,StockMarketValue,UnrealizedPnL,RealizedPnL,GrossPositionValue"
            account_summary = ib.accountSummary(managed_accounts[0] if managed_accounts else "", summary_tags)
            
            print(f"Account summary items: {len(account_summary)}")
            for item in account_summary:
                print(f"  📊 {item.tag}: {item.value} {item.currency}")
                
        except Exception as e:
            print(f"❌ Account summary error: {e}")
        
        print("\n✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("🔌 Disconnected from IBKR")

if __name__ == "__main__":
    asyncio.run(test_ibkr_connection()) 