# LNMT Installation and Migration Guide

## Overview

The Linux Network Management Toolbox (LNMT) provides a comprehensive installation, update, and migration system designed for production environments. This guide covers installation, updates, migration from legacy tools, and system management.

## Quick Start

### Basic Installation

```bash
# Download and run installer
curl -fsSL https://raw.githubusercontent.com/your-org/lnmt/main/install.sh | sudo bash

# Or download first, then run
wget https://raw.githubusercontent.com/your-org/lnmt/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Interactive Installation

```bash
sudo ./install.sh
```

The installer will:
- Detect your operating system and package manager
- Install required dependencies
- Create system user and directories
- Configure systemd services
- Set up default configurations
- Display post-installation summary

## Installation Options

### Command Line Arguments

```bash
# Force installation without prompts
sudo ./install.sh --force

# Install with Python virtual environment
sudo ./install.sh --type venv

# Unattended installation
sudo ./install.sh --unattended

# Skip dependency installation
sudo ./install.sh --skip-deps

# Custom backup directory
sudo ./install.sh --backup-dir /custom/backup/path

# Verbose installation
sudo ./install.sh --verbose
```

### Installation Types

#### Full Installation (Default)
- Complete LNMT stack with all modules
- System-wide installation in `/opt/lnmt`
- Systemd service integration
- Recommended for production

#### Virtual Environment Installation
```bash
sudo ./install.sh --type venv
```
- Isolated Python environment
- Better dependency management
- Easier updates and rollbacks

#### Docker Installation
```bash
sudo ./install.sh --type docker
```
- Container-based deployment
- Simplified scaling and management
- Requires Docker to be installed

#### Minimal Installation
```bash
sudo ./install.sh --type minimal
```
- Core functionality only
- Reduced resource usage
- Manual module enablement

## Supported Operating Systems

### Tested Distributions

| Distribution | Version | Package Manager | Status |
|-------------|---------|-----------------|--------|
| Ubuntu | 20.04+, 22.04+, 24.04+ | apt | ✅ Fully Supported |
| Debian | 11+, 12+ | apt | ✅ Fully Supported |
| RHEL/CentOS | 8+, 9+ | dnf/yum | ✅ Fully Supported |
| Fedora | 35+ | dnf | ✅ Fully Supported |
| Rocky Linux | 8+, 9+ | dnf | ✅ Fully Supported |
| AlmaLinux | 8+, 9+ | dnf | ✅ Fully Supported |
| Arch Linux | Latest | pacman | ⚠️ Community Support |
| openSUSE | 15.4+ | zypper | ⚠️ Community Support |

### System Requirements

#### Minimum Requirements
- **RAM**: 512MB (1GB recommended)
- **Storage**: 2GB free space
- **CPU**: 1 core (2+ recommended)
- **Python**: 3.8+
- **Privileges**: Root access required

#### Recommended Requirements
- **RAM**: 2GB+
- **Storage**: 10GB+ free space
- **CPU**: 2+ cores
- **Network**: Multiple interfaces for advanced features

## Post-Installation

### Service Management

```bash
# Start all LNMT services
sudo systemctl start lnmt lnmt-web lnmt-scheduler

# Enable services for auto-start
sudo systemctl enable lnmt lnmt-web lnmt-scheduler

# Check service status
sudo systemctl status lnmt
sudo systemctl status lnmt-web
sudo systemctl status lnmt-scheduler

# View logs
sudo journalctl -u lnmt -f
sudo journalctl -u lnmt-web -f
```

### Configuration

#### Main Configuration
Edit `/etc/lnmt/lnmt.yml`:

```yaml
# Core settings
core:
  data_dir: "/var/lib/lnmt"
  log_dir: "/var/log/lnmt"
  log_level: "INFO"
  debug: false

# Database settings
database:
  type: "sqlite"
  path: "/var/lib/lnmt/db/lnmt.db"
  
# Web interface
web:
  host: "0.0.0.0"
  port: 8080
  secret_key: "your-secret-key"
  
# Network settings
network:
  management_interface: "eth0"
  dns_servers:
    - "8.8.8.8"
    - "8.8.4.4"
```

#### Module Configuration
- **DNS**: `/etc/lnmt/dns.yml`
- **Firewall**: `/etc/lnmt/firewall.yml`
- **Interfaces**: `/etc/lnmt/interfaces.yml`

### Web Interface Access

1. Open browser to `http://your-server-ip:8080`
2. Default credentials (change immediately):
   - Username: `admin`
   - Password: `admin`

### CLI Usage

```bash
# General help
lnmt-cli --help

# Module-specific commands
lnmt-cli dns status
lnmt-cli firewall rules list
lnmt-cli vlan create --name "management" --id 100

# Configuration management
lnmt-cli config validate
lnmt-cli config backup
lnmt-cli config show
```

