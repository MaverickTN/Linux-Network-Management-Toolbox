#!/usr/bin/env python3
"""
LNMT VLAN Controller CLI Tool (vlanctl.py)
Command-line interface for VLAN management, monitoring, and automation
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import List, Optional
from tabulate import tabulate
import yaml

# Import the VLAN controller
sys.path.append('/opt/lnmt/services')
from vlan_controller import VLANController, VLANConfig

class VLANCLIError(Exception):
    """Custom exception for CLI errors"""
    pass

class VLANCLIFormatter:
    """Output formatting utilities"""
    
    @staticmethod
    def format_vlan_table(vlans: List[VLANConfig]) -> str:
        """Format VLANs as a table"""
        if not vlans:
            return "No VLANs configured."
        
        headers = ["VLAN ID", "Name", "Subnet", "Gateway", "Interfaces", "Bandwidth", "Status"]
        rows = []
        
        for vlan in vlans:
            interfaces = ", ".join(vlan.interfaces)
            bandwidth = f"{vlan.bandwidth_limit}Mbps" if vlan.bandwidth_limit else "Unlimited"
            status = "🔒 Auto-blacklist" if vlan.auto_blacklist else "🔓 Open"
            
            rows.append([
                vlan.vlan_id,
                vlan.name,
                vlan.subnet,
                vlan.gateway,
                interfaces,
                bandwidth,
                status
            ])
        
        return tabulate(rows, headers=headers, tablefmt="grid")
    
    @staticmethod
    def format_vlan_details(vlan: VLANConfig) -> str:
        """Format detailed VLAN information"""
        return f"""
