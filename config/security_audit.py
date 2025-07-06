#!/usr/bin/env python3
"""
LNMT Security Audit Script
Performs comprehensive security checks on LNMT installation
"""

import os
import sys
import stat
import pwd
import grp
import subprocess
import socket
import ssl
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from colorama import init, Fore, Style

init(autoreset=True)

class SecurityAuditor:
    """Perform security audit on LNMT installation"""
    
    def __init__(self):
        self.issues = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'info': []
        }
        self.checks_performed = 0
        self.checks_passed = 0
        
    def add_issue(self, severity, category, description, recommendation):
        """Add a security issue"""
        self.issues[severity].append({
            'category': category,
            'description': description,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        })
        
    def check_file_permissions(self):
        """Check file and directory permissions"""
        print(f"\n{Fore.CYAN}Checking file permissions...{Style.RESET_ALL}")
        
        # Critical files that should have restricted permissions
        critical_files = {
            '/etc/lnmt/config.yml': 0o640,
            '/etc/lnmt/lnmt.env': 0o640,
            '/etc/lnmt/keys/': 0o700,
            '/var/log/lnmt/': 0o750,
            '/var/lib/lnmt/': 0o750,
        }
        
        for path, expected_mode in critical_files.items():
            self.checks_performed += 1
            
            try:
                file_path = Path(path)
                if file_path.exists():
                    stat_info = file_path.stat()
                    current_mode = stat.S_IMODE(stat_info.st_mode)
                    
                    if current_mode > expected_mode:
                        self.add_issue(
                            'high',
                            'File Permissions',
                            f"{path} has overly permissive permissions: {oct(current_mode)}",
                            f"Set permissions to {oct(expected_mode)}: chmod {oct(expected_mode)} {path}"
                        )
                        print(f"  ✗ {path}: {oct(current_mode)} (should be {oct(expected_mode)})")
                    else:
                        self.checks_passed += 1
                        print(f"  ✓ {path}: {oct(current_mode)}")
                        
                    # Check ownership
                    try:
                        pw = pwd.getpwuid(stat_info.st_uid)
                        gr = grp.getgrgid(stat_info.st_gid)
                        
                        if pw.pw_name == 'root' and 'lnmt' in path:
                            self.add_issue(
                                'medium',
                                'File Ownership',
                                f"{path} is owned by root instead of lnmt user",
                                f"Change ownership: chown lnmt:lnmt {path}"
                            )
                    except KeyError:
                        pass
                        
            except Exception as e:
                self.add_issue(
                    'info',
                    'File Permissions',
                    f"Could not check {path}: {str(e)}",
                    "Ensure file exists with correct permissions"
                )
                
    def check_password_policy(self):
        """Check password policy configuration"""
        print(f"\n{Fore.CYAN}Checking password policy...{Style.RESET_ALL}")
        
        try:
            # Check system password policy
            self.checks_performed += 1
            
            # Check PAM configuration
            pam_files = [
                '/etc/pam.d/common-password',
                '/etc/pam.d/system-auth'
            ]
            
            policy_found = False
            for pam_file in pam_files:
                if Path(pam_file).exists():
                    with open(pam_file, 'r') as f:
                        content = f.read()
                        if 'pam_pwquality.so' in content or 'pam_cracklib.so' in content:
                            policy_found = True
                            self.checks_passed += 1
                            print(f"  ✓ Password quality requirements found in {pam_file}")
                            break
                            
            if not policy_found:
                self.add_issue(
                    'medium',
                    'Password Policy',
                    'No password quality requirements found in PAM configuration',
                    'Install and configure pam_pwquality or pam_cracklib'
                )
                print("  ✗ No password quality requirements found")
                
        except Exception as e:
            self.add_issue(
                'info',
                'Password Policy',
                f"Could not check password policy: {str(e)}",
                'Manually verify password policy configuration'
            )
            
    def check_ssl_configuration(self):
        """Check SSL/TLS configuration"""
        print(f"\n{Fore.CYAN}Checking SSL/TLS configuration...{Style.RESET_ALL}")
        
        # Check for SSL certificate
        cert_paths = [
            '/etc/lnmt/certs/server.crt',
            '/etc/ssl/certs/lnmt.crt',
            '/etc/nginx/ssl/lnmt.crt'
        ]
        
        cert_found = False
        for cert_path in cert_paths:
            self.checks_performed += 1
            
            if Path(cert_path).exists():
                cert_found = True
                
                try:
                    with open(cert_path, 'rb') as f:
                        cert_data = f.read()
                        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                        
                    # Check certificate validity
                    now = datetime.utcnow()
                    if cert.not_valid_after < now:
                        self.add_issue(
                            'critical',
                            'SSL Certificate',
                            f"SSL certificate at {cert_path} has expired",
                            'Generate or obtain a new SSL certificate immediately'
                        )
                        print(f"  ✗ Certificate expired: {cert_path}")
                    elif cert.not_valid_after < now + timedelta(days=30):
                        self.add_issue(
                            'high',
                            'SSL Certificate',
                            f"SSL certificate at {cert_path} expires soon ({cert.not_valid_after})",
                            'Plan to renew SSL certificate before expiration'
                        )
                        print(f"  ⚠ Certificate expires soon: {cert_path}")
                    else:
                        self.checks_passed += 1
                        print(f"  ✓ Certificate valid until: {cert.not_valid_after}")
                        
                    # Check key size
                    public_key = cert.public_key()
                    key_size = public_key.key_size
                    if key_size < 2048:
                        self.add_issue(
                            'high',
                            'SSL Certificate',
                            f"SSL certificate uses weak key size: {key_size} bits",
                            'Generate new certificate with at least 2048-bit key'
                        )
                        
                except Exception as e:
                    self.add_issue(
                        'medium',
                        'SSL Certificate',
                        f"Could not parse certificate at {cert_path}: {str(e)}",
                        'Verify certificate format and validity'
                    )
                    
        if not cert_found:
            self.add_issue(
                'high',
                'SSL Certificate',
                'No SSL certificate found',
                'Generate or obtain an SSL certificate for HTTPS'
            )
            print("  ✗ No SSL certificate found")
            
    def check_service_configuration(self):
        """Check service security configuration"""
        print(f"\n{Fore.CYAN}Checking service configuration...{Style.RESET_ALL}")
        
        # Check if services are running as non-root
        services = ['lnmt', 'lnmt-scheduler', 'lnmt-health']
        
        for service in services:
            self.checks_performed += 1
            
            try:
                # Check systemd service file
                service_file = f"/etc/systemd/system/{service}.service"
                if Path(service_file).exists():
                    with open(service_file, 'r') as f:
                        content = f.read()
                        
                    # Check User directive
                    if 'User=lnmt' in content:
                        self.checks_passed += 1
                        print(f"  ✓ {service} runs as non-root user")
                    elif 'User=root' in content:
                        self.add_issue(
                            'critical',
                            'Service Configuration',
                            f"{service} is configured to run as root",
                            f"Change User directive to 'lnmt' in {service_file}"
                        )
                        print(f"  ✗ {service} runs as root")
                    else:
                        self.add_issue(
                            'medium',
                            'Service Configuration',
                            f"{service} user configuration unclear",
                            f"Explicitly set User=lnmt in {service_file}"
                        )
                        
                    # Check security directives
                    security_directives = [
                        'NoNewPrivileges=true',
                        'PrivateTmp=true',
                        'ProtectSystem=strict',
                        'ProtectHome=true'
                    ]
                    
                    missing_directives = []
                    for directive in security_directives:
                        if directive not in content:
                            missing_directives.append(directive)
                            
                    if missing_directives:
                        self.add_issue(
                            'medium',
                            'Service Hardening',
                            f"{service} missing security directives: {', '.join(missing_directives)}",
                            f"Add missing directives to {service_file}"
                        )
                        
            except Exception as e:
                self.add_issue(
                    'info',
                    'Service Configuration',
                    f"Could not check {service}: {str(e)}",
                    'Manually verify service configuration'
                )
                
    def check_database_security(self):
        """Check database security configuration"""
        print(f"\n{Fore.CYAN}Checking database security...{Style.RESET_ALL}")
        
        self.checks_performed += 1
        
        # Check PostgreSQL configuration
        pg_config_paths = [
            '/etc/postgresql/*/main/postgresql.conf',
            '/var/lib/pgsql/data/postgresql.conf'
        ]
        
        for config_pattern in pg_config_paths:
            import glob
            for config_file in glob.glob(config_pattern):
                if Path(config_file).exists():
                    with open(config_file, 'r') as f:
                        content = f.read()
                        
                    # Check SSL configuration
                    if 'ssl = on' in content:
                        self.checks_passed += 1
                        print("  ✓ PostgreSQL SSL is enabled")
                    else:
                        self.add_issue(
                            'high',
                            'Database Security',
                            'PostgreSQL SSL is not enabled',
                            f"Enable SSL in {config_file}: ssl = on"
                        )
                        print("  ✗ PostgreSQL SSL is disabled")
                        
                    # Check logging
                    if 'log_connections = on' in content:
                        print("  ✓ Connection logging is enabled")
                    else:
                        self.add_issue(
                            'low',
                            'Database Security',
                            'PostgreSQL connection logging is disabled',
                            'Enable connection logging for audit purposes'
                        )
                        
    def check_api_security(self):
        """Check API security headers and configuration"""
        print(f"\n{Fore.CYAN}Checking API security...{Style.RESET_ALL}")
        
        try:
            # Test API endpoint
            response = requests.get('http://localhost:8080/api/v1/health', timeout=5)
            
            # Check security headers
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000',
                'Content-Security-Policy': None  # Check existence only
            }
            
            for header, expected_value in security_headers.items():
                self.checks_performed += 1
                
                if header in response.headers:
                    if expected_value is None or response.headers[header] == expected_value:
                        self.checks_passed += 1
                        print(f"  ✓ {header} is set correctly")
                    else:
                        self.add_issue(
                            'medium',
                            'API Security Headers',
                            f"{header} has unexpected value: {response.headers[header]}",
                            f"Set {header} to {expected_value}"
                        )
                else:
                    self.add_issue(
                        'medium',
                        'API Security Headers',
                        f"Missing security header: {header}",
                        f"Add {header} header to API responses"
                    )
                    print(f"  ✗ Missing header: {header}")
                    
        except Exception as e:
            self.add_issue(
                'info',
                'API Security',
                f"Could not test API security: {str(e)}",
                'Ensure API is running and accessible'
            )
            
    def check_authentication(self):
        """Check authentication configuration"""
        print(f"\n{Fore.CYAN}Checking authentication security...{Style.RESET_ALL}")
        
        # Check for default credentials
        self.checks_performed += 1
        
        default_creds = [
            ('admin', 'admin'),
            ('admin', 'password'),
            ('admin', 'ChangeMeNow123!'),
            ('lnmt', 'lnmt')
        ]
        
        print("  Testing for default credentials...")
        
        for username, password in default_creds:
            try:
                response = requests.post(
                    'http://localhost:8080/api/v1/auth/login',
                    json={'username': username, 'password': password},
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.add_issue(
                        'critical',
                        'Authentication',
                        f"Default credentials are active: {username}",
                        'Change default credentials immediately'
                    )
                    print(f"  ✗ Default credentials active: {username}")
                    break
            except:
                pass
        else:
            self.checks_passed += 1
            print("  ✓ No default credentials found")
            
    def check_firewall(self):
        """Check firewall configuration"""
        print(f"\n{Fore.CYAN}Checking firewall configuration...{Style.RESET_ALL}")
        
        self.checks_performed += 1
        
        # Check if firewall is active
        firewall_cmds = [
            (['ufw', 'status'], 'Status: active'),
            (['firewall-cmd', '--state'], 'running'),
            (['iptables', '-L', '-n'], None)
        ]
        
        firewall_active = False
        for cmd, expected_output in firewall_cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    if expected_output is None or expected_output in result.stdout:
                        firewall_active = True
                        self.checks_passed += 1
                        print(f"  ✓ Firewall is active ({cmd[0]})")
                        break
            except FileNotFoundError:
                continue
                
        if not firewall_active:
            self.add_issue(
                'high',
                'Firewall',
                'No active firewall detected',
                'Enable and configure a firewall (ufw, firewalld, or iptables)'
            )
            print("  ✗ No active firewall detected")
            
    def check_updates(self):
        """Check for security updates"""
        print(f"\n{Fore.CYAN}Checking for security updates...{Style.RESET_ALL}")
        
        self.checks_performed += 1
        
        # Check for package updates
        update_cmds = [
            (['apt', 'list', '--upgradeable'], 'Ubuntu/Debian'),
            (['yum', 'check-update'], 'RHEL/CentOS'),
            (['dnf', 'check-update'], 'Fedora')
        ]
        
        for cmd, distro in update_cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode in [0, 100]:  # 100 = updates available for yum/dnf
                    updates = result.stdout.strip().split('\n')
                    security_updates = [u for u in updates if 'security' in u.lower()]
                    
                    if security_updates:
                        self.add_issue(
                            'high',
                            'System Updates',
                            f"{len(security_updates)} security updates available",
                            'Apply security updates immediately'
                        )
                        print(f"  ✗ {len(security_updates)} security updates available")
                    else:
                        self.checks_passed += 1
                        print("  ✓ No security updates pending")
                    break
            except FileNotFoundError:
                continue
                
    def generate_report(self):
        """Generate security audit report"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Security Audit Report{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Summary
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        print(f"Checks performed: {self.checks_performed}")
        print(f"Checks passed: {self.checks_passed}")
        print(f"Pass rate: {self.checks_passed/self.checks_performed*100:.1f}%\n")
        
        # Issues by severity
        severities = ['critical', 'high', 'medium', 'low', 'info']
        colors = {
            'critical': Fore.RED,
            'high': Fore.MAGENTA,
            'medium': Fore.YELLOW,
            'low': Fore.CYAN,
            'info': Fore.BLUE
        }
        
        for severity in severities:
            count = len(self.issues[severity])
            if count > 0:
                print(f"{colors[severity]}{severity.upper()}: {count} issues{Style.RESET_ALL}")
                
        # Detailed issues
        print(f"\n{Fore.CYAN}Detailed Findings:{Style.RESET_ALL}")
        
        for severity in severities:
            if self.issues[severity]:
                print(f"\n{colors[severity]}=== {severity.upper()} ==={Style.RESET_ALL}")
                for issue in self.issues[severity]:
                    print(f"\nCategory: {issue['category']}")
                    print(f"Issue: {issue['description']}")
                    print(f"Recommendation: {issue['recommendation']}")
                    
        # Save report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'checks_performed': self.checks_performed,
                'checks_passed': self.checks_passed,
                'pass_rate': f"{self.checks_passed/self.checks_performed*100:.1f}%",
                'total_issues': total_issues
            },
            'issues': self.issues
        }
        
        report_path = Path('/tmp/lnmt_security_audit.json')
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\n{Fore.CYAN}Report saved to: {report_path}{Style.RESET_ALL}")
        
        # Overall security score
        if self.issues['critical']:
            print(f"\n{Fore.RED}⚠ CRITICAL SECURITY ISSUES FOUND ⚠{Style.RESET_ALL}")
            print("Address critical issues immediately!")
        elif self.issues['high']:
            print(f"\n{Fore.MAGENTA}Security Status: NEEDS IMPROVEMENT{Style.RESET_ALL}")
            print("High priority issues should be addressed soon.")
        elif self.issues['medium']:
            print(f"\n{Fore.YELLOW}Security Status: FAIR{Style.RESET_ALL}")
            print("Consider addressing medium priority issues.")
        else:
            print(f"\n{Fore.GREEN}Security Status: GOOD{Style.RESET_ALL}")
            print("No significant security issues found.")
            
    def run_audit(self):
        """Run complete security audit"""
        print(f"{Fore.CYAN}=== LNMT Security Audit ==={Style.RESET_ALL}")
        print(f"Starting audit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all checks
        self.check_file_permissions()
        self.check_password_policy()
        self.check_ssl_configuration()
        self.check_service_configuration()
        self.check_database_security()
        self.check_api_security()
        self.check_authentication()
        self.check_firewall()
        self.check_updates()
        
        # Generate report
        self.generate_report()

def main():
    """Main entry point"""
    # Check if running as root (recommended for some checks)
    if os.geteuid() != 0:
        print(f"{Fore.YELLOW}Warning: Some checks require root privileges.{Style.RESET_ALL}")
        print("Consider running with sudo for complete results.\n")
        
    auditor = SecurityAuditor()
    auditor.run_audit()
    
if __name__ == "__main__":
    main()