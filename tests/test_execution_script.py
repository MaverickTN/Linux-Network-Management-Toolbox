#!/usr/bin/env python3
"""
LNMT Test Suite Execution Script
Comprehensive test runner with coverage analysis and reporting
"""

import os
import sys
import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

def setup_test_environment():
    """Setup test environment and dependencies"""
    print("🔧 Setting up test environment...")
    
    # Ensure test directories exist
    test_dirs = ['tests/unit', 'tests/integration', 'tests/security', 'tests/performance', 'tests/fixtures']
    for directory in test_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        
    # Create __init__.py files
    for directory in test_dirs:
        init_file = Path(directory) / '__init__.py'
        if not init_file.exists():
            init_file.touch()
    
    # Install test dependencies
    test_requirements = [
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
        'pytest-xdist>=3.0.0',  # Parallel test execution
        'pytest-html>=3.0.0',   # HTML reports
        'coverage>=7.0.0',
        'httpx>=0.24.0',        # API testing
        'psutil>=5.9.0',        # Performance monitoring
        'faker>=18.0.0',        # Test data generation
    ]
    
    print("📦 Installing test dependencies...")
    for requirement in test_requirements:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', requirement], 
                         check=True, capture_output=True)
            print(f"   ✓ {requirement}")
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Failed to install {requirement}: {e}")
            return False
    
    return True

def run_security_tests():
    """Run security-focused tests"""
    print("🔒 Running security tests...")
    
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '-m', 'security',
        '-v',
        '--tb=short',
        '--html=reports/security_report.html',
        '--self-contained-html'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'report_file': 'reports/security_report.html'
    }

def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running integration tests...")
    
    cmd = [
        'python', '-m', 'pytest', 
        'tests/',
        '-m', 'integration',
        '-v',
        '--tb=short',
        '--html=reports/integration_report.html',
        '--self-contained-html'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'report_file': 'reports/integration_report.html'
    }

def run_performance_tests():
    """Run performance tests"""
    print("⚡ Running performance tests...")
    
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '-m', 'performance', 
        '-v',
        '--tb=short',
        '--html=reports/performance_report.html',
        '--self-contained-html'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout, 
        'stderr': result.stderr,
        'report_file': 'reports/performance_report.html'
    }

def run_fuzzing_tests():
    """Run fuzzing tests"""
    print("🎯 Running fuzzing tests...")
    
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '-m', 'fuzzing',
        '-v', 
        '--tb=short',
        '--html=reports/fuzzing_report.html',
        '--self-contained-html'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'report_file': 'reports/fuzzing_report.html'
    }

def run_coverage_analysis():
    """Run comprehensive coverage analysis"""
    print("📊 Running coverage analysis...")
    
    # Ensure reports directory exists
    Path('reports').mkdir(exist_ok=True)
    
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '--cov=services',
        '--cov=cli', 
        '--cov=web',
        '--cov=integration',
        '--cov-report=html:reports/coverage_html',
        '--cov-report=xml:reports/coverage.xml',
        '--cov-report=json:reports/coverage.json',
        '--cov-report=term-missing',
        '--cov-fail-under=70',  # Fail if coverage below 70%
        '-v'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse coverage data
    coverage_data = {}
    try:
        with open('reports/coverage.json', 'r') as f:
            coverage_data = json.load(f)
    except FileNotFoundError:
        pass
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'coverage_data': coverage_data,
        'html_report': 'reports/coverage_html/index.html'
    }

def run_unit_tests():
    """Run unit tests for all modules"""
    print("🧪 Running unit tests...")
    
    cmd = [
        'python', '-m', 'pytest',
        'tests/',
        '-m', 'unit or not (integration or security or performance or fuzzing)',
        '-v',
        '--tb=short',
        '--html=reports/unit_test_report.html',
        '--self-contained-html',
        '--maxfail=10'  # Stop after 10 failures
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'report_file': 'reports/unit_test_report.html'
    }

