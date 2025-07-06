#!/usr/bin/env python3
"""
LNMT TC/QoS Service Module
Traffic Control and Quality of Service management for Linux Network Management Toolbox

This module provides comprehensive traffic control functionality including:
- Interface detection and management
- Traffic shaping and policing
- QoS class and filter management
- Policy backup and restore
- Live monitoring and statistics

Author: LNMT Development Team
License: MIT
"""

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import re
import sqlite3
from contextlib import contextmanager
import yaml
import ipaddress

# Try to import pyroute2 for advanced networking
try:
    from pyroute2 import IPRoute, NetlinkError
    from pyroute2.netlink.rtnl import TC_H_ROOT, TC_H_INGRESS
    PYROUTE2_AVAILABLE = True
except ImportError:
    PYROUTE2_AVAILABLE = False

# Import LNMT database manager
try:
    from lnmt_db import DatabaseManager, DatabaseConfig
    LNMT_DB_AVAILABLE = True
except ImportError:
    LNMT_DB_AVAILABLE = False

@dataclass
class TCInterface:
    """Traffic Control Interface representation"""
    name: str
    index: int
    type: str  # ethernet, vlan, bridge, etc.
    state: str  # UP, DOWN
    mtu: int
    mac_address: str
    ip_addresses: List[str]
    parent_interface: Optional[str] = None
    vlan_id: Optional[int] = None
    speed: Optional[int] = None  # Mbps
    duplex: Optional[str] = None
    
    def __post_init__(self):
        if self.type == 'vlan' and self.vlan_id is None:
            # Extract VLAN ID from interface name
            if '.' in self.name:
                parts = self.name.split('.')
                if len(parts) == 2 and parts[1].isdigit():
                    self.vlan_id = int(parts[1])
                    self.parent_interface = parts[0]

@dataclass
class TCQdisc:
    """Traffic Control Queueing Discipline"""
    handle: str
    parent: str
    kind: str  # htb, pfifo_fast, fq_codel, etc.
    interface: str
    options: Dict[str, Any]
    created_at: datetime
    enabled: bool = True
    
    def to_tc_command(self) -> List[str]:
        """Convert to tc command arguments"""
        cmd = ['tc', 'qdisc', 'add', 'dev', self.interface]
        
        if self.parent == 'root':
            cmd.extend(['root', 'handle', self.handle])
        else:
            cmd.extend(['parent', self.parent, 'handle', self.handle])
        
        cmd.append(self.kind)
        
        # Add options
        for key, value in self.options.items():
            cmd.extend([key, str(value)])
        
        return cmd

@dataclass
class TCClass:
    """Traffic Control Class"""
    classid: str
    parent: str
    kind: str  # htb, etc.
    interface: str
    rate: str  # bandwidth rate
    ceil: str  # ceiling rate
    burst: Optional[str] = None
    cburst: Optional[str] = None
    prio: int = 0
    quantum: Optional[int] = None
    options: Dict[str, Any] = None
    created_at: datetime = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_tc_command(self) -> List[str]:
        """Convert to tc command arguments"""
        cmd = ['tc', 'class', 'add', 'dev', self.interface, 'parent', self.parent, 
               'classid', self.classid, self.kind]
        
        cmd.extend(['rate', self.rate])
        if self.ceil:
            cmd.extend(['ceil', self.ceil])
        if self.burst:
            cmd.extend(['burst', self.burst])
        if self.cburst:
            cmd.extend(['cburst', self.cburst])
        if self.prio:
            cmd.extend(['prio', str(self.prio)])
        if self.quantum:
            cmd.extend(['quantum', str(self.quantum)])
        
        # Add additional options
        for key, value in self.options.items():
            cmd.extend([key, str(value)])
        
        return cmd

