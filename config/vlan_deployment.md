# LNMT VLAN Controller Deployment Guide

## Overview

The VLAN Controller module provides comprehensive VLAN management, bandwidth control, security automation, and network topology visualization for the LNMT system.

## Features

- ✅ **VLAN CRUD Operations**: Create, read, update, delete VLANs via CLI and API
- ✅ **Interface Mapping**: Automatic VLAN interface creation and IP configuration
- ✅ **Bandwidth Management**: Dynamic bandwidth limiting and QoS priority control
- ✅ **Security Automation**: Real-time monitoring with auto-blacklisting capabilities
- ✅ **Shorewall Integration**: Automatic firewall rule generation and management
- ✅ **Topology Export**: Network diagram generation using Graphviz
- ✅ **Statistics Monitoring**: Real-time VLAN usage tracking and reporting
- ✅ **Configuration Management**: Import/export VLAN configurations

## Installation

### 1. System Requirements

```bash
# Install required system packages
sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    iproute2 \
    shorewall \
    graphviz \
    sqlite3

# Install Python dependencies
pip3 install \
    tabulate \
    pyyaml \
    flask \
    ipaddress
```

### 2. Directory Structure

```bash
# Create LNMT directory structure
sudo mkdir -p /opt/lnmt/{services,cli,web,config,logs}
sudo mkdir -p /var/lib/lnmt
sudo mkdir -p /etc/lnmt

# Set permissions
sudo chown -R $USER:$USER /opt/lnmt
sudo chmod +x /opt/lnmt/cli/vlanctl.py
```

### 3. File Deployment

```bash
# Deploy service files
sudo cp vlan_controller.py /opt/lnmt/services/
sudo cp vlanctl.py /opt/lnmt/cli/
sudo cp vlan_examples.py /opt/lnmt/examples/

# Create symbolic link for CLI
sudo ln -sf /opt/lnmt/cli/vlanctl.py /usr/local/bin/vlanctl

# Set executable permissions
sudo chmod +x /opt/lnmt/services/vlan_controller.py
sudo chmod +x /opt/lnmt/cli/vlanctl.py
sudo chmod +x /usr/local/bin/vlanctl
```

### 4. Configuration

Create the main configuration file:

```yaml
# /etc/lnmt/vlan_controller.yaml
database:
  path: "/var/lib/lnmt/vlan.db"
  backup_interval: 3600  # seconds

monitoring:
  enabled: true
  interval: 30  # seconds
  stats_retention_days: 30

shorewall:
  config_dir: "/etc/shorewall"
  auto_reload: true
  backup_config: true

security:
  auto_blacklist_duration: 3600  # seconds
  max_threshold_violations: 3
  notification_enabled: true

logging:
  level: "INFO"
  file: "/var/log/lnmt/vlan_controller.log"
  max_size: "10MB"
  backup_count: 5

topology:
  export_path: "/var/lib/lnmt/topology"
  auto_generate: true
  formats: ["dot", "png", "svg"]
```

### 5. Service Setup

Create a systemd service for the VLAN controller:

```ini
# /etc/systemd/system/lnmt-vlan-controller.service
[Unit]
Description=LNMT VLAN Controller Service
After=network.target shorewall.service
Wants=shorewall.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/lnmt/services
ExecStart=/usr/bin/python3 /opt/lnmt/services/vlan_controller.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/lnmt /var/log/lnmt /etc/shorewall

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lnmt-vlan-controller
sudo systemctl start lnmt-vlan-controller
sudo systemctl status lnmt-vlan-controller
```

## Usage Examples

### CLI Usage

#### Basic VLAN Management

```bash
# Create a new VLAN
vlanctl create 100 \
  --name "Guest Network" \
  --subnet "192.168.100.0/24" \
  --gateway "192.168.100.1" \
  --interfaces "eth0" \
  --bandwidth-limit 50 \
  --usage-threshold 80 \
  --auto-blacklist

# List all VLANs
vlanctl list

# Show VLAN details
vlanctl show 100

# Update VLAN configuration
vlanctl update 100 --bandwidth-limit 100

# Delete a VLAN
vlanctl delete 100 --force
```

#### Advanced Operations

```bash
# Export network topology
vlanctl topology --format png --output /tmp/network.png

# Monitor VLAN statistics (real-time)
vlanctl monitor

# Validate all VLAN configurations
vlanctl validate

# Import configuration from file
vlanctl import-config /path/to/vlans.yaml

# Export current configuration
vlanctl export-config --output /backup/vlans.yaml
```

### API Usage

```python
from vlan_controller import VLANController

# Initialize controller
controller = VLANController()

# Create a VLAN programmatically
success = controller.create_vlan(
    vlan_id=200,
    name="IoT Network",
    description="Network for IoT devices",
    subnet="192.168.200.0/24",
    gateway="192.168.200.1",
    interfaces=["eth0", "wlan0"],
    bandwidth_limit=50,
    usage_threshold=85,
    auto_blacklist=True,
    priority=5
)

# Start monitoring
controller.start_monitoring()

# Get statistics
vlans = controller.list_vlans()
for vlan in vlans:
    print(f"VLAN {vlan.vlan_id}: {vlan.name}")
```

### Configuration Files

#### YAML Configuration Example

```yaml
# example_vlans.yaml
vlans:
  - vlan_id: 10
    name: "DMZ Network"
    description: "Demilitarized zone for public services"
    subnet: "10.0.10.0/24"
    gateway: "10.0.10.1"
    interfaces: ["eth0"]
    bandwidth_limit: 1000
    usage_threshold: 85
    auto_blacklist: true
    priority: 2

  - vlan_id: 20
    name: "Development Network"
    description: "Network for development servers"
    subnet: "10.0.20.0/24"
    gateway: "10.0.20.1"
    interfaces: ["eth0", "eth1"]
    bandwidth_limit: 500
    usage_threshold: 75
    auto_blacklist: false
    priority: 4
```

