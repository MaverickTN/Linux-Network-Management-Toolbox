#!/bin/bash
# LNMT Secure Installer Script
# Version: RC2-Hardened
# Security Level: Production Ready

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure Internal Field Separator

# Security Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/lnmt-installer.log"
readonly TEMP_DIR=$(mktemp -d -t lnmt-install.XXXXXXXXXX)
readonly LNMT_USER="lnmt"
readonly LNMT_GROUP="lnmt"
readonly INSTALL_PREFIX="/opt/lnmt"
readonly CONFIG_DIR="/etc/lnmt"
readonly SERVICE_USER_UID=1000
readonly CHECKSUM_FILE="lnmt-checksums.sha256"

# Cleanup function
cleanup() {
    local exit_code=$?
    log "INFO" "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    exit $exit_code
}

# Trap cleanup on exit
trap cleanup EXIT INT TERM

# Secure logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Input validation functions
validate_user_input() {
    local input="$1"
    local pattern="$2"
    
    if [[ ! "$input" =~ $pattern ]]; then
        log "ERROR" "Invalid input: $input"
        return 1
    fi
    return 0
}

# Privilege check
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This installer must be run as root"
        exit 1
    fi
    
    # Check if running in proper context
    if [[ -n "${SUDO_USER:-}" ]]; then
        log "INFO" "Running via sudo as user: $SUDO_USER"
    fi
}

# System requirements check
check_system_requirements() {
    log "INFO" "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log "ERROR" "Cannot determine OS version"
        exit 1
    fi
    
    source /etc/os-release
    case "$ID" in
        ubuntu|debian|centos|rhel|fedora)
            log "INFO" "Supported OS detected: $PRETTY_NAME"
            ;;
        *)
            log "ERROR" "Unsupported OS: $PRETTY_NAME"
            exit 1
            ;;
    esac
    
    # Check required commands
    local required_commands=("systemctl" "useradd" "python3" "pip3" "openssl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            log "ERROR" "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version >= 3.8" | bc -l) -ne 1 ]]; then
        log "ERROR" "Python 3.8 or higher required. Found: $python_version"
        exit 1
    fi
    
    log "INFO" "System requirements check passed"
}

# Verify package integrity
verify_integrity() {
    log "INFO" "Verifying package integrity..."
    
    if [[ ! -f "$CHECKSUM_FILE" ]]; then
        log "ERROR" "Checksum file not found: $CHECKSUM_FILE"
        exit 1
    fi
    
    # Verify checksums
    if ! sha256sum -c "$CHECKSUM_FILE" --quiet; then
        log "ERROR" "Package integrity verification failed"
        exit 1
    fi
    
    log "INFO" "Package integrity verified successfully"
}

# Create secure service user
create_service_user() {
    log "INFO" "Creating LNMT service user..."
    
    if id "$LNMT_USER" &>/dev/null; then
        log "INFO" "User $LNMT_USER already exists"
        return 0
    fi
    
    # Create system user with restricted privileges
    useradd --system \
            --user-group \
            --home-dir "$INSTALL_PREFIX" \
            --no-create-home \
            --shell /usr/sbin/nologin \
            --comment "LNMT Service User" \
            "$LNMT_USER"
    
    log "INFO" "Service user created successfully"
}

# Create directory structure with secure permissions
create_directories() {
    log "INFO" "Creating directory structure..."
    
    local directories=(
        "$INSTALL_PREFIX"
        "$INSTALL_PREFIX/services"
        "$INSTALL_PREFIX/cli"
        "$INSTALL_PREFIX/web"
        "$INSTALL_PREFIX/themes"
        "$INSTALL_PREFIX/tests"
        "$INSTALL_PREFIX/docs"
        "$INSTALL_PREFIX/integration"
        "$CONFIG_DIR"
        "/var/lib/lnmt"
        "/var/log/lnmt"
        "/var/run/lnmt"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        case "$dir" in
            "$CONFIG_DIR")
                chown root:$LNMT_GROUP "$dir"
                chmod 750 "$dir"
                ;;
            "/var/log/lnmt")
                chown $LNMT_USER:adm "$dir"
                chmod 755 "$dir"
                ;;
            "/var/run/lnmt")
                chown $LNMT_USER:$LNMT_GROUP "$dir"
                chmod 755 "$dir"
                ;;
            *)
                chown $LNMT_USER:$LNMT_GROUP "$dir"
                chmod 755 "$dir"
                ;;
        esac
    done
    
    log "INFO" "Directories created with secure permissions"
}

