# LNMT Dual-Database Architecture Implementation
# Core Database Manager with SQLite (always) + SQL (optional) support

import sqlite3
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import hashlib

# Optional SQL database imports (install as needed)
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

@dataclass
class DatabaseConfig:
    """Configuration for dual database setup"""
    # SQLite (always present)
    sqlite_path: str = "lnmt_config.db"
    
    # SQL Database (optional)
    sql_enabled: bool = False
    sql_type: str = "postgres"  # postgres, mysql
    sql_host: str = "localhost"
    sql_port: int = 5432
    sql_database: str = "lnmt"
    sql_username: str = ""
    sql_password: str = ""
    sql_pool_size: int = 5
    
    # Sync settings
    auto_sync: bool = True
    sync_interval: int = 300  # 5 minutes
    backup_enabled: bool = True
    backup_retention_days: int = 30

class DatabaseManager:
    """Manages dual SQLite + SQL database architecture"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.sqlite_conn = None
        self.sql_conn = None
        self.sql_pool = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize databases
        self.init_sqlite()
        if self.config.sql_enabled:
            self.init_sql()
    
    def init_sqlite(self):
        """Initialize SQLite database (always present)"""
        try:
            self.sqlite_conn = sqlite3.connect(
                self.config.sqlite_path,
                check_same_thread=False,
                timeout=30.0
            )
            self.sqlite_conn.row_factory = sqlite3.Row
            self.sqlite_conn.execute("PRAGMA foreign_keys = ON")
            self.sqlite_conn.execute("PRAGMA journal_mode = WAL")
            
            # Create core configuration tables
            self.create_sqlite_schema()
            self.populate_default_config()
            
            self.logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite: {e}")
            raise
    
    def init_sql(self):
        """Initialize SQL database connection (optional)"""
        if not self.config.sql_enabled:
            return
            
        try:
            if self.config.sql_type == "postgres" and POSTGRES_AVAILABLE:
                self.sql_conn = psycopg2.connect(
                    host=self.config.sql_host,
                    port=self.config.sql_port,
                    database=self.config.sql_database,
                    user=self.config.sql_username,
                    password=self.config.sql_password
                )
                
            elif self.config.sql_type == "mysql" and MYSQL_AVAILABLE:
                self.sql_conn = pymysql.connect(
                    host=self.config.sql_host,
                    port=self.config.sql_port,
                    database=self.config.sql_database,
                    user=self.config.sql_username,
                    password=self.config.sql_password,
                    charset='utf8mb4'
                )
            
            if self.sql_conn:
                self.create_sql_schema()
                self.logger.info(f"SQL database ({self.config.sql_type}) initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SQL database: {e}")
            self.config.sql_enabled = False
    
    def create_sqlite_schema(self):
        """Create SQLite schema for core configuration"""
        schema_sql = """
        -- Core system configuration (always in SQLite)
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            type TEXT DEFAULT 'string',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Network configuration
        CREATE TABLE IF NOT EXISTS network_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interface TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            netmask TEXT NOT NULL,
            gateway TEXT,
            dns_servers TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Service configuration
        CREATE TABLE IF NOT EXISTS service_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            port INTEGER,
            config_path TEXT,
            binary_path TEXT,
            log_path TEXT,
            auto_start BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tool paths and binaries
        CREATE TABLE IF NOT EXISTS tool_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT UNIQUE NOT NULL,
            binary_path TEXT NOT NULL,
            config_path TEXT,
            log_path TEXT,
            enabled BOOLEAN DEFAULT 1,
            version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- User management
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            enabled BOOLEAN DEFAULT 1,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Secrets and certificates
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_name TEXT UNIQUE NOT NULL,
            encrypted_value TEXT NOT NULL,
            key_type TEXT DEFAULT 'generic',
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- TLS/SSL configuration
        CREATE TABLE IF NOT EXISTS tls_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            cert_path TEXT NOT NULL,
            key_path TEXT NOT NULL,
            ca_path TEXT,
            enabled BOOLEAN DEFAULT 1,
            auto_renew BOOLEAN DEFAULT 1,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- QoS/Traffic Control configuration
        CREATE TABLE IF NOT EXISTS qos_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT UNIQUE NOT NULL,
            interface TEXT NOT NULL,
            source_ip TEXT,
            dest_ip TEXT,
            protocol TEXT,
            port INTEGER,
            bandwidth_limit INTEGER,
            priority INTEGER DEFAULT 0,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Backup configuration
        CREATE TABLE IF NOT EXISTS backup_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            dest_path TEXT NOT NULL,
            schedule TEXT,
            retention_days INTEGER DEFAULT 30,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Configuration change log
        CREATE TABLE IF NOT EXISTS config_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_by TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Triggers for updated_at timestamps
        CREATE TRIGGER IF NOT EXISTS update_system_config_timestamp 
            AFTER UPDATE ON system_config
            BEGIN
                UPDATE system_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_network_config_timestamp 
            AFTER UPDATE ON network_config
            BEGIN
                UPDATE network_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_service_config_timestamp 
            AFTER UPDATE ON service_config
            BEGIN
                UPDATE service_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_tool_paths_timestamp 
            AFTER UPDATE ON tool_paths
            BEGIN
                UPDATE tool_paths SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_users_timestamp 
            AFTER UPDATE ON users
            BEGIN
                UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_secrets_timestamp 
            AFTER UPDATE ON secrets
            BEGIN
                UPDATE secrets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_tls_config_timestamp 
            AFTER UPDATE ON tls_config
            BEGIN
                UPDATE tls_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_qos_config_timestamp 
            AFTER UPDATE ON qos_config
            BEGIN
                UPDATE qos_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_backup_config_timestamp 
            AFTER UPDATE ON backup_config
            BEGIN
                UPDATE backup_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        """
        
        with self.lock:
            cursor = self.sqlite_conn.cursor()
            cursor.executescript(schema_sql)
            self.sqlite_conn.commit()
    
    def create_sql_schema(self):
        """Create SQL schema for operational data"""
        if not self.sql_conn:
            return
        
        # Adjust schema based on SQL type
        if self.config.sql_type == "postgres":
            schema_sql = """
            -- Device tracking (operational data)
            CREATE TABLE IF NOT EXISTS devices (
                id SERIAL PRIMARY KEY,
                mac_address VARCHAR(17) UNIQUE NOT NULL,
                ip_address INET,
                hostname VARCHAR(255),
                device_type VARCHAR(50),
                vendor VARCHAR(100),
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                metadata JSONB
            );
            
            -- Session tracking
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                device_id INTEGER REFERENCES devices(id),
                user_id INTEGER,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address INET NOT NULL,
                user_agent TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active'
            );
            
            -- Network traffic logs
            CREATE TABLE IF NOT EXISTS traffic_logs (
                id SERIAL PRIMARY KEY,
                device_id INTEGER REFERENCES devices(id),
                src_ip INET NOT NULL,
                dst_ip INET NOT NULL,
                src_port INTEGER,
                dst_port INTEGER,
                protocol VARCHAR(10),
                bytes_sent BIGINT DEFAULT 0,
                bytes_received BIGINT DEFAULT 0,
                packets_sent INTEGER DEFAULT 0,
                packets_received INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- System logs
            CREATE TABLE IF NOT EXISTS system_logs (
                id SERIAL PRIMARY KEY,
                level VARCHAR(10) NOT NULL,
                category VARCHAR(50),
                message TEXT NOT NULL,
                details JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Analytics data
            CREATE TABLE IF NOT EXISTS analytics (
                id SERIAL PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value NUMERIC,
                metadata JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Performance metrics
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id SERIAL PRIMARY KEY,
                cpu_usage NUMERIC(5,2),
                memory_usage NUMERIC(5,2),
                disk_usage NUMERIC(5,2),
                network_rx_bytes BIGINT,
                network_tx_bytes BIGINT,
                active_connections INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac_address);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
            CREATE INDEX IF NOT EXISTS idx_traffic_logs_timestamp ON traffic_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
            """
        
        elif self.config.sql_type == "mysql":
            schema_sql = """
            -- Device tracking (operational data)
            CREATE TABLE IF NOT EXISTS devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mac_address VARCHAR(17) UNIQUE NOT NULL,
                ip_address VARCHAR(45),
                hostname VARCHAR(255),
                device_type VARCHAR(50),
                vendor VARCHAR(100),
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                metadata JSON
            );
            
            -- Session tracking
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT,
                user_id INT,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                user_agent TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                ended_at TIMESTAMP NULL,
                status VARCHAR(20) DEFAULT 'active',
                FOREIGN KEY (device_id) REFERENCES devices(id)
            );
            
            -- Network traffic logs
            CREATE TABLE IF NOT EXISTS traffic_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT,
                src_ip VARCHAR(45) NOT NULL,
                dst_ip VARCHAR(45) NOT NULL,
                src_port INT,
                dst_port INT,
                protocol VARCHAR(10),
                bytes_sent BIGINT DEFAULT 0,
                bytes_received BIGINT DEFAULT 0,
                packets_sent INT DEFAULT 0,
                packets_received INT DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            );
            
            -- System logs
            CREATE TABLE IF NOT EXISTS system_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                level VARCHAR(10) NOT NULL,
                category VARCHAR(50),
                message TEXT NOT NULL,
                details JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Analytics data
            CREATE TABLE IF NOT EXISTS analytics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(15,4),
                metadata JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Performance metrics
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cpu_usage DECIMAL(5,2),
                memory_usage DECIMAL(5,2),
                disk_usage DECIMAL(5,2),
                network_rx_bytes BIGINT,
                network_tx_bytes BIGINT,
                active_connections INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes
            CREATE INDEX idx_devices_mac ON devices(mac_address);
            CREATE INDEX idx_sessions_token ON sessions(session_token);
            CREATE INDEX idx_traffic_logs_timestamp ON traffic_logs(timestamp);
            CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
            CREATE INDEX idx_analytics_timestamp ON analytics(timestamp);
            CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);
            """
        
        try:
            cursor = self.sql_conn.cursor()
            cursor.execute(schema_sql)
            self.sql_conn.commit()
            self.logger.info("SQL schema created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create SQL schema: {e}")
    
    def populate_default_config(self):
        """Populate default configuration values"""
        default_configs = [
            # System configuration
            ('system.version', '1.0.0', 'string', 'LNMT System Version'),
            ('system.debug', 'false', 'boolean', 'Debug mode enabled'),
            ('system.timezone', 'UTC', 'string', 'System timezone'),
            ('system.log_level', 'INFO', 'string', 'Default log level'),
            
            # Network configuration
            ('network.management_ip', '192.168.1.1', 'string', 'Management IP address'),
            ('network.management_port', '8080', 'integer', 'Management web port'),
            ('network.ssh_port', '22', 'integer', 'SSH port'),
            ('network.enable_ipv6', 'false', 'boolean', 'Enable IPv6 support'),
            
            # Security configuration
            ('security.enable_tls', 'true', 'boolean', 'Enable TLS/SSL'),
            ('security.session_timeout', '3600', 'integer', 'Session timeout in seconds'),
            ('security.max_login_attempts', '5', 'integer', 'Maximum login attempts'),
            ('security.password_min_length', '8', 'integer', 'Minimum password length'),
            
            # Service configuration
            ('services.auto_start', 'true', 'boolean', 'Auto-start services on boot'),
            ('services.restart_on_failure', 'true', 'boolean', 'Restart services on failure'),
            ('services.max_restarts', '3', 'integer', 'Maximum restart attempts'),
            
            # Monitoring configuration
            ('monitoring.enable_metrics', 'true', 'boolean', 'Enable performance metrics'),
            ('monitoring.metrics_interval', '60', 'integer', 'Metrics collection interval'),
            ('monitoring.log_retention_days', '30', 'integer', 'Log retention period'),
            
            # Backup configuration
            ('backup.auto_backup', 'true', 'boolean', 'Enable automatic backups'),
            ('backup.backup_interval', '86400', 'integer', 'Backup interval in seconds'),
            ('backup.max_backups', '7', 'integer', 'Maximum number of backups to keep'),
        ]
        
        # Default tool paths
        default_tools = [
            ('nginx', '/usr/sbin/nginx', '/etc/nginx/nginx.conf', '/var/log/nginx'),
            ('mysql', '/usr/bin/mysql', '/etc/mysql/my.cnf', '/var/log/mysql'),
            ('php-fpm', '/usr/sbin/php-fpm', '/etc/php/fpm/pool.d/www.conf', '/var/log/php-fpm'),
            ('redis', '/usr/bin/redis-server', '/etc/redis/redis.conf', '/var/log/redis'),
            ('memcached', '/usr/bin/memcached', '/etc/memcached.conf', '/var/log/memcached'),
            ('postfix', '/usr/sbin/postfix', '/etc/postfix/main.cf', '/var/log/mail'),
            ('dovecot', '/usr/sbin/dovecot', '/etc/dovecot/dovecot.conf', '/var/log/dovecot'),
            ('iptables', '/sbin/iptables', '/etc/iptables/rules.v4', '/var/log/iptables'),
            ('tc', '/sbin/tc', '/etc/tc/tc.conf', '/var/log/tc'),
            ('fail2ban', '/usr/bin/fail2ban-server', '/etc/fail2ban/jail.conf', '/var/log/fail2ban'),
        ]
        
        # Default services
        default_services = [
            ('nginx', True, 80, '/etc/nginx/nginx.conf', '/usr/sbin/nginx', '/var/log/nginx/access.log', True),
            ('mysql', True, 3306, '/etc/mysql/my.cnf', '/usr/bin/mysqld', '/var/log/mysql/error.log', True),
            ('php-fpm', True, 9000, '/etc/php/fpm/pool.d/www.conf', '/usr/sbin/php-fpm', '/var/log/php-fpm.log', True),
            ('redis', True, 6379, '/etc/redis/redis.conf', '/usr/bin/redis-server', '/var/log/redis/redis.log', True),
            ('memcached', True, 11211, '/etc/memcached.conf', '/usr/bin/memcached', '/var/log/memcached.log', True),
            ('postfix', False, 25, '/etc/postfix/main.cf', '/usr/sbin/postfix', '/var/log/mail.log', False),
            ('dovecot', False, 143, '/etc/dovecot/dovecot.conf', '/usr/sbin/dovecot', '/var/log/dovecot.log', False),
        ]
        
        with self.lock:
            cursor = self.sqlite_conn.cursor()
            
            # Insert default system configuration
            for key, value, type_, description in default_configs:
                cursor.execute("""
                    INSERT OR IGNORE INTO system_config (key, value, type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, value, type_, description))
            
            # Insert default tool paths
            for tool_name, binary_path, config_path, log_path in default_tools:
                cursor.execute("""
                    INSERT OR IGNORE INTO tool_paths (tool_name, binary_path, config_path, log_path)
                    VALUES (?, ?, ?, ?)
                """, (tool_name, binary_path, config_path, log_path))
            
            # Insert default services
            for service_name, enabled, port, config_path, binary_path, log_path, auto_start in default_services:
                cursor.execute("""
                    INSERT OR IGNORE INTO service_config 
                    (service_name, enabled, port, config_path, binary_path, log_path, auto_start)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (service_name, enabled, port, config_path, binary_path, log_path, auto_start))
            
            self.sqlite_conn.commit()
    
    # Configuration management methods
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from SQLite"""
        with self.lock:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT value, type FROM system_config WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                value, type_ = result
                if type_ == 'boolean':
                    return value.lower() in ('true', '1', 'yes', 'on')
                elif type_ == 'integer':
                    return int(value)
                elif type_ == 'float':
                    return float(value)
                elif type_ == 'json':
                    return json.loads(value)
                else:
                    return value
            return default
    
    def set_config(self, key: str, value: Any, type_: str = 'string', description: str = '') -> bool:
        """Set configuration value in SQLite"""
        try:
            with self.lock:
                cursor = self.sqlite_conn.cursor()
                
                # Convert value to string for storage
                if type_ == 'json':
                    str_value = json.dumps(value)
                else:
                    str_value = str(value)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO system_config (key, value, type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, str_value, type_, description))
                
                self.sqlite_conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to set config {key}: {e}")
            return False
    
    def get_tool_path(self, tool_name: str) -> Optional[Dict[str, str]]:
        """Get tool configuration from SQLite"""
        with self.lock:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("""
                SELECT binary_path, config_path, log_path, enabled, version
                FROM tool_paths WHERE tool_name = ?
            """, (tool_name,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'binary_path': result[0],
                    'config_path': result[1],
                    'log_path': result[2],
                    'enabled': bool(result[3]),
                    'version': result[4]
                }
            return None
    
    def set_tool_path(self, tool_name: str, binary_path: str, config_path: str = '', 
                     log_path: str = '', enabled: bool = True, version: str = '') -> bool:
        """Set tool configuration in SQLite"""
        try:
            with self.lock:
                cursor = self.sqlite_conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tool_paths 
                    (tool_name, binary_path, config_path, log_path, enabled, version)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tool_name, binary_path, config_path, log_path, enabled, version))
                
                self.sqlite_conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to set tool path for {tool_name}: {e}")
            return False
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service configuration from SQLite"""
        with self.lock:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("""
                SELECT enabled, port, config_path, binary_path, log_path, auto_start
                FROM service_config WHERE service_name = ?
            """, (service_name,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'enabled': bool(result[0]),
                    'port': result[1],
                    'config_path': result[2],
                    'binary_path': result[3],
                    'log_path': result[4],
                    'auto_start': bool(result[5])
                }
            return None
    
    def set_service_config(self, service_name: str, enabled: bool = True, port: int = None,
                          config_path: str = '', binary_path: str = '', log_path: str = '',
                          auto_start: bool = True) -> bool:
        """Set service configuration in SQLite"""
        try:
            with self.lock:
                cursor = self.sqlite_conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO service_config 
                    (service_name, enabled, port, config_path, binary_path, log_path, auto_start)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (service_name, enabled, port, config_path, binary_path, log_path, auto_start))
                
                self.sqlite_conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to set service config for {service_name}: {e}")
            return False
    
    # Operational data methods (SQL database if enabled, fallback to SQLite)
    def log_device(self, mac_address: str, ip_address: str = None, hostname: str = None,
                   device_type: str = None, vendor: str = None, metadata: Dict = None) -> bool:
        """Log device information to operational database"""
        try:
            if self.config.sql_enabled and self.sql_conn:
                # Use SQL database
                cursor = self.sql_conn.cursor()
                if self.config.sql_type == "postgres":
                    cursor.execute("""
                        INSERT INTO devices (mac_address, ip_address, hostname, device_type, vendor, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (mac_address) DO UPDATE SET
                        ip_address = EXCLUDED.ip_address,
                        hostname = EXCLUDED.hostname,
                        device_type = EXCLUDED.device_type,
                        vendor = EXCLUDED.vendor,
                        metadata = EXCLUDED.metadata,
                        last_seen = CURRENT_TIMESTAMP
                    """, (mac_address, ip_address, hostname, device_type, vendor, 
                         json.dumps(metadata) if metadata else None))
                elif self.config.sql_type == "mysql":
                    cursor.execute("""
                        INSERT INTO devices (mac_address, ip_address, hostname, device_type, vendor, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        ip_address = VALUES(ip_address),
                        hostname = VALUES(hostname),
                        device_type = VALUES(device_type),
                        vendor = VALUES(vendor),
                        metadata = VALUES(metadata),
                        last_seen = CURRENT_TIMESTAMP
                    """, (mac_address, ip_address, hostname, device_type, vendor,
                         json.dumps(metadata) if metadata else None))
                self.sql_conn.commit()
            else:
                # Fallback to SQLite
                with self.lock:
                    cursor = self.sqlite_conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS devices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            mac_address TEXT UNIQUE NOT NULL,
                            ip_address TEXT,
                            hostname TEXT,
                            device_type TEXT,
                            vendor TEXT,
                            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status TEXT DEFAULT 'active',
                            metadata TEXT
                        )
                    """)
                    cursor.execute("""
                        INSERT OR REPLACE INTO devices 
                        (mac_address, ip_address, hostname, device_type, vendor, metadata, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (mac_address, ip_address, hostname, device_type, vendor,
                         json.dumps(metadata) if metadata else None))
                    self.sqlite_conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to log device: {e}")
            return False
    
    def log_system_event(self, level: str, category: str, message: str, details: Dict = None) -> bool:
        """Log system event to operational database"""
        try:
            if self.config.sql_enabled and self.sql_conn:
                # Use SQL database
                cursor = self.sql_conn.cursor()
                if self.config.sql_type == "postgres":
                    cursor.execute("""
                        INSERT INTO system_logs (level, category, message, details)
                        VALUES (%s, %s, %s, %s)
                    """, (level, category, message, json.dumps(details) if details else None))
                elif self.config.sql_type == "mysql":
                    cursor.execute("""
                        INSERT INTO system_logs (level, category, message, details)
                        VALUES (%s, %s, %s, %s)
                    """, (level, category, message, json.dumps(details) if details else None))
                self.sql_conn.commit()
            else:
                # Fallback to SQLite
                with self.lock:
                    cursor = self.sqlite_conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS system_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            level TEXT NOT NULL,
                            category TEXT,
                            message TEXT NOT NULL,
                            details TEXT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO system_logs (level, category, message, details)
                        VALUES (?, ?, ?, ?)
                    """, (level, category, message, json.dumps(details) if details else None))
                    self.sqlite_conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to log system event: {e}")
            return False
    
    def record_performance_metric(self, cpu_usage: float = None, memory_usage: float = None,
                                 disk_usage: float = None, network_rx_bytes: int = None,
                                 network_tx_bytes: int = None, active_connections: int = None) -> bool:
        """Record performance metrics to operational database"""
        try:
            if self.config.sql_enabled and self.sql_conn:
                # Use SQL database
                cursor = self.sql_conn.cursor()
                if self.config.sql_type == "postgres":
                    cursor.execute("""
                        INSERT INTO performance_metrics 
                        (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections))
                elif self.config.sql_type == "mysql":
                    cursor.execute("""
                        INSERT INTO performance_metrics 
                        (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections))
                self.sql_conn.commit()
            else:
                # Fallback to SQLite
                with self.lock:
                    cursor = self.sqlite_conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS performance_metrics (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            cpu_usage REAL,
                            memory_usage REAL,
                            disk_usage REAL,
                            network_rx_bytes INTEGER,
                            network_tx_bytes INTEGER,
                            active_connections INTEGER,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO performance_metrics 
                        (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (cpu_usage, memory_usage, disk_usage, network_rx_bytes, network_tx_bytes, active_connections))
                    self.sqlite_conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to record performance metric: {e}")
            return False
    
    def get_recent_logs(self, limit: int = 100, level: str = None, category: str = None) -> List[Dict]:
        """Get recent system logs"""
        try:
            logs = []
            if self.config.sql_enabled and self.sql_conn:
                # Use SQL database
                cursor = self.sql_conn.cursor()
                query = "SELECT level, category, message, details, timestamp FROM system_logs"
                params = []
                
                where_conditions = []
                if level:
                    where_conditions.append("level = %s" if self.config.sql_type == "postgres" else "level = %s")
                    params.append(level)
                if category:
                    where_conditions.append("category = %s" if self.config.sql_type == "postgres" else "category = %s")
                    params.append(category)
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
                
                query += " ORDER BY timestamp DESC LIMIT %s" if self.config.sql_type == "postgres" else " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                for row in results:
                    logs.append({
                        'level': row[0],
                        'category': row[1],
                        'message': row[2],
                        'details': json.loads(row[3]) if row[3] else None,
                        'timestamp': row[4]
                    })
            else:
                # Fallback to SQLite
                with self.lock:
                    cursor = self.sqlite_conn.cursor()
                    query = "SELECT level, category, message, details, timestamp FROM system_logs"
                    params = []
                    
                    where_conditions = []
                    if level:
                        where_conditions.append("level = ?")
                        params.append(level)
                    if category:
                        where_conditions.append("category = ?")
                        params.append(category)
                    
                    if where_conditions:
                        query += " WHERE " + " AND ".join(where_conditions)
                    
                    query += " ORDER BY timestamp DESC LIMIT ?"
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    for row in results:
                        logs.append({
                            'level': row[0],
                            'category': row[1],
                            'message': row[2],
                            'details': json.loads(row[3]) if row[3] else None,
                            'timestamp': row[4]
                        })
            
            return logs
        except Exception as e:
            self.logger.error(f"Failed to get recent logs: {e}")
            return []
    
    def close(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.sql_conn:
            self.sql_conn.close()


class DatabaseMigrator:
    """Handle database migrations and synchronization"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def migrate_sqlite_to_sql(self) -> bool:
        """Migrate operational data from SQLite to SQL database"""
        if not self.db_manager.config.sql_enabled or not self.db_manager.sql_conn:
            self.logger.error("SQL database not enabled or not connected")
            return False
        
        try:
            # Tables to migrate (operational data only)
            tables_to_migrate = [
                'devices', 'sessions', 'traffic_logs', 'system_logs', 
                'analytics', 'performance_metrics'
            ]
            
            with self.db_manager.lock:
                sqlite_cursor = self.db_manager.sqlite_conn.cursor()
                sql_cursor = self.db_manager.sql_conn.cursor()
                
                for table_name in tables_to_migrate:
                    # Check if table exists in SQLite
                    sqlite_cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table_name,))
                    
                    if not sqlite_cursor.fetchone():
                        continue
                    
                    # Get all data from SQLite table
                    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
                    rows = sqlite_cursor.fetchall()
                    
                    if not rows:
                        continue
                    
                    # Get column names
                    column_names = [description[0] for description in sqlite_cursor.description]
                    
                    # Prepare SQL insert statement
                    placeholders = ', '.join(['%s'] * len(column_names))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
                    
                    # Insert data into SQL database
                    for row in rows:
                        sql_cursor.execute(insert_sql, row)
                    
                    self.logger.info(f"Migrated {len(rows)} rows from {table_name}")
                
                self.db_manager.sql_conn.commit()
                self.logger.info("Migration from SQLite to SQL completed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            if self.db_manager.sql_conn:
                self.db_manager.sql_conn.rollback()
            return False
    
    def migrate_sql_to_sqlite(self) -> bool:
        """Migrate operational data from SQL to SQLite database"""
        if not self.db_manager.config.sql_enabled or not self.db_manager.sql_conn:
            self.logger.error("SQL database not enabled or not connected")
            return False
        
        try:
            # Tables to migrate (operational data only)
            tables_to_migrate = [
                'devices', 'sessions', 'traffic_logs', 'system_logs', 
                'analytics', 'performance_metrics'
            ]
            
            with self.db_manager.lock:
                sqlite_cursor = self.db_manager.sqlite_conn.cursor()
                sql_cursor = self.db_manager.sql_conn.cursor()
                
                for table_name in tables_to_migrate:
                    # Get all data from SQL table
                    sql_cursor.execute(f"SELECT * FROM {table_name}")
                    rows = sql_cursor.fetchall()
                    
                    if not rows:
                        continue
                    
                    # Get column names
                    column_names = [description[0] for description in sql_cursor.description]
                    
                    # Create table in SQLite if it doesn't exist
                    self._create_sqlite_operational_table(table_name, sqlite_cursor)
                    
                    # Clear existing data
                    sqlite_cursor.execute(f"DELETE FROM {table_name}")
                    
                    # Prepare SQLite insert statement
                    placeholders = ', '.join(['?'] * len(column_names))
                    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
                    
                    # Insert data into SQLite database
                    for row in rows:
                        sqlite_cursor.execute(insert_sql, row)
                    
                    self.logger.info(f"Migrated {len(rows)} rows to {table_name}")
                
                self.db_manager.sqlite_conn.commit()
                self.logger.info("Migration from SQL to SQLite completed successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            if self.db_manager.sqlite_conn:
                self.db_manager.sqlite_conn.rollback()
            return False
    
    def _create_sqlite_operational_table(self, table_name: str, cursor):
        """Create operational tables in SQLite for migration"""
        table_schemas = {
            'devices': """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac_address TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    hostname TEXT,
                    device_type TEXT,
                    vendor TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    metadata TEXT
                )
            """,
            'sessions': """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER,
                    user_id INTEGER,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """,
            'traffic_logs': """
                CREATE TABLE IF NOT EXISTS traffic_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER,
                    src_ip TEXT NOT NULL,
                    dst_ip TEXT NOT NULL,
                    src_port INTEGER,
                    dst_port INTEGER,
                    protocol TEXT,
                    bytes_sent INTEGER DEFAULT 0,
                    bytes_received INTEGER DEFAULT 0,
                    packets_sent INTEGER DEFAULT 0,
                    packets_received INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'system_logs': """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    category TEXT,
                    message TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'analytics': """
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            'performance_metrics': """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    network_rx_bytes INTEGER,
                    network_tx_bytes INTEGER,
                    active_connections INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
        
        if table_name in table_schemas:
            cursor.execute(table_schemas[table_name])
    
    def sync_databases(self) -> bool:
        """Synchronize operational data between SQLite and SQL databases"""
        if not self.db_manager.config.sql_enabled or not self.db_manager.sql_conn:
            return False
        
        try:
            # For now, sync from SQLite to SQL (can be bidirectional)
            return self.migrate_sqlite_to_sql()
        except Exception as e:
            self.logger.error(f"Database sync failed: {e}")
            return False


class DatabaseBackup:
    """Handle database backup and restore operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def backup_sqlite(self, backup_path: str) -> bool:
        """Create backup of SQLite database"""
        try:
            import shutil
            
            # Close existing connection temporarily
            if self.db_manager.sqlite_conn:
                self.db_manager.sqlite_conn.close()
            
            # Create backup
            shutil.copy2(self.db_manager.config.sqlite_path, backup_path)
            
            # Reconnect
            self.db_manager.init_sqlite()
            
            self.logger.info(f"SQLite backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"SQLite backup failed: {e}")
            return False
    
    def restore_sqlite(self, backup_path: str) -> bool:
        """Restore SQLite database from backup"""
        try:
            import shutil
            
            # Close existing connection
            if self.db_manager.sqlite_conn:
                self.db_manager.sqlite_conn.close()
            
            # Restore backup
            shutil.copy2(backup_path, self.db_manager.config.sqlite_path)
            
            # Reconnect
            self.db_manager.init_sqlite()
            
            self.logger.info(f"SQLite restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"SQLite restore failed: {e}")
            return False
    
    def backup_sql(self, backup_path: str) -> bool:
        """Create backup of SQL database"""
        if not self.db_manager.config.sql_enabled or not self.db_manager.sql_conn:
            return False
        
        try:
            import subprocess
            
            if self.db_manager.config.sql_type == "postgres":
                # Use pg_dump
                cmd = [
                    'pg_dump',
                    f'--host={self.db_manager.config.sql_host}',
                    f'--port={self.db_manager.config.sql_port}',
                    f'--username={self.db_manager.config.sql_username}',
                    f'--dbname={self.db_manager.config.sql_database}',
                    f'--file={backup_path}',
                    '--verbose'
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = self.db_manager.config.sql_password
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"PostgreSQL backup created: {backup_path}")
                    return True
                else:
                    self.logger.error(f"PostgreSQL backup failed: {result.stderr}")
                    return False
            
            elif self.db_manager.config.sql_type == "mysql":
                # Use mysqldump
                cmd = [
                    'mysqldump',
                    f'--host={self.db_manager.config.sql_host}',
                    f'--port={self.db_manager.config.sql_port}',
                    f'--user={self.db_manager.config.sql_username}',
                    f'--password={self.db_manager.config.sql_password}',
                    self.db_manager.config.sql_database
                ]
                
                with open(backup_path, 'w') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"MySQL backup created: {backup_path}")
                    return True
                else:
                    self.logger.error(f"MySQL backup failed: {result.stderr}")
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"SQL backup failed: {e}")
            return False
    
    def cleanup_old_backups(self, backup_dir: str, retention_days: int = 30) -> bool:
        """Clean up old backup files"""
        try:
            import time
            
            current_time = time.time()
            retention_seconds = retention_days * 24 * 60 * 60
            
            for filename in os.listdir(backup_dir):
                filepath = os.path.join(backup_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > retention_seconds:
                        os.remove(filepath)
                        self.logger.info(f"Removed old backup: {filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return False


# CLI Tools for database management
class DatabaseCLI:
    """Command-line interface for database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.migrator = DatabaseMigrator(db_manager)
        self.backup = DatabaseBackup(db_manager)
    
    def migrate_to_sql(self):
        """Migrate operational data from SQLite to SQL"""
        print("Starting migration from SQLite to SQL...")
        if self.migrator.migrate_sqlite_to_sql():
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
    
    def migrate_to_sqlite(self):
        """Migrate operational data from SQL to SQLite"""
        print("Starting migration from SQL to SQLite...")
        if self.migrator.migrate_sql_to_sqlite():
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
    
    def sync_databases(self):
        """Synchronize databases"""
        print("Starting database synchronization...")
        if self.migrator.sync_databases():
            print("Synchronization completed successfully!")
        else:
            print("Synchronization failed!")
    
    def backup_sqlite(self, backup_path: str):
        """Create SQLite backup"""
        print(f"Creating SQLite backup: {backup_path}")
        if self.backup.backup_sqlite(backup_path):
            print("Backup created successfully!")
        else:
            print("Backup failed!")
    
    def restore_sqlite(self, backup_path: str):
        """Restore SQLite backup"""
        print(f"Restoring SQLite from: {backup_path}")
        if self.backup.restore_sqlite(backup_path):
            print("Restore completed successfully!")
        else:
            print("Restore failed!")
    
    def show_config(self):
        """Show current configuration"""
        print("\n=== LNMT Database Configuration ===")
        print(f"SQLite Path: {self.db_manager.config.sqlite_path}")
        print(f"SQL Enabled: {self.db_manager.config.sql_enabled}")
        
        if self.db_manager.config.sql_enabled:
            print(f"SQL Type: {self.db_manager.config.sql_type}")
            print(f"SQL Host: {self.db_manager.config.sql_host}")
            print(f"SQL Port: {self.db_manager.config.sql_port}")
            print(f"SQL Database: {self.db_manager.config.sql_database}")
        
        print(f"Auto Sync: {self.db_manager.config.auto_sync}")
        print(f"Backup Enabled: {self.db_manager.config.backup_enabled}")
    
    def list_tools(self):
        """List configured tools"""
        print("\n=== Configured Tools ===")
        with self.db_manager.lock:
            cursor = self.db_manager.sqlite_conn.cursor()
            cursor.execute("SELECT tool_name, binary_path, enabled FROM tool_paths ORDER BY tool_name")
            
            for row in cursor.fetchall():
                status = "✓" if row[2] else "✗"
                print(f"{status} {row[0]}: {row[1]}")
    
    def list_services(self):
        """List configured services"""
        print("\n=== Configured Services ===")
        with self.db_manager.lock:
            cursor = self.db_manager.sqlite_conn.cursor()
            cursor.execute("SELECT service_name, enabled, port, auto_start FROM service_config ORDER BY service_name")
            
            for row in cursor.fetchall():
                status = "✓" if row[1] else "✗"
                auto_start = "Auto" if row[3] else "Manual"
                port = f":{row[2]}" if row[2] else ""
                print(f"{status} {row[0]}{port} ({auto_start})")


# Example usage and initialization
def initialize_lnmt_database(config_file: str = "lnmt_db_config.json") -> DatabaseManager:
    """Initialize LNMT database system"""
    
    # Load configuration
    config = DatabaseConfig()
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Save configuration
    with open(config_file, 'w') as f:
        json.dump(asdict(config), f, indent=2)
    
    return db_manager


if __name__ == "__main__":
    import sys
    
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    db_manager = initialize_lnmt_database()
    cli = DatabaseCLI(db_manager)
    
    # Handle CLI commands
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "migrate-to-sql":
            cli.migrate_to_sql()
        elif command == "migrate-to-sqlite":
            cli.migrate_to_sqlite()
        elif command == "sync":
            cli.sync_databases()
        elif command == "backup-sqlite":
            backup_path = sys.argv[2] if len(sys.argv) > 2 else f"lnmt_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            cli.backup_sqlite(backup_path)
        elif command == "restore-sqlite":
            if len(sys.argv) > 2:
                cli.restore_sqlite(sys.argv[2])
            else:
                print("Usage: python lnmt_db.py restore-sqlite <backup_path>")
        elif command == "config":
            cli.show_config()
        elif command == "list-tools":
            cli.list_tools()
        elif command == "list-services":
            cli.list_services()
        else:
            print("Available commands:")
            print("  migrate-to-sql     - Migrate operational data from SQLite to SQL")
            print("  migrate-to-sqlite  - Migrate operational data from SQL to SQLite")
            print("  sync              - Synchronize databases")
            print("  backup-sqlite     - Create SQLite backup")
            print("  restore-sqlite    - Restore SQLite backup")
            print("  config            - Show configuration")
            print("  list-tools        - List configured tools")
            print("  list-services     - List configured services")
    else:
        cli.show_config()
        cli.list_tools()
        cli.list_services()
    
    # Close database connections
    db_manager.close()