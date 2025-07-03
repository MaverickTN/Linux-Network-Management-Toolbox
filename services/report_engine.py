#!/usr/bin/env python3
"""
LNMT Report Engine
==================

A comprehensive reporting engine for analyzing bandwidth, application usage,
and session data across VLANs, hosts, and devices.

Features:
- SQLite database queries for bandwidth and session data
- DNS-based application classification
- Per-VLAN and per-device usage analysis
- Multiple export formats (text, JSON, HTML)
- DNS whitelist support for filtering OS updates/telemetry
- Rolling time period analysis (24h, 14d, custom ranges)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Represents a network session record."""
    session_id: str
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    bytes_sent: int
    bytes_received: int
    duration: float
    hostname: Optional[str] = None
    vlan_id: Optional[int] = None
    device_mac: Optional[str] = None


@dataclass
class UsageStats:
    """Statistics for bandwidth and session usage."""
    total_bytes: int
    total_sessions: int
    avg_session_duration: float
    top_applications: Dict[str, int]
    peak_usage_hour: int
    bytes_sent: int
    bytes_received: int


@dataclass
class DeviceReport:
    """Per-device usage report."""
    device_mac: str
    device_name: Optional[str]
    vlan_id: int
    total_bandwidth: int
    session_count: int
    top_apps: Dict[str, int]
    first_seen: datetime
    last_seen: datetime


@dataclass
class VLANReport:
    """Per-VLAN usage report."""
    vlan_id: int
    vlan_name: Optional[str]
    total_bandwidth: int
    device_count: int
    session_count: int
    top_devices: List[Tuple[str, int]]  # (mac, bandwidth)
    top_applications: Dict[str, int]


class DNSClassifier:
    """Classifies network traffic based on DNS hostnames and patterns."""
    
    def __init__(self):
        # Application classification patterns
        self.app_patterns = {
            'YouTube': [
                r'.*youtube\.com$',
                r'.*googlevideo\.com$',
                r'.*ytimg\.com$'
            ],
            'Facebook': [
                r'.*facebook\.com$',
                r'.*fbcdn\.net$',
                r'.*instagram\.com$',
                r'.*whatsapp\.com$'
            ],
            'Netflix': [
                r'.*netflix\.com$',
                r'.*nflximg\.net$',
                r'.*nflxvideo\.net$'
            ],
            'Microsoft': [
                r'.*microsoft\.com$',
                r'.*live\.com$',
                r'.*outlook\.com$',
                r'.*office\.com$'
            ],
            'Apple': [
                r'.*apple\.com$',
                r'.*icloud\.com$',
                r'.*itunes\.com$'
            ],
            'Google': [
                r'.*google\.com$',
                r'.*googleapis\.com$',
                r'.*gstatic\.com$'
            ],
            'Gaming': [
                r'.*steam.*\.com$',
                r'.*battle\.net$',
                r'.*epicgames\.com$',
                r'.*xbox\.com$',
                r'.*playstation\.com$'
            ],
            'CDN': [
                r'.*cloudflare\.com$',
                r'.*amazonaws\.com$',
                r'.*akamai\.net$',
                r'.*fastly\.com$'
            ]
        }
        
        # DNS whitelist for OS updates and telemetry (to be excluded)
        self.whitelist_patterns = [
            r'.*\.windowsupdate\.com$',
            r'.*\.update\.microsoft\.com$',
            r'.*telemetry.*\.microsoft\.com$',
            r'.*\.apple\.com$',  # Many Apple services are updates/telemetry
            r'.*swscan\.apple\.com$',
            r'.*swdownload\.apple\.com$',
            r'.*ubuntu\.com$',
            r'.*canonical\.com$',
            r'.*fedoraproject\.org$',
            r'.*centos\.org$'
        ]
    
    def classify_hostname(self, hostname: str) -> Optional[str]:
        """Classify a hostname into an application category."""
        if not hostname:
            return 'Unknown'
            
        hostname = hostname.lower().strip()
        
        # Check whitelist first (return None to exclude)
        for pattern in self.whitelist_patterns:
            if re.match(pattern, hostname):
                return None
        
        # Check application patterns
        for app_name, patterns in self.app_patterns.items():
            for pattern in patterns:
                if re.match(pattern, hostname):
                    return app_name
        
        return 'Other'
    
    def is_whitelisted(self, hostname: str) -> bool:
        """Check if hostname should be excluded from reports."""
        return self.classify_hostname(hostname) is None


