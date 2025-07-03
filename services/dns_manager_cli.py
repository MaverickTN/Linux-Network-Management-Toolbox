#!/usr/bin/env python3
"""
DNS Manager CLI - Command-line interface for managing DNS reservations

Usage:
    dns_manager_ctl.py --list
    dns_manager_ctl.py --add <hostname> <mac> <ip>
    dns_manager_ctl.py --delete <identifier>
    dns_manager_ctl.py --import <csv_file>
    dns_manager_ctl.py --export <csv_file>
    dns_manager_ctl.py --reload

Examples:
    # List all reservations
    ./dns_manager_ctl.py --list
    
    # Add a device
    ./dns_manager_ctl.py --add laptop aa:bb:cc:dd:ee:ff 192.168.1.100
    
    # Remove by hostname, MAC, or IP
    ./dns_manager_ctl.py --delete laptop
    ./dns_manager_ctl.py --delete aa:bb:cc:dd:ee:ff
    ./dns_manager_ctl.py --delete 192.168.1.100
    
    # Import from CSV
    ./dns_manager_ctl.py --import devices.csv
    
    # Export to CSV
    ./dns_manager_ctl.py --export backup.csv
"""

import sys
import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.dns_manager import DNSManager


class DNSManagerCLI:
    """Command-line interface for DNS Manager."""
    
    def __init__(self):
        """Initialize CLI with DNS Manager instance."""
        self.dns_mgr = DNSManager()
        
    def list_devices(self, format: str = "table") -> None:
        """
        List all current reservations.
        
        Args:
            format: Output format (table, json, csv)
        """
        devices = self.dns_mgr.list_reservations()
        
        if not devices:
            print("No reservations found.")
            return
        
        if format == "json":
            print(json.dumps(devices, indent=2))
        elif format == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=['hostname', 'mac', 'ip'])
            writer.writeheader()
            writer.writerows(devices)
        else:  # table format
            # Calculate column widths
            max_hostname = max(len(d['hostname']) for d in devices)
            max_mac = max(len(d['mac']) for d in devices)
            
            # Print header
            print(f"{'Hostname':<{max_hostname+2}} {'MAC Address':<19} {'IP Address':<15}")
            print("-" * (max_hostname + 2 + 19 + 15 + 2))
            
            # Print devices
            for device in devices:
                print(f"{device['hostname']:<{max_hostname+2}} "
                      f"{device['mac']:<19} "
                      f"{device['ip']:<15}")
    
    def add_device(self, hostname: str, mac: str, ip: str) -> None:
        """
        Add a new device reservation.
        
        Args:
            hostname: Device hostname
            mac: MAC address
            ip: IP address
        """
        try:
            self.dns_mgr.add_device(hostname, mac, ip)
            print(f"Added device: {hostname} ({mac} -> {ip})")
            
            # Optionally reload dnsmasq
            if self.dns_mgr.reload_dnsmasq():
                print("dnsmasq service reloaded successfully")
            else:
                print("Warning: Failed to reload dnsmasq service")
                
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to add device: {e}", file=sys.stderr)
            sys.exit(1)
    
    def delete_device(self, identifier: str) -> None:
        """
        Delete a device by hostname, MAC, or IP.
        
        Args:
            identifier: Device identifier
        """
        if self.dns_mgr.remove_device(identifier):
            print(f"Removed device: {identifier}")
            
            # Optionally reload dnsmasq
            if self.dns_mgr.reload_dnsmasq():
                print("dnsmasq service reloaded successfully")
            else:
                print("Warning: Failed to reload dnsmasq service")
        else:
            print(f"Device not found: {identifier}", file=sys.stderr)
            sys.exit(1)
    
    def import_csv(self, csv_file: str) -> None:
        """
        Import devices from CSV file.
        
        Args:
            csv_file: Path to CSV file
        """
        csv_path = Path(csv_file)
        if not csv_path.exists():
            print(f"Error: File not found: {csv_file}", file=sys.stderr)
            sys.exit(1)
        
        devices = []
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Handle different header variations
                    device = {
                        'hostname': row.get('hostname', row.get('name', '')),
                        'mac': row.get('mac', row.get('mac_address', '')),
                        'ip': row.get('ip', row.get('ip_address', ''))
                    }
                    
                    # Validate required fields
                    if not all(device.values()):
                        print(f"Warning: Skipping incomplete row: {row}")
                        continue
                    
                    devices.append(device)
            
            if not devices:
                print("No valid devices found in CSV file", file=sys.stderr)
                sys.exit(1)
            
            # Update reservations
            self.dns_mgr.update_reservations(devices)
            print(f"Imported {len(devices)} devices from {csv_file}")
            
            # Reload dnsmasq
            if self.dns_mgr.reload_dnsmasq():
                print("dnsmasq service reloaded successfully")
            else:
                print("Warning: Failed to reload dnsmasq service")
                
        except Exception as e:
            print(f"Error importing CSV: {e}", file=sys.stderr)
            sys.exit(1)
    
    def export_csv(self, csv_file: str) -> None:
        """
        Export devices to CSV file.
        
        Args:
            csv_file: Path to output CSV file
        """
        devices = self.dns_mgr.list_reservations()
        
        if not devices:
            print("No reservations to export")
            return
        
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['hostname', 'mac', 'ip'])
                writer.writeheader()
                writer.writerows(devices)
            
            print(f"Exported {len(devices)} devices to {csv_file}")
            
        except Exception as e:
            print(f"Error exporting CSV: {e}", file=sys.stderr)
            sys.exit(1)
    
    def reload_service(self) -> None:
        """Reload dnsmasq service."""
        if self.dns_mgr.reload_dnsmasq():
            print("dnsmasq service reloaded successfully")
        else:
            print("Failed to reload dnsmasq service", file=sys.stderr)
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DNS Manager CLI - Manage dnsmasq static reservations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Command options
    parser.add_argument('--list', '-l', action='store_true',
                        help='List all current reservations')
    parser.add_argument('--add', '-a', nargs=3, metavar=('HOSTNAME', 'MAC', 'IP'),
                        help='Add a new device reservation')
    parser.add_argument('--delete', '-d', metavar='IDENTIFIER',
                        help='Delete device by hostname, MAC, or IP')
    parser.add_argument('--import', '-i', dest='import_file', metavar='CSV_FILE',
                        help='Import devices from CSV file')
    parser.add_argument('--export', '-e', dest='export_file', metavar='CSV_FILE',
                        help='Export devices to CSV file')
    parser.add_argument('--reload', '-r', action='store_true',
                        help='Reload dnsmasq service')
    
    # Output format option
    parser.add_argument('--format', '-f', choices=['table', 'json', 'csv'],
                        default='table', help='Output format for list command')
    
    args = parser.parse_args()
    
    # Check if any command was specified
    if not any([args.list, args.add, args.delete, args.import_file, 
                args.export_file, args.reload]):
        parser.print_help()
        sys.exit(1)
    
    # Create CLI instance
    cli = DNSManagerCLI()
    
    # Execute commands
    try:
        if args.list:
            cli.list_devices(format=args.format)
        
        if args.add:
            hostname, mac, ip = args.add
            cli.add_device(hostname, mac, ip)
        
        if args.delete:
            cli.delete_device(args.delete)
        
        if args.import_file:
            cli.import_csv(args.import_file)
        
        if args.export_file:
            cli.export_csv(args.export_file)
        
        if args.reload:
            cli.reload_service()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
