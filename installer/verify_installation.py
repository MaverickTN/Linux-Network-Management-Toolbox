#!/usr/bin/env python3
"""
LNMT Installation Verification Script
Validates that LNMT has been installed correctly
"""

import os
import sys
import time
import json
import requests
import subprocess
import socket
from pathlib import Path
from urllib.parse import urljoin
from colorama import init, Fore, Style

init(autoreset=True)

class InstallationVerifier:
    """Verify LNMT installation"""
    
    def __init__(self, base_url="http://localhost:8080", timeout=30):
        self.base_url = base_url
        self.timeout = timeout
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def add_result(self, category, message):
        """Add a test result"""
        self.results[category].append(message)
        
    def check_service_status(self):
        """Check systemd service status"""
        print(f"Starting verification at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all checks
        self.check_service_status()
        self.check_ports()
        self.check_directories()
        self.check_configuration()
        self.check_permissions()
        self.check_web_interface()
        self.check_api_health()
        self.check_database()
        self.test_api_endpoints()
        
        # Generate report
        return self.generate_report()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify LNMT installation')
    parser.add_argument(
        '--url',
        default='http://localhost:8080',
        help='LNMT base URL (default: http://localhost:8080)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Run verification
    verifier = InstallationVerifier(args.url, args.timeout)
    success = verifier.run_verification()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    main()(f"\n{Fore.CYAN}Checking services...{Style.RESET_ALL}")
        
        services = {
            'lnmt': 'Main LNMT service',
            'lnmt-scheduler': 'Scheduler service',
            'lnmt-health': 'Health monitor service',
            'postgresql': 'PostgreSQL database',
            'redis': 'Redis cache'
        }
        
        for service, description in services.items():
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout.strip() == 'active':
                    self.add_result('passed', f"{description} ({service}) is running")
                    print(f"  ✓ {description} is running")
                else:
                    if service.startswith('lnmt'):
                        self.add_result('failed', f"{description} ({service}) is not running")
                        print(f"  ✗ {description} is not running")
                    else:
                        self.add_result('warnings', f"{description} ({service}) is not running")
                        print(f"  ⚠ {description} is not running")
                        
            except FileNotFoundError:
                self.add_result('warnings', "systemctl not found - not running under systemd")
                print("  ⚠ systemctl not found - skipping service checks")
                break
                
    def check_ports(self):
        """Check if services are listening on expected ports"""
        print(f"\n{Fore.CYAN}Checking network ports...{Style.RESET_ALL}")
        
        ports = {
            8080: 'LNMT Web Interface',
            5432: 'PostgreSQL',
            6379: 'Redis',
            9090: 'Metrics endpoint'
        }
        
        for port, service in ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                self.add_result('passed', f"{service} is listening on port {port}")
                print(f"  ✓ {service} is listening on port {port}")
            else:
                if port == 8080:
                    self.add_result('failed', f"{service} is not listening on port {port}")
                    print(f"  ✗ {service} is not listening on port {port}")
                else:
                    self.add_result('warnings', f"{service} is not listening on port {port}")
                    print(f"  ⚠ {service} is not listening on port {port}")
                    
    def check_api_health(self):
        """Check API health endpoint"""
        print(f"\n{Fore.CYAN}Checking API health...{Style.RESET_ALL}")
        
        try:
            response = requests.get(
                urljoin(self.base_url, '/health'),
                timeout=5
            )
            
            if response.status_code == 200:
                health_data = response.json()
                
                # Check overall status
                if health_data.get('status') == 'healthy':
                    self.add_result('passed', "API health check passed")
                    print("  ✓ API is healthy")
                else:
                    self.add_result('failed', f"API health check failed: {health_data.get('status')}")
                    print(f"  ✗ API health status: {health_data.get('status')}")
                    
                # Check individual components
                components = health_data.get('components', {})
                for component, status in components.items():
                    if status.get('status') == 'healthy':
                        print(f"    ✓ {component}: healthy")
                    else:
                        print(f"    ✗ {component}: {status.get('status')}")
                        
            else:
                self.add_result('failed', f"API health check returned status {response.status_code}")
                print(f"  ✗ API health check failed (HTTP {response.status_code})")
                
        except requests.exceptions.ConnectionError:
            self.add_result('failed', "Cannot connect to LNMT API")
            print("  ✗ Cannot connect to LNMT API")
        except Exception as e:
            self.add_result('failed', f"API health check error: {str(e)}")
            print(f"  ✗ API health check error: {str(e)}")
            
    def check_web_interface(self):
        """Check if web interface is accessible"""
        print(f"\n{Fore.CYAN}Checking web interface...{Style.RESET_ALL}")
        
        try:
            response = requests.get(self.base_url, timeout=5)
            
            if response.status_code == 200:
                if 'LNMT' in response.text or 'Local Network Management Tool' in response.text:
                    self.add_result('passed', "Web interface is accessible")
                    print("  ✓ Web interface is accessible")
                else:
                    self.add_result('warnings', "Web interface returned unexpected content")
                    print("  ⚠ Web interface returned unexpected content")
            else:
                self.add_result('failed', f"Web interface returned status {response.status_code}")
                print(f"  ✗ Web interface returned HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.add_result('failed', "Cannot connect to web interface")
            print("  ✗ Cannot connect to web interface")
        except Exception as e:
            self.add_result('failed', f"Web interface check error: {str(e)}")
            print(f"  ✗ Web interface error: {str(e)}")
            
    def check_directories(self):
        """Check if required directories exist"""
        print(f"\n{Fore.CYAN}Checking directories...{Style.RESET_ALL}")
        
        directories = {
            '/etc/lnmt': 'Configuration directory',
            '/var/lib/lnmt': 'Data directory',
            '/var/log/lnmt': 'Log directory',
            '/var/backups/lnmt': 'Backup directory',
            '/opt/lnmt': 'Application directory'
        }
        
        for directory, description in directories.items():
            path = Path(directory)
            if path.exists():
                if os.access(directory, os.R_OK):
                    self.add_result('passed', f"{description} exists and is readable")
                    print(f"  ✓ {description} exists")
                else:
                    self.add_result('warnings', f"{description} exists but is not readable")
                    print(f"  ⚠ {description} exists but is not readable")
            else:
                self.add_result('failed', f"{description} does not exist")
                print(f"  ✗ {description} does not exist")
                
    def check_configuration(self):
        """Check configuration files"""
        print(f"\n{Fore.CYAN}Checking configuration...{Style.RESET_ALL}")
        
        config_files = {
            '/etc/lnmt/config.yml': 'Main configuration',
            '/etc/lnmt/lnmt.env': 'Environment variables',
            '/etc/lnmt/logging.conf': 'Logging configuration'
        }
        
        for config_file, description in config_files.items():
            path = Path(config_file)
            if path.exists():
                self.add_result('passed', f"{description} exists")
                print(f"  ✓ {description} exists")
            else:
                if config_file == '/etc/lnmt/config.yml':
                    self.add_result('failed', f"{description} not found")
                    print(f"  ✗ {description} not found")
                else:
                    self.add_result('warnings', f"{description} not found")
                    print(f"  ⚠ {description} not found")
                    
    def check_database(self):
        """Check database connectivity and schema"""
        print(f"\n{Fore.CYAN}Checking database...{Style.RESET_ALL}")
        
        try:
            response = requests.get(
                urljoin(self.base_url, '/api/v1/system/database-status'),
                timeout=5
            )
            
            if response.status_code == 200:
                db_status = response.json()
                if db_status.get('connected'):
                    self.add_result('passed', "Database connection successful")
                    print("  ✓ Database connection successful")
                    
                    # Check tables
                    tables = db_status.get('tables', [])
                    expected_tables = ['users', 'devices', 'vlans', 'audit_logs']
                    
                    for table in expected_tables:
                        if table in tables:
                            print(f"    ✓ Table '{table}' exists")
                        else:
                            self.add_result('warnings', f"Table '{table}' not found")
                            print(f"    ⚠ Table '{table}' not found")
                else:
                    self.add_result('failed', "Database connection failed")
                    print("  ✗ Database connection failed")
            else:
                self.add_result('warnings', "Cannot check database status via API")
                print("  ⚠ Cannot check database status via API")
                
        except Exception as e:
            self.add_result('warnings', f"Database check error: {str(e)}")
            print(f"  ⚠ Database check skipped: {str(e)}")
            
    def check_permissions(self):
        """Check file and directory permissions"""
        print(f"\n{Fore.CYAN}Checking permissions...{Style.RESET_ALL}")
        
        # Check LNMT user
        try:
            result = subprocess.run(['id', 'lnmt'], capture_output=True, text=True)
            if result.returncode == 0:
                self.add_result('passed', "LNMT user exists")
                print("  ✓ LNMT user exists")
            else:
                self.add_result('warnings', "LNMT user does not exist")
                print("  ⚠ LNMT user does not exist")
        except Exception:
            self.add_result('warnings', "Cannot check LNMT user")
            print("  ⚠ Cannot check LNMT user")
            
    def test_api_endpoints(self):
        """Test basic API endpoints"""
        print(f"\n{Fore.CYAN}Testing API endpoints...{Style.RESET_ALL}")
        
        endpoints = [
            ('/api/v1/devices', 'Devices API'),
            ('/api/v1/vlans', 'VLANs API'),
            ('/api/v1/health-checks', 'Health Checks API'),
            ('/api/v1/system/info', 'System Info API')
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(
                    urljoin(self.base_url, endpoint),
                    timeout=5
                )
                
                if response.status_code in [200, 401, 403]:
                    # 401/403 means API is working but requires auth
                    self.add_result('passed', f"{description} is responding")
                    print(f"  ✓ {description} is responding")
                else:
                    self.add_result('warnings', f"{description} returned status {response.status_code}")
                    print(f"  ⚠ {description} returned HTTP {response.status_code}")
                    
            except Exception as e:
                self.add_result('warnings', f"{description} error: {str(e)}")
                print(f"  ⚠ {description} error: {str(e)}")
                
    def generate_report(self):
        """Generate installation verification report"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Installation Verification Report{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Summary
        total_passed = len(self.results['passed'])
        total_failed = len(self.results['failed'])
        total_warnings = len(self.results['warnings'])
        
        print(f"{Fore.GREEN}Passed: {total_passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {total_failed}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Warnings: {total_warnings}{Style.RESET_ALL}")
        
        # Overall status
        print(f"\n{Fore.CYAN}Overall Status:{Style.RESET_ALL}")
        if total_failed == 0:
            if total_warnings == 0:
                print(f"{Fore.GREEN}✓ Installation verified successfully!{Style.RESET_ALL}")
                print("LNMT is ready for use.")
            else:
                print(f"{Fore.YELLOW}✓ Installation verified with warnings{Style.RESET_ALL}")
                print("LNMT is functional but some issues should be addressed.")
        else:
            print(f"{Fore.RED}✗ Installation verification failed{Style.RESET_ALL}")
            print("Please fix the issues above before using LNMT.")
            
        # Save report
        report_path = Path('/tmp/lnmt_verification_report.json')
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results,
                'summary': {
                    'passed': total_passed,
                    'failed': total_failed,
                    'warnings': total_warnings
                }
            }, f, indent=2)
            
        print(f"\nDetailed report saved to: {report_path}")
        
        return total_failed == 0
        
    def run_verification(self):
        """Run all verification checks"""
        print(f"{Fore.CYAN}=== LNMT Installation Verification ==={Style.RESET_ALL}")
        print