#!/bin/bash

# LNMT Demo Environment Setup Script
# This script imports demo data and configures LNMT for demonstration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DEMO_DIR="/opt/lnmt/demo"
CONFIG_DIR="/opt/lnmt/config"
DATA_DIR="/opt/lnmt/data"
LOG_FILE="/var/log/lnmt/demo_setup.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    LNMT Demo Setup                            ║"
    echo "║          Network Management Toolkit Demonstration            ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${CYAN}━━━ $1 ━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check if LNMT is installed
    if ! command -v lnmt &> /dev/null; then
        print_error "LNMT CLI not found. Please install LNMT first."
        exit 1
    fi
    print_success "LNMT CLI found"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Required for demo data generation."
        exit 1
    fi
    print_success "Python 3 found"
    
    # Check if demo data exists
    if [[ ! -f "$DEMO_DIR/lnmt_demo_data.json" ]]; then
        print_warning "Demo data not found. Generating now..."
        python3 - << 'EOF'
import json
import subprocess
import random

with open('/opt/lnmt/demo/lnmt_demo_data.json', 'r') as f:
    data = json.load(f)

alerts = data['alerts'][:10]  # Import first 10 alerts for demo
imported = 0

for alert in alerts:
    try:
        cmd = [
            'lnmt', 'alert', 'create',
            '--type', alert['type'],
            '--severity', alert['severity'],
            '--title', alert['title'],
            '--description', alert['description'],
            '--device', alert['device_id'],
            '--source-ip', alert['source_ip']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            imported += 1
            print(f"✅ Created alert: {alert['title']}")
        else:
            print(f"❌ Failed to create alert: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Error creating alert: {e}")

print(f"\n📊 Alert Generation Summary: {imported} alerts created")
EOF
    
    print_success "Sample alerts generated"
    log "Sample alerts created"
}

setup_scheduler() {
    print_section "Setting Up Scheduler"
    
    echo "⏰ Configuring scheduled tasks..."
    
    # Create sample scheduled jobs
    lnmt schedule job create \
        --name "Daily Device Scan" \
        --command "lnmt device scan --all" \
        --schedule "0 6 * * *" \
        --description "Scan all devices daily at 6 AM" || true
    
    lnmt schedule job create \
        --name "Weekly Report Generation" \
        --command "lnmt report generate --type weekly --email admin@lnmt.demo" \
        --schedule "0 9 * * 1" \
        --description "Generate weekly reports every Monday at 9 AM" || true
    
    lnmt schedule job create \
        --name "Backup Configuration" \
        --command "lnmt backup create --config-only" \
        --schedule "0 2 * * *" \
        --description "Daily configuration backup at 2 AM" || true
    
    print_success "Scheduler configured"
    log "Scheduled tasks configured"
}

setup_web_dashboard() {
    print_section "Setting Up Web Dashboard"
    
    echo "🌐 Configuring web dashboard..."
    
    # Set demo theme
    lnmt web theme set --theme "lnmt-modern" || true
    
    # Configure dashboard widgets
    lnmt web dashboard add-widget --type "device-status" --position "top-left" || true
    lnmt web dashboard add-widget --type "alert-summary" --position "top-right" || true
    lnmt web dashboard add-widget --type "network-usage" --position "bottom-left" || true
    lnmt web dashboard add-widget --type "system-health" --position "bottom-right" || true
    
    # Enable demo mode
    lnmt web config set --demo-mode true || true
    
    print_success "Web dashboard configured"
    log "Web dashboard setup completed"
}

create_demo_scenarios() {
    print_section "Creating Demo Scenarios"
    
    echo "📚 Setting up guided demo scenarios..."
    
    # Create scenario scripts directory
    mkdir -p "$DEMO_DIR/scenarios"
    
    # Scenario 1: New Device Onboarding
    cat > "$DEMO_DIR/scenarios/01_device_onboarding.sh" << 'SCENARIO1'
#!/bin/bash
# Demo Scenario 1: New Device Onboarding

echo "🚀 Demo Scenario 1: New Device Onboarding"
echo "This scenario walks through discovering and adding a new device to LNMT"
echo ""

echo "Step 1: Discovering new devices on the network..."
lnmt device discover --network 192.168.1.0/24

echo -e "\nStep 2: Adding a new device manually..."
lnmt device add \
    --hostname "new-device-001" \
    --ip "192.168.1.250" \
    --mac "aa:bb:cc:dd:ee:ff" \
    --type "Workstation" \
    --manufacturer "Dell" \
    --model "OptiPlex 7090" \
    --department "IT" \
    --location "Floor 2, Room 201"

echo -e "\nStep 3: Configuring monitoring for the new device..."
lnmt health monitor enable --device new-device-001

echo -e "\nStep 4: Assigning the device to appropriate VLAN..."
lnmt vlan assign --device new-device-001 --vlan 100

echo "✅ Device onboarding completed!"
SCENARIO1

    # Scenario 2: Security Alert Response
    cat > "$DEMO_DIR/scenarios/02_security_response.sh" << 'SCENARIO2'
#!/bin/bash
# Demo Scenario 2: Security Alert Response

echo "🔒 Demo Scenario 2: Security Alert Response"
echo "This scenario demonstrates responding to a security alert"
echo ""

echo "Step 1: Viewing active security alerts..."
lnmt alert list --severity critical --type security

echo -e "\nStep 2: Investigating a specific alert..."
ALERT_ID=$(lnmt alert list --format json | jq -r '.[0].alert_id' 2>/dev/null || echo "alert_0001")
lnmt alert details --id "$ALERT_ID"

echo -e "\nStep 3: Acknowledging the alert..."
lnmt alert acknowledge --id "$ALERT_ID" --user admin.demo

echo -e "\nStep 4: Implementing security policy..."
lnmt policy apply --name "Block Suspicious Traffic" --device-group all

echo -e "\nStep 5: Resolving the alert..."
lnmt alert resolve --id "$ALERT_ID" --resolution "Applied firewall rule to block suspicious traffic"

echo "✅ Security response completed!"
SCENARIO2

    # Scenario 3: Backup and Restore
    cat > "$DEMO_DIR/scenarios/03_backup_restore.sh" << 'SCENARIO3'
#!/bin/bash
# Demo Scenario 3: Backup and Restore Operations

echo "💾 Demo Scenario 3: Backup and Restore Operations"
echo "This scenario demonstrates backup and restore capabilities"
echo ""

echo "Step 1: Creating a full system backup..."
lnmt backup create --type full --description "Demo backup $(date)"

echo -e "\nStep 2: Listing available backups..."
lnmt backup list

echo -e "\nStep 3: Creating a configuration-only backup..."
lnmt backup create --type config --description "Configuration backup"

echo -e "\nStep 4: Validating backup integrity..."
BACKUP_ID=$(lnmt backup list --format json | jq -r '.[0].backup_id' 2>/dev/null || echo "backup_001")
lnmt backup verify --id "$BACKUP_ID"

echo -e "\nStep 5: Simulating a restore operation (dry-run)..."
lnmt backup restore --id "$BACKUP_ID" --dry-run

echo "✅ Backup and restore demo completed!"
SCENARIO3

    # Make scenarios executable
    chmod +x "$DEMO_DIR/scenarios/"*.sh
    
    print_success "Demo scenarios created"
    log "Demo scenarios setup completed"
}

generate_documentation() {
    print_section "Generating Demo Documentation"
    
    echo "📖 Creating demo documentation..."
    
    # Create demo guide
    cat > "$DEMO_DIR/DEMO_GUIDE.md" << 'DEMOGUIDE'
# LNMT Demo Environment Guide

Welcome to the LNMT (Linux Network Management Toolkit) demonstration environment!

## 🎯 What's Included

This demo environment includes:

- **25 Network Devices** - Routers, switches, servers, workstations, and IoT devices
- **8 VLANs** - Segmented networks for different departments and purposes  
- **30 User Accounts** - Various roles from admin to viewer
- **50+ Alerts** - Sample security and operational alerts
- **15 Policies** - Security and network management policies
- **100 Sessions** - Historical user session data

## 🚀 Quick Start

### Web Interface
1. Open your browser to `http://localhost:8080`
2. Login with demo credentials:
   - **Admin**: `admin.demo` / `DemoAdmin123!`
   - **Operator**: `operator.demo` / `DemoOp123!`
   - **Viewer**: `viewer.demo` / `DemoView123!`

### Command Line Interface
```bash
# View device status
lnmt device list

# Check system health
lnmt health status

# View active alerts
lnmt alert list --active

# Generate reports
lnmt report generate --type summary
```

## 📚 Demo Scenarios

Run these guided scenarios to explore LNMT capabilities:

```bash
# Scenario 1: Device Onboarding
cd /opt/lnmt/demo/scenarios
./01_device_onboarding.sh

# Scenario 2: Security Response
./02_security_response.sh

# Scenario 3: Backup & Restore
./03_backup_restore.sh
```

## 🎛️ Dashboard Features

### Device Management
- Real-time device status monitoring
- Network topology visualization
- Performance metrics and alerts
- Configuration management

### Security Operations
- Alert dashboard and incident response
- Policy management and enforcement
- User access control and audit logs
- Compliance reporting

### Network Operations
- VLAN management and segmentation
- DNS and DHCP configuration
- Traffic analysis and QoS
- Automated scheduling and tasks

## 🔧 Customization

### Adding Your Own Data
```bash
# Import custom device list
lnmt device import --file custom_devices.csv

# Create custom policies
lnmt policy create --from-template security_baseline

# Configure custom alerts
lnmt alert rule create --condition "cpu > 90" --action email
```

### Themes and UI
```bash
# Switch dashboard themes
lnmt web theme set --theme dark-modern

# Configure dashboard widgets
lnmt web dashboard configure
```

## 📊 Sample Data Overview

| Component | Count | Description |
|-----------|-------|-------------|
| Devices | 25 | Network infrastructure and endpoints |
| VLANs | 8 | Segmented networks (Management, Servers, etc.) |
| Users | 30 | Admin, operator, and viewer accounts |
| Alerts | 50+ | Security and operational notifications |
| Policies | 15 | Security and network management rules |
| Sessions | 100 | Historical user access data |

## 🎓 Learning Path

1. **Start with the Web Dashboard** - Get familiar with the UI
2. **Explore Device Management** - View and manage network devices  
3. **Review Security Alerts** - Learn alert handling workflows
4. **Try CLI Commands** - Master command-line operations
5. **Run Demo Scenarios** - Practice common admin tasks
6. **Customize Settings** - Adapt LNMT to your environment

## 🆘 Need Help?

- **Documentation**: `/opt/lnmt/docs/`
- **API Reference**: `lnmt help` or `lnmt <command> --help`
- **Troubleshooting**: Check `/var/log/lnmt/` for logs
- **Support**: Visit the LNMT project repository

## 🔄 Reset Demo Environment

To reset the demo data:
```bash
lnmt demo reset --confirm
/opt/lnmt/demo/setup_demo.sh
```

---

**Note**: This is a demonstration environment with sample data. Do not use demo credentials or configurations in production!
DEMOGUIDE

    print_success "Demo documentation generated"
    log "Demo documentation created"
}

display_summary() {
    print_section "Demo Setup Complete!"
    
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                     🎉 LNMT Demo Ready! 🎉                      ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║                                                                  ║"
    echo "║  Web Interface: http://localhost:8080                           ║"
    echo "║                                                                  ║"
    echo "║  Demo Credentials:                                               ║"
    echo "║  • Admin:    admin.demo    / DemoAdmin123!                       ║"
    echo "║  • Operator: operator.demo / DemoOp123!                          ║"
    echo "║  • Viewer:   viewer.demo   / DemoView123!                        ║"
    echo "║                                                                  ║"
    echo "║  Quick Commands:                                                 ║"
    echo "║  • lnmt device list                                              ║"
    echo "║  • lnmt alert list --active                                      ║"
    echo "║  • lnmt health status                                            ║"
    echo "║                                                                  ║"
    echo "║  Demo Scenarios:                                                 ║"
    echo "║  • /opt/lnmt/demo/scenarios/01_device_onboarding.sh              ║"
    echo "║  • /opt/lnmt/demo/scenarios/02_security_response.sh              ║"
    echo "║  • /opt/lnmt/demo/scenarios/03_backup_restore.sh                 ║"
    echo "║                                                                  ║"
    echo "║  Documentation: /opt/lnmt/demo/DEMO_GUIDE.md                     ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "\n${CYAN}📊 Demo Environment Summary:${NC}"
    echo "   📱 25 Network Devices imported"
    echo "   🌐 8 VLANs configured"
    echo "   👥 3 Demo users created (+ 30 sample users)"
    echo "   🚨 10 Sample alerts generated"
    echo "   📋 15 Policies imported"
    echo "   ⏰ 3 Scheduled tasks configured"
    echo "   📚 3 Demo scenarios ready"
    
    log "Demo setup completed successfully"
}

cleanup_on_error() {
    print_error "Demo setup failed. Check $LOG_FILE for details."
    exit 1
}

# Main execution
main() {
    trap cleanup_on_error ERR
    
    print_header
    
    log "Starting LNMT demo setup"
    
    check_prerequisites
    setup_demo_environment
    import_demo_devices
    import_demo_vlans
    import_demo_policies
    setup_monitoring
    generate_sample_alerts
    setup_scheduler
    setup_web_dashboard
    create_demo_scenarios
    generate_documentation
    
    display_summary
    
    log "LNMT demo setup completed successfully"
}

# Run main function
main "$@""$DEMO_DIR/generate_demo_data.py"
    fi
    print_success "Demo data available"
    
    log "Prerequisites check completed"
}

setup_demo_environment() {
    print_section "Setting Up Demo Environment"
    
    # Create demo user accounts
    echo -e "${PURPLE}Creating demo user accounts...${NC}"
    
    # Admin user
    lnmt user create \
        --username "admin.demo" \
        --email "admin@lnmt.demo" \
        --role "admin" \
        --password "DemoAdmin123!" \
        --first-name "Demo" \
        --last-name "Administrator" \
        --department "IT" || true
    
    # Operator user
    lnmt user create \
        --username "operator.demo" \
        --email "operator@lnmt.demo" \
        --role "operator" \
        --password "DemoOp123!" \
        --first-name "Demo" \
        --last-name "Operator" \
        --department "IT" || true
    
    # Viewer user
    lnmt user create \
        --username "viewer.demo" \
        --email "viewer@lnmt.demo" \
        --role "viewer" \
        --password "DemoView123!" \
        --first-name "Demo" \
        --last-name "Viewer" \
        --department "Support" || true
    
    print_success "Demo users created"
    log "Demo user accounts created"
}

import_demo_devices() {
    print_section "Importing Demo Devices"
    
    echo "📱 Importing 25 network devices..."
    
    # Use device tracker CLI to import devices
    if [[ -f "$DEMO_DIR/demo_devices.csv" ]]; then
        python3 - << 'EOF'
import json
import subprocess
import sys

# Load demo data
with open('/opt/lnmt/demo/lnmt_demo_data.json', 'r') as f:
    data = json.load(f)

devices = data['devices']
imported = 0
failed = 0

for device in devices:
    try:
        cmd = [
            'lnmt', 'device', 'add',
            '--hostname', device['hostname'],
            '--ip', device['ip_address'],
            '--mac', device['mac_address'],
            '--type', device['device_type'],
            '--manufacturer', device['manufacturer'],
            '--model', device['model'],
            '--department', device['department'],
            '--location', device['location']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            imported += 1
            print(f"✅ Imported {device['hostname']}")
        else:
            failed += 1
            print(f"❌ Failed to import {device['hostname']}: {result.stderr}")
    
    except Exception as e:
        failed += 1
        print(f"❌ Error importing {device['hostname']}: {e}")

print(f"\n📊 Import Summary: {imported} successful, {failed} failed")
EOF
    
    else
        print_error "Demo devices file not found"
        return 1
    fi
    
    print_success "Device import completed"
    log "Demo devices imported"
}

import_demo_vlans() {
    print_section "Importing Demo VLANs"
    
    echo "🌐 Configuring 8 VLANs..."
    
    python3 - << 'EOF'
import json
import subprocess

with open('/opt/lnmt/demo/lnmt_demo_data.json', 'r') as f:
    data = json.load(f)

vlans = data['vlans']
imported = 0

for vlan in vlans:
    try:
        cmd = [
            'lnmt', 'vlan', 'create',
            '--id', str(vlan['vlan_id']),
            '--name', vlan['name'],
            '--network', vlan['network'],
            '--description', vlan['description']
        ]
        
        if vlan['dhcp_enabled']:
            cmd.extend(['--dhcp-start', vlan['dhcp_range_start']])
            cmd.extend(['--dhcp-end', vlan['dhcp_range_end']])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            imported += 1
            print(f"✅ Created VLAN {vlan['vlan_id']} ({vlan['name']})")
        else:
            print(f"❌ Failed to create VLAN {vlan['name']}: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Error creating VLAN {vlan['name']}: {e}")

print(f"\n📊 VLAN Import Summary: {imported} VLANs created")
EOF
    
    print_success "VLAN import completed"
    log "Demo VLANs imported"
}

import_demo_policies() {
    print_section "Importing Demo Policies"
    
    echo "📋 Creating security and network policies..."
    
    python3 - << 'EOF'
import json
import subprocess

with open('/opt/lnmt/demo/lnmt_demo_data.json', 'r') as f:
    data = json.load(f)

policies = data['policies']
imported = 0

for policy in policies:
    try:
        # Create policy file
        policy_file = f"/tmp/policy_{policy['policy_id']}.json"
        with open(policy_file, 'w') as f:
            json.dump(policy, f, indent=2)
        
        cmd = [
            'lnmt', 'policy', 'import',
            '--file', policy_file,
            '--name', policy['name'],
            '--type', policy['type']
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            imported += 1
            print(f"✅ Imported policy: {policy['name']}")
        else:
            print(f"❌ Failed to import policy {policy['name']}: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Error importing policy {policy['name']}: {e}")

print(f"\n📊 Policy Import Summary: {imported} policies imported")
EOF
    
    print_success "Policy import completed"
    log "Demo policies imported"
}

setup_monitoring() {
    print_section "Setting Up Monitoring"
    
    echo "📊 Configuring health monitoring..."
    
    # Enable health monitoring for demo devices
    lnmt health monitor enable --all-devices || true
    
    # Configure alert thresholds
    lnmt health threshold set --cpu 85 --memory 90 --disk 95 || true
    
    # Enable backup monitoring
    lnmt backup schedule --daily --time "02:00" --retention 7 || true
    
    print_success "Monitoring configured"
    log "Monitoring setup completed"
}

generate_sample_alerts() {
    print_section "Generating Sample Alerts"
    
    echo "🚨 Creating sample alerts for demonstration..."
    
    python3 