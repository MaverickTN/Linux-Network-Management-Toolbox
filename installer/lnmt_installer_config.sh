#!/bin/bash
# LNMT Installer Configuration
# This file sets defaults for the installation

# Deployment mode: standalone or nginx
# Default: standalone (no external web server required)
DEPLOYMENT_MODE="${LNMT_DEPLOYMENT_MODE:-standalone}"

# Server settings
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8080"
DEFAULT_WORKERS="4"

# SSL settings (disabled by default for standalone)
SSL_ENABLED="${LNMT_SSL_ENABLED:-false}"
SSL_CERT_PATH="/etc/lnmt/certs/server.crt"
SSL_KEY_PATH="/etc/lnmt/certs/server.key"

# Service configuration
SYSTEMD_SERVICE_FILE="config/systemd/lnmt.service"
NGINX_CONFIG_FILE="config/nginx.conf.template"

# Installation paths
INSTALL_BASE="/opt/lnmt"
CONFIG_DIR="/etc/lnmt"
LOG_DIR="/var/log/lnmt"
DATA_DIR="/var/lib/lnmt"
BACKUP_DIR="/var/backups/lnmt"

# User and group
LNMT_USER="lnmt"
LNMT_GROUP="lnmt"

# Function to setup standalone deployment
setup_standalone() {
    echo "Setting up LNMT in standalone mode (recommended)..."
    
    # Copy the standalone runner
    cp installer/run_standalone.sh "$INSTALL_BASE/bin/"
    chmod +x "$INSTALL_BASE/bin/run_standalone.sh"
    
    # Update systemd service for standalone
    sed -i 's/# Standalone mode/# Standalone mode (default)/' "$SYSTEMD_SERVICE_FILE"
    
    # Disable nginx in config
    cat >> "$CONFIG_DIR/config.yml" << EOF

# Standalone deployment (no nginx required)
deployment:
  mode: standalone
  nginx_enabled: false
EOF
    
    echo "✓ Standalone mode configured"
    echo "  - No external web server required"
    echo "  - Access LNMT at http://${DEFAULT_HOST}:${DEFAULT_PORT}"
    echo "  - To enable SSL, see docs/DEPLOYMENT_OPTIONS.md"
}

# Function to setup nginx deployment (optional)
setup_nginx() {
    echo "Setting up LNMT with nginx reverse proxy..."
    echo "Note: This requires nginx to be installed separately"
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        echo "⚠ Warning: nginx not found. Please install nginx first."
        echo "  Ubuntu/Debian: sudo apt-get install nginx"
        echo "  RHEL/CentOS: sudo yum install nginx"
    fi
    
    # Process nginx template
    envsubst < "$NGINX_CONFIG_FILE" > /etc/nginx/sites-available/lnmt.conf
    ln -sf /etc/nginx/sites-available/lnmt.conf /etc/nginx/sites-enabled/
    
    # Update config for nginx mode
    cat >> "$CONFIG_DIR/config.yml" << EOF

# Nginx proxy deployment
deployment:
  mode: nginx
  nginx_enabled: true
  internal_port: 8080
  external_port: 80
EOF
    
    echo "✓ Nginx mode configured"
    echo "  - Remember to start/reload nginx"
    echo "  - Internal: http://127.0.0.1:8080"
    echo "  - External: http://${DEFAULT_HOST}"
}

# Export functions for use in main installer
export -f setup_standalone
export -f setup_nginx