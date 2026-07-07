# tests/run_tests.py
#!/usr/bin/env python
import pytest
import sys
import os
from datetime import datetime

def main():
    """Run all tests with comprehensive reporting"""
    
    # Set environment variables for testing
    os.environ['TEST_MODE'] = 'true'
    
    # Run tests with coverage
    args = [
        '-v',
        '--tb=short',
        '--maxfail=5',
        '--strict-markers',
        '--disable-warnings',
        '--cov=../app.py',
        '--cov-report=term-missing',
        '--cov-report=html:coverage_report',
        '--json-report',
        '--json-report-file=test_report.json'
    ]
    
    # Add markers to filter tests
    if len(sys.argv) > 1:
        if sys.argv[1] == '--functional':
            args.append('-m functional')
        elif sys.argv[1] == '--network':
            args.append('-m network')
        elif sys.argv[1] == '--performance':
            args.append('-m performance')
        elif sys.argv[1] == '--security':
            args.append('-m security')
        elif sys.argv[1] == '--quick':
            args.extend(['-k', 'not performance and not stress'])
    
    # Run pytest
    exit_code = pytest.main(args)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()