class ReportEngine:
    """Main reporting engine for network usage analysis."""
    
    def __init__(self, db_path: str):
        """Initialize the report engine with database connection."""
        self.db_path = db_path
        self.classifier = DNSClassifier()
        self.conn = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def _execute_query(self, query: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """Execute a database query and return results."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_session_data(self, 
                        start_time: datetime, 
                        end_time: datetime,
                        vlan_id: Optional[int] = None,
                        device_mac: Optional[str] = None) -> List[SessionData]:
        """Query session data from the database."""
        
        base_query = """
        SELECT 
            s.session_id,
            s.timestamp,
            s.src_ip,
            s.dst_ip,
            s.src_port,
            s.dst_port,
            s.protocol,
            s.bytes_sent,
            s.bytes_received,
            s.duration,
            d.hostname,
            d.vlan_id,
            d.mac_address as device_mac
        FROM sessions s
        LEFT JOIN dns_records d ON s.dst_ip = d.ip_address
        LEFT JOIN devices dev ON s.src_ip = dev.ip_address
        WHERE s.timestamp BETWEEN ? AND ?
        """
        
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if vlan_id is not None:
            base_query += " AND d.vlan_id = ?"
            params.append(vlan_id)
        
        if device_mac:
            base_query += " AND dev.mac_address = ?"
            params.append(device_mac)
        
        base_query += " ORDER BY s.timestamp DESC"
        
        rows = self._execute_query(base_query, tuple(params))
        
        sessions = []
        for row in rows:
            # Skip whitelisted hostnames
            if row['hostname'] and self.classifier.is_whitelisted(row['hostname']):
                continue
                
            session = SessionData(
                session_id=row['session_id'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                src_ip=row['src_ip'],
                dst_ip=row['dst_ip'],
                src_port=row['src_port'],
                dst_port=row['dst_port'],
                protocol=row['protocol'],
                bytes_sent=row['bytes_sent'] or 0,
                bytes_received=row['bytes_received'] or 0,
                duration=row['duration'] or 0.0,
                hostname=row['hostname'],
                vlan_id=row['vlan_id'],
                device_mac=row['device_mac']
            )
            sessions.append(session)
        
        return sessions
    
    def calculate_usage_stats(self, sessions: List[SessionData]) -> UsageStats:
        """Calculate usage statistics from session data."""
        if not sessions:
            return UsageStats(0, 0, 0.0, {}, 0, 0, 0)
        
        total_bytes = 0
        total_sessions = len(sessions)
        total_duration = 0.0
        bytes_sent = 0
        bytes_received = 0
        app_usage = defaultdict(int)
        hourly_usage = defaultdict(int)
        
        for session in sessions:
            session_bytes = session.bytes_sent + session.bytes_received
            total_bytes += session_bytes
            bytes_sent += session.bytes_sent
            bytes_received += session.bytes_received
            total_duration += session.duration
            
            # Classify application
            app_name = self.classifier.classify_hostname(session.hostname)
            if app_name:
                app_usage[app_name] += session_bytes
            
            # Track hourly usage
            hour = session.timestamp.hour
            hourly_usage[hour] += session_bytes
        
        avg_duration = total_duration / total_sessions if total_sessions > 0 else 0.0
        peak_hour = max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else 0
        
        # Sort applications by usage
        top_apps = dict(sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return UsageStats(
            total_bytes=total_bytes,
            total_sessions=total_sessions,
            avg_session_duration=avg_duration,
            top_applications=top_apps,
            peak_usage_hour=peak_hour,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received
        )
    
    def generate_device_reports(self, 
                              start_time: datetime, 
                              end_time: datetime) -> List[DeviceReport]:
        """Generate per-device usage reports."""
        
        query = """
        SELECT 
            d.mac_address,
            d.device_name,
            d.vlan_id,
            MIN(s.timestamp) as first_seen,
            MAX(s.timestamp) as last_seen,
            COUNT(s.session_id) as session_count,
            SUM(s.bytes_sent + s.bytes_received) as total_bandwidth
        FROM devices d
        LEFT JOIN sessions s ON d.ip_address = s.src_ip
        WHERE s.timestamp BETWEEN ? AND ?
        GROUP BY d.mac_address, d.device_name, d.vlan_id
        ORDER BY total_bandwidth DESC
        """
        
        rows = self._execute_query(query, (start_time.isoformat(), end_time.isoformat()))
        
        reports = []
        for row in rows:
            # Get detailed session data for this device
            device_sessions = self.get_session_data(
                start_time, end_time, device_mac=row['mac_address']
            )
            
            # Calculate top applications for this device
            app_usage = defaultdict(int)
            for session in device_sessions:
                app_name = self.classifier.classify_hostname(session.hostname)
                if app_name:
                    app_usage[app_name] += session.bytes_sent + session.bytes_received
            
            top_apps = dict(sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:5])
            
            report = DeviceReport(
                device_mac=row['mac_address'],
                device_name=row['device_name'],
                vlan_id=row['vlan_id'] or 0,
                total_bandwidth=row['total_bandwidth'] or 0,
                session_count=row['session_count'] or 0,
                top_apps=top_apps,
                first_seen=datetime.fromisoformat(row['first_seen']) if row['first_seen'] else start_time,
                last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else end_time
            )
            reports.append(report)
        
        return reports
    
    def generate_vlan_reports(self, 
                            start_time: datetime, 
                            end_time: datetime) -> List[VLANReport]:
        """Generate per-VLAN usage reports."""
        
        query = """
        SELECT 
            COALESCE(d.vlan_id, 0) as vlan_id,
            v.vlan_name,
            COUNT(DISTINCT d.mac_address) as device_count,
            COUNT(s.session_id) as session_count,
            SUM(s.bytes_sent + s.bytes_received) as total_bandwidth
        FROM sessions s
        LEFT JOIN devices d ON s.src_ip = d.ip_address
        LEFT JOIN vlans v ON d.vlan_id = v.vlan_id
        WHERE s.timestamp BETWEEN ? AND ?
        GROUP BY d.vlan_id, v.vlan_name
        ORDER BY total_bandwidth DESC
        """
        
        rows = self._execute_query(query, (start_time.isoformat(), end_time.isoformat()))
        
        reports = []
        for row in rows:
            vlan_id = row['vlan_id']
            
            # Get top devices for this VLAN
            device_query = """
            SELECT d.mac_address, SUM(s.bytes_sent + s.bytes_received) as bandwidth
            FROM devices d
            JOIN sessions s ON d.ip_address = s.src_ip
            WHERE d.vlan_id = ? AND s.timestamp BETWEEN ? AND ?
            GROUP BY d.mac_address
            ORDER BY bandwidth DESC
            LIMIT 5
            """
            
            device_rows = self._execute_query(
                device_query, 
                (vlan_id, start_time.isoformat(), end_time.isoformat())
            )
            top_devices = [(r['mac_address'], r['bandwidth']) for r in device_rows]
            
            # Get application usage for this VLAN
            vlan_sessions = self.get_session_data(start_time, end_time, vlan_id=vlan_id)
            app_usage = defaultdict(int)
            for session in vlan_sessions:
                app_name = self.classifier.classify_hostname(session.hostname)
                if app_name:
                    app_usage[app_name] += session.bytes_sent + session.bytes_received
            
            top_apps = dict(sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:10])
            
            report = VLANReport(
                vlan_id=vlan_id,
                vlan_name=row['vlan_name'],
                total_bandwidth=row['total_bandwidth'] or 0,
                device_count=row['device_count'] or 0,
                session_count=row['session_count'] or 0,
                top_devices=top_devices,
                top_applications=top_apps
            )
            reports.append(report)
        
        return reports
    
    def generate_comprehensive_report(self, 
                                    period_hours: int = 24,
                                    include_historical: bool = True) -> Dict[str, Any]:
        """Generate a comprehensive usage report."""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Get current period data
        sessions = self.get_session_data(start_time, end_time)
        current_stats = self.calculate_usage_stats(sessions)
        device_reports = self.generate_device_reports(start_time, end_time)
        vlan_reports = self.generate_vlan_reports(start_time, end_time)
        
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_start': start_time.isoformat(),
                'period_end': end_time.isoformat(),
                'period_hours': period_hours,
                'total_sessions_analyzed': len(sessions)
            },
            'overall_stats': asdict(current_stats),
            'device_reports': [asdict(dr) for dr in device_reports],
            'vlan_reports': [asdict(vr) for vr in vlan_reports]
        }
        
        # Add historical comparison if requested
        if include_historical and period_hours <= 24:
            historical_start = start_time - timedelta(hours=period_hours)
            historical_sessions = self.get_session_data(historical_start, start_time)
            historical_stats = self.calculate_usage_stats(historical_sessions)
            
            report['historical_comparison'] = {
                'previous_period_stats': asdict(historical_stats),
                'bandwidth_change_percent': self._calculate_change_percent(
                    historical_stats.total_bytes, current_stats.total_bytes
                ),
                'session_change_percent': self._calculate_change_percent(
                    historical_stats.total_sessions, current_stats.total_sessions
                )
            }
        
        return report
    
    def _calculate_change_percent(self, old_value: int, new_value: int) -> float:
        """Calculate percentage change between two values."""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return ((new_value - old_value) / old_value) * 100.0
    
    def export_report(self, 
                     report: Dict[str, Any], 
                     format_type: str = 'json',
                     output_file: Optional[str] = None) -> str:
        """Export report in specified format."""
        
        if format_type.lower() == 'json':
            output = json.dumps(report, indent=2, default=str)
        
        elif format_type.lower() == 'text':
            output = self._format_text_report(report)
        
        elif format_type.lower() == 'html':
            output = self._format_html_report(report)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            logger.info(f"Report exported to {output_file}")
        
        return output
    
    def _format_text_report(self, report: Dict[str, Any]) -> str:
        """Format report as human-readable text."""
        lines = []
        meta = report['report_metadata']
        stats = report['overall_stats']
        
        lines.append("=" * 60)
        lines.append("LNMT NETWORK USAGE REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {meta['generated_at']}")
        lines.append(f"Period: {meta['period_start']} to {meta['period_end']}")
        lines.append(f"Duration: {meta['period_hours']} hours")
        lines.append("")
        
        # Overall statistics
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 20)
        lines.append(f"Total Bandwidth: {self._format_bytes(stats['total_bytes'])}")
        lines.append(f"Total Sessions: {stats['total_sessions']:,}")
        lines.append(f"Average Session Duration: {stats['avg_session_duration']:.2f}s")
        lines.append(f"Peak Usage Hour: {stats['peak_usage_hour']}:00")
        lines.append(f"Data Sent: {self._format_bytes(stats['bytes_sent'])}")
        lines.append(f"Data Received: {self._format_bytes(stats['bytes_received'])}")
        lines.append("")
        
        # Top applications
        if stats['top_applications']:
            lines.append("TOP APPLICATIONS")
            lines.append("-" * 20)
            for app, bytes_used in stats['top_applications'].items():
                lines.append(f"{app}: {self._format_bytes(bytes_used)}")
            lines.append("")
        
        # VLAN reports
        if report['vlan_reports']:
            lines.append("VLAN USAGE SUMMARY")
            lines.append("-" * 20)
            for vlan in report['vlan_reports'][:10]:  # Top 10 VLANs
                name = vlan['vlan_name'] or f"VLAN {vlan['vlan_id']}"
                lines.append(f"{name}: {self._format_bytes(vlan['total_bandwidth'])} "
                           f"({vlan['device_count']} devices, {vlan['session_count']} sessions)")
            lines.append("")
        
        # Device reports  
        if report['device_reports']:
            lines.append("TOP DEVICES")
            lines.append("-" * 20)
            for device in report['device_reports'][:10]:  # Top 10 devices
                name = device['device_name'] or device['device_mac']
                lines.append(f"{name}: {self._format_bytes(device['total_bandwidth'])}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_html_report(self, report: Dict[str, Any]) -> str:
        """Format report as HTML (basic template for future web UI)."""
        meta = report['report_metadata']
        stats = report['overall_stats']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LNMT Network Usage Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
                .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LNMT Network Usage Report</h1>
                <p><strong>Generated:</strong> {meta['generated_at']}</p>
                <p><strong>Period:</strong> {meta['period_hours']} hours ({meta['period_start']} to {meta['period_end']})</p>
            </div>
            
            <div class="section">
                <h2>Overall Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <h3>Total Bandwidth</h3>
                        <p>{self._format_bytes(stats['total_bytes'])}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Total Sessions</h3>
                        <p>{stats['total_sessions']:,}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Peak Hour</h3>
                        <p>{stats['peak_usage_hour']}:00</p>
                    </div>
                </div>
            </div>
        """
        
        # Add top applications table
        if stats['top_applications']:
            html += """
            <div class="section">
                <h2>Top Applications</h2>
                <table>
                    <tr><th>Application</th><th>Bandwidth Used</th></tr>
            """
            for app, bytes_used in stats['top_applications'].items():
                html += f"<tr><td>{app}</td><td>{self._format_bytes(bytes_used)}</td></tr>"
            html += "</table></div>"
        
        html += "</body></html>"
        return html
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    def test_report_engine():
        """Test the report engine functionality."""
        
        # Initialize with a test database
        with ReportEngine("test_network.db") as engine:
            try:
                # Generate a 24-hour report
                report = engine.generate_comprehensive_report(period_hours=24)
                
                # Export in different formats
                json_output = engine.export_report(report, 'json', 'usage_report.json')
                text_output = engine.export_report(report, 'text', 'usage_report.txt')
                html_output = engine.export_report(report, 'html', 'usage_report.html')
                
                print("Report generation completed successfully!")
                print(f"JSON report length: {len(json_output)} characters")
                print(f"Text report length: {len(text_output)} characters")
                print(f"HTML report length: {len(html_output)} characters")
                
            except Exception as e:
                print(f"Test failed: {e}")
    
    # Run test if this file is executed directly
    test_report_engine()
