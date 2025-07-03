#!/usr/bin/env python3
"""
LNMT Device Tracker Service
Monitors active network devices, tracks MAC/IP/hostname history,
and flags potential MAC randomization or new device events.

Example usage:
    python3 services/device_tracker.py
    
CLI usage:
    python3 cli/device_tracker_ctl.py list
    python3 cli/device_tracker_ctl.py history aa:bb:cc:dd:ee:ff
    python3 cli/device_tracker_ctl.py alerts
"""

import sqlite3
import time
import logging
import json
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import threading
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/lnmt/device_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('device_tracker')

@dataclass
class Device:
    """Represents a network device"""
    mac_address: str
    ip_address: str
    hostname: str
    first_seen: datetime
    last_seen: datetime
    lease_expires: Optional[datetime] = None
    vendor: Optional[str] = None
    device_type: Optional[str] = None
    is_randomized_mac: bool = False
    alert_flags: List[str] = None
    
    def __post_init__(self):
        if self.alert_flags is None:
            self.alert_flags = []

@dataclass
class DeviceEvent:
    """Represents a device-related event"""
    timestamp: datetime
    event_type: str  # 'new_device', 'mac_change', 'ip_change', 'hostname_change', 'randomized_mac'
    mac_address: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: str = ""

class MACAnalyzer:
    """Analyzes MAC addresses for randomization patterns"""
    
    # Known OUI prefixes for major vendors
    VENDOR_OUIS = {
        '00:50:56': 'VMware',
        '08:00:27': 'VirtualBox',
        '52:54:00': 'QEMU/KVM',
        'b8:27:eb': 'Raspberry Pi Foundation',
        'dc:a6:32': 'Raspberry Pi Trading',
        'e4:5f:01': 'Raspberry Pi Trading',
        '3c:22:fb': 'Apple',
        'f0:18:98': 'Apple',
        '68:96:7b': 'Apple',
        '70:56:81': 'Apple',
    }
    
    @staticmethod
    def is_randomized_mac(mac: str) -> bool:
        """
        Detect if MAC address appears to be randomized
        Randomized MACs often have:
        - Locally administered bit set (2nd bit of first octet)
        - Random patterns in lower octets
        """
        if not mac or len(mac) < 17:
            return False
            
        # Clean MAC address
        clean_mac = mac.replace(':', '').replace('-', '').lower()
        if len(clean_mac) != 12:
            return False
            
        first_octet = int(clean_mac[0:2], 16)
        
        # Check if locally administered bit is set (bit 1 of first octet)
        locally_administered = (first_octet & 0x02) != 0
        
        # Check if multicast bit is NOT set (bit 0 of first octet)
        not_multicast = (first_octet & 0x01) == 0
        
        # Randomized MACs are typically locally administered and unicast
        if locally_administered and not_multicast:
            # Additional heuristics for randomization
            oui = mac[:8].lower()
            if oui not in [k.lower() for k in MACAnalyzer.VENDOR_OUIS.keys()]:
                return True
                
        return False
    
    @staticmethod
    def get_vendor(mac: str) -> Optional[str]:
        """Get vendor from MAC OUI"""
        if not mac or len(mac) < 8:
            return None
            
        oui = mac[:8].upper()
        return MACAnalyzer.VENDOR_OUIS.get(oui)

