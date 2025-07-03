#!/bin/bash
# LNMT Installer - Linux Network Management Toolbox
# Production-ready installer with multi-distro support
# Version: 1.0.0

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly LNMT_VERSION="1.0.0"
readonly LNMT_USER="lnmt"
readonly LNMT_GROUP="lnmt"
readonly LNMT_HOME="/opt/lnmt"
readonly LNMT_CONFIG_DIR="/etc/lnmt"
readonly LNMT_LOG_DIR="/var/log/lnmt"
readonly LNMT_DATA_DIR="/var/lib/lnmt"
readonly LNMT_BIN_DIR="/usr/local/bin"
readonly INSTALL_LOG="/var/log/lnmt-install.log"

# Global variables
INTERACTIVE_MODE=true
FORCE_INSTALL=false
INSTALL_TYPE="full"  # full, minimal, docker, venv
DETECTED_OS=""
DETECTED_VERSION=""
PACKAGE_MANAGER=""
PYTHON_CMD=""
BACKUP_DIR=""

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${INSTALL_LOG}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "${YELLOW}$*${NC}"; }
log_error() { log "ERROR" "${RED}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}$*${NC}"; }

# Error handling
cleanup_on_error() {
    log_error "Installation failed. Cleaning up..."
    if [[ -n "${BACKUP_DIR:-}" && -d "${BACKUP_DIR}" ]]; then
        log_info "Backup available at: ${BACKUP_DIR}"
    fi
    exit 1
}

trap cleanup_on_error ERR

# Root check
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo "Please run: sudo $0 $*"
        exit 1
    fi
}