## Updates and Upgrades

### Self-Updater

The LNMT self-updater provides safe, automated updates with rollback capabilities.

#### Check for Updates

```bash
# Check for available updates
sudo python3 /opt/lnmt/upgrade.py --check-only

# Check from specific source
sudo python3 /opt/lnmt/upgrade.py --source github --check-only
```

#### Perform Updates

```bash
# Interactive update
sudo python3 /opt/lnmt/upgrade.py

# Force update without confirmation
sudo python3 /opt/lnmt/upgrade.py --force

# Dry run (show what would be done)
sudo python3 /opt/lnmt/upgrade.py --dry-run
```

#### Update Sources

##### GitHub Releases (Default)
```bash
sudo python3 /opt/lnmt/upgrade.py --source github
```

##### PyPI Package
```bash
sudo python3 /opt/lnmt/upgrade.py --source pip
```

##### Custom Server
```bash
sudo python3 /opt/lnmt/upgrade.py --source custom
```

#### Rollback

```bash
# Rollback to previous version
sudo python3 /opt/lnmt/upgrade.py --rollback

# List available backups
sudo python3 /opt/lnmt/upgrade.py --list-backups
```

### Manual Updates

```bash
# Stop services
sudo systemctl stop lnmt-scheduler lnmt-web lnmt

# Create backup
sudo cp -r /opt/lnmt /opt/lnmt.backup

# Download new version
wget https://github.com/your-org/lnmt/archive/v1.1.0.tar.gz
tar -xzf v1.1.0.tar.gz

# Install update
sudo cp -r lnmt-1.1.0/* /opt/lnmt/

# Run migrations
sudo python3 /opt/lnmt/scripts/migrate.py

# Start services
sudo systemctl start lnmt lnmt-web lnmt-scheduler
```

## Migration from Legacy Tools

LNMT provides automated migration from popular network management tools.

### Migration Tool Usage

```bash
# General migration syntax
sudo python3 /opt/lnmt/migrate.py migrate --source <tool>

# Available migration sources
sudo python3 /opt/lnmt/migrate.py migrate --source all
```

### dnsmasq Migration

Migrates DNS, DHCP, and network configuration from dnsmasq.

```bash
# Migrate from dnsmasq
sudo python3 /opt/lnmt/migrate.py migrate --source dnsmasq

# Dry run first (recommended)
sudo python3 /opt/lnmt/migrate.py migrate --source dnsmasq --dry-run
```

#### What Gets Migrated
- DNS server configuration
- Upstream DNS servers
- Static host entries
- DHCP ranges and reservations
- Interface bindings
- Local domain configuration

#### Original Files Backed Up
- `/etc/dnsmasq.conf` → `/var/lib/lnmt/backups/migration_*/dnsmasq_main/`
- `/etc/dnsmasq.d/` → `/var/lib/lnmt/backups/migration_*/dnsmasq_includes/`

### Pi-hole Migration

Migrates DNS filtering and ad-blocking configuration from Pi-hole.

```bash
# Migrate from Pi-hole
sudo python3 /opt/lnmt/migrate.py migrate --source pihole
```

#### What Gets Migrated
- DNS server settings
- Upstream DNS configuration
- Blocklists and sources
- Whitelist/blacklist entries
- Interface configuration
- Blocking preferences

#### Original Files Backed Up
- `/etc/pihole/` → `/var/lib/lnmt/backups/migration_*/pihole/`

### Shorewall Migration

Migrates firewall rules and policies from Shorewall.

```bash
# Migrate from Shorewall
sudo python3 /opt/lnmt/migrate.py migrate --source shorewall
```

#### What Gets Migrated
- Zone definitions
- Interface assignments
- Firewall policies
- Traffic rules
- NAT/Masquerading rules
- Network interfaces

#### Original Files Backed Up
- `/etc/shorewall/` → `/var/lib/lnmt/backups/migration_*/shorewall/`

### Migration Best Practices

1. **Always backup first**:
   ```bash
   # Create system backup before migration
   sudo python3 /opt/lnmt/migrate.py backup --description "pre-migration"
   ```

2. **Test with dry-run**:
   ```bash
   # See what would be migrated
   sudo python3 /opt/lnmt/migrate.py migrate --source <tool> --dry-run
   ```

3. **Validate after migration**:
   ```bash
   # Validate migrated configuration
   sudo python3 /opt/lnmt/migrate.py validate
   ```

4. **Gradual service transition**:
   - Keep original service disabled but not removed
   - Test LNMT functionality thoroughly
   - Remove original service only after validation

### Post-Migration Steps

1. **Review Configuration**:
   ```bash
   # Check migrated settings
   sudo cat /etc/lnmt/dns.yml
   sudo cat /etc/lnmt/firewall.yml
   ```

