#!/bin/bash
# LNMT Device Tracker Installation and Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/lnmt"
SERVICE_NAME="lnmt-device-tracker"
LOG_DIR="/var/log/lnmt"
DATA_DIR="/var/lib/lnmt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

install_dependencies() {
    print_status "Installing dependencies..."
    
    # Update package list
    apt-get update
    
    # Install Python 3 and required packages
    apt-get install -y python3 python3-pip sqlite3
    
    print_status "Dependencies installed"
}

create_directories() {
    print_status "Creating directories..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/services"
    mkdir -p "$INSTALL_DIR/cli"
    
    # Create log and data directories
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
    
    # Set permissions for data and log directories
    chown -R nobody:nogroup "$DATA_DIR"
    chown -R nobody:nogroup "$LOG_DIR"
    chmod -R 755 "$DATA_DIR"
    chmod -R 755 "$LOG_DIR"
    
    print_status "Directories created"
}

install_files() {
    print_status "Installing device tracker files..."
    
    # Copy service files
    if [[ -f "$SCRIPT_DIR/services/device_tracker.py" ]]; then
        cp "$SCRIPT_DIR/services/device_tracker.py" "$INSTALL_DIR/services/"
        chmod +x "$INSTALL_DIR/services/device_tracker.py"
    else
        print_error "device_tracker.py not found in services directory"
        exit 1
    fi
    
    # Copy CLI files
    if [[ -f "$SCRIPT_DIR/cli/device_tracker_ctl.py" ]]; then
        cp "$SCRIPT_DIR/cli/device_tracker_ctl.py" "$INSTALL_DIR/cli/"
        chmod +x "$INSTALL_DIR/cli/device_tracker_ctl.py"
    else
        print_warning "device_tracker_ctl.py not found in cli directory"
    fi
    
    # Create symlink for CLI tool
    if [[ -f "$INSTALL_DIR/cli/device_tracker_ctl.py" ]]; then
        ln -sf "$INSTALL_DIR/cli/device_tracker_ctl.py" "/usr/local/bin/device_tracker_ctl"
    fi
    
    print_status "Files installed"
}

create_systemd_service() {
    print_status "Creating systemd service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=LNMT Device Tracker Service
Documentation=https://github.com/lnmt/device-tracker
After=network.target
Wants=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/services/device_tracker.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${LOG_DIR} ${DATA_DIR}
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=1024
MemoryMax=256M

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    print_status "Systemd service created"
}

check_dhcp_lease_file() {
    print_status "Checking DHCP lease file..."
    
    LEASE_FILES=(
        "/var/lib/misc/dnsmasq.leases"
        "/var/lib/dhcp/dhcpd.leases"
        "/var/lib/dhcpcd5/dhcpcd.leases"
    )
    
    FOUND_LEASE_FILE=""
    for lease_file in "${LEASE_FILES[@]}"; do
        if [[ -f "$lease_file" ]]; then
            FOUND_LEASE_FILE="$lease_file"
            print_status "Found DHCP lease file: $lease_file"
            break
        fi
    done
    
    if [[ -z "$FOUND_LEASE_FILE" ]]; then
        print_warning "No DHCP lease file found. Common locations:"
        for lease_file in "${LEASE_FILES[@]}"; do
            echo "  - $lease_file"
        done
        print_warning "You may need to configure your DHCP server or update the lease file path"
    fi
    
    # Check if nobody user can read the lease file
    if [[ -n "$FOUND_LEASE_FILE" ]]; then
        if ! sudo -u nobody test -r "$FOUND_LEASE_FILE"; then
            print_warning "User 'nobody' cannot read $FOUND_LEASE_FILE"
            print_warning "You may need to adjust permissions or add 'nobody' to appropriate group"
        fi
    fi
}

