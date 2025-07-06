# LNMT RC2 Quick Start Guide

## Pre-Installation
1. Check system requirements:
   ```bash
   python3 utils/preflight_check.py
   ```

2. Copy and configure settings:
   ```bash
   cp config/config.template.yml config/config.yml
   cp config/.env.example .env
   # Edit both files with your settings
   ```

3. Install Python dependencies:
   ```bash
   pip3 install -r config/requirements.txt
   ```

## Installation
1. Set up the database:
   ```bash
   python3 database/migrations/001_initial_setup.py
   ```

2. Install systemd services:
   ```bash
   sudo cp config/systemd/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

3. Run the installer:
   ```bash
   sudo ./installer/lnmt_installer.sh
   ```

## Post-Installation
1. Verify installation:
   ```bash
   python3 scripts/verify_installation.py
   ```

2. Run security audit:
   ```bash
   sudo python3 scripts/security_audit.py
   ```

3. Start services:
   ```bash
   sudo systemctl start lnmt lnmt-scheduler lnmt-health
   sudo systemctl enable lnmt lnmt-scheduler lnmt-health
   ```

## Access LNMT
- Web Interface: http://localhost:8080
- Default credentials: admin / ChangeMeNow123!
- API Documentation: http://localhost:8080/docs

Remember to change the default password immediately!