2. **Test Functionality**:
   ```bash
   # Test DNS resolution
   nslookup google.com localhost
   
   # Test firewall rules
   sudo iptables -L
   
   # Check service status
   sudo systemctl status lnmt
   ```

3. **Update Network Settings**:
   - Update DHCP clients to use new DNS server
   - Verify firewall rules are working
   - Test network connectivity

## Configuration Management

### Backup and Restore

#### Create Configuration Backup

```bash
# Create backup with description
sudo python3 /opt/lnmt/migrate.py backup --description "before-changes"

# List available backups
sudo python3 /opt/lnmt/migrate.py list
```

#### Restore Configuration

```bash
# Restore from specific backup
sudo python3 /opt/lnmt/migrate.py restore --backup config_backup_20241202_143000

# Dry run restore
sudo python3 /opt/lnmt/migrate.py restore --backup config_backup_20241202_143000 --dry-run
```

### Configuration Validation

```bash
# Validate all configuration files
sudo python3 /opt/lnmt/migrate.py validate

# Validate specific configuration
sudo python3 /opt/lnmt/migrate.py validate --config dns
```

### Format Conversion

```bash
# Convert YAML to JSON
sudo python3 /opt/lnmt/migrate.py convert --input /etc/lnmt/dns.yml --output dns.json --format json

# Convert JSON to YAML
sudo python3 /opt/lnmt/migrate.py convert --input config.json --output config.yml --format yaml
```

## Uninstallation

### Safe Uninstall

```bash
# Interactive uninstall (recommended)
sudo ./uninstall.sh

# Force uninstall without prompts
sudo ./uninstall.sh --force

# Uninstall with data preservation
sudo ./uninstall.sh --remove-logs
```

### Uninstall Options

```bash
# Remove everything including data
sudo ./uninstall.sh --remove-data --remove-logs

# Keep system user
sudo ./uninstall.sh --keep-user

# Skip backup creation
sudo ./uninstall.sh --no-backup

# Custom backup location
sudo ./uninstall.sh --backup-dir /custom/backup/path
```

### What Gets Removed

#### Always Removed
- Application files (`/opt/lnmt`)
- Systemd services
- Binary symlinks (`/usr/local/bin/lnmt*`)
- Configuration files (with confirmation)

#### Optionally Removed
- Data files (`/var/lib/lnmt`) - use `--remove-data`
- Log files (`/var/log/lnmt`) - use `--remove-logs`  
- System user (`lnmt`) - default, use `--keep-user` to preserve

#### Always Preserved (unless explicitly removed)
- User data and databases
- Custom configurations
- Log files for troubleshooting

## Troubleshooting

### Common Installation Issues

#### Permission Errors
```bash
# Ensure running as root
sudo ./install.sh

# Check file permissions
sudo chown -R lnmt:lnmt /opt/lnmt
sudo chmod -R 755 /opt/lnmt
```

#### Dependency Issues
```bash
# Manual dependency installation
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# RHEL/CentOS/Fedora
sudo dnf install python3 python3-pip python3-devel

# Check Python version
python3 --version  # Should be 3.8+
```

#### Service Startup Issues
```bash
# Check service logs
sudo journalctl -u lnmt -n 50

# Verify configuration
sudo python3 /opt/lnmt/migrate.py validate

# Check port availability
sudo ss -tulpn | grep :8080
```

### Migration Issues

#### Configuration Not Found
```bash
# Verify source installation
ls -la /etc/dnsmasq.conf
ls -la /etc/pihole/
ls -la /etc/shorewall/

# Check migration logs
sudo tail -f /var/log/lnmt/migration.log
```

#### Incomplete Migration
```bash
# Re-run migration with verbose output
sudo python3 /opt/lnmt/migrate.py migrate --source dnsmasq --verbose

# Check backup location
ls -la /var/lib/lnmt/backups/migration_*/
```

### Update Issues

#### Update Failure
```bash
# Check update logs
sudo tail -f /var/log/lnmt/update.log

# Rollback to previous version
sudo python3 /opt/lnmt/upgrade.py --rollback

# Manual rollback
sudo systemctl stop lnmt lnmt-web lnmt-scheduler
sudo rm -rf /opt/lnmt
sudo mv /opt/lnmt.backup /opt/lnmt
sudo systemctl start lnmt lnmt-web lnmt-scheduler
```

#### Network Issues During Update
```bash
# Use local update source
sudo python3 /opt/lnmt/upgrade.py --source local --package /path/to/lnmt-update.tar.gz

# Check network connectivity
curl -I https://github.com/your-org/lnmt/releases/latest
```

### Log Analysis

#### Important Log Locations
- **Installation**: `/var/log/lnmt-install.log`
- **Updates**: `/var/log/lnmt/update.log`
- **Migration**: `/var/log/lnmt/migration.log`
- **Application**: `/var/log/lnmt/lnmt.log`
- **Web Interface**: `/var/log/lnmt/web.log`