## Integration with Other LNMT Modules

### Device Tracker Integration

The VLAN controller integrates with the device tracker module for:

- Real-time device counting per VLAN
- Device behavior monitoring
- Automatic blacklisting of problematic devices

```python
# Example integration code
def integrate_with_device_tracker():
    from device_tracker import DeviceTracker
    
    device_tracker = DeviceTracker()
    vlan_controller = VLANController()
    
    # Get devices by VLAN
    devices = device_tracker.get_devices_by_vlan(100)
    
    # Monitor device behavior
    for device in devices:
        if device.bandwidth_usage > threshold:
            vlan_controller.db.blacklist_device(
                device.mac_address,
                device.ip_address,
                100,
                "Excessive bandwidth usage"
            )
```

### Web Dashboard Integration

```python
from flask import Flask, render_template, jsonify

app = Flask(__name__)
controller = VLANController()

@app.route('/dashboard/vlans')
def vlan_dashboard():
    vlans = controller.list_vlans()
    return render_template('vlan_dashboard.html', vlans=vlans)

@app.route('/api/vlans/<int:vlan_id>/stats')
def vlan_stats(vlan_id):
    # Return real-time statistics
    stats = controller.get_vlan_stats(vlan_id)
    return jsonify(stats)
```

## Security Considerations

### Auto-Blacklisting

The auto-blacklisting feature automatically blocks devices that exceed usage thresholds:

1. **Threshold Monitoring**: Continuous monitoring of bandwidth usage per VLAN
2. **Device Identification**: Integration with device tracker to identify high-usage devices
3. **Automatic Action**: Immediate blocking via Shorewall rules
4. **Notification**: Alerts sent to administrators
5. **Review Process**: Manual review and whitelist options

### Network Isolation

VLANs provide network segmentation for:

- **Guest Network Isolation**: Prevent guest access to internal resources
- **IoT Device Containment**: Isolate potentially vulnerable IoT devices
- **Service Segmentation**: Separate critical services from general traffic
- **Compliance Requirements**: Meet regulatory network isolation requirements

## Monitoring and Maintenance

### Log Files

```bash
# View VLAN controller logs
tail -f /var/log/lnmt/vlan_controller.log

# Check service status
sudo systemctl status lnmt-vlan-controller

# View database statistics
sqlite3 /var/lib/lnmt/vlan.db "SELECT COUNT(*) FROM vlans;"
```

### Backup and Recovery

```bash
# Backup VLAN database
cp /var/lib/lnmt/vlan.db /backup/vlan_$(date +%Y%m%d).db

# Export configuration for backup
vlanctl export-config --output /backup/vlan_config_$(date +%Y%m%d).yaml

# Restore from backup
vlanctl import-config /backup/vlan_config_20250101.yaml
```

### Performance Tuning

```bash
# Optimize database
sqlite3 /var/lib/lnmt/vlan.db "VACUUM; ANALYZE;"

# Clean old statistics
sqlite3 /var/lib/lnmt/vlan.db "DELETE FROM vlan_stats WHERE timestamp < datetime('now', '-30 days');"

# Monitor resource usage
top -p $(pgrep -f vlan_controller)
```

## Troubleshooting

### Common Issues

#### VLAN Interface Creation Fails

```bash
# Check if VLAN module is loaded
lsmod | grep 8021q

# Load VLAN module if needed
sudo modprobe 8021q

# Add to /etc/modules for persistence
echo "8021q" | sudo tee -a /etc/modules
```

#### Shorewall Integration Issues

```bash
# Check Shorewall configuration
sudo shorewall check

# Test Shorewall rules
sudo shorewall status

# Restart Shorewall
sudo systemctl restart shorewall
```

#### Database Corruption

```bash
# Check database integrity
sqlite3 /var/lib/lnmt/vlan.db "PRAGMA integrity_check;"

# Repair database if needed
sqlite3 /var/lib/lnmt/vlan.db ".recover" | sqlite3 /var/lib/lnmt/vlan_recovered.db
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Temporarily enable debug mode
sudo systemctl stop lnmt-vlan-controller
sudo python3 /opt/lnmt/services/vlan_controller.py --debug

# Or set in configuration
echo "logging.level: DEBUG" >> /etc/lnmt/vlan_controller.yaml
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python3 /opt/lnmt/examples/vlan_examples.py

# Run specific test categories
python3 -c "
from vlan_examples import *
test_basic_vlan_operations()
test_security_features()
"
```

## API Reference

### REST Endpoints

- `GET /api/vlans` - List all VLANs
- `POST /api/vlans` - Create new VLAN
- `GET /api/vlans/{id}` - Get VLAN details
- `PUT /api/vlans/{id}` - Update VLAN
- `DELETE /api/vlans/{id}` - Delete VLAN
- `GET /api/vlans/topology` - Export topology diagram
- `GET /api/vlans/{id}/stats` - Get VLAN statistics

### Python API

```python
# Core classes
VLANController()        # Main controller class
VLANConfig()           # VLAN configuration data
VLANStats()            # Statistics data structure
VLANDatabase()         # Database operations
NetworkInterface()     # Network interface management
ShorewallIntegration() # Firewall integration
VLANMonitor()         # Real-time monitoring
```

## Support

For support and additional documentation:

- Check logs: `/var/log/lnmt/vlan_controller.log`
- Review configuration: `/etc/lnmt/vlan_controller.yaml`
- Test functionality: `/opt/lnmt/examples/vlan_examples.py`
- CLI help: `vlanctl --help`

## License

This module is part of the LNMT system and follows the same licensing terms.