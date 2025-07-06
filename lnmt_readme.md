# LNMT Dual-Database Architecture

A comprehensive Linux Network Management Tool (LNMT) with dual-database architecture featuring SQLite for configuration management and optional SQL database for operational data.

## Overview

LNMT implements a robust dual-database system:
- **SQLite**: Always present, stores core configuration, settings, tool paths, user data, and secrets
- **SQL Database**: Optional PostgreSQL/MySQL for operational data like device tracking, sessions, logs, and analytics
- **Automatic Fallback**: If SQL database is unavailable, operational data falls back to SQLite
- **Migration Tools**: Bidirectional data migration between SQLite and SQL databases
- **Backup System**: Automated backup and restore capabilities for both databases

## Features

### Core Configuration Management
- **System Settings**: IP addresses, ports, TLS configuration, timezone, debug settings
- **Tool Paths**: Binary paths, configuration files, log locations for all tools
- **Service Management**: Service configuration, auto-start settings, dependencies
- **User Management**: User accounts, roles, authentication settings
- **Security**: Encrypted secrets, certificates, TLS configuration
- **Network Configuration**: Interface settings, firewall rules, QoS policies

### Operational Data Management
- **Device Tracking**: MAC addresses, IP assignments, device types, last seen
- **Session Management**: User sessions, authentication tokens, activity tracking
- **Traffic Monitoring**: Network flow data, bandwidth usage, protocol analysis
- **System Logs**: Centralized logging with categorization and filtering
- **Performance Metrics**: CPU, memory, disk, network utilization
- **Analytics**: Custom metrics and performance indicators

### Advanced Features
- **Traffic Control (QoS)**: Bandwidth shaping, priority queuing, traffic classification
- **Backup & Restore**: Automated daily backups with configurable retention
- **Database Synchronization**: Real-time sync between SQLite and SQL databases
- **CLI Management**: Comprehensive command-line interface for all operations
- **Service Integration**: Systemd services with monitoring and auto-restart
- **Security Hardening**: Encrypted storage, secure authentication, audit logging

## Installation

### Prerequisites
- Linux system (Ubuntu, Debian, CentOS, Rocky Linux, Red Hat)
- Python 3.6 or higher
- Root access for installation
- Optional: PostgreSQL or MySQL server

### Quick Installation

```bash
# Download and run the installation script
curl -sSL https://raw.githubusercontent.com/lnmt/lnmt/main/install.sh | sudo bash

# Or manual installation
git clone https://github.com/lnmt/lnmt.git
cd lnmt
sudo chmod +x install.sh
sudo ./install.sh
```

### Manual Installation Steps

1. **Install System Dependencies**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv sqlite3 nginx mysql-server redis-server