def analyze_test_failures(test_results):
    """Analyze test failures and provide insights"""
    failures = []
    
    for test_type, results in test_results.items():
        if results['exit_code'] != 0:
            failure_analysis = {
                'test_type': test_type,
                'exit_code': results['exit_code'],
                'stderr_summary': results['stderr'][:500] if results['stderr'] else '',
                'potential_causes': []
            }
            
            stderr = results['stderr'].lower()
            
            # Analyze common failure patterns
            if 'importerror' in stderr or 'modulenotfounderror' in stderr:
                failure_analysis['potential_causes'].append('Missing dependencies or import issues')
            
            if 'assertionerror' in stderr:
                failure_analysis['potential_causes'].append('Test assertions failed - logic errors')
                
            if 'timeout' in stderr:
                failure_analysis['potential_causes'].append('Tests timed out - performance issues')
                
            if 'permission' in stderr:
                failure_analysis['potential_causes'].append('Permission issues with test files/directories')
                
            if 'connection' in stderr:
                failure_analysis['potential_causes'].append('Network or database connection issues')
            
            failures.append(failure_analysis)
    
    return failures

def generate_comprehensive_report(test_results, coverage_results):
    """Generate comprehensive test execution report"""
    report = {
        'execution_info': {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd()
        },
        'test_results': test_results,
        'coverage_results': coverage_results,
        'summary': {
            'total_test_types': len(test_results),
            'passed_test_types': sum(1 for r in test_results.values() if r['exit_code'] == 0),
            'failed_test_types': sum(1 for r in test_results.values() if r['exit_code'] != 0),
            'overall_coverage': coverage_results.get('coverage_data', {}).get('totals', {}).get('percent_covered', 0)
        },
        'failure_analysis': analyze_test_failures(test_results),
        'recommendations': [],
        'next_steps': []
    }
    
    # Generate recommendations based on results
    if report['summary']['failed_test_types'] > 0:
        report['recommendations'].append('Address failing tests before deployment')
    
    if report['summary']['overall_coverage'] < 80:
        report['recommendations'].append('Increase test coverage to at least 80%')
    
    if not any('security' in str(r) for r in test_results.keys()):
        report['recommendations'].append('Add comprehensive security testing')
    
    # Generate next steps
    report['next_steps'] = [
        'Review all test reports in the reports/ directory',
        'Address any failing tests identified in the failure analysis',
        'Implement missing tests for uncovered code paths',
        'Set up automated test execution in CI/CD pipeline',
        'Schedule regular test suite maintenance and updates'
    ]
    
    return report

def create_test_documentation():
    """Create comprehensive test documentation"""
    documentation = """
# LNMT Test Suite Documentation

## Overview
The LNMT test suite provides comprehensive testing for all system components including:
- **Unit Tests**: Individual module functionality
- **Integration Tests**: Cross-module interactions and workflows
- **Security Tests**: Authentication, authorization, and attack prevention
- **Performance Tests**: Load testing and resource usage
- **Fuzzing Tests**: Input validation and edge case handling

## Test Structure
```
tests/
├── unit/                    # Unit tests for individual modules
│   ├── test_auth_engine.py
│   ├── test_dns_manager.py
│   ├── test_vlan_controller.py
│   └── ...
├── integration/            # Integration and workflow tests
│   ├── test_dns_vlan_integration.py
│   ├── test_backup_workflows.py
│   └── ...
├── security/              # Security-focused tests
│   ├── test_auth_security.py
│   ├── test_input_validation.py
│   └── ...
├── performance/           # Performance and load tests
│   ├── test_api_performance.py
│   ├── test_concurrent_operations.py
│   └── ...
├── fixtures/              # Shared test data and utilities
│   ├── sample_data.py
│   ├── mock_objects.py
│   └── ...
└── conftest.py           # Pytest configuration and shared fixtures
```

## Running Tests

### All Tests with Coverage
```bash
python test_runner.py --all --coverage
```

### Specific Test Categories
```bash
python test_runner.py --security     # Security tests only
python test_runner.py --integration  # Integration tests only
python test_runner.py --performance  # Performance tests only
python test_runner.py --fuzzing      # Fuzzing tests only
```

### Individual Test Files
```bash
pytest tests/unit/test_auth_engine.py -v
pytest tests/security/ -v
```

## Test Markers
Tests are categorized using pytest markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.fuzzing` - Fuzzing tests
- `@pytest.mark.slow` - Long-running tests

## Coverage Requirements
- **Overall Coverage**: Minimum 80%
- **Security Modules**: Minimum 95%
- **Critical Services**: Minimum 90%
- **CLI Tools**: Minimum 85%

## Test Data
Test data is generated using:
- **Fixtures**: Pytest fixtures for consistent test data
- **Factories**: Dynamic test data generation
- **Mocks**: Isolated component testing

## Continuous Integration
Tests should be run:
- On every commit (unit and security tests)
- On pull requests (full test suite)
- Nightly (performance and fuzzing tests)
- Before releases (comprehensive test suite)

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure PYTHONPATH includes LNMT source directories
2. **Permission Errors**: Run tests with appropriate file permissions
3. **Database Errors**: Ensure test database is accessible
4. **Network Errors**: Mock external dependencies in tests

### Performance Issues
1. **Slow Tests**: Use `--maxfail=N` to stop after N failures
2. **Parallel Execution**: Use `pytest-xdist` for parallel test runs
3. **Memory Usage**: Monitor memory with performance tests

## Reporting
Test reports are generated in the `reports/` directory:
- `coverage_html/index.html` - Coverage report
- `security_report.html` - Security test results
- `integration_report.html` - Integration test results
- `performance_report.html` - Performance test results
- `test_summary.json` - Comprehensive test summary
"""
    
    with open('TEST_DOCUMENTATION.md', 'w') as f:
        f.write(documentation)
    
    return 'TEST_DOCUMENTATION.md'