# OS Detection
detect_os() {
    log_info "Detecting operating system..."
    
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DETECTED_OS="$ID"
        DETECTED_VERSION="$VERSION_ID"
    elif [[ -f /etc/redhat-release ]]; then
        DETECTED_OS="rhel"
        DETECTED_VERSION=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release | head -1)
    elif [[ -f /etc/debian_version ]]; then
        DETECTED_OS="debian"
        DETECTED_VERSION=$(cat /etc/debian_version)
    else
        log_error "Unable to detect operating system"
        exit 1
    fi
    
    # Determine package manager
    case "$DETECTED_OS" in
        ubuntu|debian)
            PACKAGE_MANAGER="apt"
            ;;
        rhel|centos|fedora|rocky|almalinux)
            if command -v dnf &> /dev/null; then
                PACKAGE_MANAGER="dnf"
            else
                PACKAGE_MANAGER="yum"
            fi
            ;;
        arch|manjaro)
            PACKAGE_MANAGER="pacman"
            ;;
        opensuse*)
            PACKAGE_MANAGER="zypper"
            ;;
        *)
            log_warn "Unsupported OS: $DETECTED_OS. Proceeding with generic installation..."
            PACKAGE_MANAGER="unknown"
            ;;
    esac
    
    # Detect Python
    for python_cmd in python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v "$python_cmd" &> /dev/null; then
            PYTHON_CMD="$python_cmd"
            break
        fi
    done
    
    if [[ -z "$PYTHON_CMD" ]]; then
        log_error "Python 3.8+ is required but not found"
        exit 1
    fi
    
    local python_version=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    log_info "Detected OS: $DETECTED_OS $DETECTED_VERSION"
    log_info "Package Manager: $PACKAGE_MANAGER"
    log_info "Python: $PYTHON_CMD ($python_version)"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    local packages=""
    case "$PACKAGE_MANAGER" in
        apt)
            apt update
            packages="python3 python3-pip python3-venv python3-dev build-essential curl wget git systemd nginx sqlite3 iptables bridge-utils net-tools"
            apt install -y $packages
            ;;
        dnf|yum)
            $PACKAGE_MANAGER update -y
            packages="python3 python3-pip python3-devel gcc gcc-c++ curl wget git systemd nginx sqlite bridge-utils net-tools iptables"
            $PACKAGE_MANAGER install -y $packages
            ;;
        pacman)
            pacman -Sy --noconfirm
            packages="python python-pip python-virtualenv base-devel curl wget git systemd nginx sqlite bridge-utils net-tools iptables"
            pacman -S --noconfirm $packages
            ;;
        zypper)
            zypper refresh
            packages="python3 python3-pip python3-virtualenv python3-devel gcc gcc-c++ curl wget git systemd nginx sqlite3 bridge-utils net-tools iptables"
            zypper install -y $packages
            ;;
        *)
            log_warn "Unknown package manager. Please install dependencies manually:"
            log_warn "Python 3.8+, pip, venv, build tools, curl, wget, git, systemd, nginx, sqlite3"
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Create user and directories
create_system_resources() {
    log_info "Creating system user and directories..."
    
    # Create LNMT user if it doesn't exist
    if ! id "$LNMT_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$LNMT_HOME" -c "LNMT Service User" "$LNMT_USER"
        log_info "Created user: $LNMT_USER"
    fi
    
    # Create directories
    local dirs=(
        "$LNMT_HOME"
        "$LNMT_CONFIG_DIR"
        "$LNMT_LOG_DIR"
        "$LNMT_DATA_DIR"
        "$LNMT_HOME/bin"
        "$LNMT_HOME/lib"
        "$LNMT_HOME/web"
        "$LNMT_HOME/modules"
        "$LNMT_HOME/plugins"
        "$LNMT_DATA_DIR/backups"
        "$LNMT_DATA_DIR/db"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    # Set ownership and permissions
    chown -R "$LNMT_USER:$LNMT_GROUP" "$LNMT_HOME" "$LNMT_DATA_DIR" "$LNMT_LOG_DIR"
    chown -R root:root "$LNMT_CONFIG_DIR"
    chmod 755 "$LNMT_HOME" "$LNMT_CONFIG_DIR"
    chmod 750 "$LNMT_LOG_DIR" "$LNMT_DATA_DIR"
    chmod 644 "$LNMT_CONFIG_DIR"/*
    
    log_success "System resources created"
}

# Install Python virtual environment
setup_python_env() {
    if [[ "$INSTALL_TYPE" == "venv" ]]; then
        log_info "Setting up Python virtual environment..."
        
        local venv_dir="$LNMT_HOME/venv"
        $PYTHON_CMD -m venv "$venv_dir"
        source "$venv_dir/bin/activate"
        
        # Upgrade pip and install requirements
        pip install --upgrade pip setuptools wheel
        
        # Create requirements.txt if it doesn't exist
        cat > "$LNMT_HOME/requirements.txt" << 'EOF'
flask>=2.3.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psutil>=5.9.0
netaddr>=0.8.0
pyyaml>=6.0
click>=8.1.0
gunicorn>=21.2.0
celery>=5.3.0
redis>=4.6.0
requests>=2.31.0
cryptography>=41.0.0
bcrypt>=4.0.0
wtforms>=3.0.0
flask-wtf>=1.1.1
flask-login>=0.6.2
flask-migrate>=4.0.0
markupsafe>=2.1.3
EOF
        
        pip install -r "$LNMT_HOME/requirements.txt"
        
        chown -R "$LNMT_USER:$LNMT_GROUP" "$venv_dir"
        log_success "Python virtual environment configured"
    fi
}

# Install LNMT modules
install_lnmt_modules() {
    log_info "Installing LNMT modules..."
    
    # Main application structure
    local modules=(
        "core"
        "dns"
        "vlan"
        "firewall"
        "monitoring"
        "device_tracker"
        "scheduler"
        "web_ui"
        "api"
        "health"
    )
    
    for module in "${modules[@]}"; do
        local module_dir="$LNMT_HOME/modules/$module"
        mkdir -p "$module_dir"
        
        # Create basic module structure
        cat > "$module_dir/__init__.py" << 'EOF'
"""LNMT Module"""
__version__ = "1.0.0"
EOF
        
        log_info "Installed module: $module"
    done
    
    # Create main application entry point
    cat > "$LNMT_HOME/bin/lnmt" << 'EOF'
#!/usr/bin/env python3
"""LNMT Main Entry Point"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from lnmt.core.cli import main

if __name__ == '__main__':
    main()
EOF
    
    chmod +x "$LNMT_HOME/bin/lnmt"
    ln -sf "$LNMT_HOME/bin/lnmt" "$LNMT_BIN_DIR/lnmt"
    
    log_success "LNMT modules installed"
}

# Configure systemd services
setup_systemd_services() {
    log_info "Setting up systemd services..."
    
    # Main LNMT service
    cat > "/etc/systemd/system/lnmt.service" << EOF
[Unit]
Description=Linux Network Management Toolbox
After=network.target
Wants=network.target

[Service]
Type=forking
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
ExecStart=$LNMT_HOME/bin/lnmt daemon start
ExecStop=$LNMT_HOME/bin/lnmt daemon stop
ExecReload=$LNMT_HOME/bin/lnmt daemon reload
PIDFile=$LNMT_DATA_DIR/lnmt.pid
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LNMT_DATA_DIR $LNMT_LOG_DIR
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true

[Install]
WantedBy=multi-user.target
EOF

    # Web UI service
    cat > "/etc/systemd/system/lnmt-web.service" << EOF
[Unit]
Description=LNMT Web Interface
After=lnmt.service
Requires=lnmt.service

[Service]
Type=exec
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
ExecStart=$LNMT_HOME/bin/lnmt web start
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LNMT_DATA_DIR $LNMT_LOG_DIR
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # Scheduler service
    cat > "/etc/systemd/system/lnmt-scheduler.service" << EOF
[Unit]
Description=LNMT Task Scheduler
After=lnmt.service
Requires=lnmt.service

[Service]
Type=exec
User=$LNMT_USER
Group=$LNMT_GROUP
WorkingDirectory=$LNMT_HOME
ExecStart=$LNMT_HOME/bin/lnmt scheduler start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable services
    systemctl daemon-reload
    
    if [[ "$INTERACTIVE_MODE" == true ]]; then
        read -p "Enable LNMT services to start on boot? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            systemctl enable lnmt lnmt-web lnmt-scheduler
            log_success "LNMT services enabled for startup"
        fi
    else
        systemctl enable lnmt lnmt-web lnmt-scheduler
        log_success "LNMT services enabled for startup"
    fi
}

# Create default configuration
create_default_config() {
    log_info "Creating default configuration..."
    
    # Main configuration
    cat > "$LNMT_CONFIG_DIR/lnmt.yml" << EOF
# LNMT Configuration
version: "1.0.0"
installation_date: "$(date -Iseconds)"

# Core settings
core:
  data_dir: "$LNMT_DATA_DIR"
  log_dir: "$LNMT_LOG_DIR"
  log_level: "INFO"
  debug: false

# Database settings
database:
  type: "sqlite"
  path: "$LNMT_DATA_DIR/db/lnmt.db"
  
# Web interface
web:
  host: "0.0.0.0"
  port: 8080
  secret_key: "$(openssl rand -hex 32)"
  
# Network settings
network:
  management_interface: "eth0"
  dns_servers:
    - "8.8.8.8"
    - "8.8.4.4"
    
# Security
security:
  require_auth: true
  session_timeout: 3600
  
# Modules
modules:
  dns:
    enabled: true
    port: 53
  vlan:
    enabled: true
  firewall:
    enabled: true
  monitoring:
    enabled: true
  device_tracker:
    enabled: true
  scheduler:
    enabled: true
EOF

    # Network interfaces configuration
    cat > "$LNMT_CONFIG_DIR/interfaces.yml" << EOF
# Network Interfaces Configuration
interfaces:
  management:
    name: "eth0"
    description: "Management interface"
    
vlans: {}

bridges: {}
EOF

    # Firewall rules template
    cat > "$LNMT_CONFIG_DIR/firewall.yml" << EOF
# Firewall Configuration
firewall:
  enabled: true
  default_policy: "DROP"
  
zones:
  management:
    interfaces: ["eth0"]
    services: ["ssh", "http", "https"]
    
rules: []
EOF

    log_success "Default configuration created"
}

# Run database migrations
run_migrations() {
    log_info "Setting up database..."
    
    # Create database directory
    mkdir -p "$LNMT_DATA_DIR/db"
    
    # Initialize database (placeholder)
    touch "$LNMT_DATA_DIR/db/lnmt.db"
    chown "$LNMT_USER:$LNMT_GROUP" "$LNMT_DATA_DIR/db/lnmt.db"
    
    log_success "Database initialized"
}

# Create backup before installation
create_backup() {
    if [[ -d "$LNMT_HOME" ]]; then
        BACKUP_DIR="/tmp/lnmt-backup-$(date +%Y%m%d-%H%M%S)"
        log_info "Creating backup at: $BACKUP_DIR"
        
        mkdir -p "$BACKUP_DIR"
        
        # Backup existing installation
        if [[ -d "$LNMT_HOME" ]]; then
            cp -r "$LNMT_HOME" "$BACKUP_DIR/"
        fi
        
        if [[ -d "$LNMT_CONFIG_DIR" ]]; then
            cp -r "$LNMT_CONFIG_DIR" "$BACKUP_DIR/"
        fi
        
        if [[ -d "$LNMT_DATA_DIR" ]]; then
            cp -r "$LNMT_DATA_DIR" "$BACKUP_DIR/"
        fi
        
        log_success "Backup created at: $BACKUP_DIR"
    fi
}

# Post-installation setup
post_install_setup() {
    log_info "Running post-installation setup..."
    
    # Create CLI wrapper scripts
    cat > "/usr/local/bin/lnmt-cli" << EOF
#!/bin/bash
# LNMT CLI Wrapper
export LNMT_HOME="$LNMT_HOME"
export LNMT_CONFIG="$LNMT_CONFIG_DIR/lnmt.yml"
exec "$LNMT_HOME/bin/lnmt" "\$@"
EOF
    
    chmod +x "/usr/local/bin/lnmt-cli"
    
    # Set up log rotation
    cat > "/etc/logrotate.d/lnmt" << EOF
$LNMT_LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $LNMT_USER $LNMT_GROUP
    postrotate
        systemctl reload lnmt >/dev/null 2>&1 || true
    endscript
}
EOF

    log_success "Post-installation setup completed"
}

# Display installation summary
show_summary() {
    echo
    echo "=============================================="
    log_success "LNMT Installation Complete!"
    echo "=============================================="
    echo
    echo "Installation Details:"
    echo "  Version: $LNMT_VERSION"
    echo "  Install Type: $INSTALL_TYPE"
    echo "  Home Directory: $LNMT_HOME"
    echo "  Config Directory: $LNMT_CONFIG_DIR"
    echo "  Data Directory: $LNMT_DATA_DIR"
    echo "  Log Directory: $LNMT_LOG_DIR"
    echo "  User/Group: $LNMT_USER:$LNMT_GROUP"
    echo
    echo "Services:"
    echo "  • lnmt.service - Main LNMT daemon"
    echo "  • lnmt-web.service - Web interface"
    echo "  • lnmt-scheduler.service - Task scheduler"
    echo
    echo "Next Steps:"
    echo "  1. Review configuration: $LNMT_CONFIG_DIR/lnmt.yml"
    echo "  2. Start services: systemctl start lnmt lnmt-web lnmt-scheduler"
    echo "  3. Check status: systemctl status lnmt"
    echo "  4. Access web interface: http://localhost:8080"
    echo "  5. Use CLI: lnmt-cli --help"
    echo
    echo "Documentation:"
    echo "  • Installation log: $INSTALL_LOG"
    echo "  • Config files: $LNMT_CONFIG_DIR/"
    echo "  • Application logs: $LNMT_LOG_DIR/"
    echo
    if [[ -n "$BACKUP_DIR" ]]; then
        echo "Backup Location: $BACKUP_DIR"
        echo
    fi
    echo "For support and updates, visit: https://github.com/your-org/lnmt"
    echo "=============================================="
}

# Usage information
usage() {
    cat << EOF
LNMT Installer - Linux Network Management Toolbox

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -f, --force             Force installation (non-interactive)
    -t, --type TYPE         Installation type: full, minimal, venv, docker
    -u, --unattended        Run in unattended mode
    -v, --verbose           Enable verbose output
    --skip-deps             Skip system dependency installation
    --backup-dir DIR        Custom backup directory

Examples:
    $0                      Interactive installation
    $0 -f -t venv           Force install with virtual environment
    $0 --unattended         Unattended installation with defaults

EOF
}

# Main installation function
main() {
    local skip_deps=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--force)
                FORCE_INSTALL=true
                INTERACTIVE_MODE=false
                shift
                ;;
            -t|--type)
                INSTALL_TYPE="$2"
                shift 2
                ;;
            -u|--unattended)
                INTERACTIVE_MODE=false
                shift
                ;;
            --skip-deps)
                skip_deps=true
                shift
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Initialize logging
    mkdir -p "$(dirname "$INSTALL_LOG")"
    
    echo "LNMT Installer v$LNMT_VERSION"
    echo "=============================="
    
    # Pre-flight checks
    check_root
    detect_os
    
    # Interactive confirmation
    if [[ "$INTERACTIVE_MODE" == true && "$FORCE_INSTALL" != true ]]; then
        echo
        echo "Installation Summary:"
        echo "  OS: $DETECTED_OS $DETECTED_VERSION"
        echo "  Install Type: $INSTALL_TYPE"
        echo "  Package Manager: $PACKAGE_MANAGER"
        echo "  Python: $PYTHON_CMD"
        echo
        read -p "Continue with installation? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Installation cancelled by user"
            exit 0
        fi
    fi
    
    # Create backup of existing installation
    create_backup
    
    # Installation steps
    if [[ "$skip_deps" != true ]]; then
        install_dependencies
    fi
    
    create_system_resources
    setup_python_env
    install_lnmt_modules
    create_default_config
    run_migrations
    setup_systemd_services
    post_install_setup
    
    # Show installation summary
    show_summary
    
    log_success "LNMT installation completed successfully!"
}

# Run main function
main "$@"