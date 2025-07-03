#!/usr/bin/env python3
"""
LNMT Device Tracker CLI Tool
Command-line interface for device tracking operations.

Example usage:
    # List all devices
    python3 cli/device_tracker_ctl.py list
    
    # Show device history
    python3 cli/device_tracker_ctl.py history aa:bb:cc:dd:ee:ff
    
    # Show recent alerts/events
    python3 cli/device_tracker_ctl.py alerts
    
    # Show active devices only
    python3 cli/device_tracker_ctl.py list --active
    
    # Show status summary
    python3 cli/device_tracker_ctl.py status
    
    # Export devices to JSON
    python3 cli/device_tracker_ctl.py export devices.json
    
    # Show devices with randomized MACs
    python3 cli/device_tracker_ctl.py list --randomized
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add the parent directory to path to import the service module
sys.path.append(str(Path(__file__).parent.parent))

from services.device_tracker import DeviceDatabase, Device, DeviceEvent, MACAnalyzer

class DeviceTrackerCLI:
    """CLI interface for device tracker"""
    
    def __init__(self):
        self.db = DeviceDatabase()
        self.mac_analyzer = MACAnalyzer()
    
    def list_devices(self, active_only: bool = False, randomized_only: bool = False, 
                    json_output: bool = False):
        """List devices with optional filters"""
        devices = self.db.get_all_devices()
        current_time = datetime.now()
        
        # Apply filters
        if active_only:
            devices = [d for d in devices if d.lease_expires and d.lease_expires > current_time]
        
        if randomized_only:
            devices = [d for d in devices if d.is_randomized_mac]
        
        if json_output:
            # Output as JSON
            device_data = []
            for device in devices:
                data = {
                    'mac_address': device.mac_address,
                    'ip_address': device.ip_address,
                    'hostname': device.hostname,
                    'first_seen': device.first_seen.isoformat(),
                    'last_seen': device.last_seen.isoformat(),
                    'lease_expires': device.lease_expires.isoformat() if device.lease_expires else None,
                    'vendor': device.vendor,
                    'device_type': device.device_type,
                    'is_randomized_mac': device.is_randomized_mac,
                    'alert_flags': device.alert_flags,
                    'is_active': device.lease_expires and device.lease_expires > current_time if device.lease_expires else False
                }
                device_data.append(data)
            
            print(json.dumps(device_data, indent=2))
            return
        
        # Human-readable output
        if not devices:
            print("No devices found.")
            return
        
        print(f"{'MAC Address':<18} {'IP Address':<15} {'Hostname':<20} {'Status':<8} {'Vendor':<15} {'Last Seen'}")
        print("-" * 100)
        
        for device in devices:
            # Determine status
            status = "Unknown"
            if device.lease_expires:
                if device.lease_expires > current_time:
                    status = "Active"
                else:
                    status = "Expired"
            
            # Truncate long hostnames
            hostname = device.hostname[:19] if device.hostname else "-"
            vendor = device.vendor[:14] if device.vendor else "-"
            
            # Format last seen
            last_seen = device.last_seen.strftime("%m-%d %H:%M")
            
            # Add flags for special cases
            flags = ""
            if device.is_randomized_mac:
                flags += "[R]"
            if device.alert_flags:
                flags += "[!]"
            
            print(f"{device.mac_address:<18} {device.ip_address:<15} {hostname:<20} {status:<8} {vendor:<15} {last_seen} {flags}")
        
        print(f"\nTotal: {len(devices)} devices")
        if active_only:
            print("(Showing active devices only)")
        if randomized_only:
            print("(Showing devices with randomized MACs only)")
    
    def show_device_history(self, mac_address: str, days: int = 30):
        """Show history for a specific device"""
        device = self.db.get_device(mac_address)
        if not device:
            print(f"Device not found: {mac_address}")
            return
        
        print(f"Device History: {mac_address}")
        print(f"Current Status:")
        print(f"  Hostname: {device.hostname}")
        print(f"  IP: {device.ip_address}")
        print(f"  Vendor: {device.vendor or 'Unknown'}")
        print(f"  First Seen: {device.first_seen}")
        print(f"  Last Seen: {device.last_seen}")
        if device.is_randomized_mac:
            print(f"  ⚠️  Randomized MAC detected")
        if device.alert_flags:
            print(f"  Alert Flags: {', '.join(device.alert_flags)}")
        print()
        
        # Get history
        history = self.db.get_device_history(mac_address, days)
        if not history:
            print("No history entries found.")
            return
        
        print(f"History (last {days} days):")
        print(f"{'Timestamp':<20} {'IP Address':<15} {'Hostname':<25} {'Lease Expires'}")
        print("-" * 85)
        
        for entry in history:
            timestamp = entry['timestamp'].strftime("%m-%d %H:%M:%S")
            hostname = entry['hostname'][:24] if entry['hostname'] else "-"
            expires = ""
            if entry['lease_expires']:
                expires = entry['lease_expires'].strftime("%m-%d %H:%M")
            
            print(f"{timestamp:<20} {entry['ip_address']:<15} {hostname:<25} {expires}")
    
    def show_alerts(self, hours: int = 24):
        """Show recent alerts and events"""
        events = self.db.get_recent_events(hours)
        
        if not events:
            print(f"No events in the last {hours} hours.")
            return
        
        print(f"Recent Events (last {hours} hours):")
        print(f"{'Timestamp':<20} {'Type':<15} {'MAC Address':<18} {'Description'}")
        print("-" * 90)
        
        for event in events:
            timestamp = event.timestamp.strftime("%m-%d %H:%M:%S")
            event_type = event.event_type
            description = event.description[:45] if event.description else ""
            
            # Add severity indicator
            severity = ""
            if event.event_type in ['new_device', 'randomized_mac']:
                severity = "🔍"
            elif event.event_type in ['mac_change', 'ip_change']:
                severity = "⚠️ "
            
            print(f"{timestamp:<20} {event_type:<15} {event.mac_address:<18} {severity}{description}")
    
    def show_status(self):
        """Show system status"""
        devices = self.db.get_all_devices()
        current_time = datetime.now()
        
        # Calculate statistics
        total_devices = len(devices)
        active_devices = len([d for d in devices if d.lease_expires and d.lease_expires > current_time])
        randomized_macs = len([d for d in devices if d.is_randomized_mac])
        
        # Recent activity
        recent_events = self.db.get_recent_events(24)
        new_devices_24h = len([e for e in recent_events if e.event_type == 'new_device'])
        
        # Device breakdown by vendor
        vendor_counts = {}
        for device in devices:
            vendor = device.vendor or 'Unknown'
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        print("LNMT Device Tracker Status")
        print("=" * 30)
        print(f"Total Devices:      {total_devices}")
        print(f"Active Devices:     {active_devices}")
        print(f"Randomized MACs:    {randomized_macs}")
        print(f"New (24h):          {new_devices_24h}")
        print(f"Recent Events (24h): {len(recent_events)}")
        print()
        
        if vendor_counts:
            print("Device Vendors:")
            for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {vendor:<20} {count}")
        
        print()
        print(f"Last Update: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def export_devices(self, filename: str):
        """Export devices to JSON file"""
        devices = self.db.get_all_devices()
        current_time = datetime.now()
        
        export_data = {
            'export_timestamp': current_time.isoformat(),
            'total_devices': len(devices),
            'devices': []
        }
        
        for device in devices:
            device_data = {
                'mac_address': device.mac_address,
                'ip_address': device.ip_address,
                'hostname': device.hostname,
                'first_seen': device.first_seen.isoformat(),
                'last_seen': device.last_seen.isoformat(),
                'lease_expires': device.lease_expires.isoformat() if device.lease_expires else None,
                'vendor': device.vendor,
                'device_type': device.device_type,
                'is_randomized_mac': device.is_randomized_mac,
                'alert_flags': device.alert_flags,
                'is_active': device.lease_expires and device.lease_expires > current_time if device.lease_expires else False
            }
            export_data['devices'].append(device_data)
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"Exported {len(devices)} devices to {filename}")
        except Exception as e:
            print(f"Error exporting to {filename}: {e}")
    
    def analyze_mac(self, mac_address: str):
        """Analyze a MAC address"""
        print(f"MAC Address Analysis: {mac_address}")
        print("-" * 40)
        
        # Basic validation
        if not mac_address or len(mac_address.replace(':', '').replace('-', '')) != 12:
            print("❌ Invalid MAC address format")
            return
        
        # Check if randomized
        is_randomized = self.mac_analyzer.is_randomized_mac(mac_address)
        print(f"Randomized MAC: {'Yes' if is_randomized else 'No'}")
        
        # Get vendor
        vendor = self.mac_analyzer.get_vendor(mac_address)
        print(f"Vendor: {vendor or 'Unknown'}")
        
        # Check if we have this device in database
        device = self.db.get_device(mac_address)
        if device:
            print(f"Known Device: Yes")
            print(f"  Current IP: {device.ip_address}")
            print(f"  Hostname: {device.hostname}")
            print(f"  First Seen: {device.first_seen}")
            print(f"  Last Seen: {device.last_seen}")
            if device.alert_flags:
                print(f"  Alerts: {', '.join(device.alert_flags)}")
        else:
            print(f"Known Device: No")
        
        # MAC address structure analysis
        clean_mac = mac_address.replace(':', '').replace('-', '').lower()
        first_octet = int(clean_mac[0:2], 16)
        
        print(f"\nTechnical Details:")
        print(f"  OUI: {mac_address[:8]}")
        print(f"  Locally Administered: {'Yes' if (first_octet & 0x02) != 0 else 'No'}")
        print(f"  Multicast: {'Yes' if (first_octet & 0x01) != 0 else 'No'}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LNMT Device Tracker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                          # List all devices
  %(prog)s list --active                 # List active devices only
  %(prog)s list --randomized             # List devices with randomized MACs
  %(prog)s list --json                   # Output as JSON
  %(prog)s history aa:bb:cc:dd:ee:ff     # Show device history
  %(prog)s alerts                        # Show recent alerts
  %(prog)s alerts --hours 48             # Show alerts from last 48 hours
  %(prog)s status                        # Show system status
  %(prog)s export devices.json           # Export devices to JSON
  %(prog)s analyze aa:bb:cc:dd:ee:ff     # Analyze a MAC address
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List devices')
    list_parser.add_argument('--active', action='store_true', help='Show active devices only')
    list_parser.add_argument('--randomized', action='store_true', help='Show devices with randomized MACs only')
    list_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show device history')
    history_parser.add_argument('mac_address', help='MAC address to show history for')
    history_parser.add_argument('--days', type=int, default=30, help='Number of days of history (default: 30)')
    
    # Alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Show recent alerts/events')
    alerts_parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export devices to JSON')
    export_parser.add_argument('filename', help='Output filename')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a MAC address')
    analyze_parser.add_argument('mac_address', help='MAC address to analyze')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create CLI instance
    cli = DeviceTrackerCLI()
    
    try:
        # Execute command
        if args.command == 'list':
            cli.list_devices(
                active_only=args.active,
                randomized_only=args.randomized,
                json_output=args.json
            )
        elif args.command == 'history':
            cli.show_device_history(args.mac_address, args.days)
        elif args.command == 'alerts':
            cli.show_alerts(args.hours)
        elif args.command == 'status':
            cli.show_status()
        elif args.command == 'export':
            cli.export_devices(args.filename)
        elif args.command == 'analyze':
            cli.analyze_mac(args.mac_address)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()