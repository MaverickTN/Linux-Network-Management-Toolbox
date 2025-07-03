#!/usr/bin/env python3
"""
LNMT Report Control CLI
======================

Command-line interface for generating network usage reports using the LNMT reporting engine.

Usage:
    reportctl.py generate [options]
    reportctl.py devices [options]
    reportctl.py vlans [options]
    reportctl.py apps [options]
    reportctl.py --help

Examples:
    # Generate comprehensive 24-hour report
    reportctl.py generate --period 24 --format json --output daily_report.json
    
    # Show top devices for last 7 days
    reportctl.py devices --period 168 --limit 10
    
    # VLAN usage analysis
    reportctl.py vlans --period 24 --format text
    
    # Application usage breakdown
    reportctl.py apps --period 24 --exclude-whitelist
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import report_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.report_engine import ReportEngine, DNSClassifier
except ImportError:
    print("Error: Could not import report_engine. Please ensure it's in the services/ directory.")
    sys.exit(1)


class ReportCLI:
    """Command-line interface for the LNMT reporting engine."""
    
    def __init__(self, db_path: str = "network.db"):
        """Initialize CLI with database path."""
        self.db_path = db_path
        self.engine = None
    
    def _validate_db(self):
        """Validate that the database exists and is accessible."""
        if not os.path.exists(self.db_path):
            print(f"Error: Database file '{self.db_path}' not found.")
            print("Please ensure the LNMT tracker is running and has created the database.")
            sys.exit(1)
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"
    
    def _print_table(self, headers: list, rows: list, max_width: int = 80):
        """Print a formatted table."""
        if not rows:
            print("No data available.")
            return
        
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Print header
        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print(header_line)
        print("-" * len(header_line))
        
        # Print rows
        for row in rows:
            row_line = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
            print(row_line)
    
    def generate_report(self, args):
        """Generate a comprehensive usage report."""
        self._validate_db()
        
        try:
            with ReportEngine(self.db_path) as engine:
                print(f"Generating {args.period}-hour usage report...")
                
                report = engine.generate_comprehensive_report(
                    period_hours=args.period,
                    include_historical=args.include_historical
                )
                
                if args.output:
                    output_content = engine.export_report(report, args.format, args.output)
                    print(f"Report saved to: {args.output}")
                else:
                    output_content = engine.export_report(report, args.format)
                    if args.format.lower() == 'json':
                        print(output_content)
                    elif args.format.lower() == 'text':
                        print(output_content)
                    else:
                        print("HTML report generated. Use --output to save to file.")
                
                # Print summary to console regardless of format
                meta = report['report_metadata']
                stats = report['overall_stats']
                print(f"\nReport Summary:")
                print(f"Period: {args.period} hours")
                print(f"Total Sessions: {stats['total_sessions']:,}")
                print(f"Total Bandwidth: {self._format_bytes(stats['total_bytes'])}")
                print(f"Peak Usage Hour: {stats['peak_usage_hour']}:00")
                
        except Exception as e:
            print(f"Error generating report: {e}")
            sys.exit(1)
    
    def show_devices(self, args):
        """Show device usage statistics."""
        self._validate_db()
        
        try:
            with ReportEngine(self.db_path) as engine:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=args.period)
                
                print(f"Device usage for last {args.period} hours:")
                print()
                
                device_reports = engine.generate_device_reports(start_time, end_time)
                
                if not device_reports:
                    print("No device data found for the specified period.")
                    return
                
                # Limit results if specified
                if args.limit:
                    device_reports = device_reports[:args.limit]
                
                # Prepare table data
                headers = ["Device", "VLAN", "Bandwidth", "Sessions", "Top App"]
                rows = []
                
                for device in device_reports:
                    name = device.device_name or device.device_mac[:17]
                    vlan = f"VLAN {device.vlan_id}"
                    bandwidth = self._format_bytes(device.total_bandwidth)
                    sessions = str(device.session_count)
                    top_app = list(device.top_apps.keys())[0] if device.top_apps else "None"
                    
                    rows.append([name, vlan, bandwidth, sessions, top_app])
                
                self._print_table(headers, rows)
                
                if args.details:
                    print("\nDetailed Application Usage:")
                    for device in device_reports[:5]:  # Show details for top 5
                        name = device.device_name or device.device_mac
                        print(f"\n{name}:")
                        for app, bytes_used in device.top_apps.items():
                            print(f"  {app}: {self._format_bytes(bytes_used)}")
                
        except Exception as e:
            print(f"Error retrieving device data: {e}")
            sys.exit(1)
    
    def show_vlans(self, args):
        """Show VLAN usage statistics."""
        self._validate_db()
        
        try:
            with ReportEngine(self.db_path) as engine:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=args.period)
                
                print(f"VLAN usage for last {args.period} hours:")
                print()
                
                vlan_reports = engine.generate_vlan_reports(start_time, end_time)
                
                if not vlan_reports:
                    print("No VLAN data found for the specified period.")
                    return
                
                # Prepare table data
                headers = ["VLAN", "Devices", "Sessions", "Bandwidth", "Top Application"]
                rows = []
                
                for vlan in vlan_reports:
                    name = vlan.vlan_name or f"VLAN {vlan.vlan_id}"
                    devices = str(vlan.device_count)
                    sessions = str(vlan.session_count)
                    bandwidth = self._format_bytes(vlan.total_bandwidth)
                    top_app = list(vlan.top_applications.keys())[0] if vlan.top_applications else "None"
                    
                    rows.append([name, devices, sessions, bandwidth, top_app])
                
                self._print_table(headers, rows)
                
                if args.details:
                    print("\nTop Devices per VLAN:")
                    for vlan in vlan_reports:
                        name = vlan.vlan_name or f"VLAN {vlan.vlan_id}"
                        print(f"\n{name}:")
                        for device_mac, bandwidth in vlan.top_devices[:3]:
                            print(f"  {device_mac}: {self._format_bytes(bandwidth)}")
                
        except Exception as e:
            print(f"Error retrieving VLAN data: {e}")
            sys.exit(1)
    
    def show_applications(self, args):
        """Show application usage statistics."""
        self._validate_db()
        
        try:
            with ReportEngine(self.db_path) as engine:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=args.period)
                
                print(f"Application usage for last {args.period} hours:")
                print()
                
                sessions = engine.get_session_data(start_time, end_time)
                stats = engine.calculate_usage_stats(sessions)
                
                if not stats.top_applications:
                    print("No application data found for the specified period.")
                    return
                
                # Calculate percentages
                total_bytes = stats.total_bytes
                
                headers = ["Application", "Bandwidth", "Percentage"]
                rows = []
                
                for app, bytes_used in stats.top_applications.items():
                    percentage = (bytes_used / total_bytes * 100) if total_bytes > 0 else 0
                    rows.append([
                        app,
                        self._format_bytes(bytes_used),
                        f"{percentage:.1f}%"
                    ])
                
                self._print_table(headers, rows)
                
                # Show classification examples if requested
                if args.show_classification:
                    print("\nDNS Classification Examples:")
                    classifier = DNSClassifier()
                    
                    # Get unique hostnames from recent sessions
                    hostnames = set()
                    for session in sessions[:100]:  # Sample from recent sessions
                        if session.hostname:
                            hostnames.add(session.hostname)
                    
                    classification_examples = {}
                    for hostname in sorted(hostnames):
                        app = classifier.classify_hostname(hostname)
                        if app and app != 'Other':
                            if app not in classification_examples:
                                classification_examples[app] = []
                            if len(classification_examples[app]) < 3:
                                classification_examples[app].append(hostname)
                    
                    for app, examples in classification_examples.items():
                        print(f"  {app}: {', '.join(examples)}")
                
        except Exception as e:
            print(f"Error retrieving application data: {e}")
            sys.exit(1)
    
    def test_classifier(self, args):
        """Test the DNS classifier with custom hostnames."""
        classifier = DNSClassifier()
        
        test_hostnames = [
            "www.youtube.com",
            "facebook.com",
            "netflix.com",
            "windowsupdate.microsoft.com",
            "unknown-site.com",
            "googlevideo.com",
            "instagram.com"
        ]
        
        if args.hostname:
            test_hostnames = [args.hostname]
        
        print("DNS Classification Test:")
        print("-" * 40)
        
        for hostname in test_hostnames:
            classification = classifier.classify_hostname(hostname)
            is_whitelisted = classifier.is_whitelisted(hostname)
            
            status = "EXCLUDED" if is_whitelisted else "INCLUDED"
            app = classification or "WHITELISTED"
            
            print(f"{hostname:30} -> {app:15} ({status})")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LNMT Network Usage Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s generate --period 24 --format json --output daily.json
  %(prog)s devices --period 168 --limit 10 --details
  %(prog)s vlans --period 24 
  %(prog)s apps --period 72 --show-classification
  %(prog)s test-classifier --hostname www.youtube.com
        """
    )
    
    parser.add_argument(
        '--db', 
        default='network.db',
        help='Path to SQLite database (default: network.db)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate comprehensive usage report')
    gen_parser.add_argument('--period', type=int, default=24, help='Report period in hours (default: 24)')
    gen_parser.add_argument('--format', choices=['json', 'text', 'html'], default='text', help='Output format')
    gen_parser.add_argument('--output', '-o', help='Output file path')
    gen_parser.add_argument('--include-historical', action='store_true', help='Include historical comparison')
    
    # Devices command
    dev_parser = subparsers.add_parser('devices', help='Show device usage statistics')
    dev_parser.add_argument('--period', type=int, default=24, help='Analysis period in hours (default: 24)')
    dev_parser.add_argument('--limit', type=int, help='Limit number of devices shown')
    dev_parser.add_argument('--details', action='store_true', help='Show detailed application usage per device')
    
    # VLANs command
    vlan_parser = subparsers.add_parser('vlans', help='Show VLAN usage statistics')
    vlan_parser.add_argument('--period', type=int, default=24, help='Analysis period in hours (default: 24)')
    vlan_parser.add_argument('--details', action='store_true', help='Show top devices per VLAN')
    
    # Applications command
    app_parser = subparsers.add_parser('apps', help='Show application usage statistics')
    app_parser.add_argument('--period', type=int, default=24, help='Analysis period in hours (default: 24)')
    app_parser.add_argument('--show-classification', action='store_true', help='Show DNS classification examples')
    
    # Test classifier command
    test_parser = subparsers.add_parser('test-classifier', help='Test DNS hostname classification')
    test_parser.add_argument('--hostname', help='Test specific hostname classification')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = ReportCLI(db_path=args.db)
    
    # Route to appropriate command handler
    if args.command == 'generate':
        cli.generate_report(args)
    elif args.command == 'devices':
        cli.show_devices(args)
    elif args.command == 'vlans':
        cli.show_vlans(args)
    elif args.command == 'apps':
        cli.show_applications(args)
    elif args.command == 'test-classifier':
        cli.test_classifier(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()