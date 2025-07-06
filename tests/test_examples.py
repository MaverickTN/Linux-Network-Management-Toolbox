#!/usr/bin/env python3
"""
LNMT Report Engine - Example Usage and Tests
============================================

This file demonstrates how to use the LNMT reporting engine and includes
test data generation for development and testing purposes.
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.report_engine import ReportEngine, DNSClassifier, SessionData


def create_test_database(db_path: str = "test_network.db"):
    """Create a test database with sample network data."""
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE sessions (
        session_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        src_ip TEXT NOT NULL,
        dst_ip TEXT NOT NULL,
        src_port INTEGER NOT NULL,
        dst_port INTEGER NOT NULL,
        protocol TEXT NOT NULL,
        bytes_sent INTEGER DEFAULT 0,
        bytes_received INTEGER DEFAULT 0,
        duration REAL DEFAULT 0.0
    )
    """)
    
    cursor.execute("""
    CREATE TABLE devices (
        mac_address TEXT PRIMARY KEY,
        ip_address TEXT NOT NULL,
        device_name TEXT,
        vlan_id INTEGER,
        first_seen TEXT,
        last_seen TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE dns_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        vlan_id INTEGER,
        timestamp TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE vlans (
        vlan_id INTEGER PRIMARY KEY,
        vlan_name TEXT NOT NULL,
        description TEXT
    )
    """)
    
    # Insert sample VLANs
    vlans_data = [
        (1, "Management", "Network management VLAN"),
        (10, "User Workstations", "Employee workstation network"),
        (20, "Guest Network", "Guest and visitor access"),
        (30, "IoT Devices", "Internet of Things devices"),
        (40, "Servers", "Internal server network")
    ]
    
    cursor.executemany("INSERT INTO vlans VALUES (?, ?, ?)", vlans_data)
    
    # Insert sample devices
    devices_data = [
        ("aa:bb:cc:dd:ee:01", "192.168.10.100", "Alice-Laptop", 10, "2025-06-30 08:00:00", "2025-07-01 17:30:00"),
        ("aa:bb:cc:dd:ee:02", "192.168.10.101", "Bob-Desktop", 10, "2025-06-30 09:00:00", "2025-07-01 18:00:00"),
        ("aa:bb:cc:dd:ee:03", "192.168.20.200", "Guest-Phone", 20, "2025-07-01 10:00:00", "2025-07-01 15:00:00"),
        ("aa:bb:cc:dd:ee:04", "192.168.30.300", "Smart-TV", 30, "2025-06-30 19:00:00", "2025-07-01 23:00:00"),
        ("aa:bb:cc:dd:ee:05", "192.168.40.400", "Web-Server", 40, "2025-06-30 00:00:00", "2025-07-01 23:59:59"),
    ]
    
    cursor.executemany("INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?)", devices_data)
    
    # Insert sample DNS records
    dns_data = [
        ("www.youtube.com", "142.250.191.78", 10, "2025-07-01 10:30:00"),
        ("facebook.com", "157.240.241.35", 10, "2025-07-01 11:00:00"),
        ("netflix.com", "54.230.216.132", 30, "2025-07-01 20:00:00"),
        ("googlevideo.com", "142.250.191.142", 10, "2025-07-01 10:31:00"),
        ("instagram.com", "157.240.241.174", 20, "2025-07-01 12:00:00"),
        ("microsoft.com", "20.112.52.29", 10, "2025-07-01 09:00:00"),
        ("windowsupdate.microsoft.com", "20.118.99.224", 10, "2025-07-01 03:00:00"),
        ("apple.com", "17.253.144.10", 10, "2025-07-01 08:00:00"),
        ("steamcontent.com", "23.56.172.200", 10, "2025-07-01 15:00:00"),
    ]
    
    cursor.executemany("INSERT INTO dns_records (hostname, ip_address, vlan_id, timestamp) VALUES (?, ?, ?, ?)", dns_data)
    
    # Generate sample session data
    import random
    
    session_data = []
    now = datetime.now()
    
    # Define some destination IPs and their associated services
    services = [
        ("142.250.191.78", "www.youtube.com", 443, 50000000),   # YouTube - high bandwidth
        ("157.240.241.35", "facebook.com", 443, 5000000),      # Facebook - medium bandwidth
        ("54.230.216.132", "netflix.com", 443, 100000000),     # Netflix - very high bandwidth
        ("20.112.52.29", "microsoft.com", 443, 2000000),       # Microsoft - low bandwidth
        ("20.118.99.224", "windowsupdate.microsoft.com", 443, 500000000),  # Windows Update - excluded
        ("23.56.172.200", "steamcontent.com", 443, 80000000),  # Steam - high bandwidth
    ]
    
    device_ips = ["192.168.10.100", "192.168.10.101", "192.168.20.200", "192.168.30.300"]
    
    session_id = 1
    
    # Generate sessions for the last 48 hours
    for hours_ago in range(48, 0, -1):
        session_time = now - timedelta(hours=hours_ago)
        
        # Generate random sessions for this hour
        num_sessions = random.randint(5, 20)
        
        for _ in range(num_sessions):
            src_ip = random.choice(device_ips)
            dst_ip, hostname, dst_port, base_bandwidth = random.choice(services)
            
            # Add some randomness to bandwidth
            bandwidth_variation = random.uniform(0.1, 2.0)
            total_bytes = int(base_bandwidth * bandwidth_variation)
            
            # Split between sent and received (typically more received)
            bytes_sent = int(total_bytes * random.uniform(0.05, 0.3))
            bytes_received = total_bytes - bytes_sent
            
            duration = random.uniform(10, 3600)  # 10 seconds to 1 hour
            
            # Add some timestamp variation within the hour
            minute_offset = random.randint(0, 59)
            second_offset = random.randint(0, 59)
            actual_time = session_time.replace(minute=minute_offset, second=second_offset)
            
            session_data.append((
                f"session_{session_id:06d}",
                actual_time.isoformat(),
                src_ip,
                dst_ip,
                random.randint(32768, 65535),  # Random source port
                dst_port,
                "TCP",
                bytes_sent,
                bytes_received,
                duration
            ))
            
            session_id += 1
    
    cursor.executemany("""
        INSERT INTO sessions 
        (session_id, timestamp, src_ip, dst_ip, src_port, dst_port, protocol, bytes_sent, bytes_received, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, session_data)
    
    conn.commit()
    conn.close()
    
    print(f"Test database created: {db_path}")
    print(f"Generated {len(session_data)} sample sessions")
    print(f"Devices: {len(devices_data)}")
    print(f"VLANs: {len(vlans_data)}")
    print(f"DNS records: {len(dns_data)}")


def test_dns_classifier():
    """Test the DNS classifier functionality."""
    print("\n" + "="*60)
    print("TESTING DNS CLASSIFIER")
    print("="*60)
    
    classifier = DNSClassifier()
    
    test_hostnames = [
        "www.youtube.com",
        "googlevideo.com",
        "facebook.com",
        "instagram.com",
        "netflix.com",
        "nflxvideo.net",
        "microsoft.com",
        "windowsupdate.microsoft.com",  # Should be whitelisted
        "apple.com",
        "swdownload.apple.com",  # Should be whitelisted
        "steamcontent.com",
        "unknown-domain.com",
        "cdn.example.com"
    ]
    
    print("Hostname Classification Results:")
    print("-" * 50)
    
    for hostname in test_hostnames:
        classification = classifier.classify_hostname(hostname)
        is_whitelisted = classifier.is_whitelisted(hostname)
        
        status = "EXCLUDED" if is_whitelisted else "INCLUDED"
        app = classification or "WHITELISTED"
        
        print(f"{hostname:35} -> {app:15} ({status})")


def test_report_generation():
    """Test the report generation functionality."""
    print("\n" + "="*60)
    print("TESTING REPORT GENERATION")
    print("="*60)
    
    db_path = "test_network.db"
    
    try:
        with ReportEngine(db_path) as engine:
            # Test 1: Generate comprehensive 24-hour report
            print("\n1. Generating 24-hour comprehensive report...")
            report_24h = engine.generate_comprehensive_report(period_hours=24)
            
            print(f"   Sessions analyzed: {report_24h['report_metadata']['total_sessions_analyzed']}")
            print(f"   Total bandwidth: {report_24h['overall_stats']['total_bytes']:,} bytes")
            print(f"   Total sessions: {report_24h['overall_stats']['total_sessions']}")
            print(f"   Peak hour: {report_24h['overall_stats']['peak_usage_hour']}:00")
            
            # Test 2: Generate device reports
            print("\n2. Generating device reports...")
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            device_reports = engine.generate_device_reports(start_time, end_time)
            
            print(f"   Devices found: {len(device_reports)}")
            for device in device_reports[:3]:  # Show top 3
                name = device.device_name or device.device_mac
                print(f"   {name}: {device.total_bandwidth:,} bytes, {device.session_count} sessions")
            
            # Test 3: Generate VLAN reports
            print("\n3. Generating VLAN reports...")
            vlan_reports = engine.generate_vlan_reports(start_time, end_time)
            
            print(f"   VLANs found: {len(vlan_reports)}")
            for vlan in vlan_reports[:3]:  # Show top 3
                name = vlan.vlan_name or f"VLAN {vlan.vlan_id}"
                print(f"   {name}: {vlan.total_bandwidth:,} bytes, {vlan.device_count} devices")
            
            # Test 4: Export in different formats
            print("\n4. Testing export formats...")
            
            # JSON export
            json_output = engine.export_report(report_24h, 'json', 'test_report.json')
            print(f"   JSON export: {len(json_output)} characters")
            
            # Text export  
            text_output = engine.export_report(report_24h, 'text', 'test_report.txt')
            print(f"   Text export: {len(text_output)} characters")
            
            # HTML export
            html_output = engine.export_report(report_24h, 'html', 'test_report.html')
            print(f"   HTML export: {len(html_output)} characters")
            
            print("\n   Export files created:")
            print("   - test_report.json")
            print("   - test_report.txt") 
            print("   - test_report.html")
            
            # Test 5: Show sample text output
            print("\n5. Sample text report output:")
            print("-" * 40)
            sample_text = engine.export_report(report_24h, 'text')
            print(sample_text[:500] + "..." if len(sample_text) > 500 else sample_text)
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_api_usage():
    """Demonstrate programmatic API usage."""
    print("\n" + "="*60)
    print("DEMONSTRATING API USAGE")
    print("="*60)
    
    db_path = "test_network.db"
    
    try:
        # Example 1: Custom time range analysis
        print("\n1. Custom time range analysis...")
        with ReportEngine(db_path) as engine:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=6)  # Last 6 hours
            
            sessions = engine.get_session_data(start_time, end_time)
            stats = engine.calculate_usage_stats(sessions)
            
            print(f"   Last 6 hours: {len(sessions)} sessions")
            print(f"   Total bandwidth: {stats.total_bytes:,} bytes")
            print("   Top applications:")
            for app, bandwidth in list(stats.top_applications.items())[:3]:
                print(f"     {app}: {bandwidth:,} bytes")
        
        # Example 2: Per-VLAN analysis
        print("\n2. Per-VLAN analysis...")
        with ReportEngine(db_path) as engine:
            for vlan_id in [10, 20, 30]:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=24)
                
                sessions = engine.get_session_data(start_time, end_time, vlan_id=vlan_id)
                stats = engine.calculate_usage_stats(sessions)
                
                print(f"   VLAN {vlan_id}: {len(sessions)} sessions, {stats.total_bytes:,} bytes")
        
        # Example 3: Building custom reports
        print("\n3. Building custom analytics...")
        with ReportEngine(db_path) as engine:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            all_sessions = engine.get_session_data(start_time, end_time)
            
            # Analyze traffic by hour
            hourly_traffic = {}
            for session in all_sessions:
                hour = session.timestamp.hour
                if hour not in hourly_traffic:
                    hourly_traffic[hour] = 0
                hourly_traffic[hour] += session.bytes_sent + session.bytes_received
            
            print("   Traffic by hour:")
            for hour in sorted(hourly_traffic.keys()):
                print(f"     {hour:02d}:00 - {hourly_traffic[hour]:,} bytes")
            
    except Exception as e:
        print(f"Error during API demonstration: {e}")


def cleanup_test_files():
    """Clean up test files."""
    test_files = [
        "test_network.db",
        "test_report.json",
        "test_report.txt",
        "test_report.html"
    ]
    
    print("\nCleaning up test files...")
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"Removed: {file}")


def main():
    """Run all tests and demonstrations."""
    print("LNMT Report Engine - Testing and Examples")
    print("=" * 60)
    
    try:
        # Create test database with sample data
        create_test_database()
        
        # Run tests
        test_dns_classifier()
        test_report_generation()
        demonstrate_api_usage()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\nNext steps:")
        print("1. Integrate with your actual network database")
        print("2. Customize DNS classification patterns")
        print("3. Set up automated report generation")
        print("4. Use the CLI tool: python cli/reportctl.py --help")
        
        # Ask if user wants to keep test files
        response = input("\nKeep test files for manual inspection? (y/N): ")
        if response.lower() != 'y':
            cleanup_test_files()
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        cleanup_test_files()
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