# CentOS/Rocky/RHEL
sudo yum install -y python3 python3-pip sqlite nginx mysql-server redis
```

2. **Create LNMT User and Directories**
```bash
sudo useradd -r -s /bin/bash -d /opt/lnmt lnmt
sudo mkdir -p /opt/lnmt /etc/lnmt /var/log/lnmt /var/lib/lnmt/backups
sudo chown -R lnmt:lnmt /opt/lnmt /etc/lnmt /var/log/lnmt /var/lib/lnmt
```

3. **Install Python Dependencies**
```bash
cd /opt/lnmt
sudo -u lnmt python3 -m venv venv
sudo -u lnmt venv/bin/pip install psycopg2-binary pymysql bcrypt cryptography psutil
```

4. **Deploy LNMT Files**
```bash
sudo cp lnmt_db.py /opt/lnmt/
sudo cp config/*.json /etc/lnmt/
sudo chmod +x /opt/lnmt/lnmt_db.py
sudo chown -R lnmt:lnmt /opt/lnmt /etc/lnmt
```

5. **Create Systemd Services**
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lnmt lnmt-monitor lnmt-backup.timer
```

6. **Initialize Database**
```bash
sudo -u lnmt /opt/lnmt/venv/bin/python /opt/lnmt/lnmt_db.py init
```

## Configuration

### Database Configuration (`/etc/lnmt/lnmt_db_config.json`)

```json
{
  "sqlite_path": "/etc/lnmt/lnmt_config.db",
  "sql_enabled": false,
  "sql_type": "postgres",
  "sql_host": "localhost",
  "sql_port": 5432,
  "sql_database": "lnmt",
  "sql_username": "lnmt_user",
  "sql_password": "secure_password",
  "auto_sync": true,
  "sync_interval": 300,
  "backup_enabled": true,
  "backup_retention_days": 30
}
```

### Service Configuration (`/etc/lnmt/lnmt_services.json`)

```json
{
  "services": [
    {
      "name": "nginx",
      "enabled": true,
      "port": 80,
      "ssl_port": 443,
      "config_path": "/etc/nginx/nginx.conf",
      "binary_path": "/usr/sbin/nginx",
      "log_path": "/var/log/nginx",
      "auto_start": true,
      "dependencies": []
    }
  ]
}
```

### Network Configuration (`/etc/lnmt/lnmt_network.json`)

```json
{
  "interfaces": [
    {
      "name": "eth0",
      "ip_address": "192.168.1.100",
      "netmask": "255.255.255.0",
      "gateway": "192.168.1.1",
      "dns_servers": ["8.8.8.8", "8.8.4.4"],
      "enabled": true
    }
  ],
  "firewall": {
    "enabled": true,
    "default_policy": "DROP",
    "rules": [
      {
        "name": "allow_ssh",
        "action": "ACCEPT",
        "protocol": "tcp",
        "port": 22,
        "source": "any",
        "enabled": true
      }
    ]
  }
}
```

## Usage

### Command Line Interface

```bash
# Configuration Management
lnmt config                     # Show current configuration
lnmt list-tools                 # List configured tools
lnmt list-services              # List configured services

# Database Operations
lnmt migrate-to-sql             # Migrate operational data to SQL
lnmt migrate-to-sqlite          # Migrate operational data to SQLite
lnmt sync                       # Synchronize databases

# Backup Operations
lnmt backup-sqlite              # Backup SQLite database
lnmt backup-sql                 # Backup SQL database
lnmt restore-sqlite <file>      # Restore SQLite from backup

# Service Management
systemctl status lnmt           # Check service status
systemctl restart lnmt         # Restart main service
systemctl logs lnmt            # View service logs
```

### Python API

```python
from lnmt_db import initialize_lnmt_database

# Initialize database connection
db = initialize_lnmt_database()

# Configuration Management
debug_mode = db.get_config('system.debug', False)
db.set_config('system.debug', True, 'boolean')

# Tool Management
nginx_config = db.get_tool_path('nginx')
db.set_tool_path('nginx', '/usr/sbin/nginx', '/etc/nginx/nginx.conf')

# Service Management
service_config = db.get_service_config('nginx')
db.set_service_config('nginx', enabled=True, port=80, auto_start=True)

# Operational Data
db.log_device('00:11:22:33:44:55', '192.168.1.100', 'server-01')
db.log_system_event('INFO', 'system', 'Service started', {'service': 'nginx'})
db.record_performance_metric(cpu_usage=45.2, memory_usage=67.8)

# Retrieve Data
recent_logs = db.get_recent_logs(limit=100, level='ERROR')
```

## Database Schema

### SQLite Tables (Core Configuration)

- **system_config**: System-wide configuration settings
- **network_config**: Network interface configuration
- **service_config**: Service definitions and settings
- **tool_paths**: Binary and configuration file paths
- **users**: User accounts and authentication
- **secrets**: Encrypted secrets and certificates
- **tls_config**: TLS/SSL certificate configuration
- **qos_config**: Quality of Service rules
- **backup_config**: Backup job configuration
- **config_changes**: Configuration change audit log

### SQL Tables (Operational Data)

- **devices**: Network device tracking
- **sessions**: User session management
- **traffic_logs**: Network traffic monitoring
- **system_logs**: Application and system logs
- **analytics**: Custom metrics and analytics
- **performance_metrics**: System performance data

## Architecture Overview

### Database Architecture

```
┌─────────────────────────────────────────┐
│                 LNMT                    │
├─────────────────────────────────────────┤
│         Application Layer               │
├─────────────────────────────────────────┤
│         Database Manager                │
├─────────────┬───────────────────────────┤
│   SQLite    │      SQL Database         │
│ (Required)  │      (Optional)          │
│             │                          │
│ • Config    │ • Device Tracking        │
│ • Settings  │ • Session Data           │
│ • Tools     │ • Traffic Logs           │
│ • Users     │ • System Logs            │
│ • Secrets   │ • Performance Metrics    │
│ • Network   │ • Analytics              │
│ • QoS       │                          │
│ • Backups   │                          │
└─────────────┴───────────────────────────┘
```

### Data Flow

1. **Configuration Data**: Always stored in SQLite
2. **Operational Data**: Stored in SQL if enabled, otherwise SQLite
3. **Synchronization**: Bidirectional sync between databases
4. **Backup**: Automated backup of both databases
5. **Migration**: Tools for moving data between databases

## Traffic Control (QoS) Module

### Configuration

```python
# Add QoS rule
db.sqlite_conn.execute("""
    INSERT INTO qos_config (rule_name, interface, protocol, port, bandwidth_limit, priority, enabled)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('web_priority', 'eth0', 'tcp', 80, 10000000, 1, True))

# Apply QoS rules using Linux tc (traffic control)
def apply_qos_rules():
    cursor = db.sqlite_conn.cursor()
    cursor.execute("SELECT * FROM qos_config WHERE enabled = 1")
    
    for rule in cursor.fetchall():
        interface = rule[2]
        bandwidth = rule[7]
        priority = rule[8]
        
        # Create HTB queueing discipline
        subprocess.run([
            'tc', 'qdisc', 'add', 'dev', interface, 'root', 'handle', '1:', 'htb', 'default', '30'
        ])
        
        # Create class with bandwidth limit
        subprocess.run([
            'tc', 'class', 'add', 'dev', interface, 'parent', '1:', 'classid', f'1:{priority}', 
            'htb', 'rate', f'{bandwidth}bit'
        ])
```

### QoS Rules Management

```bash
# List current QoS rules
lnmt qos list

# Add QoS rule
lnmt qos add --name web_priority --interface eth0 --protocol tcp --port 80 --bandwidth 10mbit --priority 1

# Remove QoS rule
lnmt qos remove --name web_priority

# Apply QoS rules
lnmt qos apply

# Show traffic statistics
lnmt qos stats
```

## Monitoring and Alerting

### System Monitoring

```python
import psutil
import threading
import time

def monitor_system(db_manager):
    """Continuous system monitoring"""
    while True:
        # Collect metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Record metrics
        db_manager.record_performance_metric(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=(disk.used / disk.total) * 100,
            network_rx_bytes=network.bytes_recv,
            network_tx_bytes=network.bytes_sent,
            active_connections=len(psutil.net_connections())
        )
        
        # Check thresholds and send alerts
        check_thresholds(db_manager, cpu_percent, memory.percent, (disk.used / disk.total) * 100)
        
        time.sleep(60)

def check_thresholds(db_manager, cpu, memory, disk):
    """Check metrics against thresholds"""
    alerts = []
    
    if cpu > 80:
        alerts.append(f"High CPU usage: {cpu:.1f}%")
    if memory > 85:
        alerts.append(f"High memory usage: {memory:.1f}%")
    if disk > 90:
        alerts.append(f"High disk usage: {disk:.1f}%")
    
    for alert in alerts:
        db_manager.log_system_event('WARNING', 'monitoring', alert)
        send_alert_notification(alert)
```

### Alert Configuration

```json
{
  "alerts": {
    "enabled": true,
    "thresholds": {
      "cpu_usage": 80,
      "memory_usage": 85,
      "disk_usage": 90,
      "network_bandwidth": 80
    },
    "notifications": {
      "email": {
        "enabled": true,
        "smtp_server": "localhost",
        "smtp_port": 25,
        "from": "lnmt@example.com",
        "to": ["admin@example.com"]
      },
      "webhook": {
        "enabled": false,
        "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
      }
    }
  }
}
```

## Security Features

### Authentication and Authorization

```python
import bcrypt
import secrets
import jwt
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.secret_key = self.get_or_create_secret_key()
    
    def create_user(self, username, password, email, role='user'):
        """Create new user with hashed password"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        with self.db.lock:
            cursor = self.db.sqlite_conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, role, enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (username, password_hash.decode('utf-8'), email, role, True))
            self.db.sqlite_conn.commit()
    
    def authenticate(self, username, password):
        """Authenticate user and return JWT token"""
        with self.db.lock:
            cursor = self.db.sqlite_conn.cursor()
            cursor.execute("""
                SELECT id, password_hash, role, enabled FROM users 
                WHERE username = ?
            """, (username,))
            user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            if user[3]:  # enabled
                # Generate JWT token
                payload = {
                    'user_id': user[0],
                    'username': username,
                    'role': user[2],
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }
                token = jwt.encode(payload, self.secret_key, algorithm='HS256')
                
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (user[0],))
                self.db.sqlite_conn.commit()
                
                return token
        
        return None
    
    def get_or_create_secret_key(self):
        """Get or create JWT secret key"""
        with self.db.lock:
            cursor = self.db.sqlite_conn.cursor()
            cursor.execute("SELECT encrypted_value FROM secrets WHERE key_name = 'jwt_secret'")
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                secret = secrets.token_hex(32)
                cursor.execute("""
                    INSERT INTO secrets (key_name, encrypted_value, key_type)
                    VALUES (?, ?, ?)
                """, ('jwt_secret', secret, 'jwt'))
                self.db.sqlite_conn.commit()
                return secret
```

### TLS/SSL Management

```python
import ssl
import subprocess
from datetime import datetime
import OpenSSL.crypto

class TLSManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_certificate(self, domain, cert_path, key_path, auto_renew=True):
        """Add TLS certificate configuration"""
        # Get certificate expiry date
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_data)
            expires_at = datetime.strptime(cert.get_notAfter().decode('utf-8'), '%Y%m%d%H%M%SZ')
        
        with self.db.lock:
            cursor = self.db.sqlite_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tls_config 
                (domain, cert_path, key_path, auto_renew, expires_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (domain, cert_path, key_path, auto_renew, expires_at, True))
            self.db.sqlite_conn.commit()
    
    def check_certificate_expiry(self):
        """Check for certificates expiring soon"""
        with self.db.lock:
            cursor = self.db.sqlite_conn.cursor()
            cursor.execute("""
                SELECT domain, cert_path, expires_at FROM tls_config 
                WHERE enabled = 1 AND expires_at < datetime('now', '+30 days')
            """)
            
            expiring_certs = cursor.fetchall()
            for domain, cert_path, expires_at in expiring_certs:
                self.db.log_system_event('WARNING', 'tls', 
                    f'Certificate for {domain} expires on {expires_at}')
                
                # Auto-renew if enabled
                if self.auto_renew_enabled(domain):
                    self.renew_certificate(domain)
    
    def renew_certificate(self, domain):
        """Renew certificate using Let's Encrypt"""
        try:
            # Use certbot to renew certificate
            result = subprocess.run([
                'certbot', 'renew', '--domain', domain, '--quiet'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.db.log_system_event('INFO', 'tls', 
                    f'Certificate renewed successfully for {domain}')
                # Update database with new expiry date
                self.update_certificate_expiry(domain)
            else:
                self.db.log_system_event('ERROR', 'tls', 
                    f'Certificate renewal failed for {domain}: {result.stderr}')
        except Exception as e:
            self.db.log_system_event('ERROR', 'tls', 
                f'Certificate renewal error for {domain}: {str(e)}')
```

## Migration and Backup

### Database Migration

```python
class DatabaseMigrator:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def migrate_sqlite_to_sql(self):
        """Migrate operational data from SQLite to SQL"""
        if not self.db.config.sql_enabled:
            return False
        
        operational_tables = [
            'devices', 'sessions', 'traffic_logs', 'system_logs',
            'analytics', 'performance_metrics'
        ]
        
        try:
            with self.db.lock:
                sqlite_cursor = self.db.sqlite_conn.cursor()
                sql_cursor = self.db.sql_conn.cursor()
                
                for table in operational_tables:
                    # Check if table exists in SQLite
                    sqlite_cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    
                    if sqlite_cursor.fetchone():
                        # Get data from SQLite
                        sqlite_cursor.execute(f"SELECT * FROM {table}")
                        rows = sqlite_cursor.fetchall()
                        
                        if rows:
                            # Get column names
                            columns = [desc[0] for desc in sqlite_cursor.description]
                            
                            # Prepare SQL insert
                            placeholders = ', '.join(['%s'] * len(columns))
                            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                            
                            # Insert data
                            for row in rows:
                                sql_cursor.execute(insert_sql, row)
                            
                            self.logger.info(f"Migrated {len(rows)} rows from {table}")
                
                self.db.sql_conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False
    
    def sync_databases(self):
        """Bidirectional synchronization between databases"""
        if not self.db.config.sql_enabled:
            return False
        
        try:
            # Sync from SQLite to SQL (newer records)
            self.sync_newer_records('sqlite_to_sql')
            
            # Sync from SQL to SQLite (newer records)
            self.sync_newer_records('sql_to_sqlite')
            
            return True
        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            return False
    
    def sync_newer_records(self, direction):
        """Sync newer records between databases"""
        # Implementation for incremental sync based on timestamps
        pass
```

### Backup System

```python
class BackupManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def create_full_backup(self):
        """Create full system backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"/var/lib/lnmt/backups/full_{timestamp}"
        
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup SQLite database
            sqlite_backup = f"{backup_dir}/config.db"
            shutil.copy2(self.db.config.sqlite_path, sqlite_backup)
            
            # Backup SQL database if enabled
            if self.db.config.sql_enabled:
                sql_backup = f"{backup_dir}/operational.sql"
                self.backup_sql_database(sql_backup)
            
            # Backup configuration files
            config_backup = f"{backup_dir}/config.tar.gz"
            self.backup_configuration_files(config_backup)
            
            # Create backup manifest
            manifest = {
                'timestamp': timestamp,
                'sqlite_backup': sqlite_backup,
                'sql_backup': sql_backup if self.db.config.sql_enabled else None,
                'config_backup': config_backup,
                'lnmt_version': self.get_lnmt_version()
            }
            
            with open(f"{backup_dir}/manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Full backup created: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return None
    
    def restore_from_backup(self, backup_dir):
        """Restore system from backup"""
        try:
            # Read manifest
            with open(f"{backup_dir}/manifest.json", 'r') as f:
                manifest = json.load(f)
            
            # Stop services
            subprocess.run(['systemctl', 'stop', 'lnmt', 'lnmt-monitor'])
            
            # Restore SQLite database
            if os.path.exists(manifest['sqlite_backup']):
                shutil.copy2(manifest['sqlite_backup'], self.db.config.sqlite_path)
            
            # Restore SQL database if present
            if manifest['sql_backup'] and os.path.exists(manifest['sql_backup']):
                self.restore_sql_database(manifest['sql_backup'])
            
            # Restore configuration files
            if os.path.exists(manifest['config_backup']):
                self.restore_configuration_files(manifest['config_backup'])
            
            # Start services
            subprocess.run(['systemctl', 'start', 'lnmt', 'lnmt-monitor'])
            
            self.logger.info(f"Restore completed from: {backup_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False
    
    def cleanup_old_backups(self, retention_days=30):
        """Remove old backups"""
        backup_base = "/var/lib/lnmt/backups"
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        
        for item in os.listdir(backup_base):
            item_path = os.path.join(backup_base, item)
            if os.path.isdir(item_path) and os.path.getmtime(item_path) < cutoff_time:
                shutil.rmtree(item_path)
                self.logger.info(f"Removed old backup: {item}")
```

## Performance Optimization

### Database Optimization

```python
def optimize_sqlite_performance(db_conn):
    """Optimize SQLite performance"""
    optimizations = [
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = NORMAL", 
        "PRAGMA cache_size = 10000",
        "PRAGMA temp_store = MEMORY",
        "PRAGMA mmap_size = 268435456",  # 256MB
        "PRAGMA optimize"
    ]
    
    for pragma in optimizations:
        db_conn.execute(pragma)

def optimize_postgresql_performance(db_conn):
    """Optimize PostgreSQL performance"""
    optimizations = [
        "SET work_mem = '256MB'",
        "SET maintenance_work_mem = '256MB'",
        "SET effective_cache_size = '1GB'",
        "SET random_page_cost = 1.1",
        "SET checkpoint_completion_target = 0.9"
    ]
    
    cursor = db_conn.cursor()
    for setting in optimizations:
        cursor.execute(setting)
```

### Monitoring Performance

```python
def monitor_database_performance(db_manager):
    """Monitor database query performance"""
    # SQLite monitoring
    sqlite_stats = db_manager.sqlite_conn.execute("""
        SELECT name, sql FROM sqlite_master WHERE type='table'
    """).fetchall()
    
    # Log slow queries
    db_manager.sqlite_conn.set_trace_callback(log_slow_queries)
    
    # PostgreSQL monitoring (if enabled)
    if db_manager.config.sql_enabled and db_manager.config.sql_type == 'postgres':
        cursor = db_manager.sql_conn.cursor()
        cursor.execute("""
            SELECT query, mean_time, calls, total_time
            FROM pg_stat_statements
            WHERE mean_time > 100
            ORDER BY mean_time DESC
            LIMIT 10
        """)
        slow_queries = cursor.fetchall()
        
        for query, mean_time, calls, total_time in slow_queries:
            db_manager.log_system_event('WARNING', 'performance',
                f'Slow query detected: {mean_time}ms avg, {calls} calls')

def log_slow_queries(query):
    """Log slow SQLite queries"""
    # This would be called for each SQLite query
    # Implement timing logic here
    pass
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
```bash
# Check database connectivity
lnmt config

# Test SQL database connection
lnmt test-sql-connection

# Check database permissions
ls -la /etc/lnmt/lnmt_config.db
```

2. **Service Issues**
```bash
# Check service status
systemctl status lnmt lnmt-monitor

# View service logs
journalctl -u lnmt -f

# Check configuration
lnmt config --validate
```

3. **Performance Issues**
```bash
# Monitor system resources
htop
iotop

# Check database performance
lnmt performance --database

# Optimize databases
lnmt optimize --database
```

### Debug Mode

```bash
# Enable debug logging
lnmt config set system.debug true

# View debug logs
tail -f /var/log/lnmt/system.log

# Run in debug mode
DEBUG=1 lnmt config
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/lnmt/lnmt.git
cd lnmt

# Create development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Code formatting
black lnmt_db.py
flake8 lnmt_db.py
```

### Testing

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run performance tests
python -m pytest tests/performance/

# Generate coverage report
pytest --cov=lnmt_db --cov-report=html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: https://lnmt.readthedocs.io
- Issues: https://github.com/lnmt/lnmt/issues
- Discussions: https://github.com/lnmt/lnmt/discussions
- Email: support@lnmt.org

## Changelog

### Version 1.0.0
- Initial release with dual-database architecture
- SQLite configuration management
- Optional PostgreSQL/MySQL support
- Traffic Control (QoS) integration
- Comprehensive backup system
- CLI management interface
- Systemd service integration
- Security hardening features