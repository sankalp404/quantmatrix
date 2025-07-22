#!/usr/bin/env python3
"""
Simple Test Suite - Basic functionality tests without complex dependencies
"""

import json
import requests
import time

def test_options_api_basic():
    """Test that options API returns data and doesn't error."""
    try:
        response = requests.get("http://localhost:8000/api/v1/options/unified/portfolio", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Options API returned {response.status_code}")
            return False
            
        data = response.json()
        
        if data.get('status') != 'success':
            print(f"❌ Options API returned error: {data.get('error', 'Unknown error')}")
            return False
            
        positions = data.get('data', {}).get('positions', [])
        print(f"✅ Options API working - {len(positions)} positions")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Options API connection failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Options API returned invalid JSON: {e}")
        return False

def test_portfolio_api_basic():
    """Test that portfolio API returns data."""
    try:
        response = requests.get("http://localhost:8000/api/v1/portfolio/live", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Portfolio API returned {response.status_code}")
            return False
            
        data = response.json()
        
        if data.get('status') != 'success':
            print(f"❌ Portfolio API returned error: {data.get('error', 'Unknown error')}")
            return False
            
        accounts = data.get('data', {}).get('accounts', {})
        print(f"✅ Portfolio API working - {len(accounts)} accounts")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Portfolio API connection failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Portfolio API returned invalid JSON: {e}")
        return False

def test_health_endpoint():
    """Test basic health endpoint."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Health endpoint returned {response.status_code}")
            return False
            
        print("✅ Health endpoint working")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Health endpoint connection failed: {e}")
        return False

def test_no_fake_data_in_statements():
    """Test that statements endpoint doesn't return fake data."""
    try:
        response = requests.get("http://localhost:8000/api/v1/portfolio/statements?days=30", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Statements API returned {response.status_code}")
            return False
            
        data = response.json()
        
        if data.get('status') != 'success':
            print(f"❌ Statements API returned error: {data.get('error', 'Unknown error')}")
            return False
            
        transactions = data.get('data', {}).get('transactions', [])
        
        # Check for fake data sources
        fake_sources = ['realistic_sample', 'ibkr_sample']
        for transaction in transactions:
            if transaction.get('source') in fake_sources:
                print(f"❌ Found fake transaction data: {transaction.get('source')}")
                return False
                
        print(f"✅ No fake data in {len(transactions)} transactions")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Statements API connection failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Statements API returned invalid JSON: {e}")
        return False

def main():
    """Run all simple tests."""
    print("🧪 Running Simple QuantMatrix Tests")
    print("=" * 40)
    
    tests = [
        test_health_endpoint,
        test_portfolio_api_basic,
        test_options_api_basic,
        test_no_fake_data_in_statements,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed - check issues above")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 