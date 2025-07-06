#!/usr/bin/env python3
"""
LNMT TC Control CLI Tool (tcctl)
Command-line interface for Traffic Control and Quality of Service management

Usage:
    tcctl interfaces                           # List all interfaces
    tcctl policies                             # List all policies
    tcctl create-policy <name> <config.json>   # Create policy from config
    tcctl apply <policy_name>                  # Apply policy
    tcctl test <policy_name>                   # Test policy (dry run)
    tcctl remove <interface>                   # Remove TC config from interface
    tcctl status <interface>                   # Show TC status
    tcctl stats <interface>                    # Show TC statistics
    tcctl export <policy_name> [format]       # Export policy (json/yaml)
    tcctl import <file> [format]               # Import policy
    tcctl rollback <interface>                 # Rollback to previous config
    tcctl monitor <interface>                  # Monitor interface statistics
    tcctl cleanup                              # Cleanup old statistics
    tcctl htb-wizard                           # Interactive HTB policy wizard

Author: LNMT Development Team
License: MIT
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

# Import TC service
try:
    from tc_service import TCManager, TCPolicy, TCQdisc, TCClass, TCFilter
except ImportError:
    print("Error: tc_service module not found. Please ensure tc_service.py is in the Python path.")
    sys.exit(1)

class TCControlCLI:
    """TC Control Command Line Interface"""
    
    def __init__(self):
        self.tc_manager = TCManager()
    
    def list_interfaces(self):
        """List all network interfaces"""
        interfaces = self.tc_manager.discover_interfaces()
        
        if not interfaces:
            print("No interfaces found")
            return
        
        print(f"{'Interface':<15} {'Type':<10} {'State':<8} {'Speed':<10} {'IP Addresses'}")
        print("-" * 70)
        
        for interface in interfaces:
            speed = f"{interface.speed}Mbps" if interface.speed else "Unknown"
            ip_addresses = ", ".join(interface.ip_addresses) if interface.ip_addresses else "None"
            print(f"{interface.name:<15} {interface.type:<10} {interface.state:<8} {speed:<10} {ip_addresses}")
    
    def list_policies(self):
        """List all TC policies"""
        policies = self.tc_manager.list_policies()
        
        if not policies:
            print("No policies found")
            return
        
        print(f"{'Policy Name':<20} {'Interface':<15} {'Status':<10} {'Created'}")
        print("-" * 70)
        
        for policy_name in policies:
            policy = self.tc_manager.get_policy(policy_name)
            if policy:
                status = "Enabled" if policy.enabled else "Disabled"
                created = policy.created_at.strftime("%Y-%m-%d %H:%M")
                print(f"{policy.name:<20} {policy.interface:<15} {status:<10} {created}")
    
    def create_policy_from_config(self, name: str, config_file: str):
        """Create policy from configuration file"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                print(f"Error: Configuration file not found: {config_file}")
                return False
            
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            # Convert config to policy objects
            policy = self._config_to_policy(name, config)
            
            if self.tc_manager.create_policy(policy):
                print(f"Policy '{name}' created successfully")
                return True
            else:
                print(f"Failed to create policy '{name}'")
                return False
                
        except Exception as e:
            print(f"Error creating policy from config: {e}")
            return False
    
    def _config_to_policy(self, name: str, config: Dict[str, Any]) -> TCPolicy:
        """Convert configuration dictionary to TCPolicy object"""
        qdiscs = []
        classes = []
        filters = []
        
        # Convert qdiscs
        for qdisc_config in config.get('qdiscs', []):
            qdisc = TCQdisc(
                handle=qdisc_config['handle'],
                parent=qdisc_config['parent'],
                kind=qdisc_config['kind'],
                interface=config['interface'],
                options=qdisc_config.get('options', {}),
                created_at=datetime.now(),
                enabled=qdisc_config.get('enabled', True)
            )
            qdiscs.append(qdisc)
        
        # Convert classes
        for class_config in config.get('classes', []):
            class_obj = TCClass(
                classid=class_config['classid'],
                parent=class_config['parent'],
                kind=class_config['kind'],
                interface=config['interface'],
                rate=class_config['rate'],
                ceil=class_config.get('ceil', class_config['rate']),
                burst=class_config.get('burst'),
                cburst=class_config.get('cburst'),
                prio=class_config.get('prio', 0),
                quantum=class_config.get('quantum'),
                options=class_config.get('options', {}),
                created_at=datetime.now(),
                enabled=class_config.get('enabled', True)
            )
            classes.append(class_obj)
        
        # Convert filters
        for filter_config in config.get('filters', []):
            filter_obj = TCFilter(
                handle=filter_config['handle'],
                parent=filter_config['parent'],
                protocol=filter_config['protocol'],
                prio=filter_config['prio'],
                kind=filter_config['kind'],
                interface=config['interface'],
                match_criteria=filter_config.get('match_criteria', {}),
                flowid=filter_config['flowid'],
                action=filter_config.get('action'),
                created_at=datetime.now(),
                enabled=filter_config.get('enabled', True)
            )
            filters.append(filter_obj)
        
        return TCPolicy(
            name=name,
            description=config.get('description', f'Policy for {config["interface"]}'),
            interface=config['interface'],
            qdiscs=qdiscs,
            classes=classes,
            filters=filters,
            enabled=config.get('enabled', True)
        )
    
    def apply_policy(self, policy_name: str):
        """Apply a TC policy"""
        print(f"Applying policy '{policy_name}'...")
        
        if self.tc_manager.apply_policy(policy_name):
            print(f"Policy '{policy_name}' applied successfully")
            return True
        else:
            print(f"Failed to apply policy '{policy_name}'")
            return False
    
    def test_policy(self, policy_name: str):
        """Test a TC policy (dry run)"""
        print(f"Testing policy '{policy_name}' (dry run)...")
        
        if self.tc_manager.apply_policy(policy_name, test_mode=True):
            print(f"Policy '{policy_name}' test passed - ready to apply")
            return True
        else:
            print(f"Policy '{policy_name}' test failed")
            return False
    
    def remove_tc_config(self, interface: str):
        """Remove TC configuration from interface"""
        print(f"Removing TC configuration from interface '{interface}'...")
        
        try:
            self.tc_manager._clear_tc_config(interface)
            print(f"TC configuration removed from '{interface}'")
            return True
        except Exception as e:
            print(f"Failed to remove TC configuration: {e}")
            return False
    
    def show_status(self, interface: str):
        """Show TC status for interface"""
        config = self.tc_manager.get_current_tc_config(interface)
        
        if not any(config.values()):
            print(f"No TC configuration found for interface '{interface}'")
            return
        
        print(f"TC Status for interface '{interface}':")
        print("=" * 50)
        
        # Show qdiscs
        if config['qdiscs']:
            print("\nQueueing Disciplines:")
            for qdisc in config['qdiscs']:
                print(f"  {qdisc['kind']} handle {qdisc['handle']} parent {qdisc['parent']}")
                for key, value in qdisc.get('options', {}).items():
                    print(f"    {key}: {value}")
        
        # Show classes
        if config['classes']:
            print("\nClasses:")
            for class_info in config['classes']:
                print(f"  {class_info['kind']} classid {class_info['classid']} parent {class_info['parent']}")
                for key, value in class_info.get('options', {}).items():
                    print(f"    {key}: {value}")
        
        # Show filters
        if config['filters']:
            print("\nFilters:")
            for filter_info in config['filters']:
                print(f"  {filter_info['kind']} protocol {filter_info['protocol']} prio {filter_info['prio']}")
                for key, value in filter_info.get('options', {}).items():
                    print(f"    {key}: {value}")
    
    def show_statistics(self, interface: str):
        """Show TC statistics for interface"""
        stats = self.tc_manager.get_statistics(interface)
        
        if not stats:
            print(f"No statistics available for interface '{interface}'")
            return
        
        print(f"TC Statistics for interface '{interface}':")
        print("=" * 50)
        print(f"Timestamp: {stats['timestamp']}")
        
        # Show qdisc statistics
        if stats.get('qdisc_stats'):
            print("\nQdisc Statistics:")
            for i, qdisc_stat in enumerate(stats['qdisc_stats']):
                print(f"  Qdisc {i+1}:")
                print(f"    Bytes sent: {qdisc_stat.get('bytes_sent', 0):,}")
                print(f"    Packets sent: {qdisc_stat.get('packets_sent', 0):,}")
                print(f"    Drops: {qdisc_stat.get('drops', 0):,}")
                print(f"    Overlimits: {qdisc_stat.get('overlimits', 0):,}")
                print(f"    Requeues: {qdisc_stat.get('requeues', 0):,}")
        
        # Show class statistics
        if stats.get('class_stats'):
            print("\nClass Statistics:")
            for i, class_stat in enumerate(stats['class_stats']):
                print(f"  Class {i+1}:")
                print(f"    Bytes sent: {class_stat.get('bytes_sent', 0):,}")
                print(f"    Packets sent: {class_stat.get('packets_sent', 0):,}")
                print(f"    Drops: {class_stat.get('drops', 0):,}")
                print(f"    Overlimits: {class_stat.get('overlimits', 0):,}")
                print(f"    Requeues: {class_stat.get('requeues', 0):,}")
    
    def export_policy(self, policy_name: str, format: str = 'json'):
        """Export policy to file"""
        exported = self.tc_manager.export_policy(policy_name, format)
        
        if exported:
            filename = f"{policy_name}.{format}"
            with open(filename, 'w') as f:
                f.write(exported)
            
            print(f"Policy '{policy_name}' exported to '{filename}'")
            return True
        else:
            print(f"Failed to export policy '{policy_name}'")
            return False
    
    def import_policy(self, filename: str, format: str = None):
        """Import policy from file"""
        try:
            file_path = Path(filename)
            if not file_path.exists():
                print(f"Error: File not found: {filename}")
                return False
            
            # Auto-detect format if not specified
            if format is None:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    format = 'yaml'
                else:
                    format = 'json'
            
            with open(file_path, 'r') as f:
                policy_data = f.read()
            
            if self.tc_manager.import_policy(policy_data, format):
                print(f"Policy imported successfully from '{filename}'")
                return True
            else:
                print(f"Failed to import policy from '{filename}'")
                return False
                
        except Exception as e:
            print(f"Error importing policy: {e}")
            return False
    
    def rollback_config(self, interface: str):
        """Rollback to previous configuration"""
        print(f"Rolling back configuration for interface '{interface}'...")
        
        # Get the most recent rollback entry
        try:
            cursor = self.tc_manager.db_conn.cursor()
            cursor.execute("""
                SELECT id FROM tc_rollback_history 
                WHERE interface = ? AND status = 'active'
                ORDER BY applied_at DESC
                LIMIT 1
            """, (interface,))
            
            row = cursor.fetchone()
            if row:
                rollback_id = str(row[0])
                if self.tc_manager._rollback_config(rollback_id):
                    print(f"Configuration rolled back successfully for '{interface}'")
                    return True
                else:
                    print(f"Failed to rollback configuration for '{interface}'")
                    return False
            else:
                print(f"No rollback data found for interface '{interface}'")
                return False
                
        except Exception as e:
            print(f"Error during rollback: {e}")
            return False
    
    def monitor_interface(self, interface: str, interval: int = 5):
        """Monitor interface statistics in real-time"""
        print(f"Monitoring interface '{interface}' (press Ctrl+C to stop)...")
        print("=" * 80)
        
        try:
            while True:
                stats = self.tc_manager.get_statistics(interface)
                
                if stats:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Interface: {interface}")
                    
                    # Show summary statistics
                    total_bytes = sum(stat.get('bytes_sent', 0) for stat in stats.get('qdisc_stats', []))
                    total_packets = sum(stat.get('packets_sent', 0) for stat in stats.get('qdisc_stats', []))
                    total_drops = sum(stat.get('drops', 0) for stat in stats.get('qdisc_stats', []))
                    
                    print(f"  Total Bytes: {total_bytes:,}")
                    print(f"  Total Packets: {total_packets:,}")
                    print(f"  Total Drops: {total_drops:,}")
                    
                    # Record statistics
                    self.tc_manager.record_statistics(interface)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    
    def cleanup_statistics(self):
        """Clean up old statistics"""
        print("Cleaning up old statistics...")
        self.tc_manager.cleanup_old_statistics()
        print("Statistics cleanup completed.")
    
    def htb_wizard(self):
        """Interactive HTB policy creation wizard"""
        print("HTB Policy Creation Wizard")
        print("=" * 30)
        
        # Get policy details
        name = input("Policy name: ").strip()
        if not name:
            print("Error: Policy name is required")
            return False
        
        # List interfaces
        interfaces = self.tc_manager.discover_interfaces()
        if not interfaces:
            print("Error: No interfaces found")
            return False
        
        print("\nAvailable interfaces:")
        for i, interface in enumerate(interfaces):
            print(f"  {i+1}. {interface.name} ({interface.type}) - {interface.state}")
        
        try:
            choice = int(input("Select interface (number): ").strip())
            if choice < 1 or choice > len(interfaces):
                print("Error: Invalid interface selection")
                return False
            
            selected_interface = interfaces[choice - 1].name
        except ValueError:
            print("Error: Invalid input")
            return False
        
        # Get total bandwidth
        total_rate = input("Total bandwidth (e.g., 100mbit): ").strip()
        if not total_rate:
            print("Error: Total bandwidth is required")
            return False
        
        # Get classes
        classes = []
        print("\nDefine traffic classes (press Enter without input to finish):")
        
        class_num = 1
        while True:
            print(f"\nClass {class_num}:")
            
            rate = input("  Rate (e.g., 10mbit): ").strip()
            if not rate:
                break
            
            ceil = input(f"  Ceiling (default: {rate}): ").strip()
            if not ceil:
                ceil = rate
            
            prio = input("  Priority (1-8, default: 1): ").strip()
            if not prio:
                prio = 1
            else:
                try:
                    prio = int(prio)
                except ValueError:
                    prio = 1
            
            # Match criteria
            print("  Match criteria (optional):")
            src_ip = input("    Source IP/Network: ").strip()
            dst_ip = input("    Destination IP/Network: ").strip()
            sport = input("    Source port: ").strip()
            dport = input("    Destination port: ").strip()
            
            match = {}
            if src_ip:
                match['src'] = src_ip
            if dst_ip:
                match['dst'] = dst_ip
            if sport:
                try:
                    match['sport'] = int(sport)
                except ValueError:
                    pass
            if dport:
                try:
                    match['dport'] = int(dport)
                except ValueError:
                    pass
            
            class_config = {
                'rate': rate,
                'ceil': ceil,
                'prio': prio
            }
            
            if match:
                class_config['match'] = match
            
            classes.append(class_config)
            class_num += 1
        
        if not classes:
            print("Error: At least one class is required")
            return False
        
        # Create policy
        print(f"\nCreating HTB policy '{name}' with {len(classes)} classes...")
        
        if self.tc_manager.create_simple_htb_policy(name, selected_interface, total_rate, classes):
            print(f"HTB policy '{name}' created successfully!")
            
            # Ask if user wants to apply it
            apply = input("Apply policy now? (y/N): ").strip().lower()
            if apply == 'y':
                return self.apply_policy(name)
            
            return True
        else:
            print("Failed to create HTB policy")
            return False
    
    def delete_policy(self, policy_name: str):
        """Delete a policy"""
        confirm = input(f"Are you sure you want to delete policy '{policy_name}'? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return False
        
        if self.tc_manager.delete_policy(policy_name):
            print(f"Policy '{policy_name}' deleted successfully")
            return True
        else:
            print(f"Failed to delete policy '{policy_name}'")
            return False
    
    def show_policy_details(self, policy_name: str):
        """Show detailed policy information"""
        policy = self.tc_manager.get_policy(policy_name)
        
        if not policy:
            print(f"Policy '{policy_name}' not found")
            return False
        
        print(f"Policy: {policy.name}")
        print("=" * 50)
        print(f"Description: {policy.description}")
        print(f"Interface: {policy.interface}")
        print(f"Enabled: {policy.enabled}")
        print(f"Created: {policy.created_at}")
        print(f"Updated: {policy.updated_at}")
        
        # Show qdiscs
        if policy.qdiscs:
            print(f"\nQueueing Disciplines ({len(policy.qdiscs)}):")
            for qdisc in policy.qdiscs:
                print(f"  {qdisc.kind} handle {qdisc.handle} parent {qdisc.parent}")
                print(f"    Enabled: {qdisc.enabled}")
                if qdisc.options:
                    print(f"    Options: {qdisc.options}")
        
        # Show classes
        if policy.classes:
            print(f"\nClasses ({len(policy.classes)}):")
            for class_obj in policy.classes:
                print(f"  {class_obj.kind} classid {class_obj.classid} parent {class_obj.parent}")
                print(f"    Rate: {class_obj.rate}, Ceil: {class_obj.ceil}")
                print(f"    Priority: {class_obj.prio}")
                print(f"    Enabled: {class_obj.enabled}")
        
        # Show filters
        if policy.filters:
            print(f"\nFilters ({len(policy.filters)}):")
            for filter_obj in policy.filters:
                print(f"  {filter_obj.kind} protocol {filter_obj.protocol} prio {filter_obj.prio}")
                print(f"    Handle: {filter_obj.handle}, Parent: {filter_obj.parent}")
                print(f"    Flowid: {filter_obj.flowid}")
                print(f"    Match: {filter_obj.match_criteria}")
                print(f"    Enabled: {filter_obj.enabled}")
        
        return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='LNMT Traffic Control CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tcctl interfaces                    # List all interfaces
  tcctl policies                      # List all policies
  tcctl create-policy web_policy config.json  # Create policy from config
  tcctl apply web_policy              # Apply policy
  tcctl test web_policy               # Test policy (dry run)
  tcctl status eth0                   # Show TC status for eth0
  tcctl stats eth0                    # Show TC statistics for eth0
  tcctl export web_policy yaml        # Export policy to YAML
  tcctl import policy.json            # Import policy from JSON
  tcctl htb-wizard                    # Interactive HTB policy creation
  tcctl monitor eth0                  # Monitor eth0 in real-time
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # interfaces command
    subparsers.add_parser('interfaces', help='List all network interfaces')
    
    # policies command
    subparsers.add_parser('policies', help='List all TC policies')
    
    # create-policy command
    create_parser = subparsers.add_parser('create-policy', help='Create policy from configuration file')
    create_parser.add_argument('name', help='Policy name')
    create_parser.add_argument('config', help='Configuration file path')
    
    # apply command
    apply_parser = subparsers.add_parser('apply', help='Apply a TC policy')
    apply_parser.add_argument('policy', help='Policy name to apply')
    
    # test command
    test_parser = subparsers.add_parser('test', help='Test a TC policy (dry run)')
    test_parser.add_argument('policy', help='Policy name to test')
    
    # remove command
    remove_parser = subparsers.add_parser('remove', help='Remove TC configuration from interface')
    remove_parser.add_argument('interface', help='Interface name')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Show TC status for interface')
    status_parser.add_argument('interface', help='Interface name')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Show TC statistics for interface')
    stats_parser.add_argument('interface', help='Interface name')
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export policy to file')
    export_parser.add_argument('policy', help='Policy name to export')
    export_parser.add_argument('format', nargs='?', default='json', choices=['json', 'yaml'], help='Export format')
    
    # import command
    import_parser = subparsers.add_parser('import', help='Import policy from file')
    import_parser.add_argument('file', help='File path to import')
    import_parser.add_argument('format', nargs='?', choices=['json', 'yaml'], help='Import format (auto-detected if not specified)')
    
    # rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback interface to previous configuration')
    rollback_parser.add_argument('interface', help='Interface name')
    
    # monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor interface statistics in real-time')
    monitor_parser.add_argument('interface', help='Interface name')
    monitor_parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    
    # cleanup command
    subparsers.add_parser('cleanup', help='Clean up old statistics')
    
    # htb-wizard command
    subparsers.add_parser('htb-wizard', help='Interactive HTB policy creation wizard')
    
    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a policy')
    delete_parser.add_argument('policy', help='Policy name to delete')
    
    # show command
    show_parser = subparsers.add_parser('show', help='Show detailed policy information')
    show_parser.add_argument('policy', help='Policy name to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        cli = TCControlCLI()
        
        if args.command == 'interfaces':
            cli.list_interfaces()
        elif args.command == 'policies':
            cli.list_policies()
        elif args.command == 'create-policy':
            success = cli.create_policy_from_config(args.name, args.config)
            return 0 if success else 1
        elif args.command == 'apply':
            success = cli.apply_policy(args.policy)
            return 0 if success else 1
        elif args.command == 'test':
            success = cli.test_policy(args.policy)
            return 0 if success else 1
        elif args.command == 'remove':
            success = cli.remove_tc_config(args.interface)
            return 0 if success else 1
        elif args.command == 'status':
            cli.show_status(args.interface)
        elif args.command == 'stats':
            cli.show_statistics(args.interface)
        elif args.command == 'export':
            success = cli.export_policy(args.policy, args.format)
            return 0 if success else 1
        elif args.command == 'import':
            success = cli.import_policy(args.file, args.format)
            return 0 if success else 1
        elif args.command == 'rollback':
            success = cli.rollback_config(args.interface)
            return 0 if success else 1
        elif args.command == 'monitor':
            cli.monitor_interface(args.interface, args.interval)
        elif args.command == 'cleanup':
            cli.cleanup_statistics()
        elif args.command == 'htb-wizard':
            success = cli.htb_wizard()
            return 0 if success else 1
        elif args.command == 'delete':
            success = cli.delete_policy(args.policy)
            return 0 if success else 1
        elif args.command == 'show':
            success = cli.show_policy_details(args.policy)
            return 0 if success else 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Cleanup
        try:
            cli.tc_manager.close()
        except:
            pass


if __name__ == '__main__':
    sys.exit(main())