class DeviceDatabase:
    """Manages SQLite database for device tracking"""
    
    def __init__(self, db_path: str = "/var/lib/lnmt/device_tracker.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_database()
        self._lock = threading.Lock()
    
    def _ensure_db_dir(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    mac_address TEXT PRIMARY KEY,
                    ip_address TEXT,
                    hostname TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    lease_expires TIMESTAMP,
                    vendor TEXT,
                    device_type TEXT,
                    is_randomized_mac BOOLEAN DEFAULT 0,
                    alert_flags TEXT DEFAULT '[]'
                );
                
                CREATE TABLE IF NOT EXISTS device_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac_address TEXT,
                    ip_address TEXT,
                    hostname TEXT,
                    timestamp TIMESTAMP,
                    lease_expires TIMESTAMP,
                    FOREIGN KEY (mac_address) REFERENCES devices (mac_address)
                );
                
                CREATE TABLE IF NOT EXISTS device_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    event_type TEXT,
                    mac_address TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    description TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_device_history_mac ON device_history(mac_address);
                CREATE INDEX IF NOT EXISTS idx_device_history_timestamp ON device_history(timestamp);
                CREATE INDEX IF NOT EXISTS idx_device_events_timestamp ON device_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_device_events_type ON device_events(event_type);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper locking"""
        with self._lock:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def get_device(self, mac_address: str) -> Optional[Device]:
        """Get device by MAC address"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM devices WHERE mac_address = ?", 
                (mac_address,)
            ).fetchone()
            
            if row:
                return Device(
                    mac_address=row['mac_address'],
                    ip_address=row['ip_address'],
                    hostname=row['hostname'],
                    first_seen=row['first_seen'],
                    last_seen=row['last_seen'],
                    lease_expires=row['lease_expires'],
                    vendor=row['vendor'],
                    device_type=row['device_type'],
                    is_randomized_mac=bool(row['is_randomized_mac']),
                    alert_flags=json.loads(row['alert_flags'] or '[]')
                )
        return None
    
    def save_device(self, device: Device):
        """Save or update device"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO devices 
                (mac_address, ip_address, hostname, first_seen, last_seen, 
                 lease_expires, vendor, device_type, is_randomized_mac, alert_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.mac_address, device.ip_address, device.hostname,
                device.first_seen, device.last_seen, device.lease_expires,
                device.vendor, device.device_type, device.is_randomized_mac,
                json.dumps(device.alert_flags)
            ))
    
    def add_history_entry(self, mac_address: str, ip_address: str, 
                         hostname: str, lease_expires: Optional[datetime] = None):
        """Add device history entry"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO device_history 
                (mac_address, ip_address, hostname, timestamp, lease_expires)
                VALUES (?, ?, ?, ?, ?)
            """, (mac_address, ip_address, hostname, datetime.now(), lease_expires))
    
    def add_event(self, event: DeviceEvent):
        """Add device event"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO device_events 
                (timestamp, event_type, mac_address, old_value, new_value, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp, event.event_type, event.mac_address,
                event.old_value, event.new_value, event.description
            ))
    
    def get_all_devices(self) -> List[Device]:
        """Get all devices"""
        devices = []
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
            for row in rows:
                devices.append(Device(
                    mac_address=row['mac_address'],
                    ip_address=row['ip_address'],
                    hostname=row['hostname'],
                    first_seen=row['first_seen'],
                    last_seen=row['last_seen'],
                    lease_expires=row['lease_expires'],
                    vendor=row['vendor'],
                    device_type=row['device_type'],
                    is_randomized_mac=bool(row['is_randomized_mac']),
                    alert_flags=json.loads(row['alert_flags'] or '[]')
                ))
        return devices
    
    def get_device_history(self, mac_address: str, days: int = 30) -> List[Dict]:
        """Get device history"""
        cutoff = datetime.now() - timedelta(days=days)
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM device_history 
                WHERE mac_address = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (mac_address, cutoff)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_recent_events(self, hours: int = 24) -> List[DeviceEvent]:
        """Get recent device events"""
        cutoff = datetime.now() - timedelta(hours=hours)
        events = []
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM device_events 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff,)).fetchall()
            
            for row in rows:
                events.append(DeviceEvent(
                    timestamp=row['timestamp'],
                    event_type=row['event_type'],
                    mac_address=row['mac_address'],
                    old_value=row['old_value'],
                    new_value=row['new_value'],
                    description=row['description']
                ))
        
        return events

