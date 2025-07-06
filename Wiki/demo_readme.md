# 🚀 LNMT Demo Environment

Welcome to the **Linux Network Management Toolkit (LNMT)** demonstration environment! This comprehensive demo showcases LNMT's capabilities for network device management, security monitoring, VLAN configuration, and operational automation.

## 📁 Directory Structure

```
/demo/
├── README.md                           # This file
├── DEMO_GUIDE.md                       # Detailed demo walkthrough  
├── generate_demo_data.py               # Demo data generator script
├── setup_demo.sh                       # Automated demo setup script
├── lnmt_demo_data.json                 # Complete demo dataset
├── reset_demo.sh                       # Reset demo environment
├── requirements.txt                    # Python dependencies
├── data/                               # Generated demo data files
│   ├── demo_devices.csv               # 25 network devices
│   ├── demo_vlans.csv                 # 8 VLAN configurations
│   ├── demo_users.csv                 # 30 user accounts
│   ├── demo_alerts.csv                # 50+ security/operational alerts
│   ├── demo_sessions.csv              # 100 user session records
│   └── demo_policies.csv              # 15 security policies
├── scenarios/                          # Guided demo scenarios
│   ├── 01_device_onboarding.sh        # New device discovery & setup
│   ├── 02_security_response.sh        # Security incident response
│   ├── 03_backup_restore.sh           # Backup and restore operations
│   ├── 04_vlan_management.sh          # VLAN configuration demo
│   └── 05_reporting_analytics.sh      # Reports and analytics
├── screenshots/                        # Dashboard screenshots for docs
├── templates/                          # Configuration templates
│   ├── device_import_template.csv     # Device import template
│   ├── user_import_template.csv       # User import template
│   └── policy_templates/              # Security policy templates
└── scripts/                           # Utility scripts
    ├── health_check.sh                # Demo environment health check
    ├── performance_test.sh            # Load testing script
    └── cleanup.sh                     # Cleanup temporary files
```

## 🎯 What's Included

### Demo Data
- **25 Network Devices**: Routers, switches, servers, workstations, IoT devices, and more
- **8 VLANs**: Management, Servers, Workstations, Guest, IoT, DMZ, VoIP, and Security networks
- **30 User Accounts**: Admin, operator, and viewer roles with realistic permissions
- **50+ Alerts**: Critical, high, medium, and low priority alerts across security and operations
- **100 User Sessions**: Historical login data with various access patterns
- **15 Security Policies**: Firewall rules, access controls, backup policies, and compliance rules

### Pre-configured Features
- **Multi-role Authentication**: Admin, operator, and viewer access levels
- **Real-time Monitoring**: Device health, performance metrics, and network utilization
- **Alert Management**: Automated alert generation and incident response workflows
- **Backup & Restore**: Scheduled backups with integrity verification
- **VLAN Management**: Network segmentation and access control
- **Policy Enforcement**: Security baseline and compliance rule automation
- **Reporting**: Automated report generation and analytics dashboards

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# Clone or download LNMT demo files
cd /opt/lnmt/demo

# Make setup script executable
chmod +x setup_demo.sh

# Run automated setup
sudo ./setup_demo.sh
```

### Option 2: Manual Setup
```bash
# Generate demo data
python3 generate_demo_data.py

# Import devices
lnmt device import --file data/demo_devices.csv

# Configure VLANs
lnmt vlan import --file data/demo_vlans.csv

# Create demo users
lnmt user import --file data/demo_users.csv

