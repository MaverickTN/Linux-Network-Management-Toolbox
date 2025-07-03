#!/usr/bin/env python3
"""
DNS Manager Test Suite and Integration Examples

This file contains unit tests and integration examples for the DNS Manager module.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sqlite3
from typing import List, Dict

# Assuming dns_manager.py is in services directory
from services.dns_manager import DNSManager


class TestDNSManager(unittest.TestCase):
    """Unit tests for DNS Manager."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "dnsmasq.d"
        self.backup_dir = Path(self.temp_dir) / "backups"
        
        # Create DNS manager instance
        self.dns_mgr = DNSManager(
            config_dir=str(self.config_dir),
            backup_dir=str(self.backup_dir)
        )
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_validate_device(self):
        """Test device validation."""
        # Valid device
        valid_device = {
            "hostname": "test-device",
            "mac": "aa:bb:cc:dd:ee:ff",
            "ip": "192.168.1.100"
        }
        is_valid, error = self.dns_mgr.validate_device(valid_device)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Invalid hostname
        invalid_hostname = {
            "hostname": "test device",  # Space not allowed
            "mac": "aa:bb:cc:dd:ee:ff",
            "ip": "192.168.1.100"
        }
        is_valid, error = self.dns_mgr.validate_device(invalid_hostname)
        self.assertFalse(is_valid)
        self.assertIn("hostname", error)
        
        # Invalid MAC
        invalid_mac = {
            "hostname": "test-device",
            "mac": "invalid-mac",
            "ip": "192.168.1.100"
        }
        is_valid, error = self.dns_mgr.validate_device(invalid_mac)
        self.assertFalse(is_valid)
        self.assertIn("MAC", error)
        
        # Invalid IP
        invalid_ip = {
            "hostname": "test-device",
            "mac": "aa:bb:cc:dd:ee:ff",
            "ip": "192.168.1.999"  # Invalid octet
        }
        is_valid, error = self.dns_mgr.validate_device(invalid_ip)
        self.assertFalse(is_valid)
        self.assertIn("IP", error)
    
    def test_normalize_mac(self):
        """Test MAC address normalization."""
        test_cases = [
            ("AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"),
            ("aa-bb-cc-dd-ee-ff", "aa:bb:cc:dd:ee:ff"),
            ("AABBCCDDEEFF", "aa:bb:cc:dd:ee:ff"),
            ("aa:BB:cc:DD:ee:FF", "aa:bb:cc:dd:ee:ff"),
        ]
        
        for input_mac, expected in test_cases:
            result = self.dns_mgr.normalize_mac(input_mac)
            self.assertEqual(result, expected)
    
    def test_write_and_list_reservations(self):
        """Test writing and reading reservations."""
        devices = [
            {"hostname": "laptop", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"},
            {"hostname": "printer", "mac": "11:22:33:44:55:66", "ip": "192.168.1.101"},
            {"hostname": "nas", "mac": "ab:cd:ef:12:34:56", "ip": "192.168.1.102"}
        ]
        
        # Write reservations
        self.dns_mgr.write_reservations(devices)
        
        # Verify file exists
        self.assertTrue(self.dns_mgr.reservations_path.exists())
        
        # Read back reservations
        read_devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(read_devices), 3)
        
        # Verify devices match (normalized MACs)
        for original, read in zip(devices, read_devices):
            self.assertEqual(original['hostname'], read['hostname'])
            self.assertEqual(original['ip'], read['ip'])
            self.assertEqual(
                self.dns_mgr.normalize_mac(original['mac']),
                self.dns_mgr.normalize_mac(read['mac'])
            )
    
    def test_duplicate_detection(self):
        """Test duplicate device detection."""
        devices = [
            {"hostname": "device1", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"},
            {"hostname": "device2", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.101"},  # Duplicate MAC
            {"hostname": "device3", "mac": "11:22:33:44:55:66", "ip": "192.168.1.100"},  # Duplicate IP
            {"hostname": "device1", "mac": "99:88:77:66:55:44", "ip": "192.168.1.102"},  # Duplicate hostname
        ]
        
        # Write reservations (should skip duplicates)
        self.dns_mgr.write_reservations(devices)
        
        # Read back - should only have first device
        read_devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(read_devices), 1)
        self.assertEqual(read_devices[0]['hostname'], 'device1')
    
    def test_add_remove_device(self):
        """Test adding and removing individual devices."""
        # Start with some devices
        initial_devices = [
            {"hostname": "laptop", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"},
            {"hostname": "printer", "mac": "11:22:33:44:55:66", "ip": "192.168.1.101"}
        ]
        self.dns_mgr.update_reservations(initial_devices)
        
        # Add a device
        self.dns_mgr.add_device("phone", "99:88:77:66:55:44", "192.168.1.102")
        devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(devices), 3)
        
        # Remove by hostname
        self.assertTrue(self.dns_mgr.remove_device("printer"))
        devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(devices), 2)
        
        # Remove by MAC
        self.assertTrue(self.dns_mgr.remove_device("99:88:77:66:55:44"))
        devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(devices), 1)
        
        # Remove by IP
        self.assertTrue(self.dns_mgr.remove_device("192.168.1.100"))
        devices = self.dns_mgr.list_reservations()
        self.assertEqual(len(devices), 0)
        
        # Try to remove non-existent device
        self.assertFalse(self.dns_mgr.remove_device("nonexistent"))
    
    def test_backup_functionality(self):
        """Test backup creation."""
        # No backup if no file exists
        backup_path = self.dns_mgr.backup_config()
        self.assertIsNone(backup_path)
        
        # Create initial config
        devices = [{"hostname": "test", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"}]
        self.dns_mgr.write_reservations(devices)
        
        # Create backup
        backup_path = self.dns_mgr.backup_config()
        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())
        
        # Verify backup content matches original
        with open(self.dns_mgr.reservations_path) as f:
            original_content = f.read()
        with open(backup_path) as f:
            backup_content = f.read()
        self.assertEqual(original_content, backup_content)


class DNSManagerIntegration:
    """
    Integration example showing how DNS Manager works with SQLite database
    for device tracking in the LNMT system.
    """
    
    def __init__(self, db_path: str = "lnmt_devices.db"):
        """Initialize integration with database."""
        self.db_path = db_path
        self.dns_mgr = DNSManager()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE NOT NULL,
                mac TEXT UNIQUE NOT NULL,
                ip TEXT UNIQUE NOT NULL,
                device_type TEXT,
                location TEXT,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dns_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                device_hostname TEXT,
                device_mac TEXT,
                device_ip TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user TEXT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def sync_dns_from_database(self) -> None:
        """Sync DNS reservations from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all active devices
        cursor.execute('''
            SELECT hostname, mac, ip FROM devices
            ORDER BY ip
        ''')
        
        devices = []
        for row in cursor.fetchall():
            devices.append({
                'hostname': row[0],
                'mac': row[1],
                'ip': row[2]
            })
        
        conn.close()
        
        # Update DNS reservations
        if devices:
            self.dns_mgr.update_reservations(devices)
            self._log_action('sync', details=f'Synced {len(devices)} devices from database')
    
    def add_device_with_tracking(self, hostname: str, mac: str, ip: str,
                                device_type: str = None, location: str = None) -> bool:
        """
        Add device to both database and DNS.
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Add to database
            cursor.execute('''
                INSERT INTO devices (hostname, mac, ip, device_type, location)
                VALUES (?, ?, ?, ?, ?)
            ''', (hostname, mac, ip, device_type, location))
            
            conn.commit()
            
            # Add to DNS
            self.dns_mgr.add_device(hostname, mac, ip)
            
            # Log action
            self._log_action('add', hostname, mac, ip, 
                           f'Added device: type={device_type}, location={location}')
            
            # Reload DNS service
            self.dns_mgr.reload_dnsmasq()
            
            return True
            
        except sqlite3.IntegrityError as e:
            print(f"Database error: {e}")
            return False
        except Exception as e:
            print(f"Error adding device: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def remove_device_with_tracking(self, identifier: str) -> bool:
        """
        Remove device from both database and DNS.
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find device in database
            cursor.execute('''
                SELECT hostname, mac, ip FROM devices
                WHERE hostname = ? OR mac = ? OR ip = ?
            ''', (identifier, identifier, identifier))
            
            device = cursor.fetchone()
            if not device:
                return False
            
            hostname, mac, ip = device
            
            # Remove from database
            cursor.execute('''
                DELETE FROM devices
                WHERE hostname = ? OR mac = ? OR ip = ?
            ''', (identifier, identifier, identifier))
            
            conn.commit()
            
            # Remove from DNS
            self.dns_mgr.remove_device(identifier)
            
            # Log action
            self._log_action('remove', hostname, mac, ip, f'Removed device')
            
            # Reload DNS service
            self.dns_mgr.reload_dnsmasq()
            
            return True
            
        except Exception as e:
            print(f"Error removing device: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _log_action(self, action: str, hostname: str = None, mac: str = None,
                    ip: str = None, details: str = None):
        """Log DNS management action to audit table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dns_audit_log (action, device_hostname, device_mac, device_ip, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (action, hostname, mac, ip, details))
        
        conn.commit()
        conn.close()
    
    def get_device_history(self, identifier: str) -> List[Dict]:
        """Get audit history for a device."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action, timestamp, details FROM dns_audit_log
            WHERE device_hostname = ? OR device_mac = ? OR device_ip = ?
            ORDER BY timestamp DESC
        ''', (identifier, identifier, identifier))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'action': row[0],
                'timestamp': row[1],
                'details': row[2]
            })
        
        conn.close()
        return history


# Example usage and integration tests
def example_usage():
    """Demonstrate DNS Manager usage with database integration."""
    print("=== DNS Manager Integration Example ===\n")
    
    # Initialize integration
    integration = DNSManagerIntegration(db_path="/tmp/lnmt_test.db")
    
    # Add some devices
    print("Adding devices...")
    devices = [
        ("workstation1", "aa:bb:cc:dd:ee:01", "192.168.1.101", "desktop", "office"),
        ("printer-hp", "aa:bb:cc:dd:ee:02", "192.168.1.102", "printer", "office"),
        ("nas-storage", "aa:bb:cc:dd:ee:03", "192.168.1.103", "nas", "server-room"),
        ("laptop-john", "aa:bb:cc:dd:ee:04", "192.168.1.104", "laptop", "mobile"),
    ]
    
    for hostname, mac, ip, device_type, location in devices:
        if integration.add_device_with_tracking(hostname, mac, ip, device_type, location):
            print(f"  ✓ Added {hostname}")
        else:
            print(f"  ✗ Failed to add {hostname}")
    
    # Sync from database
    print("\nSyncing DNS from database...")
    integration.sync_dns_from_database()
    
    # List current reservations
    print("\nCurrent DNS reservations:")
    for device in integration.dns_mgr.list_reservations():
        print(f"  {device['hostname']:<15} {device['mac']:<18} -> {device['ip']}")
    
    # Remove a device
    print("\nRemoving printer...")
    if integration.remove_device_with_tracking("printer-hp"):
        print("  ✓ Printer removed")
    
    # Show audit history
    print("\nAudit history for NAS:")
    history = integration.get_device_history("nas-storage")
    for entry in history:
        print(f"  {entry['timestamp']}: {entry['action']} - {entry['details']}")
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...\n")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration example
    print("\n" + "="*50 + "\n")
    example_usage()