#!/bin/bash
# lnmt/install.sh
# Linux Network Management Toolbox Installer/Updater

set -e

APP_NAME="lnmt"
CONFIG_DIR="/etc/lnmt"
DB_FILE="$CONFIG_DIR/lnmt.sqlite3"
SYSTEMD_SERVICE="/etc/systemd/system/lnmt.service"
BIN_TARGET="/usr/local/bin/lnmt"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Linux Network Management Toolbox..."

# Create config and data directories
sudo mkdir -p "$CONFIG_DIR"

# Copy configuration template if not present
if [ ! -f "$CONFIG_DIR/server_config.json" ]; then
    sudo cp "$REPO_DIR/config/server_config.json.example" "$CONFIG_DIR/server_config.json"
fi

# Place executable wrapper
sudo cp "$REPO_DIR/lnmt-runner.py" "$BIN_TARGET"
sudo chmod +x "$BIN_TARGET"

# Copy systemd service file
sudo tee "$SYSTEMD_SERVICE" > /dev/null <<EOL
[Unit]
Description=Linux Network Management Toolbox Web Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 $BIN_TARGET web
WorkingDirectory=$CONFIG_DIR
Restart=on-failure
User=lnmt
Group=lnmt

[Install]
WantedBy=multi-user.target
EOL

echo "Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable lnmt.service

echo "Creating lnmt user/group if necessary..."
if ! id -u lnmt >/dev/null 2>&1; then
    sudo useradd -r -s /bin/false lnmt
fi

echo "Installation complete! Start with: sudo systemctl start lnmt"
