# 🧠 LNMT Device Tracker Module

A comprehensive network device monitoring system that tracks MAC/IP/hostname history, detects MAC randomization, and flags security events.

## 📋 Features

- **Real-time Device Monitoring**: Polls DHCP leases every 30 seconds
- **Historical Tracking**: SQLite database stores complete device history
- **MAC Randomization Detection**: Identifies potentially randomized MAC addresses
- **Vendor Identification**: Recognizes devices by MAC OUI (Organizationally Unique Identifier)
- **Event Logging**: Tracks device changes, new devices, and security events
- **CLI Interface**: Comprehensive command-line tools for device management
- **Web-Ready**: JSON exports and structured data for future web UI integration

## 🚀 Quick Start

### Installation

1. **Automated Installation** (Recommended):
   ```bash
   sudo chmod +x install_device_tracker.sh
   sudo ./install_device_tracker.sh
   ```

2. **Manual Installation**:
   ```bash
   # Create directories
   sudo mkdir -p /opt/lnmt/{services,cli}
   sudo mkdir -p /var/{log,lib}/lnmt
   
   # Copy files
   sudo cp services/device_tracker.py /opt/lnmt/services/
   sudo cp cli/device_tracker_ctl.py /opt/lnmt/cli/
   sudo ln -s /opt/lnmt/cli/device_tracker_ctl.py /usr/local/bin/device_tracker_ctl
   ```

### Starting the Service

```bash
# Start the service
sudo systemctl start lnmt-device-tracker

# Enable on boot
sudo systemctl enable lnmt-device-tracker

# Check status
sudo systemctl status lnmt-device-tracker
```

## 📊 Usage Examples

### CLI Commands

```bash
# List all devices
device_tracker_ctl list

# Show only active devices
device_tracker_ctl list --active

# Show devices with randomized MACs
device_tracker_ctl list --randomized

# Get JSON output
device_tracker_ctl list --json

# Show device history
device_tracker_ctl history aa:bb:cc:dd:ee:ff

# Show recent alerts
device_tracker_ctl alerts

# Show system status
device_tracker_ctl status

# Export devices to JSON
device_tracker_ctl export devices.json

# Analyze a MAC address
device_tracker_ctl analyze aa:bb:cc:dd:ee:ff
```

### Sample Output

```
MAC Address        IP Address      Hostname             Status   Vendor          Last Seen
----------------------------------------------------------------------------------------------------
b8:27:eb:12:34:56  192.168.1.100   raspberry-pi         Active   Raspberry Pi    07-01 14:30
3c:22:fb:ab:cd:ef  192.168.1.101   johns-iphone         Active   Apple           07-01 14:25
02:00:00:12:34:56  192.168.1.102   random-device        Active   -               07-01 14:20 [R]
08:00:27:11:22:33  192.168.1.103   test-vm              Expired  VirtualBox      07-01 13:45

Total: 4 devices
[R] = Randomized MAC detected
```

## 🔍 Security Features

### MAC Randomization Detection

The system automatically detects potentially randomized MAC addresses by:

- Checking the locally administered bit (bit 1 of first octet)
- Analyzing OUI patterns against known vendor databases
- Flagging suspicious MAC patterns

### Event Types

- `new_device`: First time a device is seen
- `ip_change`: Device changed IP address
- `hostname_change`: Device hostname changed
- `mac_change`: Suspicious MAC address change
- `randomized_mac`: Randomized MAC detected

### Alert Examples

```
Recent Events (last 24 hours):
Timestamp            Type            MAC Address        Description
----------------------------------------------------------------------------------
07-01 14:30:15      new_device      02:00:00:12:34:56  🔍New device: random-device (192.168.1.102)
07-01 14:25:30      ip_change       b8:27:eb:12:34:56  ⚠️ IP changed from 192.168.1.99 to 192.168.1.100
07-01 13:45:12      randomized_mac  06:aa:bb:cc:dd:ee  ⚠️ Randomized MAC detected
```

## 🗄️ Database Schema

### Devices Table
- `mac_address` (PRIMARY KEY)
- `ip_address`
- `hostname`
- `first_seen`, `last_seen`
- `lease_expires`
- `vendor`, `device_type`
- `is_randomized_mac`
- `alert_flags` (JSON array)

### Device History Table
- `mac_address`, `ip_address`, `hostname`
- `timestamp`, `lease_expires`

### Device Events Table
- `timestamp`, `event_type`
- `mac_address`, `old_value`, `new_value`
- `description`

## ⚙️ Configuration

### DHCP Lease File Locations

The system automatically searches for DHCP lease files in common locations:

