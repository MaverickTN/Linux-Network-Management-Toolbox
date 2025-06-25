#!/bin/bash

set -e

VERSION=$(python3 -c "from lnmt.__version__ import __version__; print(__version__)")

echo "Linux Network Management Toolbox (LNMT) Installer"
echo "Version: $VERSION"

if [[ $EUID -ne 0 ]]; then
   echo "This installer must be run as root." 
   exit 1
fi

INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/lnmt"
SERVICE_FILE="/etc/systemd/system/lnmt.service"

echo "Creating config directory at $CONFIG_DIR (if not exists)..."
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    echo "Created $CONFIG_DIR"
else
    echo "$CONFIG_DIR already exists. Skipping overwrite."
fi

echo "Installing LNMT core executable..."
cp lnmt/cli/main.py "$INSTALL_DIR/lnmt"
chmod +x "$INSTALL_DIR/lnmt"

echo "Copying systemd service file..."
if [ ! -f "$SERVICE_FILE" ]; then
    cp lnmt.service "$SERVICE_FILE"
    systemctl daemon-reexec
    systemctl daemon-reload
    echo "Service file installed at $SERVICE_FILE"
else
    echo "Service file already exists. Skipping overwrite."
fi

echo "Installation complete. You can enable the service with:"
echo "  systemctl enable lnmt"
echo "  systemctl start lnmt"
