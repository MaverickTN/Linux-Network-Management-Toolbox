#!/bin/bash
set -e

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_DIR="$HOME/.config/lnmt"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_FILE="lnmt.service"

echo "== Linux Network Management Toolbox Installer =="

# 1. Create config dir
mkdir -p "$CONFIG_DIR"
echo "Created config directory at $CONFIG_DIR"

# 2. Copy/initialize config and database if not present
if [ ! -f "$CONFIG_DIR/server_config.json" ]; then
    cp "$REPO_DIR/default_config.json" "$CONFIG_DIR/server_config.json" 2>/dev/null || touch "$CONFIG_DIR/server_config.json"
    echo "Config file created."
fi

if [ ! -f "$CONFIG_DIR/lnmt.sqlite3" ]; then
    python3 -c 'import lnmt.core.database'
    echo "Database initialized."
fi

# 3. Install Python dependencies
if [ -f "$REPO_DIR/requirements.txt" ]; then
    pip3 install --user -r "$REPO_DIR/requirements.txt"
fi

# 4. Install or update CLI script
if [ ! -L "/usr/local/bin/lnmt" ]; then
    sudo ln -sf "$REPO_DIR/lnmt-runner.py" /usr/local/bin/lnmt
    sudo chmod +x "$REPO_DIR/lnmt-runner.py"
    echo "Installed lnmt CLI entry point."
fi

# 5. Copy systemd service
if [ -f "$REPO_DIR/$SERVICE_FILE" ]; then
    sudo cp "$REPO_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/"
    sudo systemctl daemon-reload
    echo "Service file copied."
    echo "You can now enable the web service with:"
    echo "  sudo systemctl enable --now lnmt"
fi

echo "== Install complete. =="
