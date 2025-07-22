#!/usr/bin/env python3
"""
Comprehensive Test Suite for Discord Notifications
Tests all Discord endpoints to ensure notifications work reliably.
"""

import asyncio
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class DiscordNotificationTester:
    """Test suite for Discord notification system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.failed_tests = []
        
    def run_test(self, test_name: str, test_func):
        """Run a single test and track results."""
        print(f"🧪 Running {test_name}...")
        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            if result.get('success', False):
                print(f"✅ {test_name} - {duration:.2f}s")
                self.test_results.append({
                    'test': test_name,
                    'status': 'PASS',
                    'duration': duration,
                    'details': result.get('details', 'OK')
                })
            else:
                print(f"❌ {test_name} - {result.get('error', 'Unknown error')}")
                self.failed_tests.append(test_name)
                self.test_results.append({
                    'test': test_name,
                    'status': 'FAIL',
                    'duration': duration,
                    'error': result.get('error', 'Unknown error')
                })
                
        except Exception as e:
            print(f"💥 {test_name} - Exception: {e}")
            self.failed_tests.append(test_name)
            self.test_results.append({
                'test': test_name,
                'status': 'ERROR',
                'duration': 0,
                'error': str(e)
            })
    
    def test_basic_discord_connection(self) -> Dict[str, Any]:
        """Test basic Discord webhook connectivity."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/test-discord")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {'success': True, 'details': 'Discord playground test sent'}
                else:
                    return {'success': False, 'error': f"Discord not configured: {data.get('message')}"}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Connection error: {e}"}
    
    def test_all_discord_channels(self) -> Dict[str, Any]:
        """Test all Discord channels."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/test-all-discord-channels")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    results = data.get('results', [])
                    working_channels = len([r for r in results if r.startswith('✅')])
                    return {'success': True, 'details': f"{working_channels} channels working"}
                else:
                    return {'success': False, 'error': data.get('message', 'Unknown error')}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Request error: {e}"}
    
    def test_signals_endpoint(self) -> Dict[str, Any]:
        """Test ATR signals generation and Discord delivery."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/send-signals", timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                signals_sent = data.get('signals_sent', 0)
                return {'success': True, 'details': f"{signals_sent} signals sent to Discord"}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Signals error: {e}"}
    
    def test_morning_brew_endpoint(self) -> Dict[str, Any]:
        """Test morning brew generation and Discord delivery."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/send-morning-brew", timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                opportunities = data.get('opportunities_found', 0)
                return {'success': True, 'details': f"Morning brew sent with {opportunities} opportunities"}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Morning brew error: {e}"}
    
    def test_portfolio_digest_endpoint(self) -> Dict[str, Any]:
        """Test portfolio digest generation and Discord delivery."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/send-portfolio-digest", timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    accounts = len(data.get('accounts_processed', []))
                    total_value = data.get('total_portfolio_value', 0)
                    return {'success': True, 'details': f"Portfolio digest sent for {accounts} accounts (${total_value:,.2f})"}
                else:
                    return {'success': False, 'error': data.get('message', 'Unknown error')}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Portfolio digest error: {e}"}
    
    def test_system_status_endpoint(self) -> Dict[str, Any]:
        """Test system status generation and Discord delivery."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/send-system-status", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                system_health = data.get('system_health', 'Unknown')
                market_status = data.get('market_status', 'Unknown')
                return {'success': True, 'details': f"System status sent - Health: {system_health}, Market: {market_status}"}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"System status error: {e}"}
    
    def test_portfolio_alerts_endpoint(self) -> Dict[str, Any]:
        """Test portfolio alerts generation."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/force-portfolio-alerts", timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    alerts_sent = data.get('alerts_sent', 0)
                    return {'success': True, 'details': f"{alerts_sent} portfolio alerts processed"}
                else:
                    return {'success': False, 'error': data.get('message', 'Unknown error')}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Portfolio alerts error: {e}"}
    
    def test_post_market_brew_endpoint(self) -> Dict[str, Any]:
        """Test post-market brew generation."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/send-post-market-brew", timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    return {'success': True, 'details': data['message']}
                else:
                    return {'success': True, 'details': 'Post-market brew sent'}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Post-market brew error: {e}"}
    
    def test_scanner_endpoint(self) -> Dict[str, Any]:
        """Test manual scanner trigger."""
        try:
            response = requests.post(f"{self.base_url}/api/v1/tasks/run-scanner", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'started':
                    task_id = data.get('task_id', 'unknown')
                    return {'success': True, 'details': f"Scanner started with task ID: {task_id}"}
                else:
                    return {'success': False, 'error': data.get('message', 'Unknown error')}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Scanner error: {e}"}
    
    def test_tasks_status_endpoint(self) -> Dict[str, Any]:
        """Test task status endpoint."""
        try:
            response = requests.get(f"{self.base_url}/api/v1/tasks/status")
            
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'details': f"Task status retrieved"}
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {'success': False, 'error': f"Task status error: {e}"}
    
    def run_all_tests(self):
        """Run all Discord notification tests."""
        print("🚀 Starting Discord Notification Test Suite")
        print("=" * 60)
        
        # Core tests
        self.run_test("Basic Discord Connection", self.test_basic_discord_connection)
        self.run_test("All Discord Channels", self.test_all_discord_channels)
        
        # Main notification tests  
        self.run_test("ATR Signals", self.test_signals_endpoint)
        self.run_test("Morning Brew", self.test_morning_brew_endpoint)
        self.run_test("Portfolio Digest", self.test_portfolio_digest_endpoint)
        self.run_test("System Status", self.test_system_status_endpoint)
        
        # Additional tests
        self.run_test("Portfolio Alerts", self.test_portfolio_alerts_endpoint)
        self.run_test("Post-Market Brew", self.test_post_market_brew_endpoint)
        self.run_test("Manual Scanner", self.test_scanner_endpoint)
        self.run_test("Task Status", self.test_tasks_status_endpoint)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'PASS'])
        failed_tests = len([t for t in self.test_results if t['status'] in ['FAIL', 'ERROR']])
        
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n💥 Failed Tests: {', '.join(self.failed_tests)}")
            print("\n🔍 Failure Details:")
            for result in self.test_results:
                if result['status'] in ['FAIL', 'ERROR']:
                    print(f"  ❌ {result['test']}: {result.get('error', 'Unknown error')}")
        else:
            print("\n🎉 All Discord notification tests passed!")
        
        print(f"\n⏱️  Total Test Duration: {sum(r.get('duration', 0) for r in self.test_results):.2f}s")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': passed_tests/total_tests*100,
            'details': self.test_results
        }


def main():
    """Run the Discord notification test suite."""
    tester = DiscordNotificationTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main() 