class DHCPLeaseParser:
    """Parses DHCP lease files"""
    
    def __init__(self, lease_file: str = "/var/lib/misc/dnsmasq.leases"):
        self.lease_file = lease_file
    
    def parse_leases(self) -> List[Tuple[str, str, str, datetime]]:
        """
        Parse DHCP leases from dnsmasq.leases file
        Returns: List of (mac, ip, hostname, expires) tuples
        """
        leases = []
        
        try:
            if not Path(self.lease_file).exists():
                logger.warning(f"DHCP lease file not found: {self.lease_file}")
                return leases
                
            with open(self.lease_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # dnsmasq.leases format: timestamp mac ip hostname client-id
                    parts = line.split()
                    if len(parts) >= 4:
                        timestamp_str, mac, ip, hostname = parts[:4]
                        
                        # Convert timestamp
                        try:
                            expires = datetime.fromtimestamp(int(timestamp_str))
                        except (ValueError, OSError):
                            expires = datetime.now() + timedelta(hours=24)  # Default
                        
                        # Clean up hostname
                        if hostname == '*':
                            hostname = ''
                        
                        leases.append((mac.lower(), ip, hostname, expires))
                        
        except Exception as e:
            logger.error(f"Error parsing DHCP leases: {e}")
        
        return leases

class DeviceTracker:
    """Main device tracking service"""
    
    def __init__(self, lease_file: str = "/var/lib/misc/dnsmasq.leases"):
        self.db = DeviceDatabase()
        self.dhcp_parser = DHCPLeaseParser(lease_file)
        self.mac_analyzer = MACAnalyzer()
        self.running = False
        self.poll_interval = 30  # seconds
        
    def start(self):
        """Start the device tracking service"""
        self.running = True
        logger.info("Starting LNMT Device Tracker service")
        
        while self.running:
            try:
                self._poll_devices()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)
        
        logger.info("Device Tracker service stopped")
    
    def stop(self):
        """Stop the device tracking service"""
        self.running = False
    
    def _poll_devices(self):
        """Poll for active devices"""
        logger.debug("Polling for active devices")
        
        # Parse current DHCP leases
        leases = self.dhcp_parser.parse_leases()
        current_time = datetime.now()
        
        for mac, ip, hostname, expires in leases:
            self._process_device(mac, ip, hostname, expires, current_time)
    
    def _process_device(self, mac: str, ip: str, hostname: str, 
                       expires: datetime, current_time: datetime):
        """Process a single device"""
        # Get existing device
        existing_device = self.db.get_device(mac)
        
        # Add history entry
        self.db.add_history_entry(mac, ip, hostname, expires)
        
        if existing_device:
            # Update existing device
            self._update_existing_device(existing_device, mac, ip, hostname, expires, current_time)
        else:
            # New device
            self._process_new_device(mac, ip, hostname, expires, current_time)
    
    def _process_new_device(self, mac: str, ip: str, hostname: str, 
                          expires: datetime, current_time: datetime):
        """Process a new device"""
        logger.info(f"New device detected: {mac} ({ip}) - {hostname}")
        
        # Analyze MAC address
        is_randomized = self.mac_analyzer.is_randomized_mac(mac)
        vendor = self.mac_analyzer.get_vendor(mac)
        
        # Create device
        device = Device(
            mac_address=mac,
            ip_address=ip,
            hostname=hostname,
            first_seen=current_time,
            last_seen=current_time,
            lease_expires=expires,
            vendor=vendor,
            is_randomized_mac=is_randomized
        )
        
        # Add alerts
        if is_randomized:
            device.alert_flags.append('randomized_mac')
            logger.warning(f"Randomized MAC detected: {mac}")
        
        # Save device
        self.db.save_device(device)
        
        # Add event
        event = DeviceEvent(
            timestamp=current_time,
            event_type='new_device',
            mac_address=mac,
            description=f"New device: {hostname} ({ip})"
        )
        self.db.add_event(event)
    
    def _update_existing_device(self, device: Device, mac: str, ip: str, 
                              hostname: str, expires: datetime, current_time: datetime):
        """Update existing device"""
        events = []
        
        # Check for changes
        if device.ip_address != ip:
            events.append(DeviceEvent(
                timestamp=current_time,
                event_type='ip_change',
                mac_address=mac,
                old_value=device.ip_address,
                new_value=ip,
                description=f"IP changed from {device.ip_address} to {ip}"
            ))
            device.ip_address = ip
        
        if device.hostname != hostname:
            events.append(DeviceEvent(
                timestamp=current_time,
                event_type='hostname_change',
                mac_address=mac,
                old_value=device.hostname,
                new_value=hostname,
                description=f"Hostname changed from {device.hostname} to {hostname}"
            ))
            device.hostname = hostname
        
        # Update timestamps
        device.last_seen = current_time
        device.lease_expires = expires
        
        # Save device and events
        self.db.save_device(device)
        for event in events:
            self.db.add_event(event)
            logger.info(f"Device change: {event.description}")

    def get_device_status(self) -> Dict:
        """Get current device status summary"""
        devices = self.db.get_all_devices()
        current_time = datetime.now()
        
        active_devices = [d for d in devices if d.lease_expires and d.lease_expires > current_time]
        randomized_macs = [d for d in devices if d.is_randomized_mac]
        recent_events = self.db.get_recent_events(24)
        
        return {
            'total_devices': len(devices),
            'active_devices': len(active_devices),
            'randomized_macs': len(randomized_macs),
            'recent_events': len(recent_events),
            'last_scan': current_time.isoformat()
        }

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start tracker
    tracker = DeviceTracker()
    
    try:
        tracker.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
