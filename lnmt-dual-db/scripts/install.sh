#!/bin/bash
# LNMT Dual-Database Architecture Installation Script

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root"
    exit 1
fi

log_info "Installing LNMT Dual-Database Architecture..."

# Install system dependencies
log_info "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip python3-venv sqlite3
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip sqlite
fi

# Create user and directories
log_info "Creating user and directories..."
if ! id "lnmt" &>/dev/null; then
    useradd -r -s /bin/bash -d /opt/lnmt lnmt
fi

mkdir -p /opt/lnmt
mkdir -p /etc/lnmt
mkdir -p /var/lib/lnmt
mkdir -p /var/log/lnmt

# Create virtual environment
log_info "Setting up Python environment..."
python3 -m venv /opt/lnmt/venv
/opt/lnmt/venv/bin/pip install --upgrade pip
/opt/lnmt/venv/bin/pip install -r requirements.txt

# Copy files
log_info "Installing files..."
cp -r core/* /opt/lnmt/
cp -r config/* /etc/lnmt/
cp -r systemd/* /etc/systemd/system/

# Set permissions
chown -R lnmt:lnmt /opt/lnmt
chown -R lnmt:lnmt /etc/lnmt
chown -R lnmt:lnmt /var/lib/lnmt
chown -R lnmt:lnmt /var/log/lnmt

chmod 640 /etc/lnmt/*.json
chmod +x /opt/lnmt/*.py

# Enable systemd services
log_info "Enabling systemd services..."
systemctl daemon-reload
systemctl enable lnmt
systemctl enable lnmt-backup.timer

# Initialize database
log_info "Initializing database..."
sudo -u lnmt /opt/lnmt/venv/bin/python /opt/lnmt/lnmt_db.py init

# Create CLI symlink
ln -sf /opt/lnmt/lnmt_db.py /usr/local/bin/lnmt

log_info "Installation completed successfully!"
echo
echo "Usage:"
echo "  lnmt config                    # Show configuration"
echo "  systemctl start lnmt           # Start service"
echo "  systemctl status lnmt          # Check status"
