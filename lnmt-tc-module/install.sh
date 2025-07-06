#!/bin/bash
# LNMT TC Module Installation

echo "Installing LNMT TC/QoS Module..."

# Install Python dependencies
pip3 install -r requirements.txt

# Make CLI executable
chmod +x cli/tcctl.py

# Create symlink for global access (optional)
# sudo ln -sf $PWD/cli/tcctl.py /usr/local/bin/tcctl

echo "Installation complete!"
echo "Usage: python cli/tcctl.py interfaces"
