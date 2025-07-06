#!/bin/bash
# LNMT Dual-Database Architecture Installation Script
# Version: 1.0.0

set -euo pipefail

# Configuration
LNMT_USER="lnmt"
LNMT_GROUP="lnmt"
LNMT_HOME="/opt/lnmt"
LNMT_CONFIG_DIR="/etc/lnmt"
LNMT_LOG_DIR="/var/log/lnmt"
LNMT_DATA_DIR="/var/lib/lnmt"
LNMT_BACKUP_DIR="/var/lib/lnmt/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${DEBUG:-}" == "1" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Cannot detect OS"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VER"
}

# Function to install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $OS in
        "Ubuntu"*)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv sqlite3 \
                              curl wget git htop iotop netstat-nat \
                              iptables-persistent fail2ban logrotate \
                              nginx mysql-server redis-server \
                              php-fpm php-mysql php-redis \
                              postfix dovecot-core memcached \
                              iproute2 tcpdump
            ;;
        "CentOS"*|"Red Hat"*|"Rocky"*)
            yum update -y
            yum install -y python3 python3-pip sqlite curl wget git \
                          htop iotop net-tools iptables-services \
                          fail2ban logrotate nginx mysql-server \
                          redis php-fpm php-mysql postfix \
                          dovecot memcached iproute tcpdump
            ;;
        "Debian"*)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv sqlite3 \
                              curl wget git htop iotop net-tools \
                              iptables-persistent fail2ban logrotate \
                              nginx mysql-server redis-server \
                              php-fpm php-mysql php-redis \
                              postfix dovecot-core memcached \
                              iproute2 tcpdump
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
}

# Function to install Python dependencies
install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "${LNMT_HOME}/venv"
    source "${LNMT_HOME}/venv/bin/activate"
    
    # Install required packages
    pip install --upgrade pip
    pip install psycopg2-binary pymysql bcrypt cryptography psutil
    
    # Create requirements.txt
    cat > "${LNMT_HOME}/requirements.txt" << EOF
psycopg2-binary>=2.9.0
pymysql>=1.0.0
bcrypt>=3.2.0
cryptography>=3.4.0
psutil>=5.8.0
EOF
    
    deactivate
}

# Function to create user and directories
create_user_and_directories() {
    log_info "Creating LNMT user and directories..."
    
    # Create user
    if ! id "$LNMT_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$LNMT_HOME" "$LNMT_USER"
        log_info "Created user: $LNMT_USER"
    fi
    
    # Create directories
    mkdir -p "$LNMT_HOME"
    mkdir -p "$LNMT_CONFIG_DIR"
    mkdir -p "$LNMT_LOG_DIR"
    mkdir -p "$LNMT_DATA_DIR"
    mkdir -p "$LNMT_BACKUP_DIR"
    
    # Set permissions
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_HOME"
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_CONFIG_DIR"
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_LOG_DIR"
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_DATA_DIR"
    
    chmod 750 "$LNMT_HOME"
    chmod 750 "$LNMT_CONFIG_DIR"
    chmod 750 "$LNMT_LOG_DIR"
    chmod 750 "$LNMT_DATA_DIR"
    chmod 750 "$LNMT_BACKUP_DIR"
}