#### Log Commands
```bash
# Follow installation log
sudo tail -f /var/log/lnmt-install.log

# Check last 100 lines of application log
sudo tail -n 100 /var/log/lnmt/lnmt.log

# Search for errors
sudo grep -i error /var/log/lnmt/*.log

# System journal logs
sudo journalctl -u lnmt --since "1 hour ago"
```

## Advanced Configuration

### Custom Installation Paths

```bash
# Use environment variables to customize paths
export LNMT_HOME="/custom/lnmt"
export LNMT_CONFIG_DIR="/custom/etc/lnmt"
sudo ./install.sh
```

### Development Installation

```bash
# Development mode with editable installation
git clone https://github.com/your-org/lnmt.git
cd lnmt
sudo ./install.sh --type dev

# Or use pip in development mode
sudo pip3 install -e .
```

### Docker Deployment

```bash
# Build Docker image
docker build -t lnmt:latest .

# Run container
docker run -d \
  --name lnmt \
  --network host \
  --cap-add NET_ADMIN \
  -v /etc/lnmt:/etc/lnmt \
  -v /var/lib/lnmt:/var/lib/lnmt \
  lnmt:latest

# Docker Compose
docker-compose up -d
```

### Cluster Deployment

```bash
# Multi-node setup with shared configuration
# Node 1 (Primary)
sudo ./install.sh --type cluster --role primary

# Node 2+ (Secondary)
sudo ./install.sh --type cluster --role secondary --primary-host node1.example.com
```

## Security Considerations

### Firewall Configuration

```bash
# Allow LNMT web interface
sudo ufw allow 8080/tcp

# Allow DNS (if using LNMT DNS)
sudo ufw allow 53/udp
sudo ufw allow 53/tcp

# Restrict to specific networks
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

### SSL/TLS Configuration

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/lnmt/ssl/lnmt.key \
  -out /etc/lnmt/ssl/lnmt.crt

# Update configuration to use SSL
# Edit /etc/lnmt/lnmt.yml:
web:
  ssl:
    enabled: true
    cert_file: "/etc/lnmt/ssl/lnmt.crt"
    key_file: "/etc/lnmt/ssl/lnmt.key"
```

### User Management

```bash
# Create additional admin user
lnmt-cli user create --username newadmin --role admin

# Change default password
lnmt-cli user passwd admin

# Disable default account
lnmt-cli user disable admin
```

## Performance Tuning

### Database Optimization

```bash
# For SQLite (default)
# Edit /etc/lnmt/lnmt.yml:
database:
  type: "sqlite"
  path: "/var/lib/lnmt/db/lnmt.db"
  options:
    journal_mode: "WAL"
    synchronous: "NORMAL"
    cache_size: 10000

# For PostgreSQL (production)
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "lnmt"
  username: "lnmt"
  password: "secure_password"
```

### Resource Limits

```bash
# Edit systemd service files
sudo systemctl edit lnmt

# Add resource limits:
[Service]
MemoryLimit=1G
CPUQuota=200%
TasksMax=100
```

### Log Rotation

```bash
# Configure log rotation in /etc/logrotate.d/lnmt:
/var/log/lnmt/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 lnmt lnmt
    postrotate
        systemctl reload lnmt >/dev/null 2>&1 || true
    endscript
}
```

## Support and Community

### Getting Help

- **Documentation**: https://docs.lnmt.example.com
- **GitHub Issues**: https://github.com/your-org/lnmt/issues
- **Community Forum**: https://community.lnmt.example.com
- **Email Support**: support@lnmt.example.com

### Contributing

```bash
# Development setup
git clone https://github.com/your-org/lnmt.git
cd lnmt
pip3 install -r requirements-dev.txt
pre-commit install

# Run tests
python3 -m pytest tests/

# Submit pull request
git checkout -b feature/my-feature
git commit -m "Add new feature"
git push origin feature/my-feature
```

### Reporting Issues

When reporting issues, please include:

1. LNMT version: `lnmt-cli --version`
2. Operating system: `cat /etc/os-release`
3. Installation method: (script, manual, package)
4. Error logs: `/var/log/lnmt/*.log`
5. Configuration: `/etc/lnmt/lnmt.yml` (sanitized)
6. Steps to reproduce

### Version History

| Version | Release Date | Major Changes |
|---------|-------------|---------------|
| 1.0.0 | 2024-12-02 | Initial release |
| 1.0.1 | 2024-12-15 | Bug fixes, improved migration |
| 1.1.0 | 2025-01-15 | New modules, enhanced UI |

---

**Note**: This documentation is for LNMT v1.0.0. For the latest version, visit: https://docs.lnmt.example.com