@dataclass
class TCFilter:
    """Traffic Control Filter"""
    handle: str
    parent: str
    protocol: str  # ip, ipv6, etc.
    prio: int
    kind: str  # u32, fw, etc.
    interface: str
    match_criteria: Dict[str, Any]
    flowid: str  # target class
    action: Optional[str] = None
    created_at: datetime = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_tc_command(self) -> List[str]:
        """Convert to tc command arguments"""
        cmd = ['tc', 'filter', 'add', 'dev', self.interface, 'parent', self.parent,
               'protocol', self.protocol, 'prio', str(self.prio), self.kind]
        
        # Add match criteria
        for key, value in self.match_criteria.items():
            if key == 'src':
                cmd.extend(['match', 'ip', 'src', value])
            elif key == 'dst':
                cmd.extend(['match', 'ip', 'dst', value])
            elif key == 'sport':
                cmd.extend(['match', 'ip', 'sport', str(value), '0xffff'])
            elif key == 'dport':
                cmd.extend(['match', 'ip', 'dport', str(value), '0xffff'])
            elif key == 'protocol':
                cmd.extend(['match', 'ip', 'protocol', str(value), '0xff'])
            else:
                cmd.extend([key, str(value)])
        
        cmd.extend(['flowid', self.flowid])
        
        if self.action:
            cmd.extend(['action', self.action])
        
        return cmd

@dataclass
class TCPolicy:
    """Traffic Control Policy - Collection of qdiscs, classes, and filters"""
    name: str
    description: str
    interface: str
    qdiscs: List[TCQdisc]
    classes: List[TCClass]
    filters: List[TCFilter]
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class TCManager:
    """Traffic Control Manager - Core TC/QoS functionality"""
    
    def __init__(self, config_path: str = "/etc/lnmt/tc_config.json", 
                 db_manager: Optional[Any] = None):
        self.config_path = Path(config_path)
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize database
        self._init_database()
        
        # Initialize pyroute2 if available
        if PYROUTE2_AVAILABLE:
            try:
                self.ipr = IPRoute()
            except Exception as e:
                self.logger.warning(f"Failed to initialize pyroute2: {e}")
                self.ipr = None
        else:
            self.ipr = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load TC configuration"""
        default_config = {
            "tc_path": "/sbin/tc",
            "ip_path": "/sbin/ip",
            "backup_dir": "/var/lib/lnmt/tc_backups",
            "default_qdisc": "htb",
            "default_rates": {
                "ethernet": "1gbit",
                "vlan": "100mbit",
                "bridge": "1gbit"
            },
            "monitoring": {
                "enabled": True,
                "interval": 30,
                "history_retention": 7  # days
            },
            "safety": {
                "backup_before_apply": True,
                "rollback_timeout": 300,  # seconds
                "max_rollback_history": 10
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _init_database(self):
        """Initialize TC database tables"""
        if self.db_manager and hasattr(self.db_manager, 'sqlite_conn'):
            # Use existing LNMT database
            self.db_conn = self.db_manager.sqlite_conn
        else:
            # Create standalone database
            db_path = "/var/lib/lnmt/tc.db"
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
            self.db_conn.row_factory = sqlite3.Row
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create TC database tables"""
        schema = """
        -- TC Interfaces
        CREATE TABLE IF NOT EXISTS tc_interfaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            index_num INTEGER,
            type TEXT NOT NULL,
            state TEXT NOT NULL,
            mtu INTEGER,
            mac_address TEXT,
            ip_addresses TEXT,
            parent_interface TEXT,
            vlan_id INTEGER,
            speed INTEGER,
            duplex TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- TC Policies
        CREATE TABLE IF NOT EXISTS tc_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            interface TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- TC Qdiscs
        CREATE TABLE IF NOT EXISTS tc_qdiscs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            handle TEXT NOT NULL,
            parent TEXT NOT NULL,
            kind TEXT NOT NULL,
            interface TEXT NOT NULL,
            options TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES tc_policies(id)
        );
        
        -- TC Classes
        CREATE TABLE IF NOT EXISTS tc_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            classid TEXT NOT NULL,
            parent TEXT NOT NULL,
            kind TEXT NOT NULL,
            interface TEXT NOT NULL,
            rate TEXT NOT NULL,
            ceil TEXT,
            burst TEXT,
            cburst TEXT,
            prio INTEGER DEFAULT 0,
            quantum INTEGER,
            options TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES tc_policies(id)
        );
        
        -- TC Filters
        CREATE TABLE IF NOT EXISTS tc_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id INTEGER,
            handle TEXT NOT NULL,
            parent TEXT NOT NULL,
            protocol TEXT NOT NULL,
            prio INTEGER NOT NULL,
            kind TEXT NOT NULL,
            interface TEXT NOT NULL,
            match_criteria TEXT,
            flowid TEXT NOT NULL,
            action TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES tc_policies(id)
        );
        
        -- TC Statistics
        CREATE TABLE IF NOT EXISTS tc_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interface TEXT NOT NULL,
            classid TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0,
            packets_sent INTEGER DEFAULT 0,
            packets_received INTEGER DEFAULT 0,
            drops INTEGER DEFAULT 0,
            overlimits INTEGER DEFAULT 0,
            requeues INTEGER DEFAULT 0,
            backlog INTEGER DEFAULT 0,
            qlen INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- TC Rollback History
        CREATE TABLE IF NOT EXISTS tc_rollback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_name TEXT NOT NULL,
            interface TEXT NOT NULL,
            backup_data TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rolled_back_at TIMESTAMP,
            status TEXT DEFAULT 'active'
        );
        
        -- TC Configuration
        CREATE TABLE IF NOT EXISTS tc_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Triggers for updated_at
        CREATE TRIGGER IF NOT EXISTS update_tc_interfaces_timestamp 
            AFTER UPDATE ON tc_interfaces
            BEGIN
                UPDATE tc_interfaces SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_tc_policies_timestamp 
            AFTER UPDATE ON tc_policies
            BEGIN
                UPDATE tc_policies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        
        CREATE TRIGGER IF NOT EXISTS update_tc_config_timestamp 
            AFTER UPDATE ON tc_config
            BEGIN
                UPDATE tc_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        """
        
        with self.lock:
            self.db_conn.executescript(schema)
            self.db_conn.commit()
    
    def discover_interfaces(self) -> List[TCInterface]:
        """Discover all network interfaces"""
        interfaces = []
        
        try:
            if self.ipr:
                # Use pyroute2 for detailed interface information
                for link in self.ipr.get_links():
                    interface = self._parse_interface_pyroute2(link)
                    if interface:
                        interfaces.append(interface)
            else:
                # Fall back to parsing /proc/net/dev and ip commands
                interfaces = self._discover_interfaces_fallback()
            
            # Update database
            self._update_interfaces_db(interfaces)
            
            self.logger.info(f"Discovered {len(interfaces)} interfaces")
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Failed to discover interfaces: {e}")
            return []
    
    def _parse_interface_pyroute2(self, link) -> Optional[TCInterface]:
        """Parse interface information from pyroute2 link data"""
        try:
            attrs = dict(link['attrs'])
            
            # Get IP addresses
            ip_addresses = []
            try:
                for addr in self.ipr.get_addr(index=link['index']):
                    addr_attrs = dict(addr['attrs'])
                    if 'IFA_ADDRESS' in addr_attrs:
                        ip_addresses.append(addr_attrs['IFA_ADDRESS'])
            except Exception:
                pass
            
            # Determine interface type
            interface_type = self._determine_interface_type(attrs['IFLA_IFNAME'])
            
            # Get speed and duplex for ethernet interfaces
            speed = None
            duplex = None
            if interface_type == 'ethernet':
                speed, duplex = self._get_interface_speed_duplex(attrs['IFLA_IFNAME'])
            
            return TCInterface(
                name=attrs['IFLA_IFNAME'],
                index=link['index'],
                type=interface_type,
                state='UP' if link['state'] == 'up' else 'DOWN',
                mtu=attrs.get('IFLA_MTU', 1500),
                mac_address=attrs.get('IFLA_ADDRESS', ''),
                ip_addresses=ip_addresses,
                speed=speed,
                duplex=duplex
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse interface {link.get('index', 'unknown')}: {e}")
            return None
    
    def _discover_interfaces_fallback(self) -> List[TCInterface]:
        """Fallback interface discovery using system commands"""
        interfaces = []
        
        try:
            # Parse /proc/net/dev
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]  # Skip header
                
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 1:
                    interface_name = parts[0].rstrip(':')
                    
                    # Get interface details using ip command
                    interface = self._get_interface_details_ip(interface_name)
                    if interface:
                        interfaces.append(interface)
                        
        except Exception as e:
            self.logger.error(f"Fallback interface discovery failed: {e}")
        
        return interfaces
    
    def _get_interface_details_ip(self, interface_name: str) -> Optional[TCInterface]:
        """Get interface details using ip command"""
        try:
            # Get interface info
            result = subprocess.run(
                [self.config['ip_path'], 'link', 'show', interface_name],
                capture_output=True, text=True, check=True
            )
            
            # Parse ip link output
            line = result.stdout.strip().split('\n')[0]
            
            # Extract index
            index_match = re.search(r'^(\d+):', line)
            index = int(index_match.group(1)) if index_match else 0
            
            # Extract MAC address
            mac_match = re.search(r'link/\w+ ([0-9a-f:]+)', line)
            mac_address = mac_match.group(1) if mac_match else ''
            
            # Extract MTU
            mtu_match = re.search(r'mtu (\d+)', line)
            mtu = int(mtu_match.group(1)) if mtu_match else 1500
            
            # Extract state
            state = 'UP' if 'state UP' in line else 'DOWN'
            
            # Get IP addresses
            ip_addresses = self._get_interface_ip_addresses(interface_name)
            
            # Determine interface type
            interface_type = self._determine_interface_type(interface_name)
            
            return TCInterface(
                name=interface_name,
                index=index,
                type=interface_type,
                state=state,
                mtu=mtu,
                mac_address=mac_address,
                ip_addresses=ip_addresses
            )
            
        except subprocess.CalledProcessError:
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get details for {interface_name}: {e}")
            return None
    
    def _get_interface_ip_addresses(self, interface_name: str) -> List[str]:
        """Get IP addresses for an interface"""
        try:
            result = subprocess.run(
                [self.config['ip_path'], 'addr', 'show', interface_name],
                capture_output=True, text=True, check=True
            )
            
            ip_addresses = []
            for line in result.stdout.split('\n'):
                if 'inet ' in line:
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            ip_addresses.append(parts[i + 1].split('/')[0])
            
            return ip_addresses
            
        except subprocess.CalledProcessError:
            return []
    
    def _determine_interface_type(self, interface_name: str) -> str:
        """Determine interface type based on name"""
        if interface_name.startswith('eth'):
            return 'ethernet'
        elif interface_name.startswith('wlan') or interface_name.startswith('wifi'):
            return 'wireless'
        elif interface_name.startswith('br'):
            return 'bridge'
        elif interface_name.startswith('vlan') or '.' in interface_name:
            return 'vlan'
        elif interface_name.startswith('bond'):
            return 'bond'
        elif interface_name.startswith('tun') or interface_name.startswith('tap'):
            return 'tunnel'
        elif interface_name == 'lo':
            return 'loopback'
        else:
            return 'other'
    
    def _get_interface_speed_duplex(self, interface_name: str) -> Tuple[Optional[int], Optional[str]]:
        """Get interface speed and duplex using ethtool"""
        try:
            result = subprocess.run(
                ['ethtool', interface_name],
                capture_output=True, text=True, check=True
            )
            
            speed = None
            duplex = None
            
            for line in result.stdout.split('\n'):
                if 'Speed:' in line:
                    speed_match = re.search(r'Speed: (\d+)Mb/s', line)
                    if speed_match:
                        speed = int(speed_match.group(1))
                elif 'Duplex:' in line:
                    duplex_match = re.search(r'Duplex: (\w+)', line)
                    if duplex_match:
                        duplex = duplex_match.group(1)
            
            return speed, duplex
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None, None
    
    def _update_interfaces_db(self, interfaces: List[TCInterface]):
        """Update interfaces in database"""
        with self.lock:
            cursor = self.db_conn.cursor()
            
            for interface in interfaces:
                cursor.execute("""
                    INSERT OR REPLACE INTO tc_interfaces 
                    (name, index_num, type, state, mtu, mac_address, ip_addresses, 
                     parent_interface, vlan_id, speed, duplex)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interface.name, interface.index, interface.type, interface.state,
                    interface.mtu, interface.mac_address, json.dumps(interface.ip_addresses),
                    interface.parent_interface, interface.vlan_id, interface.speed, interface.duplex
                ))
            
            self.db_conn.commit()
    
    def get_interface(self, name: str) -> Optional[TCInterface]:
        """Get interface by name"""
        with self.lock:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM tc_interfaces WHERE name = ?", (name,))
            row = cursor.fetchone()
            
            if row:
                return TCInterface(
                    name=row['name'],
                    index=row['index_num'],
                    type=row['type'],
                    state=row['state'],
                    mtu=row['mtu'],
                    mac_address=row['mac_address'],
                    ip_addresses=json.loads(row['ip_addresses']) if row['ip_addresses'] else [],
                    parent_interface=row['parent_interface'],
                    vlan_id=row['vlan_id'],
                    speed=row['speed'],
                    duplex=row['duplex']
                )
            return None
    
    def get_current_tc_config(self, interface: str) -> Dict[str, Any]:
        """Get current TC configuration for an interface"""
        config = {
            'qdiscs': [],
            'classes': [],
            'filters': []
        }
        
        try:
            # Get qdiscs
            result = subprocess.run(
                [self.config['tc_path'], 'qdisc', 'show', 'dev', interface],
                capture_output=True, text=True, check=True
            )
            config['qdiscs'] = self._parse_tc_qdiscs(result.stdout)
            
            # Get classes
            result = subprocess.run(
                [self.config['tc_path'], 'class', 'show', 'dev', interface],
                capture_output=True, text=True, check=True
            )
            config['classes'] = self._parse_tc_classes(result.stdout)
            
            # Get filters
            result = subprocess.run(
                [self.config['tc_path'], 'filter', 'show', 'dev', interface],
                capture_output=True, text=True, check=True
            )
            config['filters'] = self._parse_tc_filters(result.stdout)
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get TC config for {interface}: {e}")
        
        return config
    
    def _parse_tc_qdiscs(self, output: str) -> List[Dict[str, Any]]:
        """Parse tc qdisc show output"""
        qdiscs = []
        
        for line in output.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    qdisc = {
                        'kind': parts[1],
                        'handle': parts[2] if len(parts) > 2 else '',
                        'parent': parts[3] if len(parts) > 3 else '',
                        'options': {}
                    }
                    
                    # Parse options
                    for i in range(4, len(parts), 2):
                        if i + 1 < len(parts):
                            qdisc['options'][parts[i]] = parts[i + 1]
                    
                    qdiscs.append(qdisc)
        
        return qdiscs
    
    def _parse_tc_classes(self, output: str) -> List[Dict[str, Any]]:
        """Parse tc class show output"""
        classes = []
        
        for line in output.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    class_info = {
                        'kind': parts[1],
                        'parent': parts[2],
                        'classid': parts[3],
                        'options': {}
                    }
                    
                    # Parse options
                    for i in range(4, len(parts), 2):
                        if i + 1 < len(parts):
                            class_info['options'][parts[i]] = parts[i + 1]
                    
                    classes.append(class_info)
        
        return classes
    
    def _parse_tc_filters(self, output: str) -> List[Dict[str, Any]]:
        """Parse tc filter show output"""
        filters = []
        
        for line in output.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    filter_info = {
                        'kind': parts[1],
                        'protocol': parts[2],
                        'prio': parts[3],
                        'handle': parts[4] if len(parts) > 4 else '',
                        'options': {}
                    }
                    
                    # Parse options
                    for i in range(5, len(parts), 2):
                        if i + 1 < len(parts):
                            filter_info['options'][parts[i]] = parts[i + 1]
                    
                    filters.append(filter_info)
        
        return filters
    
    def create_policy(self, policy: TCPolicy) -> bool:
        """Create a new TC policy"""
        try:
            with self.lock:
                cursor = self.db_conn.cursor()
                
                # Insert policy
                cursor.execute("""
                    INSERT INTO tc_policies (name, description, interface, enabled)
                    VALUES (?, ?, ?, ?)
                """, (policy.name, policy.description, policy.interface, policy.enabled))
                
                policy_id = cursor.lastrowid
                
                # Insert qdiscs
                for qdisc in policy.qdiscs:
                    cursor.execute("""
                        INSERT INTO tc_qdiscs (policy_id, handle, parent, kind, interface, options, enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (policy_id, qdisc.handle, qdisc.parent, qdisc.kind, 
                         qdisc.interface, json.dumps(qdisc.options), qdisc.enabled))
                
                # Insert classes
                for class_obj in policy.classes:
                    cursor.execute("""
                        INSERT INTO tc_classes (policy_id, classid, parent, kind, interface, rate, ceil, 
                                              burst, cburst, prio, quantum, options, enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (policy_id, class_obj.classid, class_obj.parent, class_obj.kind,
                         class_obj.interface, class_obj.rate, class_obj.ceil, class_obj.burst,
                         class_obj.cburst, class_obj.prio, class_obj.quantum,
                         json.dumps(class_obj.options), class_obj.enabled))
                
                # Insert filters
                for filter_obj in policy.filters:
                    cursor.execute("""
                        INSERT INTO tc_filters (policy_id, handle, parent, protocol, prio, kind, 
                                              interface, match_criteria, flowid, action, enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (policy_id, filter_obj.handle, filter_obj.parent, filter_obj.protocol,
                         filter_obj.prio,