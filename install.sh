#!/bin/bash
set -e

echo "Installing LNMT Integration Polish Pack..."

# Create config directory if not exists
mkdir -p /etc/lnmt
touch /etc/lnmt/lnmt.conf

# Setup log directory
mkdir -p /var/log/lnmt

# Python deps
pip install -r requirements.txt

echo "Installation complete."
