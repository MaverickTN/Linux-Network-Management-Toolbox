#!/usr/bin/env python3
"""
LNMT Test Configuration and Coverage System
Comprehensive test setup, fixtures, and coverage analysis
"""

import pytest
import os
import sys
import json
import tempfile
import sqlite3
import logging
from pathlib import Path
from unittest.mock import Mock, patch
import coverage
from datetime import datetime
import subprocess

# ==================== conftest.py content ====================

# Global test configuration for pytest
def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "fuzzing: mark test as fuzzing test"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Auto-mark tests based on file names
        if "security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "fuzzing" in item.nodeid:
            item.add_marker(pytest.mark.fuzzing)
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)

# ==================== Shared Fixtures ====================

@pytest.fixture(scope="session")
def test_database():
    """Create temporary test database"""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = db_file.name
    db_file.close()
    
    # Initialize test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables
    test_tables = [
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            permissions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE devices (
            mac_address TEXT PRIMARY KEY,
            ip_address TEXT,
            hostname TEXT,
            vlan_id INTEGER,
            last_seen TIMESTAMP,
            status TEXT DEFAULT 'unknown'
        )""",
        """CREATE TABLE dns_records (
            id INTEGER PRIMARY KEY,
            hostname TEXT,
            ip_address TEXT,
            record_type TEXT DEFAULT 'A',
            ttl INTEGER DEFAULT 3600,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE vlans (
            vlan_id INTEGER PRIMARY KEY,
            name TEXT,
            subnet TEXT,
            gateway TEXT,
            enabled BOOLEAN DEFAULT 1
        )""",
        """CREATE TABLE backups (
            id INTEGER PRIMARY KEY,
            backup_id TEXT UNIQUE,
            backup_type TEXT,
            file_path TEXT,
            size_bytes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE scheduled_jobs (
            id INTEGER PRIMARY KEY,
            job_id TEXT UNIQUE,
            schedule TEXT,
            command TEXT,
            enabled BOOLEAN DEFAULT 1,
            last_run TIMESTAMP,
            next_run TIMESTAMP
        )"""
    ]
    
    for table_sql in test_tables:
        cursor.execute(table_sql)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)

@pytest.fixture
def mock_network_interface():
    """Mock network interface for testing"""
    interface = Mock()
    interface.name = "eth0"
    interface.ip_address = "192.168.1.100"
    interface.mac_address = "aa:bb:cc:dd:ee:ff"
    interface.is_up = True
    interface.speed = 1000  # Mbps
    
    interface.scan_network.return_value = [
        {"ip": "192.168.1.1", "mac": "00:11:22:33:44:55", "hostname": "router.local"},
        {"ip": "192.168.1.10", "mac": "aa:bb:cc:dd:ee:01", "hostname": "device1.local"},
        {"ip": "192.168.1.20", "mac": "aa:bb:cc:dd:ee:02", "hostname": "device2.local"}
    ]
    
    return interface

@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "database": {
            "type": "sqlite",
            "path": ":memory:"
        },
        "authentication": {
            "secret_key": "test_secret_key_12345",
            "session_timeout": 3600,
            "max_login_attempts": 5,
            "rate_limit_window": 300
        },
        "dns": {
            "servers": ["8.8.8.8", "8.8.4.4"],
            "default_ttl": 3600,
            "enable_caching": True
        },
        "vlans": {
            "default_vlan": 1,
            "management_vlan": 100,
            "max_vlans": 4094
        },
        "backup": {
            "retention_days": 30,
            "compression": True,
            "encryption": True
        },
        "monitoring": {
            "check_interval": 60,
            "alert_threshold": 0.8,
            "enable_notifications": False  # Disable for tests
        },
        "web": {
            "host": "127.0.0.1",
            "port": 8080,
            "debug": True
        }
    }

@pytest.fixture
def mock_file_system():
    """Mock file system operations"""
    fs = Mock()
    fs.temp_dir = tempfile.mkdtemp()
    fs.config_dir = os.path.join(fs.temp_dir, "config")
    fs.data_dir = os.path.join(fs.temp_dir, "data")
    fs.backup_dir = os.path.join(fs.temp_dir, "backups")
    fs.log_dir = os.path.join(fs.temp_dir, "logs")
    
    # Create directories
    for directory in [fs.config_dir, fs.data_dir, fs.backup_dir, fs.log_dir]:
        os.makedirs(directory, exist_ok=True)
    
    def cleanup():
        import shutil
        shutil.rmtree(fs.temp_dir, ignore_errors=True)
    
    fs.cleanup = cleanup
    
    yield fs
    
    cleanup()

@pytest.fixture
def sample_devices():
    """Provide sample device data for testing"""
    return [
        {
            "mac": "aa:bb:cc:dd:ee:01",
            "ip": "192.168.1.101",
            "hostname": "workstation-01.local",
            "vlan_id": 100,
            "device_type": "computer",
            "vendor": "Dell Inc.",
            "last_seen": datetime.now().isoformat()
        },
        {
            "mac": "aa:bb:cc:dd:ee:02", 
            "ip": "192.168.1.102",
            "hostname": "printer-lobby.local",
            "vlan_id": 200,
            "device_type": "printer",
            "vendor": "HP",
            "last_seen": datetime.now().isoformat()
        },
        {
            "mac": "aa:bb:cc:dd:ee:03",
            "ip": "192.168.1.103",
            "hostname": "ap-office-1.local", 
            "vlan_id": 300,
            "device_type": "access_point",
            "vendor": "Ubiquiti",
            "last_seen": datetime.now().isoformat()
        }
    ]

@pytest.fixture
def sample_dns_records():
    """Provide sample DNS records for testing"""
    return [
        {"hostname": "gateway.local", "ip": "192.168.1.1", "type": "A"},
        {"hostname": "fileserver.local", "ip": "192.168.1.10", "type": "A"},
        {"hostname": "mail.local", "ip": "192.168.1.20", "type": "A"},
        {"hostname": "www.local", "ip": "192.168.1.30", "type": "A"},
        {"hostname": "local", "ip": "192.168.1.20", "type": "MX", "priority": 10}
    ]

@pytest.fixture
def sample_vlan_config():
    """Provide sample VLAN configuration for testing"""
    return [
        {"vlan_id": 1, "name": "default", "subnet": "192.168.1.0/24", "gateway": "192.168.1.1"},
        {"vlan_id": 100, "name": "workstations", "subnet": "192.168.100.0/24", "gateway": "192.168.100.1"},
@pytest.fixture
def sample_vlan_config():
    """Provide sample VLAN configuration for testing"""
    return [
        {"vlan_id": 1, "name": "default", "subnet": "192.168.1.0/24", "gateway": "192.168.1.1"},
        {"vlan_id": 100, "name": "workstations", "subnet": "192.168.100.0/24", "gateway": "192.168.100.1"},
        {"vlan_id": 200, "name": "printers", "subnet": "192.168.200.0/24", "gateway": "192.168.200.1"},
        {"vlan_id": 300, "name": "iot_devices", "subnet": "192.168.300.0/24", "gateway": "192.168.300.1"},
        {"vlan_id": 400, "name": "guest", "subnet": "192.168.400.0/24", "gateway": "192.168.400.1"}
    ]

@pytest.fixture
def mock_logger():
    """Provide mock logger for testing"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    
    # Capture log messages for assertions
    logger.messages = {
        'debug': [],
        'info': [],
        'warning': [], 
        'error': [],
        'critical': []
    }
    
    def capture_log(level, message):
        logger.messages[level].append(message)
    
    logger.debug.side_effect = lambda msg: capture_log('debug', msg)
    logger.info.side_effect = lambda msg: capture_log('info', msg)
    logger.warning.side_effect = lambda msg: capture_log('warning', msg)
    logger.error.side_effect = lambda msg: capture_log('error', msg)
    logger.critical.side_effect = lambda msg: capture_log('critical', msg)
    
    return logger

# ==================== Coverage Analysis System ====================

class LNMTCoverageAnalyzer:
    """Comprehensive coverage analysis for LNMT test suite"""
    
    def __init__(self, source_dirs=None, test_dirs=None):
        self.source_dirs = source_dirs or ['services/', 'cli/', 'web/', 'integration/']
        self.test_dirs = test_dirs or ['tests/']
        self.coverage = coverage.Coverage()
        self.results = {}
        
    def start_coverage(self):
        """Start coverage measurement"""
        self.coverage.start()
        
    def stop_coverage(self):
        """Stop coverage measurement"""
        self.coverage.stop()
        self.coverage.save()
        
    def generate_report(self, output_file='coverage_report.html'):
        """Generate comprehensive coverage report"""
        # Generate HTML report
        self.coverage.html_report(directory='htmlcov')
        
        # Generate XML report for CI
        self.coverage.xml_report(outfile='coverage.xml')
        
        # Generate detailed analysis
        analysis = self._analyze_coverage()
        
        # Save detailed report
        with open('coverage_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
            
        return analysis
    
    def _analyze_coverage(self):
        """Analyze coverage data and identify gaps"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'overall_coverage': 0,
            'module_coverage': {},
            'uncovered_lines': {},
            'critical_gaps': [],
            'recommendations': []
        }
        
        # Analyze each source file
        for source_dir in self.source_dirs:
            if os.path.exists(source_dir):
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            self._analyze_file_coverage(file_path, analysis)
        
        # Calculate overall coverage
        total_lines = sum(data.get('total_lines', 0) for data in analysis['module_coverage'].values())
        covered_lines = sum(data.get('covered_lines', 0) for data in analysis['module_coverage'].values())
        
        if total_lines > 0:
            analysis['overall_coverage'] = (covered_lines / total_lines) * 100
        
        # Identify critical gaps
        analysis['critical_gaps'] = self._identify_critical_gaps(analysis)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_file_coverage(self, file_path, analysis):
        """Analyze coverage for a specific file"""
        try:
            # Get coverage data for file
            file_data = self.coverage.analysis2(file_path)
            
            if file_data:
                executed_lines, missing_lines, excluded_lines, missing_branches = file_data[1:]
                
                total_lines = len(executed_lines) + len(missing_lines)
                covered_lines = len(executed_lines)
                coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0
                
                analysis['module_coverage'][file_path] = {
                    'total_lines': total_lines,
                    'covered_lines': covered_lines,
                    'coverage_percent': coverage_percent,
                    'missing_lines': list(missing_lines),
                    'missing_branches': missing_branches
                }
                
                if missing_lines:
                    analysis['uncovered_lines'][file_path] = list(missing_lines)
                    
        except Exception as e:
            # Handle files that can't be analyzed
            analysis['module_coverage'][file_path] = {
                'error': str(e),
                'coverage_percent': 0
            }
    
    def _identify_critical_gaps(self, analysis):
        """Identify critical coverage gaps"""
        gaps = []
        
        # Files with very low coverage
        for file_path, data in analysis['module_coverage'].items():
            coverage_percent = data.get('coverage_percent', 0)
            
            if coverage_percent < 50:  # Less than 50% coverage
                gaps.append({
                    'type': 'low_coverage',
                    'file': file_path,
                    'coverage': coverage_percent,
                    'severity': 'high' if coverage_percent < 25 else 'medium'
                })
        
        # Security-critical files with any missing coverage
        security_critical = ['auth_engine.py', 'authentication', 'security', 'crypto']
        for file_path, data in analysis['module_coverage'].items():
            if any(critical in file_path.lower() for critical in security_critical):
                if data.get('coverage_percent', 0) < 95:  # Security files should have >95% coverage
                    gaps.append({
                        'type': 'security_gap',
                        'file': file_path,
                        'coverage': data.get('coverage_percent', 0),
                        'severity': 'critical'
                    })
        
        return gaps
    
    def _generate_recommendations(self, analysis):
        """Generate testing recommendations based on coverage analysis"""
        recommendations = []
        
        # Low coverage recommendations
        low_coverage_files = [
            file_path for file_path, data in analysis['module_coverage'].items()
            if data.get('coverage_percent', 0) < 70
        ]
        
        if low_coverage_files:
            recommendations.append({
                'type': 'increase_coverage',
                'priority': 'high',
                'description': f'Increase test coverage for {len(low_coverage_files)} files with <70% coverage',
                'files': low_coverage_files[:5]  # Show top 5
            })
        
        # Missing test categories
        existing_tests = []
        for test_dir in self.test_dirs:
            if os.path.exists(test_dir):
                for root, dirs, files in os.walk(test_dir):
                    existing_tests.extend([f for f in files if f.endswith('.py')])
        
        needed_test_types = []
        if not any('security' in test for test in existing_tests):
            needed_test_types.append('security')
        if not any('performance' in test for test in existing_tests):
            needed_test_types.append('performance')
        if not any('integration' in test for test in existing_tests):
            needed_test_types.append('integration')
        
        if needed_test_types:
            recommendations.append({
                'type': 'add_test_categories',
                'priority': 'medium',
                'description': f'Add missing test categories: {", ".join(needed_test_types)}',
                'categories': needed_test_types
            })
        
        return recommendations

# ==================== Test Data Generators ====================

class TestDataGenerator:
    """Generate realistic test data for LNMT testing"""
    
    @staticmethod
    def generate_devices(count=10):
        """Generate realistic device test data"""
        import random
        
        vendors = ['Dell Inc.', 'HP', 'Lenovo', 'Apple', 'Cisco', 'Ubiquiti', 'Netgear', 'D-Link']
        device_types = ['computer', 'printer', 'router', 'switch', 'access_point', 'phone', 'tablet']
        
        devices = []
        for i in range(count):
            mac = ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)])
            ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            
            devices.append({
                'mac': mac,
                'ip': ip,
                'hostname': f'device-{i:03d}.local',
                'vlan_id': random.choice([1, 100, 200, 300]),
                'device_type': random.choice(device_types),
                'vendor': random.choice(vendors),
                'last_seen': datetime.now().isoformat()
            })
        
        return devices
    
    @staticmethod
    def generate_dns_records(count=20):
        """Generate realistic DNS record test data"""
        import random
        
        record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT']
        subdomains = ['www', 'mail', 'ftp', 'api', 'admin', 'test', 'dev', 'staging']
        
        records = []
        for i in range(count):
            if i < 5:  # Always include some basic records
                hostname = ['gateway', 'router', 'fileserver', 'printserver', 'mailserver'][i] + '.local'
                ip = f"192.168.1.{i+1}"
                record_type = 'A'
            else:
                hostname = f"{random.choice(subdomains)}-{i}.local"
                ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
                record_type = random.choice(record_types)
            
            records.append({
                'hostname': hostname,
                'ip': ip,
                'type': record_type,
                'ttl': random.choice([300, 600, 1800, 3600])
            })
        
        return records
    
    @staticmethod
    def generate_users(count=5):
        """Generate test user accounts"""
        import random
        import hashlib
        
        roles = ['admin', 'operator', 'viewer', 'guest']
        
        users = []
        for i in range(count):
            username = f'user{i:02d}'
            password = f'password{i:02d}'
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            users.append({
                'username': username,
                'password_hash': password_hash,
                'role': random.choice(roles),
                'permissions': json.dumps(['device_read', 'dns_read'] if i > 0 else ['admin']),
                'created_at': datetime.now().isoformat()
            })
        
        return users

# ==================== Test Utilities ====================

class TestUtilities:
    """Utility functions for LNMT testing"""
    
    @staticmethod
    def assert_valid_ip(ip_address):
        """Assert that an IP address is valid"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def assert_valid_mac(mac_address):
        """Assert that a MAC address is valid"""
        import re
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})
        return re.match(pattern, mac_address) is not None
    
    @staticmethod
    def assert_valid_hostname(hostname):
        """Assert that a hostname is valid"""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*
        return re.match(pattern, hostname) is not None
    
    @staticmethod
    def wait_for_condition(condition_func, timeout=10, interval=0.1):
        """Wait for a condition to become true"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        
        return False
    
    @staticmethod
    def capture_logs(logger, level='INFO'):
        """Capture log messages during test execution"""
        class LogCapture:
            def __init__(self):
                self.messages = []
            
            def emit(self, record):
                self.messages.append(record.getMessage())
        
        capture = LogCapture()
        handler = logging.StreamHandler()
        handler.emit = capture.emit
        
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level))
        
        return capture

# ==================== Performance Test Utilities ====================

class PerformanceTestUtils:
    """Utilities for performance testing"""
    
    @staticmethod
    def time_function(func, *args, **kwargs):
        """Time function execution"""
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    
    @staticmethod
    def memory_usage_monitor():
        """Monitor memory usage during test"""
        import psutil
        import threading
        import time
        
        measurements = []
        stop_monitoring = threading.Event()
        
        def monitor():
            process = psutil.Process()
            while not stop_monitoring.is_set():
                measurements.append(process.memory_info().rss / 1024 / 1024)  # MB
                time.sleep(0.1)
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.start()
        
        class MemoryMonitor:
            def stop(self):
                stop_monitoring.set()
                monitor_thread.join()
                return {
                    'peak_memory_mb': max(measurements) if measurements else 0,
                    'avg_memory_mb': sum(measurements) / len(measurements) if measurements else 0,
                    'measurements': measurements
                }
        
        return MemoryMonitor()
    
    @staticmethod
    def stress_test_decorator(iterations=100, concurrent=False):
        """Decorator for stress testing functions"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if concurrent:
                    import threading
                    import queue
                    
                    results = queue.Queue()
                    threads = []
                    
                    def run_test():
                        try:
                            result = func(*args, **kwargs)
                            results.put(('success', result))
                        except Exception as e:
                            results.put(('error', str(e)))
                    
                    # Start concurrent executions
                    for _ in range(iterations):
                        thread = threading.Thread(target=run_test)
                        threads.append(thread)
                        thread.start()
                    
                    # Wait for completion
                    for thread in threads:
                        thread.join()
                    
                    # Collect results
                    successes = 0
                    errors = []
                    while not results.empty():
                        status, result = results.get()
                        if status == 'success':
                            successes += 1
                        else:
                            errors.append(result)
                    
                    return {
                        'iterations': iterations,
                        'successes': successes,
                        'errors': errors,
                        'success_rate': successes / iterations
                    }
                else:
                    # Sequential execution
                    results = []
                    for i in range(iterations):
                        try:
                            result = func(*args, **kwargs)
                            results.append(('success', result))
                        except Exception as e:
                            results.append(('error', str(e)))
                    
                    successes = sum(1 for status, _ in results if status == 'success')
                    return {
                        'iterations': iterations,
                        'successes': successes,
                        'success_rate': successes / iterations,
                        'results': results
                    }
            
            return wrapper
        return decorator

# ==================== Test Execution Manager ====================

class TestExecutionManager:
    """Manage test execution and reporting"""
    
    def __init__(self, test_dirs=None):
        self.test_dirs = test_dirs or ['tests/']
        self.coverage_analyzer = LNMTCoverageAnalyzer()
        
    def run_test_suite(self, test_categories=None, generate_coverage=True):
        """Run complete test suite with coverage analysis"""
        if generate_coverage:
            self.coverage_analyzer.start_coverage()
        
        # Build pytest arguments
        pytest_args = ['-v', '--tb=short']
        
        if test_categories:
            # Add markers for specific test categories
            marker_expr = ' or '.join(test_categories)
            pytest_args.extend(['-m', marker_expr])
        
        # Add test directories
        pytest_args.extend(self.test_dirs)
        
        # Run tests
        exit_code = pytest.main(pytest_args)
        
        if generate_coverage:
            self.coverage_analyzer.stop_coverage()
            coverage_report = self.coverage_analyzer.generate_report()
            
            return {
                'exit_code': exit_code,
                'coverage_report': coverage_report
            }
        
        return {'exit_code': exit_code}
    
    def run_security_tests(self):
        """Run security-focused tests"""
        return self.run_test_suite(['security'])
    
    def run_performance_tests(self):
        """Run performance tests"""
        return self.run_test_suite(['performance'])
    
    def run_integration_tests(self):
        """Run integration tests"""
        return self.run_test_suite(['integration'])
    
    def generate_summary_report(self, results):
        """Generate comprehensive test summary report"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'test_results': results,
            'recommendations': [],
            'next_steps': []
        }
        
        # Analyze results and generate recommendations
        if results.get('exit_code', 0) != 0:
            summary['recommendations'].append(
                'Some tests failed - review test output and fix failing tests'
            )
        
        coverage_report = results.get('coverage_report', {})
        overall_coverage = coverage_report.get('overall_coverage', 0)
        
        if overall_coverage < 80:
            summary['recommendations'].append(
                f'Test coverage is {overall_coverage:.1f}% - aim for >80% coverage'
            )
        
        critical_gaps = coverage_report.get('critical_gaps', [])
        if critical_gaps:
            summary['recommendations'].append(
                f'Address {len(critical_gaps)} critical coverage gaps'
            )
        
        # Next steps
        summary['next_steps'] = [
            'Review coverage report and identify untested code paths',
            'Add tests for edge cases and error conditions',
            'Implement missing security and integration tests',
            'Set up continuous integration with automated testing',
            'Regularly review and update test suite'
        ]
        
        return summary

if __name__ == '__main__':
    # Example usage
    manager = TestExecutionManager()
    
    print("Running LNMT Test Suite...")
    results = manager.run_test_suite()
    
    print(f"Tests completed with exit code: {results['exit_code']}")
    
    if 'coverage_report' in results:
        coverage = results['coverage_report']['overall_coverage']
        print(f"Overall test coverage: {coverage:.1f}%")
    
    # Generate summary
    summary = manager.generate_summary_report(results)
    
    with open('test_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("Test summary saved to test_summary.json")
