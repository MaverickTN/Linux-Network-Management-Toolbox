#!/usr/bin/env python3
"""
DNS Manager Service Module for LNMT System

This module manages static DNS reservations for dnsmasq by maintaining
entries in /etc/dnsmasq.d/reservations.conf file.

Usage Example:
    from services.dns_manager import DNSManager
    
    # Initialize manager
    dns_mgr = DNSManager()
    
    # Add devices
    devices = [
        {"hostname": "laptop", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"},
        {"hostname": "printer", "mac": "11:22:33:44:55:66", "ip": "192.168.1.101"}
    ]
    dns_mgr.update_reservations(devices)
    
    # Get current reservations
    current = dns_mgr.list_reservations()
"""

import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sqlite3
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DNSManager:
    """Manages static DNS reservations for dnsmasq."""
    
    def __init__(self, config_dir: str = "/etc/dnsmasq.d", 
                 reservations_file: str = "reservations.conf",
                 backup_dir: str = "/var/backups/dnsmasq"):
        """
        Initialize DNS Manager.
        
        Args:
            config_dir: Directory containing dnsmasq config files
            reservations_file: Name of the reservations config file
            backup_dir: Directory for storing config backups
        """
        self.config_dir = Path(config_dir)
        self.reservations_path = self.config_dir / reservations_file
        self.backup_dir = Path(backup_dir)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate MAC address pattern
        self.mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        # Validate IP address pattern
        self.ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
        # Validate hostname pattern (RFC 1123)
        self.hostname_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$')
    
    def validate_device(self, device: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate device record format.
        
        Args:
            device: Dictionary with hostname, mac, and ip keys
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ['hostname', 'mac', 'ip']
        for field in required_fields:
            if field not in device:
                return False, f"Missing required field: {field}"
        
        # Validate hostname
        if not self.hostname_pattern.match(device['hostname']):
            return False, f"Invalid hostname format: {device['hostname']}"
        
        # Validate MAC address
        if not self.mac_pattern.match(device['mac']):
            return False, f"Invalid MAC address format: {device['mac']}"
        
        # Validate IP address
        if not self.ip_pattern.match(device['ip']):
            return False, f"Invalid IP address format: {device['ip']}"
        
        return True, None
    
    def normalize_mac(self, mac: str) -> str:
        """
        Normalize MAC address to lowercase with colons.
        
        Args:
            mac: MAC address string
            
        Returns:
            Normalized MAC address
        """
        # Remove any non-hex characters
        mac_clean = re.sub(r'[^0-9A-Fa-f]', '', mac)
        # Insert colons every 2 characters
        mac_parts = [mac_clean[i:i+2] for i in range(0, 12, 2)]
        return ':'.join(mac_parts).lower()
    
    def backup_config(self) -> Optional[Path]:
        """
        Create backup of current reservations config.
        
        Returns:
            Path to backup file or None if no existing config
        """
        if not self.reservations_path.exists():
            logger.info("No existing reservations config to backup")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"reservations_{timestamp}.conf"
        
        try:
            shutil.copy2(self.reservations_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def write_reservations(self, devices: List[Dict[str, str]]) -> None:
        """
        Write device reservations to dnsmasq config file.
        
        Args:
            devices: List of device dictionaries
        """
        # Validate all devices first
        for device in devices:
            is_valid, error = self.validate_device(device)
            if not is_valid:
                raise ValueError(f"Invalid device: {error}")
        
        # Create config content
        lines = [
            "# LNMT DNS Manager - Static DHCP Reservations",
            f"# Generated: {datetime.now().isoformat()}",
            "# Format: dhcp-host=<mac>,<ip>,<hostname>",
            ""
        ]
        
        # Sort devices by IP for readability
        sorted_devices = sorted(devices, key=lambda d: tuple(map(int, d['ip'].split('.'))))
        
        # Track duplicates
        seen_macs = set()
        seen_ips = set()
        seen_hostnames = set()
        
        for device in sorted_devices:
            mac = self.normalize_mac(device['mac'])
            ip = device['ip']
            hostname = device['hostname'].lower()
            
            # Check for duplicates
            if mac in seen_macs:
                logger.warning(f"Duplicate MAC address: {mac}")
                continue
            if ip in seen_ips:
                logger.warning(f"Duplicate IP address: {ip}")
                continue
            if hostname in seen_hostnames:
                logger.warning(f"Duplicate hostname: {hostname}")
                continue
            
            seen_macs.add(mac)
            seen_ips.add(ip)
            seen_hostnames.add(hostname)
            
            # Add reservation entry
            lines.append(f"dhcp-host={mac},{ip},{hostname}")
        
        # Write to file
        try:
            self.reservations_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.reservations_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')
            logger.info(f"Wrote {len(seen_macs)} reservations to {self.reservations_path}")
        except Exception as e:
            logger.error(f"Failed to write reservations: {e}")
            raise
    
    def update_reservations(self, devices: List[Dict[str, str]]) -> None:
        """
        Update reservations with backup and validation.
        
        Args:
            devices: List of device dictionaries
        """
        # Backup existing config
        backup_path = self.backup_config()
        
        try:
            # Write new reservations
            self.write_reservations(devices)
            
            # Test dnsmasq config
            if self.test_dnsmasq_config():
                logger.info("DNS configuration updated successfully")
            else:
                # Restore backup if test fails
                if backup_path:
                    shutil.copy2(backup_path, self.reservations_path)
                    logger.error("Config test failed, restored from backup")
                raise RuntimeError("dnsmasq configuration test failed")
                
        except Exception as e:
            # Restore backup on any error
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, self.reservations_path)
                logger.error(f"Error updating reservations, restored from backup: {e}")
            raise
    
    def test_dnsmasq_config(self) -> bool:
        """
        Test dnsmasq configuration validity.
        
        Returns:
            True if config is valid, False otherwise
        """
        try:
            result = subprocess.run(
                ['dnsmasq', '--test'],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("dnsmasq not found, skipping config test")
            return True
    
    def reload_dnsmasq(self) -> bool:
        """
        Reload dnsmasq service to apply changes.
        
        Returns:
            True if reload successful, False otherwise
        """
        try:
            # Try systemctl first
            result = subprocess.run(
                ['systemctl', 'reload', 'dnsmasq'],
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                logger.info("dnsmasq service reloaded")
                return True
            
            # Fallback to service command
            result = subprocess.run(
                ['service', 'dnsmasq', 'reload'],
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                logger.info("dnsmasq service reloaded")
                return True
            
            logger.error("Failed to reload dnsmasq service")
            return False
            
        except Exception as e:
            logger.error(f"Error reloading dnsmasq: {e}")
            return False
    
    def list_reservations(self) -> List[Dict[str, str]]:
        """
        Read and parse current reservations.
        
        Returns:
            List of device dictionaries
        """
        devices = []
        
        if not self.reservations_path.exists():
            return devices
        
        try:
            with open(self.reservations_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse dhcp-host line
                    if line.startswith('dhcp-host='):
                        parts = line[10:].split(',')
                        if len(parts) >= 3:
                            devices.append({
                                'mac': parts[0],
                                'ip': parts[1],
                                'hostname': parts[2]
                            })
        except Exception as e:
            logger.error(f"Error reading reservations: {e}")
        
        return devices
    
    def add_device(self, hostname: str, mac: str, ip: str) -> None:
        """
        Add a single device to reservations.
        
        Args:
            hostname: Device hostname
            mac: MAC address
            ip: IP address
        """
        current_devices = self.list_reservations()
        
        # Check if device already exists
        mac_normalized = self.normalize_mac(mac)
        for device in current_devices:
            if self.normalize_mac(device['mac']) == mac_normalized:
                logger.warning(f"Device with MAC {mac} already exists")
                return
        
        # Add new device
        current_devices.append({
            'hostname': hostname,
            'mac': mac,
            'ip': ip
        })
        
        self.update_reservations(current_devices)
    
    def remove_device(self, identifier: str) -> bool:
        """
        Remove device by hostname, MAC, or IP.
        
        Args:
            identifier: Hostname, MAC address, or IP address
            
        Returns:
            True if device was removed, False if not found
        """
        current_devices = self.list_reservations()
        filtered_devices = []
        removed = False
        
        identifier_lower = identifier.lower()
        
        for device in current_devices:
            # Check if identifier matches any field
            if (device['hostname'].lower() == identifier_lower or
                self.normalize_mac(device['mac']) == self.normalize_mac(identifier) or
                device['ip'] == identifier):
                removed = True
                logger.info(f"Removing device: {device}")
            else:
                filtered_devices.append(device)
        
        if removed:
            self.update_reservations(filtered_devices)
        
        return removed


# Example test code
if __name__ == "__main__":
    # Example usage
    dns_mgr = DNSManager(
        config_dir="/tmp/dnsmasq.d",  # Use /tmp for testing
        backup_dir="/tmp/dnsmasq_backups"
    )
    
    # Test devices
    test_devices = [
        {"hostname": "laptop", "mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.100"},
        {"hostname": "printer", "mac": "11-22-33-44-55-66", "ip": "192.168.1.101"},
        {"hostname": "nas", "mac": "AB:CD:EF:12:34:56", "ip": "192.168.1.102"}
    ]
    
    # Update reservations
    print("Adding test devices...")
    dns_mgr.update_reservations(test_devices)
    
    # List current reservations
    print("\nCurrent reservations:")
    for device in dns_mgr.list_reservations():
        print(f"  {device['hostname']}: {device['mac']} -> {device['ip']}")
    
    # Add single device
    print("\nAdding single device...")
    dns_mgr.add_device("phone", "99:88:77:66:55:44", "192.168.1.103")
    
    # Remove device
    print("\nRemoving printer...")
    if dns_mgr.remove_device("printer"):
        print("  Printer removed")
    
    # Final list
    print("\nFinal reservations:")
    for device in dns_mgr.list_reservations():
        print(f"  {device['hostname']}: {device['mac']} -> {device['ip']}")