def main():
    """Main test execution function"""
    parser = argparse.ArgumentParser(description='LNMT Test Suite Runner')
    parser.add_argument('--all', action='store_true', help='Run all test categories')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--fuzzing', action='store_true', help='Run fuzzing tests')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--setup', action='store_true', help='Setup test environment')
    parser.add_argument('--docs', action='store_true', help='Generate test documentation')
    
    args = parser.parse_args()
    
    # Setup environment if requested
    if args.setup:
        if not setup_test_environment():
            print("❌ Failed to setup test environment")
            return 1
        print("✅ Test environment setup complete")
    
    # Generate documentation if requested
    if args.docs:
        doc_file = create_test_documentation()
        print(f"📝 Test documentation generated: {doc_file}")
    
    # If no specific tests requested, show help
    if not any([args.all, args.unit, args.integration, args.security, 
               args.performance, args.fuzzing, args.coverage]):
        parser.print_help()
        return 0
    
    # Ensure reports directory exists
    Path('reports').mkdir(exist_ok=True)
    
    print("🚀 Starting LNMT Test Suite Execution")
    print("=" * 50)
    
    start_time = time.time()
    test_results = {}
    coverage_results = {}
    
    # Run requested test categories
    if args.all or args.unit:
        test_results['unit'] = run_unit_tests()
    
    if args.all or args.integration:
        test_results['integration'] = run_integration_tests()
    
    if args.all or args.security:
        test_results['security'] = run_security_tests()
    
    if args.all or args.performance:
        test_results['performance'] = run_performance_tests()
    
    if args.all or args.fuzzing:
        test_results['fuzzing'] = run_fuzzing_tests()
    
    # Run coverage analysis if requested
    if args.all or args.coverage:
        coverage_results = run_coverage_analysis()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print("\n" + "=" * 50)
    print(f"⏱️  Total execution time: {execution_time:.2f} seconds")
    
    # Generate comprehensive report
    report = generate_comprehensive_report(test_results, coverage_results)
    
    # Save report
    with open('reports/test_execution_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n📊 Test Execution Summary:")
    print(f"   Test Types Run: {report['summary']['total_test_types']}")
    print(f"   Passed: {report['summary']['passed_test_types']}")
    print(f"   Failed: {report['summary']['failed_test_types']}")
    
    if coverage_results:
        coverage_percent = report['summary']['overall_coverage']
        print(f"   Coverage: {coverage_percent:.1f}%")
    
    # Print recommendations
    if report['recommendations']:
        print("\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
    
    # Print failure analysis
    if report['failure_analysis']:
        print("\n❌ Failure Analysis:")
        for failure in report['failure_analysis']:
            print(f"   • {failure['test_type']}: {failure['potential_causes']}")
    
    print(f"\n📁 Detailed reports available in: reports/")
    print("   • test_execution_report.json - Comprehensive summary")
    
    if coverage_results and 'html_report' in coverage_results:
        print(f"   • {coverage_results['html_report']} - Coverage report")
    
    for test_type, results in test_results.items():
        if 'report_file' in results:
            print(f"   • {results['report_file']} - {test_type.title()} test report")
    
    # Return appropriate exit code
    overall_success = report['summary']['failed_test_types'] == 0
    
    if overall_success:
        print("\n✅ All tests passed successfully!")
        return 0
    else:
        print(f"\n❌ {report['summary']['failed_test_types']} test categories failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
