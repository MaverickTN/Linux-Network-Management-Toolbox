# 🧠 LNMT Health Monitor

A comprehensive health monitoring system for LNMT (Linux, Nginx, MariaDB, Tailscale) infrastructure with focus on DNS services (dnsmasq, Pi-hole, unbound) and firewall (Shorewall).

## 🎯 Features

- **Service Monitoring**: Real-time status checks for critical services
- **Resource Monitoring**: CPU, memory, disk usage with configurable thresholds  
- **Configuration Validation**: Syntax checking and change detection
- **Multi-channel Alerts**: CLI, log files, and web UI endpoints
- **Safety-first Design**: Actionable alerts with detailed context
- **JSON Output**: Machine-readable format for automation

## 📦 Components

### Core Module: `services/health_monitor.py`
- `HealthMonitor` class with comprehensive monitoring capabilities
- Service status checking with process and functionality validation
- Resource usage monitoring with threshold-based alerting
- Configuration file validation and change detection
- Alert management with multiple severity levels

### CLI Interface: `cli/healthctl.py`
- User-friendly command-line interface
- Human-readable and JSON output modes
- Comprehensive status reporting and service checking
- Alert log management and filtering

### Examples & Tests: `examples_and_tests.py`
- Usage examples for all major features
- Basic test suite for validation
- Integration patterns for automation systems

## 🚀 Quick Start

### Installation

```bash
# Install required dependencies
sudo pip3 install psutil

# Copy files to system locations
sudo mkdir -p /usr/local/lib/lnmt/services
sudo mkdir -p /usr/local/bin
sudo mkdir -p /var/lib/lnmt

# Install core module
sudo cp services/health_monitor.py /usr/local/lib/lnmt/services/

# Install CLI tool
sudo cp cli/healthctl.py /usr/local/bin/
sudo chmod +x /usr/local/bin/healthctl.py

# Create symlink for easier access
sudo ln -sf /usr/local/bin/healthctl.py /usr/local/bin/healthctl
```

### Basic Usage

```bash
# Check overall system health
healthctl --status

# Check specific service
healthctl --check dnsmasq
healthctl --check pihole

# View system resources
healthctl --resources

# Check configuration files
healthctl --configs

# View recent alerts
healthctl --alertlog

# Get JSON output for automation
healthctl --status --json
```

## 📊 Monitored Services

| Service | Process | Config Files | Port | Special Checks |
|---------|---------|--------------|------|----------------|
| **dnsmasq** | `dnsmasq` | `/etc/dnsmasq.conf`, `/etc/dnsmasq.d/` | 53 | Config syntax validation |
| **Pi-hole** | `pihole-FTL` | `/etc/pihole/pihole-FTL.conf` | 4711 | Process monitoring |
| **unbound** | `unbound` | `/etc/unbound/unbound.conf` | 5335 | Config validation with `unbound-checkconf` |
| **Shorewall** | `shorewall` | `/etc/shorewall/` | - | Status command validation |

## ⚡ Resource Thresholds

| Resource | Warning | Critical | Action |
|----------|---------|----------|--------|
| **CPU** | 80% | 95% | High usage alert |
| **Memory** | 85% | 95% | Memory pressure alert |
| **Disk** | 85% | 95% | Disk space alert |

## 🔔 Alert Levels

- **🟢 INFO**: Informational messages (config changes, service restarts)
- **🟡 WARNING**: Elevated resource usage, minor issues
- **🟠 ERROR**: Service failures, configuration errors
- **🔴 CRITICAL**: System-threatening issues, service outages

## 📋 CLI Commands Reference

### Status Commands
```bash
healthctl --status              # Overall system health
healthctl --check <service>     # Individual service status
healthctl --resources           # Resource usage details
healthctl --configs             # Configuration validation
```

### Alert Management
```bash
healthctl --alertlog                    # Recent alerts (24 hours)
healthctl --alertlog --hours 6         # Alerts from last 6 hours
healthctl --alertlog --level critical  # Critical alerts only
healthctl --clear-alerts --hours 48     # Clear old alerts
```

### Output Formats
```bash
healthctl --status --json       # JSON output
healthctl --check dnsmasq -v    # Verbose output
```

## 🔧 Integration Examples

### Cron Jobs
```bash
# Hourly health check with JSON logging
0 * * * * /usr/local/bin/healthctl --status --json > /var/log/lnmt-status.json

# Check for critical alerts every 15 minutes
*/15 * * * * /usr/local/bin/healthctl --alertlog --hours 1 --level critical
```

### Systemd Service
```ini
[Unit]
Description=LNMT Health Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/healthctl --status
User=root
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```