# Import security policies
lnmt policy import --file data/demo_policies.csv
```

## 🎮 Demo Scenarios

### 1. Device Onboarding Walkthrough
Demonstrates discovering, adding, and configuring new network devices.

```bash
cd /opt/lnmt/demo/scenarios
./01_device_onboarding.sh
```

**What you'll learn:**
- Network device discovery
- Manual device registration
- Monitoring configuration
- VLAN assignment

### 2. Security Incident Response
Shows how to handle security alerts and implement protective measures.

```bash
./02_security_response.sh
```

**What you'll learn:**
- Alert investigation and triage
- Security policy implementation
- Incident documentation and resolution
- Compliance reporting

### 3. Backup & Restore Operations
Covers backup creation, validation, and restore procedures.

```bash
./03_backup_restore.sh
```

**What you'll learn:**
- Automated backup scheduling
- Backup integrity verification
- Disaster recovery procedures
- Configuration versioning

### 4. VLAN Management
Demonstrates network segmentation and access control.

```bash
./04_vlan_management.sh
```

**What you'll learn:**
- VLAN creation and configuration
- Device assignment to VLANs
- Inter-VLAN routing rules
- Network security policies

### 5. Reporting & Analytics
Shows report generation and performance analytics.

```bash
./05_reporting_analytics.sh
```

**What you'll learn:**
- Automated report generation
- Performance trend analysis
- Compliance reporting
- Custom dashboard creation

## 🌐 Web Interface Access

### Demo Credentials
| Username | Password | Role | Description |
|----------|----------|------|-------------|
| `admin.demo` | `DemoAdmin123!` | Administrator | Full system access |
| `operator.demo` | `DemoOp123!` | Operator | Device management and monitoring |
| `viewer.demo` | `DemoView123!` | Viewer | Read-only dashboard access |

### Dashboard Features
- **Device Status Overview**: Real-time device health and performance
- **Network Topology**: Visual network layout and connections
- **Alert Dashboard**: Active alerts with priority-based sorting
- **Performance Metrics**: CPU, memory, disk, and network utilization
- **Security Center**: Threat detection and policy compliance
- **Backup Status**: Backup job status and restore points

## 🔧 Customization

### Adding Your Own Data
```bash
# Import custom device inventory
lnmt device import --file your_devices.csv --format csv

# Create custom security policies
lnmt policy create --template firewall --name "Custom Firewall Policy"

# Configure custom monitoring thresholds
lnmt health threshold set --cpu 85 --memory 90 --disk 95
```

### Modifying Demo Data
```bash
# Edit the demo data generator
nano generate_demo_data.py

# Regenerate with your changes
python3 generate_demo_data.py

# Re-import updated data
./setup_demo.sh --update-only
```

## 📊 Performance Metrics

The demo environment includes realistic performance data:

- **Response Times**: 50-500ms for typical operations
- **Device Discovery**: 1-5 seconds per device
- **Alert Processing**: Real-time with 1-2 second latency
- **Report Generation**: 5-30 seconds depending on scope
- **Backup Operations**: Varies by data size (demo: 2-5 minutes)

## 🔍 Monitoring & Troubleshooting

### Health Check
```bash
# Check demo environment health
./scripts/health_check.sh

# View system logs
tail -f /var/log/lnmt/lnmt.log

# Check service status
systemctl status lnmt
```

### Common Issues
1. **Port Conflicts**: Default web port is 8080, change in config if needed
2. **Permission Errors**: Ensure demo scripts run with appropriate privileges
3. **Database Issues**: Check PostgreSQL/MySQL connection settings
4. **Memory Usage**: Demo may require 2-4GB RAM for optimal performance

## 📈 Load Testing

Test LNMT performance with simulated load:

```bash
# Run performance test
./scripts/performance_test.sh

# Simulate concurrent users
./scripts/performance_test.sh --users 50 --duration 300
```

## 🔄 Reset Demo Environment

To start fresh:

```bash
# Full reset (removes all demo data)
./reset_demo.sh --full

# Partial reset (keeps users, resets devices/alerts)
./reset_demo.sh --partial

# Reset with confirmation prompt
./reset_demo.sh --interactive
```

## 📚 Learning Resources

### Documentation
- **User Guide**: `/opt/lnmt/docs/lnmt_documentation.md`
- **API Reference**: `/opt/lnmt/docs/lnmt_api_reference.md`
- **Developer Guide**: `/opt/lnmt/docs/lnmt_developer_guide.md`
- **Troubleshooting**: `/opt/lnmt/docs/lnmt_troubleshooting.md`

### Command Line Help
```bash
# General help
lnmt --help

# Command-specific help
lnmt device --help
lnmt alert --help
lnmt backup --help
```

## 🤝 Contributing

Want to improve the demo environment?

1. **Add New Scenarios**: Create scripts in `/scenarios/` directory
2. **Enhance Data Generation**: Modify `generate_demo_data.py`
3. **Improve Documentation**: Update README files and guides
4. **Report Issues**: Use the project's issue tracker

## ⚠️ Important Notes

- **Demo Data Only**: This environment uses simulated data for demonstration
- **Not for Production**: Do not use demo credentials or configurations in production
- **Resource Requirements**: Requires 2-4GB RAM and 5-10GB disk space
- **Network Impact**: Demo device discovery may scan local networks

## 🏷️ Version Information

- **Demo Version**: 2.0.0
- **LNMT Compatibility**: 2.x and above
- **Python Requirements**: 3.8+
- **Last Updated**: 2025-07-02

---

**Ready to explore LNMT? Start with the automated setup and follow the guided scenarios!**

For questions or support, check the main LNMT documentation or visit the project repository.