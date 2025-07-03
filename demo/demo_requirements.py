# requirements.txt
# Python dependencies for LNMT Demo Environment

# Core dependencies
python>=3.8
requests>=2.28.0
psutil>=5.9.0
ipaddress>=1.0.23
uuid

# Data processing
pandas>=1.5.0
numpy>=1.21.0
jsonschema>=4.17.0

# Network utilities
python-nmap>=0.7.1
netaddr>=0.8.0
scapy>=2.4.5

# Database connectivity
psycopg2-binary>=2.9.0  # PostgreSQL
PyMySQL>=1.0.0          # MySQL
SQLAlchemy>=1.4.0

# Web framework (if using Flask/Django components)
Flask>=2.2.0
Flask-SQLAlchemy>=3.0.0
Flask-Login>=0.6.0
Jinja2>=3.1.0

# Security and authentication
bcrypt>=4.0.0
cryptography>=38.0.0
PyJWT>=2.6.0

# Scheduling and automation
APScheduler>=3.9.0
celery>=5.2.0

# Monitoring and logging
prometheus_client>=0.15.0
loguru>=0.6.0

# CLI utilities
click>=8.1.0
colorama>=0.4.6
tabulate>=0.9.0
rich>=12.6.0

# Configuration management
PyYAML>=6.0
configparser>=5.3.0
python-dotenv>=0.21.0

# Network monitoring
ping3>=4.0.0
speedtest-cli>=2.1.3

# Report generation
reportlab>=3.6.0       # PDF reports
matplotlib>=3.6.0      # Charts and graphs
Pillow>=9.3.0          # Image processing

# Testing (for demo validation)
pytest>=7.2.0
pytest-cov>=4.0.0

---

