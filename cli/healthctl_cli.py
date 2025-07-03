#!/usr/bin/env python3
"""
LNMT Health Control CLI

Command-line interface for LNMT health monitoring system.
Provides status checks, service monitoring, and alert management.

Usage:
    healthctl.py --status              # Show overall system status
    healthctl.py --check dnsmasq       # Check specific service
    healthctl.py --alertlog            # Show recent alerts
    healthctl.py --resources           # Show resource usage
    healthctl.py --configs             # Validate configurations
    healthctl.py --json                # Output in JSON format
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Optional

# Add the parent directory to path to import health_monitor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from services.health_monitor import HealthMonitor, AlertLevel, ServiceStatus
except ImportError:
    print("Error: Could not import health_monitor module.")
    print("Make sure you're running this from the correct directory structure.")
    sys.exit(1)


class HealthCLI:
    """CLI interface for LNMT health monitoring"""
    
    def __init__(self):
        self.monitor = HealthMonitor()
        self.json_output = False
    
    def set_json_output(self, json_mode: bool) -> None:
        """Enable or disable JSON output mode"""
        self.json_output = json_mode
    
    def print_output(self, data, title: Optional[str] = None) -> None:
        """Print output in either JSON or human-readable format"""
        if self.json_output:
            if title:
                output = {title.lower().replace(' ', '_'): data}
            else:
                output = data
            print(json.dumps(output, indent=2, default=str))
        else:
            if title:
                print(f"\n=== {title} ===")
            
            if isinstance(data, dict):
                self._print_dict(data)
            elif isinstance(data, list):
                self._print_list(data)
            else:
                print(data)
    
    def _print_dict(self, data: dict, indent: int = 0) -> None:
        """Print dictionary in human-readable format"""
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_dict(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}:")
                self._print_list(value, indent + 1)
            else:
                print(f"{prefix}{key}: {value}")
    
    def _print_list(self, data: list, indent: int = 0) -> None:
        """Print list in human-readable format"""
        prefix = "  " * indent
        for i, item in enumerate(data):
            if isinstance(item, dict):
                print(f"{prefix}[{i}]:")
                self._print_dict(item, indent + 1)
            else:
                print(f"{prefix}- {item}")
    
    def show_status(self) -> None:
        """Display overall system health status"""
        try:
            status = self.monitor.get_system_status()
            
            if self.json_output:
                self.print_output(status, "System Status")
                return
            
            print("\n=== LNMT System Health Status ===")
            print(f"Timestamp: {status['timestamp']}")
            print(f"Overall Health: {status['overall_health'].upper()}")
            
            # Health indicator
            health_indicators = {
                'healthy': '🟢',
                'warning': '🟡', 
                'degraded': '🟠',
                'critical': '🔴'
            }
            indicator = health_indicators.get(status['overall_health'], '❓')
            print(f"Status: {indicator} {status['overall_health'].title()}")
            
            # Summary
            summary = status['summary']
            print(f"\nSummary:")
            print(f"  Services: {summary['total_services'] - summary['failed_services']}/{summary['total_services']} running")
            print(f"  Configs: {summary['total_configs'] - summary['failed_configs']}/{summary['total_configs']} valid")
            
            # Services overview
            print(f"\nServices:")
            for service in status['services']:
                status_symbol = {
                    'running': '🟢',
                    'stopped': '🔴',
                    'failed': '🟠',
                    'unknown': '❓'
                }.get(service['status'], '❓')
                
                print(f"  {status_symbol} {service['name']}: {service['status']}")
                if service['pid']:
                    print(f"    PID: {service['pid']}, Memory: {service['memory_mb']:.1f}MB")
                    if service['uptime']:
                        print(f"    Uptime: {service['uptime']}")
            
            # Resources overview
            if 'resources' in status and status['resources']:
                resources = status['resources']
                print(f"\nResource Usage:")
                print(f"  CPU: {resources.get('cpu_percent', 0):.1f}%")
                print(f"  Memory: {resources.get('memory_percent', 0):.1f}%")
                print(f"  Disk: {resources.get('disk_percent', 0):.1f}%")
                if 'load_avg' in resources:
                    load = resources['load_avg']
                    print(f"  Load Average: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
        
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error getting system status: {e}")
            sys.exit(1)
    
    def check_service(self, service_name: str) -> None:
        """Check status of a specific service"""
        try:
            service_info = self.monitor.check_service(service_name)
            
            if self.json_output:
                # Convert to dict for JSON output
                service_dict = {
                    'name': service_info.name,
                    'status': service_info.status.value,
                    'pid': service_info.pid,
                    'memory_mb': service_info.memory_mb,
                    'cpu_percent': service_info.cpu_percent,
                    'uptime': service_info.uptime,
                    'config_files': service_info.config_files
                }
                self.print_output(service_dict, f"Service {service_name}")
                return
            
            print(f"\n=== Service: {service_name} ===")
            
            # Status with indicator
            status_symbols = {
                'running': '🟢 RUNNING',
                'stopped': '🔴 STOPPED',
                'failed': '🟠 FAILED',
                'unknown': '❓ UNKNOWN'
            }
            status_display = status_symbols.get(service_info.status.value, service_info.status.value)
            print(f"Status: {status_display}")
            
            if service_info.pid:
                print(f"Process ID: {service_info.pid}")
                print(f"Memory Usage: {service_info.memory_mb:.1f} MB")
                print(f"CPU Usage: {service_info.cpu_percent:.1f}%")
                if service_info.uptime:
                    print(f"Uptime: {service_info.uptime}")
            
            print(f"Configuration Files:")
            for config_file in service_info.config_files:
                exists = "✓" if os.path.exists(config_file) else "✗"
                print(f"  {exists} {config_file}")
            
            # Show any recent alerts for this service
            recent_alerts = self.monitor.get_recent_alerts(hours=1)
            service_alerts = [a for a in recent_alerts if a['service'] == service_name]
            
            if service_alerts:
                print(f"\nRecent Alerts ({len(service_alerts)}):")
                for alert in service_alerts[:3]:  # Show last 3
                    level_symbol = {
                        'info': 'ℹ️',
                        'warning': '⚠️',
                        'error': '❌',
                        'critical': '🚨'
                    }.get(alert['level'], '•')
                    timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%H:%M:%S')
                    print(f"  {level_symbol} [{timestamp}] {alert['message']}")
        
        except ValueError as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ {e}")
                print(f"Available services: {', '.join(self.monitor.CRITICAL_SERVICES.keys())}")
            sys.exit(1)
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error checking service {service_name}: {e}")
            sys.exit(1)
    
    def show_resources(self) -> None:
        """Display system resource usage"""
        try:
            resources = self.monitor.get_system_resources()
            
            if self.json_output:
                resource_dict = {
                    'cpu_percent': resources.cpu_percent,
                    'memory_percent': resources.memory_percent,
                    'disk_percent': resources.disk_percent,
                    'load_avg': resources.load_avg,
                    'uptime': resources.uptime
                }
                self.print_output(resource_dict, "System Resources")
                return
            
            print("\n=== System Resources ===")
            
            # CPU
            cpu_status = "🔴" if resources.cpu_percent >= 95 else "🟡" if resources.cpu_percent >= 80 else "🟢"
            print(f"CPU Usage: {cpu_status} {resources.cpu_percent:.1f}%")
            
            # Memory
            mem_status = "🔴" if resources.memory_percent >= 95 else "🟡" if resources.memory_percent >= 85 else "🟢"
            print(f"Memory Usage: {mem_status} {resources.memory_percent:.1f}%")
            
            # Disk
            disk_status = "🔴" if resources.disk_percent >= 95 else "🟡" if resources.disk_percent >= 85 else "🟢"
            print(f"Disk Usage: {disk_status} {resources.disk_percent:.1f}%")
            
            # Load average
            print(f"Load Average: {resources.load_avg[0]:.2f}, {resources.load_avg[1]:.2f}, {resources.load_avg[2]:.2f}")
            print(f"System Uptime: {resources.uptime}")
            
            # Show thresholds
            print(f"\nThresholds:")
            print(f"  🟢 Normal  🟡 Warning (80%+)  🔴 Critical (95%+)")
        
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error getting system resources: {e}")
            sys.exit(1)
    
    def show_configs(self) -> None:
        """Display configuration validation results"""
        try:
            config_results = self.monitor.validate_configs()
            
            if self.json_output:
                self.print_output(config_results, "Configuration Validation")
                return
            
            print("\n=== Configuration Validation ===")
            
            valid_count = sum(1 for result in config_results.values() if result)
            total_count = len(config_results)
            
            print(f"Status: {valid_count}/{total_count} configurations valid")
            
            for config_path, is_valid in config_results.items():
                status_symbol = "✓" if is_valid else "✗"
                status_color = "🟢" if is_valid else "🔴"
                print(f"  {status_color} {status_symbol} {config_path}")
            
            # Show recent config-related alerts
            recent_alerts = self.monitor.get_recent_alerts(hours=24)
            config_alerts = [a for a in recent_alerts 
                           if 'config' in a['message'].lower() or 'configuration' in a['message'].lower()]
            
            if config_alerts:
                print(f"\nRecent Configuration Alerts:")
                for alert in config_alerts[:5]:
                    level_symbol = {
                        'info': 'ℹ️',
                        'warning': '⚠️',
                        'error': '❌',
                        'critical': '🚨'
                    }.get(alert['level'], '•')
                    timestamp = datetime.fromisoformat(alert['timestamp']).strftime('%m-%d %H:%M')
                    print(f"  {level_symbol} [{timestamp}] {alert['service']}: {alert['message']}")
        
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error validating configurations: {e}")
            sys.exit(1)
    
    def show_alertlog(self, hours: int = 24, level: Optional[str] = None) -> None:
        """Display recent alerts"""
        try:
            # Convert string level to enum if provided
            alert_level = None
            if level:
                try:
                    alert_level = AlertLevel(level.lower())
                except ValueError:
                    valid_levels = [l.value for l in AlertLevel]
                    if self.json_output:
                        self.print_output({"error": f"Invalid level. Use: {', '.join(valid_levels)}"}, "Error")
                    else:
                        print(f"❌ Invalid alert level '{level}'. Valid levels: {', '.join(valid_levels)}")
                    sys.exit(1)
            
            alerts = self.monitor.get_recent_alerts(hours=hours, level=alert_level)
            
            if self.json_output:
                self.print_output(alerts, "Alert Log")
                return
            
            level_filter = f" ({level.upper()})" if level else ""
            time_desc = "hour" if hours == 1 else f"{hours} hours"
            print(f"\n=== Alert Log{level_filter} - Last {time_desc} ===")
            
            if not alerts:
                print("No alerts found.")
                return
            
            print(f"Found {len(alerts)} alerts:")
            
            # Group alerts by level for summary
            level_counts = {}
            for alert in alerts:
                level_counts[alert['level']] = level_counts.get(alert['level'], 0) + 1
            
            print("Summary:")
            for alert_level_name, count in sorted(level_counts.items()):
                level_symbol = {
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'critical': '🚨'
                }.get(alert_level_name, '•')
                print(f"  {level_symbol} {alert_level_name.upper()}: {count}")
            
            print(f"\nRecent Alerts:")
            for i, alert in enumerate(alerts[:20]):  # Show last 20 alerts
                level_symbol = {
                    'info': 'ℹ️',
                    'warning': '⚠️',
                    'error': '❌',
                    'critical': '🚨'
                }.get(alert['level'], '•')
                
                timestamp = datetime.fromisoformat(alert['timestamp'])
                time_str = timestamp.strftime('%m-%d %H:%M:%S')
                
                print(f"{i+1:2d}. {level_symbol} [{time_str}] {alert['service']}: {alert['message']}")
                
                # Show details for critical alerts
                if alert['level'] == 'critical' and alert.get('details'):
                    for key, value in alert['details'].items():
                        if key != 'error':  # Skip error details in summary
                            print(f"     {key}: {value}")
            
            if len(alerts) > 20:
                print(f"\n... and {len(alerts) - 20} more alerts")
        
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error getting alerts: {e}")
            sys.exit(1)
    
    def clear_alerts(self, hours: Optional[int] = None) -> None:
        """Clear old alerts"""
        try:
            cleared_count = self.monitor.clear_alerts(hours)
            
            if self.json_output:
                result = {
                    "cleared_count": cleared_count,
                    "hours": hours
                }
                self.print_output(result, "Clear Alerts")
                return
            
            if hours:
                print(f"✓ Cleared {cleared_count} alerts older than {hours} hours")
            else:
                print(f"✓ Cleared all {cleared_count} alerts")
        
        except Exception as e:
            if self.json_output:
                self.print_output({"error": str(e)}, "Error")
            else:
                print(f"❌ Error clearing alerts: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LNMT Health Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  healthctl.py --status                    # Show overall system status
  healthctl.py --check dnsmasq             # Check dnsmasq service
  healthctl.py --check pihole              # Check Pi-hole service
  healthctl.py --resources                 # Show resource usage
  healthctl.py --configs                   # Validate configurations
  healthctl.py --alertlog                  # Show alerts from last 24 hours
  healthctl.py --alertlog --hours 6        # Show alerts from last 6 hours
  healthctl.py --alertlog --level critical # Show only critical alerts
  healthctl.py --status --json             # Output in JSON format
  healthctl.py --clear-alerts --hours 48   # Clear alerts older than 48 hours
        """
    )
    
    # Main action arguments (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--status', action='store_true',
                             help='Show overall system health status')
    action_group.add_argument('--check', metavar='SERVICE',
                             help='Check specific service (dnsmasq, pihole, unbound, shorewall)')
    action_group.add_argument('--resources', action='store_true',
                             help='Show system resource usage')
    action_group.add_argument('--configs', action='store_true',
                             help='Validate configuration files')
    action_group.add_argument('--alertlog', action='store_true',
                             help='Show recent alerts')
    action_group.add_argument('--clear-alerts', action='store_true',
                             help='Clear old alerts')
    
    # Modifier arguments
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to look back for alerts (default: 24)')
    parser.add_argument('--level', choices=['info', 'warning', 'error', 'critical'],
                       help='Filter alerts by level')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Check if running as root for certain operations
    if os.geteuid() != 0 and not args.json:
        print("⚠️  Warning: Not running as root. Some checks may be limited.")
    
    try:
        cli = HealthCLI()
        cli.set_json_output(args.json)
        
        if args.status:
            cli.show_status()
        elif args.check:
            cli.check_service(args.check)
        elif args.resources:
            cli.show_resources()
        elif args.configs:
            cli.show_configs()
        elif args.alertlog:
            cli.show_alertlog(hours=args.hours, level=args.level)
        elif args.clear_alerts:
            cli.clear_alerts(hours=args.hours if args.hours != 24 else None)
    
    except KeyboardInterrupt:
        if not args.json:
            print("\n\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": f"Unexpected error: {e}"}, indent=2))
        else:
            print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()