VLAN Details:
=============
ID: {vlan.vlan_id}
Name: {vlan.name}
Description: {vlan.description}
Subnet: {vlan.subnet}
Gateway: {vlan.gateway}
Interfaces: {', '.join(vlan.interfaces)}
Bandwidth Limit: {vlan.bandwidth_limit}Mbps if vlan.bandwidth_limit else 'Unlimited'}
Usage Threshold: {vlan.usage_threshold}% if vlan.usage_threshold else 'None'}
Auto-blacklist: {'Enabled' if vlan.auto_blacklist else 'Disabled'}
Priority: {vlan.priority}
Created: {vlan.created_at}
Updated: {vlan.updated_at}
"""
    
    @staticmethod
    def format_json(data) -> str:
        """Format data as JSON"""
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def format_yaml(data) -> str:
        """Format data as YAML"""
        return yaml.dump(data, default_flow_style=False)

class VLANCLICommands:
    """CLI command implementations"""
    
    def __init__(self, controller: VLANController):
        self.controller = controller
        self.formatter = VLANCLIFormatter()
    
    def create_vlan(self, args) -> None:
        """Create a new VLAN"""
        try:
            # Parse interfaces
            interfaces = [iface.strip() for iface in args.interfaces.split(',')]
            
            # Validate required fields
            if not all([args.vlan_id, args.name, args.subnet, args.gateway]):
                raise VLANCLIError("Missing required fields: vlan_id, name, subnet, gateway")
            
            success = self.controller.create_vlan(
                vlan_id=args.vlan_id,
                name=args.name,
                description=args.description or "",
                subnet=args.subnet,
                gateway=args.gateway,
                interfaces=interfaces,
                bandwidth_limit=args.bandwidth_limit,
                usage_threshold=args.usage_threshold,
                auto_blacklist=args.auto_blacklist,
                priority=args.priority
            )
            
            if success:
                print(f"✅ Successfully created VLAN {args.vlan_id} ({args.name})")
                if args.verbose:
                    vlan = self.controller.get_vlan(args.vlan_id)
                    if vlan:
                        print(self.formatter.format_vlan_details(vlan))
            else:
                raise VLANCLIError(f"Failed to create VLAN {args.vlan_id}")
                
        except Exception as e:
            raise VLANCLIError(f"Error creating VLAN: {e}")
    
    def list_vlans(self, args) -> None:
        """List all VLANs"""
        try:
            vlans = self.controller.list_vlans()
            
            if args.output_format == 'json':
                data = [vlan.__dict__ for vlan in vlans]
                print(self.formatter.format_json(data))
            elif args.output_format == 'yaml':
                data = [vlan.__dict__ for vlan in vlans]
                print(self.formatter.format_yaml(data))
            else:
                print(self.formatter.format_vlan_table(vlans))
                
        except Exception as e:
            raise VLANCLIError(f"Error listing VLANs: {e}")
    
    def show_vlan(self, args) -> None:
        """Show detailed VLAN information"""
        try:
            vlan = self.controller.get_vlan(args.vlan_id)
            if not vlan:
                raise VLANCLIError(f"VLAN {args.vlan_id} not found")
            
            if args.output_format == 'json':
                print(self.formatter.format_json(vlan.__dict__))
            elif args.output_format == 'yaml':
                print(self.formatter.format_yaml(vlan.__dict__))
            else:
                print(self.formatter.format_vlan_details(vlan))
                
        except Exception as e:
            raise VLANCLIError(f"Error showing VLAN: {e}")
    
    def update_vlan(self, args) -> None:
        """Update VLAN configuration"""
        try:
            # Build update dictionary
            updates = {}
            if args.name:
                updates['name'] = args.name
            if args.description:
                updates['description'] = args.description
            if args.bandwidth_limit is not None:
                updates['bandwidth_limit'] = args.bandwidth_limit
            if args.usage_threshold is not None:
                updates['usage_threshold'] = args.usage_threshold
            if args.auto_blacklist is not None:
                updates['auto_blacklist'] = args.auto_blacklist
            if args.priority is not None:
                updates['priority'] = args.priority
            
            if not updates:
                raise VLANCLIError("No fields specified for update")
            
            success = self.controller.update_vlan(args.vlan_id, **updates)
            
            if success:
                print(f"✅ Successfully updated VLAN {args.vlan_id}")
                if args.verbose:
                    vlan = self.controller.get_vlan(args.vlan_id)
                    if vlan:
                        print(self.formatter.format_vlan_details(vlan))
            else:
                raise VLANCLIError(f"Failed to update VLAN {args.vlan_id}")
                
        except Exception as e:
            raise VLANCLIError(f"Error updating VLAN: {e}")
    
    def delete_vlan(self, args) -> None:
        """Delete a VLAN"""
        try:
            # Confirm deletion unless --force is used
            if not args.force:
                vlan = self.controller.get_vlan(args.vlan_id)
                if not vlan:
                    raise VLANCLIError(f"VLAN {args.vlan_id} not found")
                
                response = input(f"Are you sure you want to delete VLAN {args.vlan_id} ({vlan.name})? [y/N]: ")
                if response.lower() != 'y':
                    print("Deletion cancelled.")
                    return
            
            success = self.controller.delete_vlan(args.vlan_id)
            
            if success:
                print(f"✅ Successfully deleted VLAN {args.vlan_id}")
            else:
                raise VLANCLIError(f"Failed to delete VLAN {args.vlan_id}")
                
        except Exception as e:
            raise VLANCLIError(f"Error deleting VLAN: {e}")
    
    def monitor_vlans(self, args) -> None:
        """Monitor VLAN statistics"""
        try:
            print("Starting VLAN monitoring... (Press Ctrl+C to stop)")
            self.controller.start_monitoring()
            
            import time
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping VLAN monitoring...")
            self.controller.stop_monitoring()
        except Exception as e:
            raise VLANCLIError(f"Error monitoring VLANs: {e}")
    
    def export_topology(self, args) -> None:
        """Export VLAN topology diagram"""
        try:
            output_file = args.output or "/tmp/vlan_topology.dot"
            success = self.controller.export_topology(output_file)
            
            if success:
                print(f"✅ Topology exported to {output_file}")
                
                # Optionally generate PNG if graphviz is available
                if args.format and args.format != 'dot':
                    try:
                        png_file = output_file.replace('.dot', f'.{args.format}')
                        subprocess.run(['dot', f'-T{args.format}', output_file, '-o', png_file], 
                                     check=True, capture_output=True)
                        print(f"✅ Diagram generated: {png_file}")
                    except subprocess.CalledProcessError:
                        print("⚠️  Graphviz not available - only DOT file created")
                    except FileNotFoundError:
                        print("⚠️  Graphviz not installed - only DOT file created")
            else:
                raise VLANCLIError("Failed to export topology")
                
        except Exception as e:
            raise VLANCLIError(f"Error exporting topology: {e}")
    
    def validate_config(self, args) -> None:
        """Validate VLAN configurations"""
        try:
            vlans = self.controller.list_vlans()
            issues = []
            
            # Check for VLAN ID conflicts
            vlan_ids = [vlan.vlan_id for vlan in vlans]
            duplicates = [vid for vid in set(vlan_ids) if vlan_ids.count(vid) > 1]
            if duplicates:
                issues.append(f"Duplicate VLAN IDs: {duplicates}")
            
            # Check for subnet overlaps
            import ipaddress
            networks = []
            for vlan in vlans:
                try:
                    network = ipaddress.IPv4Network(vlan.subnet)
                    for existing_network, existing_vlan in networks:
                        if network.overlaps(existing_network):
                            issues.append(f"Subnet overlap: VLAN {vlan.vlan_id} ({vlan.subnet}) overlaps with VLAN {existing_vlan} ({existing_network})")
                    networks.append((network, vlan.vlan_id))
                except ValueError as e:
                    issues.append(f"Invalid subnet in VLAN {vlan.vlan_id}: {e}")
            
            # Check interface availability
            for vlan in vlans:
                for interface in vlan.interfaces:
                    # Check if interface exists
                    try:
                        result = subprocess.run(['ip', 'link', 'show', interface], 
                                              capture_output=True, text=True)
                        if result.returncode != 0:
                            issues.append(f"Interface {interface} not found (used by VLAN {vlan.vlan_id})")
                    except FileNotFoundError:
                        issues.append("ip command not available - cannot validate interfaces")
            
            if issues:
                print("❌ Configuration validation failed:")
                for issue in issues:
                    print(f"  • {issue}")
                sys.exit(1)
            else:
                print("✅ All VLAN configurations are valid")
                
        except Exception as e:
            raise VLANCLIError(f"Error validating configuration: {e}")
    
    def import_config(self, args) -> None:
        """Import VLAN configuration from file"""
        try:
            config_file = Path(args.config_file)
            if not config_file.exists():
                raise VLANCLIError(f"Configuration file not found: {args.config_file}")
            
            # Read configuration
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            # Validate configuration structure
            if 'vlans' not in config:
                raise VLANCLIError("Configuration must contain 'vlans' key")
            
            # Import VLANs
            imported = 0
            failed = 0
            
            for vlan_config in config['vlans']:
                try:
                    success = self.controller.create_vlan(
                        vlan_id=vlan_config['vlan_id'],
                        name=vlan_config['name'],
                        description=vlan_config.get('description', ''),
                        subnet=vlan_config['subnet'],
                        gateway=vlan_config['gateway'],
                        interfaces=vlan_config['interfaces'],
                        bandwidth_limit=vlan_config.get('bandwidth_limit'),
                        usage_threshold=vlan_config.get('usage_threshold'),
                        auto_blacklist=vlan_config.get('auto_blacklist', False),
                        priority=vlan_config.get('priority', 1)
                    )
                    
                    if success:
                        imported += 1
                        print(f"✅ Imported VLAN {vlan_config['vlan_id']} ({vlan_config['name']})")
                    else:
                        failed += 1
                        print(f"❌ Failed to import VLAN {vlan_config['vlan_id']}")
                        
                except Exception as e:
                    failed += 1
                    print(f"❌ Error importing VLAN {vlan_config.get('vlan_id', 'unknown')}: {e}")
            
            print(f"\n📊 Import Summary: {imported} imported, {failed} failed")
            
        except Exception as e:
            raise VLANCLIError(f"Error importing configuration: {e}")
    
    def export_config(self, args) -> None:
        """Export VLAN configuration to file"""
        try:
            vlans = self.controller.list_vlans()
            
            # Build configuration structure
            config = {
                'vlans': [vlan.__dict__ for vlan in vlans],
                'exported_at': datetime.now().isoformat()
            }
            
            # Write configuration
            output_file = args.output or "vlan_config.yaml"
            with open(output_file, 'w') as f:
                if output_file.endswith('.json'):
                    json.dump(config, f, indent=2, default=str)
                else:
                    yaml.dump(config, f, default_flow_style=False)
            
            print(f"✅ Configuration exported to {output_file}")
            
        except Exception as e:
            raise VLANCLIError(f"Error exporting configuration: {e}")

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        description="LNMT VLAN Controller CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new VLAN
  vlanctl create 100 --name "Guest Network" --subnet "192.168.100.0/24" --gateway "192.168.100.1" --interfaces "eth0"
  
  # List all VLANs
  vlanctl list
  
  # Show VLAN details
  vlanctl show 100
  
  # Update VLAN bandwidth limit
  vlanctl update 100 --bandwidth-limit 50
  
  # Delete a VLAN
  vlanctl delete 100
  
  # Monitor VLAN statistics
  vlanctl monitor
  
  # Export topology diagram
  vlanctl topology --format png
  
  # Validate configuration
  vlanctl validate
  
  # Import configuration
  vlanctl import-config vlans.yaml
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output-format', choices=['table', 'json', 'yaml'], 
                       default='table', help='Output format')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create VLAN command
    create_parser = subparsers.add_parser('create', help='Create a new VLAN')
    create_parser.add_argument('vlan_id', type=int, help='VLAN ID (1-4094)')
    create_parser.add_argument('--name', required=True, help='VLAN name')
    create_parser.add_argument('--description', help='VLAN description')
    create_parser.add_argument('--subnet', required=True, help='Subnet (e.g., 192.168.100.0/24)')
    create_parser.add_argument('--gateway', required=True, help='Gateway IP address')
    create_parser.add_argument('--interfaces', required=True, help='Comma-separated list of interfaces')
    create_parser.add_argument('--bandwidth-limit', type=int, help='Bandwidth limit in Mbps')
    create_parser.add_argument('--usage-threshold', type=int, help='Usage threshold percentage')
    create_parser.add_argument('--auto-blacklist', action='store_true', help='Enable auto-blacklisting')
    create_parser.add_argument('--priority', type=int, default=1, help='QoS priority (1-7)')
    
    # List VLANs command
    list_parser = subparsers.add_parser('list', help='List all VLANs')
    
    # Show VLAN command
    show_parser = subparsers.add_parser('show', help='Show VLAN details')
    show_parser.add_argument('vlan_id', type=int, help='VLAN ID')
    
    # Update VLAN command
    update_parser = subparsers.add_parser('update', help='Update VLAN configuration')
    update_parser.add_argument('vlan_id', type=int, help='VLAN ID')
    update_parser.add_argument('--name', help='VLAN name')
    update_parser.add_argument('--description', help='VLAN description')
    update_parser.add_argument('--bandwidth-limit', type=int, help='Bandwidth limit in Mbps')
    update_parser.add_argument('--usage-threshold', type=int, help='Usage threshold percentage')
    update_parser.add_argument('--auto-blacklist', action='store_true', help='Enable auto-blacklisting')
    update_parser.add_argument('--priority', type=int, help='QoS priority (1-7)')
    
    # Delete VLAN command
    delete_parser = subparsers.add_parser('delete', help='Delete a VLAN')
    delete_parser.add_argument('vlan_id', type=int, help='VLAN ID')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor VLAN statistics')
    
    # Export topology command
    topology_parser = subparsers.add_parser('topology', help='Export VLAN topology diagram')
    topology_parser.add_argument('--output', help='Output file path')
    topology_parser.add_argument('--format', choices=['dot', 'png', 'svg', 'pdf'], 
                                default='dot', help='Output format')
    
    # Validate configuration command
    validate_parser = subparsers.add_parser('validate', help='Validate VLAN configurations')
    
    # Import configuration command
    import_parser = subparsers.add_parser('import-config', help='Import VLAN configuration from file')
    import_parser.add_argument('config_file', help='Configuration file (JSON or YAML)')
    
    # Export configuration command
    export_parser = subparsers.add_parser('export-config', help='Export VLAN configuration to file')
    export_parser.add_argument('--output', help='Output file path')
    
    return parser

def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Initialize controller
        controller = VLANController()
        cli = VLANCLICommands(controller)
        
        # Execute command
        command_method = getattr(cli, args.command.replace('-', '_'))
        command_method(args)
        
    except VLANCLIError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()