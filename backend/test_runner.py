#!/usr/bin/env python3
"""
Automated Test Runner with File Watching
Runs tests automatically when files change to catch issues immediately.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class TestRunner(FileSystemEventHandler):
    """File system event handler that runs tests when files change."""
    
    def __init__(self, test_pattern="test_portfolio_sync.py", debounce_seconds=2):
        self.test_pattern = test_pattern
        self.debounce_seconds = debounce_seconds
        self.last_run = 0
        self.test_queue = set()
        
    def should_run_tests(self, file_path):
        """Determine if tests should run based on file changes."""
        file_path = Path(file_path)
        
        # Run tests for Python files in these directories
        relevant_paths = [
            'backend/api/',
            'backend/services/', 
            'backend/models/',
            'backend/',
        ]
        
        # Skip certain files
        skip_patterns = [
            '__pycache__',
            '.pyc',
            '.git',
            'logs/',
            '.pytest_cache',
            'htmlcov/'
        ]
        
        # Check if file should trigger tests
        str_path = str(file_path)
        for skip in skip_patterns:
            if skip in str_path:
                return False
                
        for relevant in relevant_paths:
            if relevant in str_path and str_path.endswith('.py'):
                return True
                
        return False
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not isinstance(event, FileModifiedEvent):
            return
            
        if self.should_run_tests(event.src_path):
            self.test_queue.add(event.src_path)
            self.schedule_test_run()
    
    def on_created(self, event):
        """Handle file creation events.""" 
        if not isinstance(event, FileCreatedEvent):
            return
            
        if self.should_run_tests(event.src_path):
            self.test_queue.add(event.src_path)
            self.schedule_test_run()
    
    def schedule_test_run(self):
        """Schedule a test run with debouncing to avoid excessive runs."""
        current_time = time.time()
        if current_time - self.last_run >= self.debounce_seconds:
            self.run_tests()
        
    def run_tests(self):
        """Run the test suite."""
        self.last_run = time.time()
        
        if self.test_queue:
            changed_files = list(self.test_queue)
            self.test_queue.clear()
            
            logger.info(f"🧪 Files changed: {[Path(f).name for f in changed_files]}")
            logger.info("🚀 Running tests...")
            
            try:
                # Run tests with coverage
                cmd = [
                    'python', '-m', 'pytest', 
                    self.test_pattern,
                    '-v',
                    '--tb=short',
                    '--durations=5',
                    '-x'  # Stop on first failure
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    cwd=Path(__file__).parent
                )
                
                if result.returncode == 0:
                    logger.info("✅ All tests passed!")
                    print(result.stdout)
                else:
                    logger.error("❌ Tests failed!")
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
                    
                    # Also run a quick smoke test on the API
                    self.run_api_smoke_test()
                    
            except Exception as e:
                logger.error(f"Error running tests: {e}")
                
    def run_api_smoke_test(self):
        """Run a quick smoke test on the API endpoints."""
        logger.info("🔍 Running API smoke test...")
        
        try:
            import requests
            import time
            
            # Wait a moment for any server restarts
            time.sleep(1)
            
            # Test critical endpoints
            endpoints = [
                "http://localhost:8000/health",
                "http://localhost:8000/api/v1/portfolio/live",
                "http://localhost:8000/api/v1/options/unified/portfolio"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"✅ {endpoint} - OK")
                    else:
                        logger.warning(f"⚠️  {endpoint} - {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ {endpoint} - {e}")
                    
        except ImportError:
            logger.info("💡 Install requests for API smoke tests: pip install requests")
        except Exception as e:
            logger.error(f"Error in smoke test: {e}")

def main():
    """Main function to start the test runner."""
    parser = argparse.ArgumentParser(description='Automated test runner with file watching')
    parser.add_argument('--test-pattern', default='test_portfolio_sync.py', 
                       help='Test file pattern to run')
    parser.add_argument('--debounce', type=int, default=2,
                       help='Debounce time in seconds between test runs')
    parser.add_argument('--run-once', action='store_true',
                       help='Run tests once and exit')
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Initialize test runner
    test_runner = TestRunner(args.test_pattern, args.debounce)
    
    if args.run_once:
        logger.info("Running tests once...")
        test_runner.test_queue.add("manual_run")
        test_runner.run_tests()
        return
    
    # Setup file watcher
    observer = Observer()
    observer.schedule(test_runner, path='.', recursive=True)
    observer.start()
    
    logger.info("🔍 Watching for file changes...")
    logger.info("📁 Monitoring: backend/api/, backend/services/, backend/models/")
    logger.info("🧪 Test pattern: " + args.test_pattern)
    logger.info("⏱️  Debounce: " + str(args.debounce) + "s")
    logger.info("🛑 Press Ctrl+C to stop")
    
    # Run initial test
    logger.info("🚀 Running initial tests...")
    test_runner.test_queue.add("initial_run")
    test_runner.run_tests()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Stopping test runner...")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main() 