- `/var/lib/misc/dnsmasq.leases` (dnsmasq)
- `/var/lib/dhcp/dhcpd.leases` (ISC DHCP)
- `/var/lib/dhcpcd5/dhcpcd.leases` (dhcpcd)

### Custom Configuration

Edit the service file to customize behavior:

```bash
sudo systemctl edit lnmt-device-tracker
```

Add environment variables:
```ini
[Service]
Environment=LNMT_LEASE_FILE=/custom/path/leases
Environment=LNMT_POLL_INTERVAL=60
Environment=LNMT_DB_PATH=/custom/path/tracker.db
```

## 📝 File Structure

```
/opt/lnmt/
├── services/
│   └── device_tracker.py          # Main service
├── cli/
│   └── device_tracker_ctl.py      # CLI tool
/var/lib/lnmt/
├── device_tracker.db              # SQLite database
└── test_dnsmasq.leases           # Test data
/var/log/lnmt/
└── device_tracker.log            # Service logs
/etc/systemd/system/
└── lnmt-device-tracker.service   # Service definition
```

## 🧪 Testing

### Run Tests

```bash
# Run unit tests
python3 test_device_tracker.py

# Run examples with sample data
python3 test_device_tracker.py --examples
```

### Manual Testing

```bash
# Test with sample data
sudo PYTHONPATH=/opt/lnmt python3 /opt/lnmt/services/device_tracker.py \
  --lease-file /var/lib/lnmt/test_dnsmasq.leases --poll-once

# Check results
device_tracker_ctl list
device_tracker_ctl status
```

## 🔧 Troubleshooting

### Common Issues

1. **No devices detected**:
   ```bash
   # Check DHCP lease file
   ls -la /var/lib/misc/dnsmasq.leases
   
   # Verify permissions
   sudo -u nobody cat /var/lib/misc/dnsmasq.leases
   ```

2. **Service won't start**:
   ```bash
   # Check logs
   sudo journalctl -u lnmt-device-tracker -f
   
   # Verify syntax
   python3 -m py_compile /opt/lnmt/services/device_tracker.py
   ```

3. **Database permissions**:
   ```bash
   # Fix ownership
   sudo chown -R nobody:nogroup /var/lib/lnmt
   sudo chmod -R 755 /var/lib/lnmt
   ```

### Logging

View detailed logs:
```bash
# Service logs
sudo journalctl -u lnmt-device-tracker -f

# Application logs
sudo tail -f /var/log/lnmt/device_tracker.log

# Enable debug logging
sudo systemctl edit lnmt-device-tracker
# Add: Environment=LNMT_LOG_LEVEL=DEBUG
```

## 🔮 Future Enhancements

### Planned Features

- **Passive OS Fingerprinting**: Identify device types by network behavior
- **Web UI Integration**: Real-time dashboard and device management
- **Network Scanning**: Active device discovery beyond DHCP
- **Machine Learning**: Anomaly detection for security events
- **Integration APIs**: REST API for external systems
- **Mobile App**: Device monitoring on-the-go

### Extensibility Points

- **Custom Analyzers**: Plugin system for device identification
- **Alert Handlers**: Custom notification systems
- **Export Formats**: Additional data export options
- **Database Backends**: Support for PostgreSQL, MySQL

## 📚 API Reference

### DeviceDatabase Class

```python
from services.device_tracker import DeviceDatabase

db = DeviceDatabase("/path/to/database.db")

# Get device
device = db.get_device("aa:bb:cc:dd:ee:ff")

# Get all devices
devices = db.get_all_devices()

# Get device history
history = db.get_device_history("aa:bb:cc:dd:ee:ff", days=30)

# Get recent events
events = db.get_recent_events(hours=24)
```

### MACAnalyzer Class

```python
from services.device_tracker import MACAnalyzer

analyzer = MACAnalyzer()

# Check if MAC is randomized
is_random = analyzer.is_randomized_mac("02:00:00:12:34:56")

# Get vendor
vendor = analyzer.get_vendor("b8:27:eb:12:34:56")
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd device-tracker

# Install development dependencies
pip3 install -r requirements-dev.txt

# Run tests
python3 -m pytest tests/

# Run linting
python3 -m flake8 services/ cli/
```

### Code Standards

- Python 3.10+ compatibility
- PEP 8 compliance
- Type hints encouraged
- Comprehensive docstrings
- Unit test coverage >80%

## 📄 License

This project is part of the LNMT (Linux Network Monitoring Tools) suite.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section
2. Review logs for error messages
3. Test with sample data
4. Create an issue with full error details

---

**LNMT Device Tracker** - Network visibility made simple! 🚀