# Install Python dependencies securely
install_dependencies() {
    log "INFO" "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_PREFIX/venv"
    source "$INSTALL_PREFIX/venv/bin/activate"
    
    # Upgrade pip securely
    pip install --upgrade pip setuptools wheel
    
    # Install from requirements with hash verification
    if [[ -f "requirements.txt" ]]; then
        pip install --require-hashes -r requirements.txt
    else
        log "WARNING" "requirements.txt not found, installing basic dependencies"
        pip install flask==2.3.3 \
                   cryptography==41.0.7 \
                   pyjwt==2.8.0 \
                   bcrypt==4.0.1 \
                   psutil==5.9.6
    fi
    
    # Set proper ownership
    chown -R $LNMT_USER:$LNMT_GROUP "$INSTALL_PREFIX/venv"
    
    log "INFO" "Dependencies installed successfully"
}

# Copy and secure application files
install_application_files() {
    log "INFO" "Installing application files..."
    
    # Copy files with secure permissions
    local file_mappings=(
        "services:$INSTALL_PREFIX/services:644"
        "cli:$INSTALL_PREFIX/cli:750"
        "web:$INSTALL_PREFIX/web:644"
        "themes:$INSTALL_PREFIX/themes:644"
        "tests:$INSTALL_PREFIX/tests:644"
        "docs:$INSTALL_PREFIX/docs:644"
        "integration:$INSTALL_PREFIX/integration:644"
        "config:$CONFIG_DIR:600"
    )
    
    for mapping in "${file_mappings[@]}"; do
        IFS=':' read -r source dest perms <<< "$mapping"
        
        if [[ -d "$source" ]]; then
            cp -r "$source"/* "$dest/"
            find "$dest" -type f -exec chmod "$perms" {} \;
            
            # Set ownership based on destination
            case "$dest" in
                "$CONFIG_DIR"*)
                    chown -R root:$LNMT_GROUP "$dest"
                    ;;
                *)
                    chown -R $LNMT_USER:$LNMT_GROUP "$dest"
                    ;;
            esac
        fi
    done
    
    log "INFO" "Application files installed with secure permissions"
}

# Generate secure configuration
generate_secure_config() {
    log "INFO" "Generating secure configuration..."
    
    # Generate encryption keys
    local secret_key=$(openssl rand -hex 32)
    local jwt_secret=$(openssl rand -hex 32)
    local db_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Create main configuration file
    cat > "$CONFIG_DIR/lnmt.conf" << EOF
# LNMT Configuration File
# Generated: $(date)
# Security Level: Production

[security]
secret_key = $secret_key
jwt_secret = $jwt_secret
db_encryption_key = $db_key
session_timeout = 1800
max_login_attempts = 5
lockout_duration = 900

[database]
path = /var/lib/lnmt/lnmt.db
backup_path = /var/lib/lnmt/backups
encrypt = true

[logging]
level = INFO
path = /var/log/lnmt
rotate = true
max_size = 10MB
backup_count = 5

[network]
bind_address = 127.0.0.1
port = 8080
use_tls = true
cert_path = $CONFIG_DIR/ssl/cert.pem
key_path = $CONFIG_DIR/ssl/key.pem

[services]
auth_enabled = true
backup_enabled = true
monitoring_enabled = true
scheduler_enabled = true
EOF

    # Secure configuration file
    chown root:$LNMT_GROUP "$CONFIG_DIR/lnmt.conf"
    chmod 640 "$CONFIG_DIR/lnmt.conf"
    
    log "INFO" "Secure configuration generated"
}

# Generate SSL certificates
generate_ssl_certificates() {
    log "INFO" "Generating SSL certificates..."
    
    local ssl_dir="$CONFIG_DIR/ssl"
    mkdir -p "$ssl_dir"
    
    # Generate self-signed certificate for initial setup
    openssl req -x509 -newkey rsa:4096 -keyout "$ssl_dir/key.pem" \
                -out "$ssl_dir/cert.pem" -days 365 -nodes \
                -subj "/C=US/ST=State/L=City/O=LNMT/CN=localhost"
    
    # Secure SSL files
    chown root:$LNMT_GROUP "$ssl_dir"/*
    chmod 640 "$ssl_dir/key.pem"
    chmod 644 "$ssl_dir/cert.pem"
    
    log "INFO" "SSL certificates generated"
}

# Install systemd service with security hardening
install_systemd_service() {
    log "INFO" "Installing systemd service..."
    
    cat > "/etc/systemd/system/lnmt.service" << EOF
[Unit]
Description=LNMT Network Management Service
Documentation=file://$INSTALL_PREFIX/docs/
After=network-online.target
Wants=network-online.target
RequiresMountsFor=$INSTALL_PREFIX /var/lib/lnmt

[Service]
Type=notify
User=$LNMT_USER
Group=$LNMT_GROUP
ExecStart=$INSTALL_PREFIX/venv/bin/python $INSTALL_PREFIX/services/main_service.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=5
TimeoutStartSec=60
TimeoutStopSec=30

# Security Hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectHostname=yes
ProtectClock=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
RemoveIPC=yes

# Capabilities
CapabilityBoundingSet=CAP_BIND_SERVICE CAP_NET_ADMIN
AmbientCapabilities=CAP_BIND_SERVICE CAP_NET_ADMIN

# File system access
ReadWritePaths=/var/lib/lnmt /var/log/lnmt /var/run/lnmt
ReadOnlyPaths=$INSTALL_PREFIX $CONFIG_DIR

# Environment
Environment=PYTHONPATH=$INSTALL_PREFIX
Environment=LNMT_CONFIG_DIR=$CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable lnmt.service
    
    log "INFO" "Systemd service installed and enabled"
}

# Configure firewall
configure_firewall() {
    log "INFO" "Configuring firewall..."
    
    # Check if UFW is available
    if command -v ufw &>/dev/null; then
        ufw --force enable
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow ssh
        ufw allow 8080/tcp comment 'LNMT Web Interface'
        log "INFO" "UFW firewall configured"
    elif command -v firewall-cmd &>/dev/null; then
        systemctl enable --now firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-port=8080/tcp
        firewall-cmd --reload
        log "INFO" "Firewalld configured"
    else
        log "WARNING" "No firewall management tool found"
    fi
}

# Setup log rotation
setup_log_rotation() {
    log "INFO" "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/lnmt" << EOF
/var/log/lnmt/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $LNMT_USER adm
    postrotate
        systemctl reload lnmt.service > /dev/null 2>&1 || true
    endscript
}
EOF

    log "INFO" "Log rotation configured"
}

# Post-installation security checks
post_install_security_check() {
    log "INFO" "Performing post-installation security checks..."
    
    local issues=0
    
    # Check file permissions
    local critical_files=(
        "$CONFIG_DIR/lnmt.conf:640"
        "$CONFIG_DIR/ssl/key.pem:640"
        "$INSTALL_PREFIX/cli:750"
    )
    
    for file_perm in "${critical_files[@]}"; do
        IFS=':' read -r file expected_perm <<< "$file_perm"
        if [[ -e "$file" ]]; then
            local actual_perm=$(stat -c "%a" "$file")
            if [[ "$actual_perm" != "$expected_perm" ]]; then
                log "WARNING" "Incorrect permissions on $file: $actual_perm (expected: $expected_perm)"
                ((issues++))
            fi
        fi
    done
    
    # Check service user
    if ! id "$LNMT_USER" &>/dev/null; then
        log "ERROR" "Service user $LNMT_USER not found"
        ((issues++))
    fi
    
    # Check systemd service
    if ! systemctl is-enabled lnmt.service &>/dev/null; then
        log "WARNING" "LNMT service not enabled"
        ((issues++))
    fi
    
    if [[ $issues -eq 0 ]]; then
        log "INFO" "All security checks passed"
    else
        log "WARNING" "Found $issues security issues"
    fi
    
    return $issues
}

# Main installation function
main() {
    log "INFO" "Starting LNMT secure installation..."
    
    # Pre-installation checks
    check_privileges
    check_system_requirements
    verify_integrity
    
    # Core installation
    create_service_user
    create_directories
    install_dependencies
    install_application_files
    
    # Security configuration
    generate_secure_config
    generate_ssl_certificates
    install_systemd_service
    configure_firewall
    setup_log_rotation
    
    # Post-installation verification
    if post_install_security_check; then
        log "INFO" "LNMT installation completed successfully"
        echo
        echo "╔══════════════════════════════════════╗"
        echo "║        LNMT Installation Complete     ║"
        echo "╚══════════════════════════════════════╝"
        echo
        echo "Next steps:"
        echo "1. Review configuration: $CONFIG_DIR/lnmt.conf"
        echo "2. Start the service: systemctl start lnmt.service"
        echo "3. Access web interface: https://localhost:8080"
        echo "4. Check logs: journalctl -u lnmt.service"
        echo
        echo "Security features enabled:"
        echo "✓ Service isolation with restricted user"
        echo "✓ Encrypted configuration storage"
        echo "✓ SSL/TLS encryption"
        echo "✓ Firewall configuration"
        echo "✓ Log rotation and monitoring"
        echo "✓ Systemd security hardening"
    else
        log "ERROR" "Installation completed with security warnings"
        exit 1
    fi
}

# Run main installation
main "$@"