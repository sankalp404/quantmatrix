#!/usr/bin/env python3
"""
QuantMatrix V1 - Consolidated Test Runner
=========================================

Single test runner for the entire ATR system.
Organized test suite with pre/post rebuild validation.

Usage:
    python backend/run_tests.py                # Run all tests
    python backend/run_tests.py --quick        # Quick tests only
    python backend/run_tests.py --discord      # Discord tests only
    python backend/run_tests.py --integration  # Integration tests only
    python backend/run_tests.py --pre-rebuild  # Pre-rebuild validation
    python backend/run_tests.py --post-rebuild # Post-rebuild validation
"""

import asyncio
import sys
import os
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def setup_logging(verbose=False):
    """Setup logging for test output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/quantmatrix_tests.log')
        ]
    )

async def run_pre_rebuild_validation():
    """Run pre-rebuild validation."""
    try:
        from backend.tests.test_pre_rebuild_validation import PreRebuildValidator
        
        validator = PreRebuildValidator()
        success = await validator.run_all_checks()
        return success
        
    except Exception as e:
        print(f"❌ Pre-rebuild validation failed: {e}")
        return False

async def run_post_rebuild_validation():
    """Run post-rebuild validation."""
    try:
        from backend.tests.test_database_api import run_post_rebuild_validation
        
        await run_post_rebuild_validation()
        return True
        
    except Exception as e:
        print(f"❌ Post-rebuild validation failed: {e}")
        return False

async def run_core_tests():
    """Run core ATR tests."""
    try:
        from backend.tests.test_atr_system_complete import (
            run_quick_tests,
            run_integration_tests,
            run_discord_tests,
            run_all_tests
        )
        
        return await run_all_tests()
        
    except Exception as e:
        print(f"❌ Core tests failed: {e}")
        return False

async def run_quick_tests_only():
    """Run quick tests only."""
    try:
        from backend.tests.test_atr_system_complete import run_quick_tests
        
        await run_quick_tests()
        return True
        
    except Exception as e:
        print(f"❌ Quick tests failed: {e}")
        return False

async def run_discord_tests_only():
    """Run Discord tests only."""
    try:
        from backend.tests.test_atr_system_complete import run_discord_tests
        
        await run_discord_tests()
        return True
        
    except Exception as e:
        print(f"❌ Discord tests failed: {e}")
        return False

async def run_integration_tests_only():
    """Run integration tests only."""
    try:
        from backend.tests.test_atr_system_complete import run_integration_tests
        
        await run_integration_tests()
        return True
        
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
        return False

async def run_model_tests_only():
    """Run model tests only."""
    try:
        from backend.tests.test_models import run_model_tests
        
        return run_model_tests()
        
    except Exception as e:
        print(f"❌ Model tests failed: {e}")
        return False

async def run_service_tests_only():
    """Run service tests only."""
    try:
        from backend.tests.test_services import run_service_tests
        
        return await run_service_tests()
        
    except Exception as e:
        print(f"❌ Service tests failed: {e}")
        return False

async def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='QuantMatrix ATR System Test Runner')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--discord', action='store_true', help='Run Discord tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--pre-rebuild', action='store_true', help='Run pre-rebuild validation')
    parser.add_argument('--post-rebuild', action='store_true', help='Run post-rebuild validation')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    print("🚀 QuantMatrix V1 - ATR System Test Suite")
    print("=" * 50)
    print(f"🕐 Started: {asyncio.get_event_loop().time()}")
    print("")
    
    try:
        success = False
        
        if args.pre_rebuild:
            print("🔍 Running Pre-Rebuild Validation...")
            success = await run_pre_rebuild_validation()
            
        elif args.post_rebuild:
            print("✅ Running Post-Rebuild Validation...")
            success = await run_post_rebuild_validation()
            
        elif args.quick:
            print("⚡ Running Quick Tests Only...")
            success = await run_quick_tests_only()
            
        elif args.discord:
            print("📢 Running Discord Tests Only...")
            success = await run_discord_tests_only()
            
        elif args.integration:
            print("🔗 Running Integration Tests Only...")
            success = await run_integration_tests_only()
            
        else:
            print("🎯 Running Complete Test Suite...")
            success = await run_core_tests()
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Your QuantMatrix ATR system is ready!")
            
            # Provide next steps based on test type
            if args.pre_rebuild:
                print("\n🎯 Next Step:")
                print("   ./backend/rebuild_db_docker.sh")
            elif args.post_rebuild:
                print("\n🚀 System is production ready!")
                print("   Start live trading automation!")
            else:
                print("✅ System validation complete!")
        else:
            print("\n❌ SOME TESTS FAILED!")
            print("🔧 Check the output above for issues to fix")
        
        return success
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 