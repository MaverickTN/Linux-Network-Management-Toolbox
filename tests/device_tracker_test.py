#!/usr/bin/env python3
"""
LNMT Device Tracker Test and Example Code
Demonstrates usage and provides test cases for the device tracker module.

Run tests:
    python3 test_device_tracker.py

Run examples:
    python3 test_device_tracker.py --examples
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.device_tracker import (
    DeviceDatabase, DeviceTracker, MACAnalyzer, 
    DHCPLeaseParser, Device, DeviceEvent
)

class TestMACAnalyzer(unittest.TestCase):
    """Test MAC address analysis functionality"""
    
    def setUp(self):
        self.analyzer = MACAnalyzer()
    
    def test_randomized_mac_detection(self):
        """Test randomized MAC detection"""
        # Locally administered MACs (likely randomized)
        randomized_macs = [
            "02:00:00:00:00:01",  # Locally administered
            "06:12:34:56:78:9a",  # Locally administered
            "0a:bb:cc:dd:ee:ff",  # Locally administered
        ]
        
        for mac in randomized_macs:
            with self.subTest(mac=mac):
                self.assertTrue(self.analyzer.is_randomized_mac(mac))
    
    def test_vendor_mac_detection(self):
        """Test vendor MAC detection"""
        # Known vendor MACs (not randomized)
        vendor_macs = [
            "b8:27:eb:12:34:56",  # Raspberry Pi
            "3c:22:fb:ab:cd:ef",  # Apple
            "08:00:27:11:22:33",  # VirtualBox
        ]
        
        for mac in vendor_macs:
            with self.subTest(mac=mac):
                self.assertFalse(self.analyzer.is_randomized_mac(mac))
    
    def test_vendor_lookup(self):
        """Test vendor lookup"""
        test_cases = [
            ("b8:27:eb:12:34:56", "Raspberry Pi Foundation"),
            ("3c:22:fb:ab:cd:ef", "Apple"),
            ("08:00:27:11:22:33", "VirtualBox"),
            ("00:11:22:33:44:55", None),  # Unknown vendor
        ]
        
        for mac, expected_vendor in test_cases:
            with self.subTest(mac=mac):
                vendor = self.analyzer.get_vendor(mac)
                self.assertEqual(vendor, expected_vendor)

class TestDeviceDatabase(unittest.TestCase):
    """Test device database functionality"""
    
    def setUp(self):
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DeviceDatabase(self.temp_db.name)
    
    def tearDown(self):
        # Clean up temporary database
        os.unlink(self.temp_db.name)
    
    def test_device_crud_operations(self):
        """Test device CRUD operations"""
        # Create test device
        device = Device(
            mac_address="aa:bb:cc:dd:ee:ff",
            ip_address="192.168.1.100",
            hostname="test-device",
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            vendor="Test Vendor",
            is_randomized_mac=False,
            alert_flags=["test_flag"]
        )
        
        # Save device
        self.db.save_device(device)
        
        # Retrieve device
        retrieved = self.db.get_device("aa:bb:cc:dd:ee:ff")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.mac_address, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(retrieved.ip_address, "192.168.1.100")
        self.assertEqual(retrieved.hostname, "test-device")
        self.assertEqual(retrieved.vendor, "Test Vendor")
        self.assertFalse(retrieved.is_randomized_mac)
        self.assertEqual(retrieved.alert_flags, ["test_flag"])
        
        # Update device
        device.ip_address = "192.168.1.101"
        device.hostname = "updated-device"
        self.db.save_device(device)
        
        # Verify update
        updated = self.db.get_device("aa:bb:cc:dd:ee:ff")
        self.assertEqual(updated.ip_address, "192.168.1.101")
        self.assertEqual(updated.hostname, "updated-device")
    
    def test_device_history(self):
        """Test device history tracking"""
        mac = "aa:bb:cc:dd:ee:ff"
        
        # Add history entries
        self.db.add_history_entry(mac, "192.168.1.100", "device1")
        self.db.add_history_entry(mac, "192.168.1.101", "device1-updated")
        
        # Retrieve history
        history = self.db.get_device_history(mac)
        self.assertEqual(len(history), 2)
        
        # Verify order (newest first)
        self.assertEqual(history[0]['ip_address'], "192.168.1.101")
        self.assertEqual(history[1]['ip_address'], "192.168.1.100")
    
    def test_device_events(self):
        """Test device event logging"""
        event = DeviceEvent(
            timestamp=datetime.now(),
            event_type="new_device",
            mac_address="aa:bb:cc:dd:ee:ff",
            description="Test device detected"
        )
        
        # Add event
        self.db.add_event(event)
        
        # Retrieve events
        events = self.db.get_recent_events(24)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "new_device")
        self.assertEqual(events[0].mac_address, "aa:bb:cc:dd:ee:ff")

class TestDHCPLeaseParser(unittest.TestCase):
    """Test DHCP lease parsing"""
    
    def setUp(self):
        # Create temporary lease file
        self.temp_lease_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.leases')
        
        # Write sample lease data
        lease_data = """1625097600 aa:bb:cc:dd:ee:ff 192.168.1.100 device1 *