# Function to install LNMT files
install_lnmt_files() {
    log_info "Installing LNMT files..."
    
    # Copy main database module
    cp lnmt_db.py "$LNMT_HOME/"
    
    # Create configuration files
    cat > "$LNMT_CONFIG_DIR/lnmt_db_config.json" << EOF
{
  "sqlite_path": "$LNMT_CONFIG_DIR/lnmt_config.db",
  "sql_enabled": false,
  "sql_type": "postgres",
  "sql_host": "localhost",
  "sql_port": 5432,
  "sql_database": "lnmt",
  "sql_username": "lnmt_user",
  "sql_password": "$(openssl rand -base64 32)",
  "sql_pool_size": 5,
  "auto_sync": true,
  "sync_interval": 300,
  "backup_enabled": true,
  "backup_retention_days": 30
}
EOF
    
    # Create service configuration
    cat > "$LNMT_CONFIG_DIR/lnmt_services.json" << EOF
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
    },
    {
      "name": "mysql",
      "enabled": true,
      "port": 3306,
      "config_path": "/etc/mysql/my.cnf",
      "binary_path": "/usr/bin/mysqld",
      "log_path": "/var/log/mysql",
      "auto_start": true,
      "dependencies": []
    },
    {
      "name": "php-fpm",
      "enabled": true,
      "port": 9000,
      "config_path": "/etc/php/fpm/pool.d/www.conf",
      "binary_path": "/usr/sbin/php-fpm",
      "log_path": "/var/log/php-fpm",
      "auto_start": true,
      "dependencies": ["mysql"]
    },
    {
      "name": "redis",
      "enabled": true,
      "port": 6379,
      "config_path": "/etc/redis/redis.conf",
      "binary_path": "/usr/bin/redis-server",
      "log_path": "/var/log/redis",
      "auto_start": true,
      "dependencies": []
    }
  ]
}
EOF
    
    # Create network configuration
    cat > "$LNMT_CONFIG_DIR/lnmt_network.json" << EOF
{
  "interfaces": [
    {
      "name": "eth0",
      "ip_address": "$(ip route get 1 | awk '{print $NF; exit}')",
      "netmask": "255.255.255.0",
      "gateway": "$(ip route | grep default | awk '{print $3}')",
      "dns_servers": ["8.8.8.8", "8.8.4.4"],
      "enabled": true,
      "dhcp": false
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
        "port": 443,
        "source": "any",
        "enabled": true
      },
      {
        "name": "allow_management",
        "action": "ACCEPT",
        "protocol": "tcp",
        "port": 8080,
        "source": "192.168.1.0/24",
        "enabled": true
      }
    ]
  },
  "qos": {
    "enabled": false,
    "rules": [
      {
        "name": "web_priority",
        "interface": "eth0",
        "protocol": "tcp",
        "ports": [80, 443],
        "bandwidth_limit": "10mbit",
        "priority": 1,
        "enabled": true
      }
    ]
  }
}
EOF
    
    # Create monitoring configuration
    cat > "$LNMT_CONFIG_DIR/lnmt_monitoring.json" << EOF
{
  "metrics": {
    "enabled": true,
    "collection_interval": 60,
    "retention_days": 30,
    "thresholds": {
      "cpu_usage": 80,
      "memory_usage": 85,
      "disk_usage": 90,
      "network_bandwidth": 80
    }
  },
  "alerts": {
    "enabled": true,
    "email_notifications": {
      "enabled": false,
      "smtp_server": "localhost",
      "smtp_port": 25,
      "from_address": "lnmt@$(hostname -f)",
      "recipients": ["admin@$(hostname -f)"]
    }
  },
  "logging": {
    "level": "INFO",
    "max_file_size": "10MB",
    "max_files": 10,
    "log_paths": {
      "system": "$LNMT_LOG_DIR/system.log",
      "access": "$LNMT_LOG_DIR/access.log",
      "error": "$LNMT_LOG_DIR/error.log",
      "security": "$LNMT_LOG_DIR/security.log"
    }
  }
}
EOF
    
    # Set proper permissions
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_HOME"
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_CONFIG_DIR"
    chmod 640 "$LNMT_CONFIG_DIR"/*.json
    chmod 600 "$LNMT_CONFIG_DIR/lnmt_db_config.json"  # Contains passwords
    chmod +x "$LNMT_HOME/lnmt_db.py"
}

# Function to create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/lnmt.service << EOF
[Unit]
Description=LNMT Management Service
Documentation=https://github.com/lnmt/lnmt
After=network.target mysql.service postgresql.service redis.service

[Service]
Type=simple
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
Environment=PATH=$LNMT_HOME/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$LNMT_HOME/venv/bin/python $LNMT_HOME/lnmt_db.py daemon
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$LNMT_HOME $LNMT_CONFIG_DIR $LNMT_LOG_DIR $LNMT_DATA_DIR
ProtectHome=true
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF
    
    # Create monitoring service
    cat > /etc/systemd/system/lnmt-monitor.service << EOF
[Unit]
Description=LNMT Monitoring Service
Documentation=https://github.com/lnmt/lnmt
After=lnmt.service
Requires=lnmt.service

[Service]
Type=simple
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
Environment=PATH=$LNMT_HOME/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$LNMT_HOME/venv/bin/python $LNMT_HOME/lnmt_db.py monitor
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$LNMT_HOME $LNMT_CONFIG_DIR $LNMT_LOG_DIR $LNMT_DATA_DIR
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF
    
    # Create backup timer
    cat > /etc/systemd/system/lnmt-backup.service << EOF
[Unit]
Description=LNMT Backup Service
Documentation=https://github.com/lnmt/lnmt

[Service]
Type=oneshot
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
Environment=PATH=$LNMT_HOME/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$LNMT_HOME/venv/bin/python $LNMT_HOME/lnmt_db.py backup-auto
StandardOutput=journal
StandardError=journal
EOF
    
    cat > /etc/systemd/system/lnmt-backup.timer << EOF
[Unit]
Description=Run LNMT backup daily
Requires=lnmt-backup.service

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1800

[Install]
WantedBy=timers.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
}

# Function to create CLI wrapper
create_cli_wrapper() {
    log_info "Creating CLI wrapper..."
    
    cat > /usr/local/bin/lnmt << 'EOF'
#!/bin/bash
# LNMT CLI Wrapper

LNMT_HOME="/opt/lnmt"
LNMT_USER="lnmt"

# Check if running as LNMT user
if [[ "$USER" != "$LNMT_USER" && "$EUID" -ne 0 ]]; then
    echo "This command must be run as $LNMT_USER user or root"
    exit 1
fi

# Switch to LNMT user if running as root
if [[ "$EUID" -eq 0 ]]; then
    exec su - "$LNMT_USER" -c "cd $LNMT_HOME && $LNMT_HOME/venv/bin/python $LNMT_HOME/lnmt_db.py $*"
else
    cd "$LNMT_HOME"
    exec "$LNMT_HOME/venv/bin/python" "$LNMT_HOME/lnmt_db.py" "$@"
fi
EOF
    
    chmod +x /usr/local/bin/lnmt
}

# Function to setup logrotate
setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/lnmt << EOF
$LNMT_LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $LNMT_USER $LNMT_GROUP
    postrotate
        systemctl reload lnmt >/dev/null 2>&1 || true
    endscript
}
EOF
}

# Function to setup database
setup_database() {
    log_info "Setting up database..."
    
    # Initialize SQLite database
    sudo -u "$LNMT_USER" "$LNMT_HOME/venv/bin/python" "$LNMT_HOME/lnmt_db.py" init
    
    # Ask user about SQL database setup
    echo
    read -p "Do you want to setup a SQL database (PostgreSQL/MySQL)? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Select SQL database type:"
        echo "1) PostgreSQL"
        echo "2) MySQL"
        read -p "Enter choice [1-2]: " -n 1 -r
        echo
        
        case $REPLY in
            1)
                setup_postgresql
                ;;
            2)
                setup_mysql
                ;;
            *)
                log_warn "Invalid choice. Skipping SQL database setup."
                ;;
        esac
    fi
}

# Function to setup PostgreSQL
setup_postgresql() {
    log_info "Setting up PostgreSQL..."
    
    # Install PostgreSQL if not present
    if ! command -v psql &> /dev/null; then
        case $OS in
            "Ubuntu"*|"Debian"*)
                apt-get install -y postgresql postgresql-contrib
                ;;
            "CentOS"*|"Red Hat"*|"Rocky"*)
                yum install -y postgresql postgresql-server postgresql-contrib
                postgresql-setup initdb
                ;;
        esac
    fi
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE DATABASE lnmt;
CREATE USER lnmt_user WITH PASSWORD '$(openssl rand -base64 32)';
GRANT ALL PRIVILEGES ON DATABASE lnmt TO lnmt_user;
\q
EOF
    
    # Update configuration
    sudo -u "$LNMT_USER" "$LNMT_HOME/venv/bin/python" -c "
import json
config_file = '$LNMT_CONFIG_DIR/lnmt_db_config.json'
with open(config_file, 'r') as f:
    config = json.load(f)
config['sql_enabled'] = True
config['sql_type'] = 'postgres'
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
"
    
    log_info "PostgreSQL setup completed"
}

# Function to setup MySQL
setup_mysql() {
    log_info "Setting up MySQL..."
    
    # Install MySQL if not present
    if ! command -v mysql &> /dev/null; then
        case $OS in
            "Ubuntu"*|"Debian"*)
                apt-get install -y mysql-server
                ;;
            "CentOS"*|"Red Hat"*|"Rocky"*)
                yum install -y mysql-server
                ;;
        esac
    fi
    
    # Start MySQL
    systemctl start mysql
    systemctl enable mysql
    
    # Generate password
    DB_PASSWORD=$(openssl rand -base64 32)
    
    # Create database and user
    mysql -u root << EOF
CREATE DATABASE lnmt;
CREATE USER 'lnmt_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON lnmt.* TO 'lnmt_user'@'localhost';
FLUSH PRIVILEGES;
EOF
    
    # Update configuration
    sudo -u "$LNMT_USER" "$LNMT_HOME/venv/bin/python" -c "
import json
config_file = '$LNMT_CONFIG_DIR/lnmt_db_config.json'
with open(config_file, 'r') as f:
    config = json.load(f)
config['sql_enabled'] = True
config['sql_type'] = 'mysql'
config['sql_password'] = '$DB_PASSWORD'
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
"
    
    log_info "MySQL setup completed"
}

# Function to setup firewall
setup_firewall() {
    log_info "Setting up firewall..."
    
    # Create basic iptables rules
    cat > /etc/iptables/rules.v4 << EOF
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]

# Allow loopback
-A INPUT -i lo -j ACCEPT

# Allow established connections
-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Allow SSH
-A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
-A INPUT -p tcp --dport 80 -j ACCEPT
-A INPUT -p tcp --dport 443 -j ACCEPT

# Allow management interface
-A INPUT -p tcp --dport 8080 -s 192.168.0.0/16 -j ACCEPT

# Allow ping
-A INPUT -p icmp --icmp-type echo-request -j ACCEPT

COMMIT
EOF
    
    # Load rules
    iptables-restore < /etc/iptables/rules.v4
    
    # Enable on boot
    systemctl enable netfilter-persistent
}

# Function to create backup scripts
create_backup_scripts() {
    log_info "Creating backup scripts..."
    
    cat > "$LNMT_HOME/backup.sh" << EOF
#!/bin/bash
# LNMT Backup Script

BACKUP_DIR="$LNMT_BACKUP_DIR"
DATE=\$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "\$BACKUP_DIR"

# Backup SQLite database
echo "Backing up SQLite database..."
cp "$LNMT_CONFIG_DIR/lnmt_config.db" "\$BACKUP_DIR/config_\$DATE.db"

# Backup configuration files
echo "Backing up configuration files..."
tar -czf "\$BACKUP_DIR/config_\$DATE.tar.gz" -C "$LNMT_CONFIG_DIR" .

# Backup SQL database if enabled
if [[ -f "$LNMT_CONFIG_DIR/lnmt_db_config.json" ]]; then
    SQL_ENABLED=\$(python3 -c "import json; print(json.load(open('$LNMT_CONFIG_DIR/lnmt_db_config.json'))['sql_enabled'])")
    if [[ "\$SQL_ENABLED" == "True" ]]; then
        echo "Backing up SQL database..."
        "$LNMT_HOME/venv/bin/python" "$LNMT_HOME/lnmt_db.py" backup-sql "\$BACKUP_DIR/operational_\$DATE.sql"
    fi
fi

# Clean old backups
echo "Cleaning old backups..."
find "\$BACKUP_DIR" -name "*.db" -mtime +\$RETENTION_DAYS -delete
find "\$BACKUP_DIR" -name "*.tar.gz" -mtime +\$RETENTION_DAYS -delete
find "\$BACKUP_DIR" -name "*.sql" -mtime +\$RETENTION_DAYS -delete

echo "Backup completed: \$DATE"
EOF
    
    chmod +x "$LNMT_HOME/backup.sh"
    chown "$LNMT_USER:$LNMT_GROUP" "$LNMT_HOME/backup.sh"
}

# Function to enable services
enable_services() {
    log_info "Enabling services..."
    
    # Enable and start LNMT services
    systemctl enable lnmt
    systemctl enable lnmt-monitor
    systemctl enable lnmt-backup.timer
    
    # Start services
    systemctl start lnmt
    systemctl start lnmt-monitor
    systemctl start lnmt-backup.timer
    
    log_info "Services enabled and started"
}

# Function to run post-install tests
run_tests() {
    log_info "Running post-install tests..."
    
    # Test database initialization
    if sudo -u "$LNMT_USER" "$LNMT_HOME/venv/bin/python" "$LNMT_HOME/lnmt_db.py" config > /dev/null 2>&1; then
        log_info "✓ Database initialization test passed"
    else
        log_error "✗ Database initialization test failed"
        return 1
    fi
    
    # Test service status
    if systemctl is-active --quiet lnmt; then
        log_info "✓ LNMT service is running"
    else
        log_error "✗ LNMT service is not running"
        return 1
    fi
    
    # Test CLI wrapper
    if /usr/local/bin/lnmt config > /dev/null 2>&1; then
        log_info "✓ CLI wrapper test passed"
    else
        log_error "✗ CLI wrapper test failed"
        return 1
    fi
    
    log_info "All tests passed!"
    return 0
}

# Function to display post-install information
display_info() {
    log_info "Installation completed successfully!"
    echo
    echo "=== LNMT Installation Summary ==="
    echo "Installation Directory: $LNMT_HOME"
    echo "Configuration Directory: $LNMT_CONFIG_DIR"
    echo "Log Directory: $LNMT_LOG_DIR"
    echo "Data Directory: $LNMT_DATA_DIR"
    echo "Backup Directory: $LNMT_BACKUP_DIR"
    echo "User: $LNMT_USER"
    echo
    echo "=== Available Commands ==="
    echo "lnmt config                 - Show configuration"
    echo "lnmt list-tools             - List configured tools"
    echo "lnmt list-services          - List configured services"
    echo "lnmt migrate-to-sql         - Migrate to SQL database"
    echo "lnmt backup-sqlite          - Backup SQLite database"
    echo "lnmt sync                   - Sync databases"
    echo
    echo "=== Service Management ==="
    echo "systemctl status lnmt       - Check service status"
    echo "systemctl restart lnmt      - Restart service"
    echo "systemctl logs lnmt         - View service logs"
    echo
    echo "=== Configuration Files ==="
    echo "Database Config: $LNMT_CONFIG_DIR/lnmt_db_config.json"
    echo "Services Config: $LNMT_CONFIG_DIR/lnmt_services.json"
    echo "Network Config: $LNMT_CONFIG_DIR/lnmt_network.json"
    echo "Monitoring Config: $LNMT_CONFIG_DIR/lnmt_monitoring.json"
    echo
    echo "=== Next Steps ==="
    echo "1. Review and customize configuration files"
    echo "2. Configure services as needed"
    echo "3. Set up monitoring and alerts"
    echo "4. Test backup and restore procedures"
    echo
}

# Main installation function
main() {
    log_info "Starting LNMT installation..."
    
    check_root
    detect_os
    
    # Create user and directories first
    create_user_and_directories
    
    # Install dependencies
    install_dependencies
    install_python_dependencies
    
    # Install LNMT files
    install_lnmt_files
    
    # Create system integration
    create_systemd_service
    create_cli_wrapper
    setup_logrotate
    create_backup_scripts
    
    # Setup database
    setup_database
    
    # Setup firewall (optional)
    read -p "Do you want to setup basic firewall rules? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_firewall
    fi
    
    # Enable services
    enable_services
    
    # Run tests
    if run_tests; then
        display_info
    else
        log_error "Installation completed with errors. Please check the logs."
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "LNMT Installation Script"
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --debug        Enable debug output"
        echo "  --uninstall    Uninstall LNMT"
        echo
        exit 0
        ;;
    --debug)
        export DEBUG=1
        shift
        ;;
    --uninstall)
        log_info "Uninstalling LNMT..."
        
        # Stop services
        systemctl stop lnmt lnmt-monitor lnmt-backup.timer 2>/dev/null || true
        systemctl disable lnmt lnmt-monitor lnmt-backup.timer 2>/dev/null || true
        
        # Remove service files
        rm -f /etc/systemd/system/lnmt.service
        rm -f /etc/systemd/system/lnmt-monitor.service
        rm -f /etc/systemd/system/lnmt-backup.service
        rm -f /etc/systemd/system/lnmt-backup.timer
        systemctl daemon-reload
        
        # Remove files
        rm -rf "$LNMT_HOME"
        rm -rf "$LNMT_CONFIG_DIR"
        rm -rf "$LNMT_LOG_DIR"
        rm -f /usr/local/bin/lnmt
        rm -f /etc/logrotate.d/lnmt
        
        # Remove user
        userdel "$LNMT_USER" 2>/dev/null || true
        
        log_info "LNMT uninstalled successfully"
        exit 0
        ;;
esac

# Run main installation
main "$@"",
        "protocol": "tcp",
        "port": 22,
        "source": "any",
        "enabled": true
      },
      {
        "name": "allow_http",
        "action": "ACCEPT",
        "protocol": "tcp",
        "port": 80,
        "source": "any",
        "enabled": true
      },
      {
        "name": "allow_https",
        "action": "ACCEPT