#!/usr/bin/env python3
"""
LNMT Pre-flight Check
Validates system configuration before starting the application
"""

import os
import sys
import socket
import psutil
import subprocess
from pathlib import Path
import yaml
import redis
import psycopg2
import mysql.connector
from colorama import init, Fore, Style

init(autoreset=True)

class PreflightCheck:
    """Perform pre-flight checks for LNMT"""
    
    def __init__(self, config_path="/etc/lnmt/config.yml"):
        self.config_path = config_path
        self.config = None
        self.errors = []
        self.warnings = []
        self.info = []
        
    def load_config(self):
        """Load configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.info.append(f"Configuration loaded from {self.config_path}")
            return True
        except FileNotFoundError:
            self.errors.append(f"Configuration file not found: {self.config_path}")
            return False
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in configuration: {e}")
            return False
            
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            self.info.append(f"Python version {version.major}.{version.minor}.{version.micro} ✓")
        else:
            self.errors.append(f"Python 3.8+ required, found {version.major}.{version.minor}.{version.micro}")
            
    def check_system_resources(self):
        """Check available system resources"""
        # Check CPU
        cpu_count = psutil.cpu_count()
        if cpu_count < 2:
            self.warnings.append(f"Only {cpu_count} CPU core(s) detected. Recommend 2+ cores")
        else:
            self.info.append(f"CPU cores: {cpu_count} ✓")
            
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < 4:
            self.warnings.append(f"Only {ram_gb:.1f} GB RAM detected. Recommend 4+ GB")
        else:
            self.info.append(f"RAM: {ram_gb:.1f} GB ✓")
            
        # Check disk space
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 10:
            self.warnings.append(f"Only {free_gb:.1f} GB free disk space. Recommend 20+ GB")
        else:
            self.info.append(f"Free disk space: {free_gb:.1f} GB ✓")
            
    def check_directories(self):
        """Check required directories exist and are writable"""
        directories = [
            "/var/lib/lnmt",
            "/var/log/lnmt",
            "/var/backups/lnmt",
            "/etc/lnmt",
            "/run/lnmt"
        ]
        
        for directory in directories:
            path = Path(directory)
            if not path.exists():
                self.warnings.append(f"Directory does not exist: {directory}")
            elif not os.access(directory, os.W_OK):
                self.errors.append(f"Directory not writable: {directory}")
            else:
                self.info.append(f"Directory {directory} ✓")
                
    def check_ports(self):
        """Check if required ports are available"""
        if not self.config:
            return
            
        ports_to_check = [
            (self.config.get('server', {}).get('port', 8080), 'LNMT Web'),
            (self.config.get('monitoring', {}).get('metrics', {}).get('port', 9090), 'Metrics')
        ]
        
        for port, service in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                self.errors.append(f"Port {port} ({service}) is already in use")
            else:
                self.info.append(f"Port {port} ({service}) is available ✓")
                
    def check_database(self):
        """Check database connectivity"""
        if not self.config:
            return
            
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'postgresql')
        
        try:
            if db_type == 'postgresql':
                conn = psycopg2.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 5432),
                    database=db_config.get('name', 'lnmt_db'),
                    user=db_config.get('user', 'lnmt_user'),
                    password=db_config.get('password', '')
                )
                conn.close()
            elif db_type == 'mysql':
                conn = mysql.connector.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 3306),
                    database=db_config.get('name', 'lnmt_db'),
                    user=db_config.get('user', 'lnmt_user'),
                    password=db_config.get('password', '')
                )
                conn.close()
                
            self.info.append(f"Database connection ({db_type}) successful ✓")
        except Exception as e:
            self.errors.append(f"Database connection failed: {str(e)}")
            
    def check_redis(self):
        """Check Redis connectivity"""
        if not self.config:
            return
            
        redis_config = self.config.get('redis', {})
        if not redis_config.get('enabled', True):
            self.info.append("Redis disabled in configuration")
            return
            
        try:
            r = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                password=redis_config.get('password', None),
                db=redis_config.get('db', 0)
            )
            r.ping()
            self.info.append("Redis connection successful ✓")
        except Exception as e:
            self.errors.append(f"Redis connection failed: {str(e)}")
            
    def check_permissions(self):
        """Check file permissions"""
        # Check if running as root (not recommended)
        if os.geteuid() == 0:
            self.warnings.append("Running as root user is not recommended")
            
        # Check LNMT user exists
        try:
            subprocess.run(['id', 'lnmt'], check=True, capture_output=True)
            self.info.append("LNMT user exists ✓")
        except subprocess.CalledProcessError:
            self.warnings.append("LNMT user does not exist. Will run as current user")
            
    def check_systemd(self):
        """Check systemd service status"""
        services = ['lnmt', 'lnmt-scheduler', 'lnmt-health']
        
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-enabled', f'{service}.service'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.info.append(f"Service {service} is enabled ✓")
                else:
                    self.warnings.append(f"Service {service} is not enabled")
            except FileNotFoundError:
                self.warnings.append("systemctl not found. Not running under systemd")
                break
                
    def check_ssl_certificates(self):
        """Check SSL certificate configuration"""
        if not self.config:
            return
            
        ssl_config = self.config.get('server', {}).get('ssl', {})
        if not ssl_config.get('enabled', False):
            self.info.append("SSL disabled in configuration")
            return
            
        cert_file = ssl_config.get('cert_file', '')
        key_file = ssl_config.get('key_file', '')
        
        if Path(cert_file).exists():
            self.info.append(f"SSL certificate found: {cert_file} ✓")
        else:
            self.errors.append(f"SSL certificate not found: {cert_file}")
            
        if Path(key_file).exists():
            self.info.append(f"SSL key found: {key_file} ✓")
        else:
            self.errors.append(f"SSL key not found: {key_file}")
            
    def run_all_checks(self):
        """Run all pre-flight checks"""
        print(f"{Fore.CYAN}=== LNMT Pre-flight Check ==={Style.RESET_ALL}\n")
        
        # Load configuration first
        if not self.load_config():
            self.print_results()
            return False
            
        # Run all checks
        self.check_python_version()
        self.check_system_resources()
        self.check_directories()
        self.check_ports()
        self.check_database()
        self.check_redis()
        self.check_permissions()
        self.check_systemd()
        self.check_ssl_certificates()
        
        # Print results
        self.print_results()
        
        # Return success/failure
        return len(self.errors) == 0
        
    def print_results(self):
        """Print check results"""
        # Print info messages
        if self.info:
            print(f"{Fore.GREEN}✓ Checks Passed:{Style.RESET_ALL}")
            for msg in self.info:
                print(f"  {msg}")
            print()
            
        # Print warnings
        if self.warnings:
            print(f"{Fore.YELLOW}⚠ Warnings:{Style.RESET_ALL}")
            for msg in self.warnings:
                print(f"  {msg}")
            print()
            
        # Print errors
        if self.errors:
            print(f"{Fore.RED}✗ Errors:{Style.RESET_ALL}")
            for msg in self.errors:
                print(f"  {msg}")
            print()
            
        # Summary
        if self.errors:
            print(f"{Fore.RED}Pre-flight check FAILED{Style.RESET_ALL}")
            print("Please fix the errors above before starting LNMT")
        elif self.warnings:
            print(f"{Fore.YELLOW}Pre-flight check passed with warnings{Style.RESET_ALL}")
            print("LNMT can start but some issues should be addressed")
        else:
            print(f"{Fore.GREEN}Pre-flight check PASSED{Style.RESET_ALL}")
            print("LNMT is ready to start")
            
def main():
    """Main entry point"""
    # Check for config file argument
    config_path = "/etc/lnmt/config.yml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        
    # Run checks
    checker = PreflightCheck(config_path)
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    main()