1625097700 11:22:33:44:55:66 192.168.1.101 device2 *
1625097800 ff:ee:dd:cc:bb:aa 192.168.1.102 * *
"""
        self.temp_lease_file.write(lease_data)
        self.temp_lease_file.close()
        
        self.parser = DHCPLeaseParser(self.temp_lease_file.name)
    
    def tearDown(self):
        os.unlink(self.temp_lease_file.name)
    
    def test_lease_parsing(self):
        """Test DHCP lease file parsing"""
        leases = self.parser.parse_leases()
        
        self.assertEqual(len(leases), 3)
        
        # Check first lease
        mac, ip, hostname, expires = leases[0]
        self.assertEqual(mac, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(ip, "192.168.1.100")
        self.assertEqual(hostname, "device1")
        
        # Check lease with no hostname
        mac, ip, hostname, expires = leases[2]
        self.assertEqual(mac, "ff:ee:dd:cc:bb:aa")
        self.assertEqual(ip, "192.168.1.102")
        self.assertEqual(hostname, "")  # Should be empty, not "*"

def create_sample_dhcp_leases():
    """Create sample DHCP lease file for demonstration"""
    lease_content = f"""
{int(datetime.now().timestamp()) + 3600} b8:27:eb:12:34:56 192.168.1.100 raspberry-pi *
{int(datetime.now().timestamp()) + 3600} 3c:22:fb:ab:cd:ef 192.168.1.101 johns-iphone *
{int(datetime.now().timestamp()) + 3600} 02:00:00:12:34:56 192.168.1.102 random-device *
{int(datetime.now().timestamp()) + 3600} 08:00:27:11:22:33 192.168.1.103 test-vm *
{int(datetime.now().timestamp()) + 3600} 06:aa:bb:cc:dd:ee 192.168.1.104 * *
""".strip()
    
    return lease_content

def run_examples():
    """Run example scenarios"""
    print("🔍 LNMT Device Tracker Examples")
    print("=" * 50)
    
    # Create temporary database and lease file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    temp_lease = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.leases')
    temp_lease.write(create_sample_dhcp_leases())
    temp_lease.close()
    
    try:
        # Initialize components
        db = DeviceDatabase(temp_db.name)
        tracker = DeviceTracker(temp_lease.name)
        analyzer = MACAnalyzer()
        
        print("\n1. Analyzing MAC addresses:")
        print("-" * 30)
        
        test_macs = [
            "b8:27:eb:12:34:56",  # Raspberry Pi
            "02:00:00:12:34:56",  # Randomized
            "3c:22:fb:ab:cd:ef",  # Apple
            "06:aa:bb:cc:dd:ee",  # Randomized
        ]
        
        for mac in test_macs:
            is_randomized = analyzer.is_randomized_mac(mac)
            vendor = analyzer.get_vendor(mac)
            print(f"  {mac} - Vendor: {vendor or 'Unknown':<20} Randomized: {'Yes' if is_randomized else 'No'}")
        
        print("\n2. Processing DHCP leases:")
        print("-" * 30)
        
        # Simulate one polling cycle
        tracker._poll_devices()
        
        # Show results
        devices = db.get_all_devices()
        print(f"  Discovered {len(devices)} devices")
        
        for device in devices:
            status = "🔍 New" if device.first_seen == device.last_seen else "📍 Updated"
            randomized = " [RANDOMIZED]" if device.is_randomized_mac else ""
            print(f"  {status} {device.mac_address} ({device.ip_address}) - {device.hostname or 'Unknown'}{randomized}")
        
        print("\n3. Device events:")
        print("-" * 30)
        
        events = db.get_recent_events(24)
        for event in events:
            print(f"  {event.timestamp.strftime('%H:%M:%S')} - {event.event_type}: {event.description}")
        
        print("\n4. Statistics:")
        print("-" * 30)
        
        total_devices = len(devices)
        randomized_count = len([d for d in devices if d.is_randomized_mac])
        vendor_devices = len([d for d in devices if d.vendor])
        
        print(f"  Total devices: {total_devices}")
        print(f"  Randomized MACs: {randomized_count}")
        print(f"  Known vendors: {vendor_devices}")
        print(f"  Recent events: {len(events)}")
        
        print("\n5. JSON export example:")
        print("-" * 30)
        
        # Export to JSON
        export_data = []
        for device in devices:
            export_data.append({
                'mac': device.mac_address,
                'ip': device.ip_address,
                'hostname': device.hostname,
                'vendor': device.vendor,
                'randomized': device.is_randomized_mac,
                'first_seen': device.first_seen.isoformat(),
                'last_seen': device.last_seen.isoformat()
            })
        
        print(json.dumps(export_data[:2], indent=2))  # Show first 2 devices
        if len(export_data) > 2:
            print(f"  ... and {len(export_data) - 2} more devices")
        
    finally:
        # Cleanup
        os.unlink(temp_db.name)
        os.unlink(temp_lease.name)
    
    print("\n✅ Examples completed!")
    print("\nTo use in production:")
    print("1. Ensure /var/lib/misc/dnsmasq.leases exists")
    print("2. Run: python3 services/device_tracker.py")
    print("3. Use: python3 cli/device_tracker_ctl.py list")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Device Tracker Test Suite')
    parser.add_argument('--examples', action='store_true', help='Run examples instead of tests')
    args = parser.parse_args()
    
    if args.examples:
        run_examples()
    else:
        # Run unit tests
        unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == "__main__":
    main()