### Monitoring Integration
```bash
# Prometheus/Grafana metrics collection
healthctl --status --json | jq '.resources.cpu_percent'

# Nagios/Icinga check script
#!/bin/bash
STATUS=$(healthctl --status --json | jq -r '.overall_health')
case $STATUS in
    "healthy") exit 0 ;;
    "warning") exit 1 ;;
    *) exit 2 ;;
esac
```

## 🐍 Python API Usage

### Basic Health Check
```python
from services.health_monitor import HealthMonitor

monitor = HealthMonitor()

# Get overall status
status = monitor.get_system_status()
print(f"Health: {status['overall_health']}")

# Check individual service
service_info = monitor.check_service("dnsmasq")
if service_info.status == ServiceStatus.RUNNING:
    print(f"dnsmasq is running (PID: {service_info.pid})")
```

### Resource Monitoring
```python
# Monitor resources with custom thresholds
resources = monitor.get_system_resources()

if resources.cpu_percent > 90:
    print("High CPU usage detected!")
    
if resources.memory_percent > 85:
    print("Memory usage is elevated")
```

### Alert Management
```python
# Get recent critical alerts
critical_alerts = monitor.get_recent_alerts(
    hours=6, 
    level=AlertLevel.CRITICAL
)

for alert in critical_alerts:
    print(f"CRITICAL: {alert['service']} - {alert['message']}")
```

## 🏗️ Configuration

### Log Files
- Main log: `/var/log/lnmt-health.log`
- Config hashes: `/var/lib/lnmt/config_hashes.json`
- Web alerts: `/tmp/lnmt_web_alerts.json` (stub)

### Customizing Thresholds
```python
# Modify thresholds in health_monitor.py
THRESHOLDS = {
    'cpu_warning': 75.0,     # Lower CPU warning threshold
    'cpu_critical': 90.0,    # Lower CPU critical threshold
    'memory_warning': 80.0,  # Lower memory warning
    'memory_critical': 90.0, # Lower memory critical
    'disk_warning': 80.0,    # Lower disk warning
    'disk_critical': 90.0    # Lower disk critical
}
```

### Adding Custom Services
```python
# Add to CRITICAL_SERVICES in health_monitor.py
CRITICAL_SERVICES = {
    'nginx': {
        'process_name': 'nginx',
        'config_files': ['/etc/nginx/nginx.conf'],
        'port': 80
    },
    # ... existing services
}
```

## 🧪 Testing

### Run Tests
```bash
# Run the test suite
python3 examples_and_tests.py --test

# Run examples
python3 examples_and_tests.py
```

### Manual Testing
```bash
# Test CLI functionality
healthctl --status
healthctl --check dnsmasq
healthctl --resources --json

# Test with invalid service
healthctl --check nonexistent_service  # Should show error
```

## 🔒 Security Considerations

- **Root Access**: Many system checks require root privileges
- **File Permissions**: Config files should have appropriate read permissions
- **Log Rotation**: Set up logrotate for `/var/log/lnmt-health.log`
- **Web Alerts**: Implement authentication for web UI endpoints in production

## 🚨 Troubleshooting

### Common Issues

**Permission Denied**
```bash
# Ensure running as root for system access
sudo healthctl --status
```

**Import Errors**
```bash
# Check Python path and module locations
export PYTHONPATH="/usr/local/lib/lnmt:$PYTHONPATH"
```

**Service Not Found**
```bash
# Check if service is in monitored list
healthctl --check dnsmasq  # Valid
healthctl --check apache   # Invalid - not monitored
```

**High Resource Usage Alerts**
```bash
# Check actual usage
healthctl --resources

# Review recent alerts
healthctl --alertlog --level warning
```

### Debug Mode
```python
# Enable debug logging in health_monitor.py
logging.basicConfig(level=logging.DEBUG)
```

## 🛣️ Roadmap

- [ ] **Web Dashboard**: Real-time web interface
- [ ] **Email Notifications**: SMTP alert delivery
- [ ] **Webhook Integration**: Slack/Teams notifications  
- [ ] **Historical Data**: Trend analysis and reporting
- [ ] **Service Dependencies**: Dependency mapping and cascade alerts
- [ ] **Performance Metrics**: Response time monitoring
- [ ] **Auto-remediation**: Basic self-healing capabilities

## 📝 License

This module is part of the LNMT system and follows the same licensing terms.

## 🤝 Contributing

1. Test thoroughly on your LNMT system
2. Follow the existing code style and patterns
3. Add examples for new features
4. Update documentation for any changes
5. Ensure safety-first approach for all monitoring

---

**Safety Note**: This monitoring system is designed with a safety-first approach. All alerts include actionable information and context to help administrators make informed decisions. Always verify system state before taking corrective actions.