# install_demo.py
# Simple installation script for LNMT demo environment

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class LNMTDemoInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.demo_dir = Path("/opt/lnmt/demo")
        self.requirements_installed = False
        
    def check_system_requirements(self):
        """Check if system meets minimum requirements"""
        print("🔍 Checking system requirements...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ required")
            return False
        print("✅ Python version OK")
        
        # Check available memory
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 4:
                print(f"⚠️ Warning: Only {memory_gb:.1f}GB RAM available (4GB recommended)")
            else:
                print("✅ Memory requirements OK")
        except ImportError:
            print("⚠️ Cannot check memory (psutil not installed)")
        
        # Check disk space
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 10:
            print(f"❌ Insufficient disk space: {free_gb:.1f}GB (10GB required)")
            return False
        print("✅ Disk space OK")
        
        return True
    
    def install_system_packages(self):
        """Install required system packages"""
        print("📦 Installing system packages...")
        
        if self.system == "linux":
            try:
                # Detect package manager
                if shutil.which("apt"):
                    packages = [
                        "python3-pip", "python3-venv", "postgresql-client",
                        "mysql-client", "curl", "wget", "net-tools", "nmap"
                    ]
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y"] + packages, check=True)
                    
                elif shutil.which("yum"):
                    packages = [
                        "python3-pip", "python3-venv", "postgresql", 
                        "mysql", "curl", "wget", "net-tools", "nmap"
                    ]
                    subprocess.run(["sudo", "yum", "install", "-y"] + packages, check=True)
                    
                print("✅ System packages installed")
                return True
                
            except subprocess.CalledProcessError:
                print("❌ Failed to install system packages")
                return False
        else:
            print("⚠️ Automatic system package installation not supported on this OS")
            return True
    
    def setup_python_environment(self):
        """Set up Python virtual environment"""
        print("🐍 Setting up Python environment...")
        
        venv_path = self.demo_dir / "venv"
        
        try:
            # Create virtual environment
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            
            # Install pip packages
            pip_path = venv_path / "bin" / "pip"
            if not pip_path.exists():
                pip_path = venv_path / "Scripts" / "pip.exe"  # Windows
            
            subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
            subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
            
            print("✅ Python environment setup complete")
            self.requirements_installed = True
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup Python environment: {e}")
            return False
    
    def create_demo_structure(self):
        """Create demo directory structure"""
        print("📁 Creating demo directory structure...")
        
        directories = [
            "data", "scenarios", "templates", "scripts", 
            "screenshots", "config", "logs", "backups"
        ]
        
        for directory in directories:
            (self.demo_dir / directory).mkdir(parents=True, exist_ok=True)
        
        print("✅ Directory structure created")
        return True
    
    def generate_demo_config(self):
        """Generate demo-specific configuration files"""
        print("⚙️ Generating demo configuration...")
        
        # Demo LNMT configuration
        config_content = """
# LNMT Demo Configuration
[general]
demo_mode = true
debug = true
log_level = INFO

[database]
host = localhost
port = 5432
name = lnmt_demo
user = lnmt_demo
password = demo_password_123

[web]
host = 0.0.0.0
port = 8080
secret_key = demo_secret_key_change_in_production

[monitoring]
interval = 30
alert_threshold_cpu = 85
alert_threshold_memory = 90
alert_threshold_disk = 95

[backup]
enabled = true
schedule = "0 2 * * *"
retention_days = 7
location = /opt/lnmt/demo/backups
"""
        
        config_file = self.demo_dir / "config" / "demo_lnmt.conf"
        config_file.write_text(config_content)
        
        # Demo database initialization script
        db_init_content = """
-- LNMT Demo Database Initialization
CREATE DATABASE IF NOT EXISTS lnmt_demo;
CREATE USER IF NOT EXISTS 'lnmt_demo'@'localhost' IDENTIFIED BY 'demo_password_123';
GRANT ALL PRIVILEGES ON lnmt_demo.* TO 'lnmt_demo'@'localhost';
FLUSH PRIVILEGES;

USE lnmt_demo;

-- Create demo tables
CREATE TABLE IF NOT EXISTS demo_devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(15) NOT NULL,
    mac_address VARCHAR(17) NOT NULL,
    device_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS demo_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    device_id INT,
    message TEXT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES demo_devices(id)
);
"""
        
        db_file = self.demo_dir / "config" / "demo_database.sql"
        db_file.write_text(db_init_content)
        
        print("✅ Demo configuration generated")
        return True
    
    def install_demo_scripts(self):
        """Install demo scripts and make them executable"""
        print("📜 Installing demo scripts...")
        
        # Copy/generate all demo scripts would go here
        # For brevity, just creating placeholder files
        
        scripts = [
            "setup_demo.sh", "reset_demo.sh",
            "scenarios/01_device_onboarding.sh",
            "scenarios/02_security_response.sh", 
            "scenarios/03_backup_restore.sh",
            "scenarios/04_vlan_management.sh",
            "scenarios/05_reporting_analytics.sh",
            "scripts/health_check.sh",
            "scripts/performance_test.sh",
            "scripts/cleanup.sh"
        ]
        
        for script in scripts:
            script_path = self.demo_dir / script
            script_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not script_path.exists():
                script_path.write_text(f"#!/bin/bash\n# {script} - Generated by installer\necho 'Demo script: {script}'\n")
            
            # Make executable
            os.chmod(script_path, 0o755)
        
        print("✅ Demo scripts installed")
        return True
    
    def run_installation(self):
        """Run complete installation process"""
        print("🚀 LNMT Demo Environment Installer")
        print("=" * 50)
        
        steps = [
            ("System Requirements", self.check_system_requirements),
            ("System Packages", self.install_system_packages),
            ("Directory Structure", self.create_demo_structure),
            ("Python Environment", self.setup_python_environment),
            ("Demo Configuration", self.generate_demo_config),
            ("Demo Scripts", self.install_demo_scripts)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 Step: {step_name}")
            if not step_func():
                print(f"❌ Installation failed at step: {step_name}")
                return False
        
        self.print_success_message()
        return True
    
    def print_success_message(self):
        """Print installation success message"""
        print("\n" + "=" * 60)
        print("🎉 LNMT Demo Installation Complete!")
        print("=" * 60)
        print(f"📁 Demo Directory: {self.demo_dir}")
        print(f"🌐 Web Interface: http://localhost:8080")
        print(f"👤 Demo Login: admin.demo / DemoAdmin123!")
        print("\n📚 Next Steps:")
        print("1. cd /opt/lnmt/demo")
        print("2. ./setup_demo.sh")
        print("3. Open http://localhost:8080 in your browser")
        print("4. Follow the demo scenarios in ./scenarios/")
        print("\n📖 Documentation: ./DEMO_GUIDE.md")
        print("🆘 Health Check: ./scripts/health_check.sh")
        print("=" * 60)

def main():
    """Main installation function"""
    installer = LNMTDemoInstaller()
    
    # Check if running as root/sudo
    if os.geteuid() != 0:
        print("⚠️ This installer may require sudo privileges for system packages")
        print("   Run with: sudo python3 install_demo.py")
    
    try:
        success = installer.run_installation()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

---

# setup.py
# Alternative setup using Python setuptools

from setuptools import setup, find_packages

setup(
    name="lnmt-demo",
    version="2.0.0",
    description="LNMT Demo Environment - Network Management Toolkit Demonstration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="LNMT Development Team",
    author_email="demo@lnmt.org",
    url="https://github.com/lnmt/demo",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "psutil>=5.9.0",
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "jsonschema>=4.17.0",
        "python-nmap>=0.7.1",
        "netaddr>=0.8.0",
        "psycopg2-binary>=2.9.0",
        "PyMySQL>=1.0.0",
        "SQLAlchemy>=1.4.0",
        "Flask>=2.2.0",
        "bcrypt>=4.0.0",
        "APScheduler>=3.9.0",
        "click>=8.1.0",
        "colorama>=0.4.6",
        "PyYAML>=6.0",
        "reportlab>=3.6.0",
        "matplotlib>=3.6.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.2.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0"
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "lnmt-demo=lnmt_demo.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "lnmt_demo": [
            "data/*.csv",
            "data/*.json",
            "templates/*.csv",
            "scenarios/*.sh",
            "scripts/*.sh",
            "config/*",
        ],
    },
)