create_test_data() {
    print_status "Creating test DHCP lease file..."
    
    TEST_LEASE_FILE="$DATA_DIR/test_dnsmasq.leases"
    CURRENT_TIME=$(date +%s)
    EXPIRE_TIME=$((CURRENT_TIME + 3600))  # 1 hour from now
    
    cat > "$TEST_LEASE_FILE" << EOF
$EXPIRE_TIME b8:27:eb:12:34:56 192.168.1.100 raspberry-pi *
$EXPIRE_TIME 3c:22:fb:ab:cd:ef 192.168.1.101 johns-iphone *
$EXPIRE_TIME 02:00:00:12:34:56 192.168.1.102 random-device *
$EXPIRE_TIME 08:00:27:11:22:33 192.168.1.103 test-vm *
$EXPIRE_TIME 06:aa:bb:cc:dd:ee 192.168.1.104 * *
EOF
    
    chown nobody:nogroup "$TEST_LEASE_FILE"
    chmod 644 "$TEST_LEASE_FILE"
    
    print_status "Test lease file created at: $TEST_LEASE_FILE"
}

run_tests() {
    print_status "Running basic tests..."
    
    # Test Python script syntax
    if python3 -m py_compile "$INSTALL_DIR/services/device_tracker.py"; then
        print_status "✅ device_tracker.py syntax OK"
    else
        print_error "❌ device_tracker.py syntax error"
        exit 1
    fi
    
    if [[ -f "$INSTALL_DIR/cli/device_tracker_ctl.py" ]]; then
        if python3 -m py_compile "$INSTALL_DIR/cli/device_tracker_ctl.py"; then
            print_status "✅ device_tracker_ctl.py syntax OK"
        else
            print_error "❌ device_tracker_ctl.py syntax error"
            exit 1
        fi
    fi
    
    # Test database creation
    cd "$INSTALL_DIR"
    if python3 -c "
import sys
sys.path.append('$INSTALL_DIR')
from services.device_tracker import DeviceDatabase
db = DeviceDatabase('$DATA_DIR/test.db')
print('Database test passed')
"; then
        print_status "✅ Database creation test passed"
        rm -f "$DATA_DIR/test.db"
    else
        print_error "❌ Database test failed"
        exit 1
    fi
    
    print_status "All tests passed"
}

show_usage() {
    cat << EOF

=== LNMT Device Tracker Installation Complete ===

Service Management:
  Start service:    sudo systemctl start $SERVICE_NAME
  Stop service:     sudo systemctl stop $SERVICE_NAME
  Enable on boot:   sudo systemctl enable $SERVICE_NAME
  Check status:     sudo systemctl status $SERVICE_NAME
  View logs:        sudo journalctl -u $SERVICE_NAME -f

CLI Usage:
  List devices:     device_tracker_ctl list
  Show history:     device_tracker_ctl history <mac_address>
  Show alerts:      device_tracker_ctl alerts
  Show status:      device_tracker_ctl status
  
Configuration:
  Service file:     /etc/systemd/system/$SERVICE_NAME.service
  Installation:     $INSTALL_DIR
  Database:         $DATA_DIR/device_tracker.db
  Logs:             $LOG_DIR/device_tracker.log
  Test data:        $DATA_DIR/test_dnsmasq.leases

Testing:
  # Test with sample data
  sudo PYTHONPATH=$INSTALL_DIR python3 $INSTALL_DIR/services/device_tracker.py --lease-file $DATA_DIR/test_dnsmasq.leases --poll-once
  
  # Check results
  device_tracker_ctl list

Next Steps:
1. Configure your DHCP server lease file path if needed
2. Start the service: sudo systemctl start $SERVICE_NAME
3. Enable on boot: sudo systemctl enable $SERVICE_NAME
4. Monitor with: device_tracker_ctl status

EOF
}

main() {
    echo "LNMT Device Tracker Installation Script"
    echo "======================================"
    
    check_root
    install_dependencies
    create_directories
    install_files
    create_systemd_service
    check_dhcp_lease_file
    create_test_data
    run_tests
    show_usage
    
    print_status "Installation completed successfully!"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi