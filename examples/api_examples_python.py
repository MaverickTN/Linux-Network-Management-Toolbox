#!/usr/bin/env python3
"""
LNMT Python API Usage Examples

This file demonstrates various ways to use the LNMT Python API client
for common network management tasks.
"""

import sys
import time
import json
from lnmt_api import LNMTClient, LNMTAPIError, quick_device_scan, export_device_inventory

# Configuration
LNMT_SERVER = "https://api.lnmt.local"
USERNAME = "admin"
PASSWORD = "your_password"

def example_basic_usage():
    """Basic API usage example"""
    print("=== Basic Usage Example ===")
    
    try:
        # Create client and login
        with LNMTClient(LNMT_SERVER) as client:
            client.login(USERNAME, PASSWORD)
            
            # Get system health
            health = client.get_health_status()
            print(f"System Status: {health['status']}")
            print(f"Uptime: {health['uptime']} seconds")
            
            # Get current user info
            user = client.get_current_user()
            print(f"Logged in as: {user['username']} ({user['role']})")
            
    except LNMTAPIError as e:
        print(f"Error: {e}")

def example_device_management():
    """Device management examples"""
    print("\n=== Device Management Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List all devices
        devices_result = client.get_devices()
        print(f"Total devices: {devices_result['total']}")
        
        # List only online devices
        online_devices = client.get_devices(status='online')
        print(f"Online devices: {len(online_devices['devices'])}")
        
        # Get devices by type
        servers = client.get_devices(device_type='server')
        print(f"Servers: {len(servers['devices'])}")
        
        # Print device summary
        for device in devices_result['devices'][:5]:  # First 5 devices
            status_icon = "🟢" if device['status'] == 'online' else "🔴"
            print(f"  {status_icon} {device['hostname']} ({device['ip_address']}) - {device['device_type']}")
        
        # Create a new device manually
        try:
            new_device = client.create_device(
                ip_address="192.168.1.100",
                hostname="test-device",
                device_type="workstation",
                tags=["test", "example"]
            )
            print(f"Created device: {new_device['id']}")
            
            # Update the device
            updated_device = client.update_device(
                new_device['id'],
                hostname="updated-test-device",
                device_type="server"
            )
            print(f"Updated device hostname to: {updated_device['hostname']}")
            
            # Delete the test device
            client.delete_device(new_device['id'])
            print("Test device deleted")
            
        except LNMTAPIError as e:
            print(f"Backup error: {e}")

def example_scheduler():
    """Scheduler examples"""
    print("\n=== Scheduler Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List scheduled jobs
        jobs_result = client.get_scheduled_jobs()
        print(f"Scheduled jobs: {len(jobs_result['jobs'])}")
        
        for job in jobs_result['jobs']:
            status_icon = "✅" if job['enabled'] else "❌"
            print(f"  {status_icon} {job['name']} ({job['type']}) - {job['schedule']}")
            if job['last_run']:
                print(f"    Last run: {job['last_run']}")
            if job['next_run']:
                print(f"    Next run: {job['next_run']}")
        
        # Create a scheduled backup job
        try:
            backup_job = client.create_scheduled_job(
                name="Daily Backup",
                job_type="backup",
                schedule="0 2 * * *",  # Daily at 2 AM
                description="Automated daily system backup",
                parameters={
                    "include_configs": True,
                    "include_data": True,
                    "compression": True
                }
            )
            print(f"Created scheduled job: {backup_job['name']}")
            
        except LNMTAPIError as e:
            print(f"Scheduler error: {e}")

def example_system_monitoring():
    """System monitoring examples"""
    print("\n=== System Monitoring Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # Get detailed system metrics
        metrics = client.get_system_metrics()
        print("System Metrics:")
        print(f"  CPU Usage: {metrics['cpu_usage']:.1f}%")
        print(f"  Memory Usage: {metrics['memory_usage']:.1f}%")
        print(f"  Disk Usage: {metrics['disk_usage']:.1f}%")
        print(f"  Active Connections: {metrics['active_connections']}")
        print(f"  Devices Online: {metrics['devices_online']}/{metrics['devices_total']}")
        
        # Network I/O
        if 'network_io' in metrics:
            io = metrics['network_io']
            print(f"  Network I/O: {io['bytes_sent']} sent, {io['bytes_received']} received")

def example_error_handling():
    """Error handling examples"""
    print("\n=== Error Handling Examples ===")
    
    try:
        # Try to connect with wrong credentials
        with LNMTClient(LNMT_SERVER) as client:
            client.login("wrong_user", "wrong_pass")
            
    except LNMTAPIError as e:
        print(f"Expected authentication error: {e}")
        print(f"Status code: {e.status_code}")
        if e.response:
            print(f"Error details: {e.response}")
    
    try:
        # Try to access non-existent resource
        with LNMTClient(LNMT_SERVER) as client:
            client.login(USERNAME, PASSWORD)
            client.get_device("non-existent-id")
            
    except LNMTAPIError as e:
        print(f"Expected not found error: {e}")

def example_convenience_functions():
    """Using convenience functions"""
    print("\n=== Convenience Functions Examples ===")
    
    # Quick device scan
    try:
        print("Performing quick device scan...")
        devices = quick_device_scan(LNMT_SERVER, USERNAME, PASSWORD, "192.168.1.0/24")
        print(f"Discovered {len(devices)} devices")
        
        for device in devices[:3]:  # Show first 3
            print(f"  {device['hostname']} - {device['ip_address']}")
            
    except LNMTAPIError as e:
        print(f"Quick scan error: {e}")
    
    # Export device inventory
    try:
        print("Exporting device inventory...")
        csv_data = export_device_inventory(LNMT_SERVER, USERNAME, PASSWORD, "devices.csv")
        print(f"Exported device inventory to devices.csv ({len(csv_data)} characters)")
        
    except LNMTAPIError as e:
        print(f"Export error: {e}")

def example_bulk_operations():
    """Bulk operations example"""
    print("\n=== Bulk Operations Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # Bulk device updates - add tags to all servers
        try:
            devices_result = client.get_devices(device_type='server')
            server_count = 0
            
            for device in devices_result['devices']:
                # Add 'managed' tag to all servers
                existing_tags = device.get('tags', [])
                if 'managed' not in existing_tags:
                    new_tags = existing_tags + ['managed']
                    client.update_device(device['id'], tags=new_tags)
                    server_count += 1
            
            print(f"Added 'managed' tag to {server_count} servers")
            
        except LNMTAPIError as e:
            print(f"Bulk update error: {e}")
        
        # Bulk VLAN assignment based on IP ranges
        try:
            devices_result = client.get_devices()
            vlan_assignments = 0
            
            for device in devices_result['devices']:
                ip = device['ip_address']
                
                # Assign VLAN based on IP range
                if ip.startswith('192.168.10.'):
                    target_vlan = 10
                elif ip.startswith('192.168.20.'):
                    target_vlan = 20
                else:
                    continue
                
                # Only update if VLAN is different
                if device.get('vlan_id') != target_vlan:
                    client.update_device(device['id'], vlan_id=target_vlan)
                    vlan_assignments += 1
            
            print(f"Updated VLAN assignments for {vlan_assignments} devices")
            
        except LNMTAPIError as e:
            print(f"Bulk VLAN assignment error: {e}")

def example_monitoring_dashboard():
    """Create a simple monitoring dashboard"""
    print("\n=== Monitoring Dashboard Example ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # Collect dashboard data
        health = client.get_health_status()
        metrics = client.get_system_metrics()
        devices_result = client.get_devices()
        vlans_result = client.get_vlans()
        
        # Calculate statistics
        total_devices = devices_result['total']
        online_devices = len([d for d in devices_result['devices'] if d['status'] == 'online'])
        offline_devices = total_devices - online_devices
        
        device_types = {}
        for device in devices_result['devices']:
            dtype = device.get('device_type', 'unknown')
            device_types[dtype] = device_types.get(dtype, 0) + 1
        
        # Display dashboard
        print("┌─────────────────────────────────────────────────────────────┐")
        print("│                    LNMT Dashboard                           │")
        print("├─────────────────────────────────────────────────────────────┤")
        print(f"│ System Status: {health['status']:>42} │")
        print(f"│ Uptime: {health['uptime']:>48} seconds │")
        print("├─────────────────────────────────────────────────────────────┤")
        print(f"│ CPU Usage: {metrics['cpu_usage']:>46.1f}% │")
        print(f"│ Memory Usage: {metrics['memory_usage']:>43.1f}% │")
        print(f"│ Disk Usage: {metrics['disk_usage']:>45.1f}% │")
        print("├─────────────────────────────────────────────────────────────┤")
        print(f"│ Total Devices: {total_devices:>44} │")
        print(f"│ Online: {online_devices:>49} │")
        print(f"│ Offline: {offline_devices:>48} │")
        print("├─────────────────────────────────────────────────────────────┤")
        print(f"│ VLANs Configured: {len(vlans_result['vlans']):>40} │")
        print("├─────────────────────────────────────────────────────────────┤")
        print("│ Device Types:                                               │")
        for dtype, count in sorted(device_types.items()):
            print(f"│   {dtype}: {count:>48} │")
        print("└─────────────────────────────────────────────────────────────┘")

def main():
    """Run all examples"""
    print("LNMT Python API Examples")
    print("=" * 50)
    
    examples = [
        example_basic_usage,
        example_device_management,
        example_network_scanning,
        example_vlan_management,
        example_dns_management,
        example_reporting,
        example_backup_restore,
        example_scheduler,
        example_system_monitoring,
        example_error_handling,
        example_convenience_functions,
        example_bulk_operations,
        example_monitoring_dashboard
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"Example {example_func.__name__} failed: {e}")
        
        print()  # Add spacing between examples

if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("LNMT Python API Examples")
            print("Usage: python api_examples.py [server_url] [username] [password]")
            print()
            print("Available examples:")
            print("  - Basic API usage")
            print("  - Device management")
            print("  - Network scanning")
            print("  - VLAN management")
            print("  - DNS management")
            print("  - Reporting")
            print("  - Backup/restore")
            print("  - Job scheduling")
            print("  - System monitoring")
            print("  - Error handling")
            print("  - Convenience functions")
            print("  - Bulk operations")
            print("  - Monitoring dashboard")
            sys.exit(0)
        
        # Override defaults with command line arguments
        if len(sys.argv) >= 2:
            LNMT_SERVER = sys.argv[1]
        if len(sys.argv) >= 3:
            USERNAME = sys.argv[2]
        if len(sys.argv) >= 4:
            PASSWORD = sys.argv[3]
    
    # Run examples
    main():
            print(f"Device management error: {e}")

def example_network_scanning():
    """Network scanning example"""
    print("\n=== Network Scanning Example ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # Start a network scan
        scan_result = client.start_network_scan(subnet="192.168.1.0/24")
        scan_id = scan_result['scan_id']
        print(f"Started scan: {scan_id}")
        
        # Wait for scan to complete
        try:
            final_status = client.wait_for_scan(scan_id, timeout=120)
            print(f"Scan completed. Found {final_status['devices_found']} devices")
            
            # Get updated device list
            devices = client.get_devices()
            print(f"Total devices after scan: {devices['total']}")
            
        except LNMTAPIError as e:
            print(f"Scan error: {e}")

def example_vlan_management():
    """VLAN management examples"""
    print("\n=== VLAN Management Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List existing VLANs
        vlans_result = client.get_vlans()
        print(f"Configured VLANs: {len(vlans_result['vlans'])}")
        
        for vlan in vlans_result['vlans']:
            print(f"  VLAN {vlan['id']}: {vlan['name']} ({vlan['device_count']} devices)")
        
        # Create a new VLAN
        try:
            new_vlan = client.create_vlan(
                vlan_id=200,
                name="IoT Network",
                description="Network for IoT devices",
                subnet="192.168.200.0/24",
                gateway="192.168.200.1"
            )
            print(f"Created VLAN {new_vlan['id']}: {new_vlan['name']}")
            
            # Update VLAN
            updated_vlan = client.update_vlan(
                200,
                description="Updated IoT device network"
            )
            print(f"Updated VLAN description")
            
            # Delete the test VLAN
            client.delete_vlan(200)
            print("Test VLAN deleted")
            
        except LNMTAPIError as e:
            print(f"VLAN management error: {e}")

def example_dns_management():
    """DNS management examples"""
    print("\n=== DNS Management Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List DNS zones
        zones_result = client.get_dns_zones()
        print(f"DNS zones: {len(zones_result['zones'])}")
        
        for zone in zones_result['zones']:
            print(f"  {zone['name']} ({zone['type']}) - {zone['record_count']} records")
        
        # Create a test zone
        try:
            test_zone = client.create_dns_zone(
                name="test.local",
                zone_type="master"
            )
            print(f"Created DNS zone: test.local")
            
            # Add DNS records
            a_record = client.create_dns_record(
                zone_name="test.local",
                name="www",
                record_type="A",
                value="192.168.1.10"
            )
            print(f"Created A record: www.test.local -> 192.168.1.10")
            
            cname_record = client.create_dns_record(
                zone_name="test.local",
                name="mail",
                record_type="CNAME",
                value="www.test.local"
            )
            print(f"Created CNAME record: mail.test.local -> www.test.local")
            
            # List records in the zone
            records_result = client.get_dns_records("test.local")
            print(f"Records in test.local: {len(records_result['records'])}")
            
        except LNMTAPIError as e:
            print(f"DNS management error: {e}")

def example_reporting():
    """Reporting examples"""
    print("\n=== Reporting Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List available reports
        reports_result = client.get_available_reports()
        print("Available reports:")
        for report in reports_result['reports']:
            print(f"  {report['type']}: {report['name']}")
            print(f"    {report['description']}")
            print(f"    Formats: {', '.join(report['available_formats'])}")
        
        # Generate network summary report
        try:
            network_report = client.generate_report('network_summary', period='24h')
            print(f"\nNetwork Summary (24h):")
            print(f"  Generated at: {network_report['generated_at']}")
            print(f"  Report data: {json.dumps(network_report['data'], indent=2)}")
            
            # Generate CSV report
            csv_report = client.generate_report('device_status', format='csv')
            print(f"\nDevice status CSV report generated ({len(csv_report)} characters)")
            
        except LNMTAPIError as e:
            print(f"Reporting error: {e}")

def example_backup_restore():
    """Backup and restore examples"""
    print("\n=== Backup/Restore Examples ===")
    
    with LNMTClient(LNMT_SERVER) as client:
        client.login(USERNAME, PASSWORD)
        
        # List existing backups
        backups_result = client.get_backups()
        print(f"Available backups: {len(backups_result['backups'])}")
        
        for backup in backups_result['backups'][:3]:  # Show first 3
            print(f"  {backup['filename']} ({backup['size']} bytes) - {backup['created_at']}")
        
        # Create a new backup
        try:
            backup_job = client.create_backup(
                include_configs=True,
                include_data=True,
                compression=True
            )
            print(f"Backup job started: {backup_job['job_id']}")
            
        except LNMTAPIError as e