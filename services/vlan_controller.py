#!/usr/bin/env python3
"""
LNMT VLAN Controller Service
Manages VLAN creation, interface mapping, bandwidth policies, and security automation
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import sqlite3
import ipaddress
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VLANConfig:
    """VLAN configuration data structure"""
    vlan_id: int
    name: str
    description: str
    subnet: str
    gateway: str
    interfaces: List[str]
    bandwidth_limit: Optional[int] = None  # Mbps
    usage_threshold: Optional[int] = None  # Percentage
    auto_blacklist: bool = False
    priority: int = 1  # QoS priority (1-7)
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

@dataclass
class VLANStats:
    """VLAN usage statistics"""
    vlan_id: int
    bytes_in: int
    bytes_out: int
    packets_in: int
    packets_out: int
    bandwidth_usage: float  # Mbps
    connected_devices: int
    timestamp: str
    
class VLANDatabase:
    """Database handler for VLAN configurations and statistics"""
    
    def __init__(self, db_path: str = "/var/lib/lnmt/vlan.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS vlans (
                vlan_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                subnet TEXT NOT NULL,
                gateway TEXT NOT NULL,
                interfaces TEXT,  -- JSON array
                bandwidth_limit INTEGER,
                usage_threshold INTEGER,
                auto_blacklist BOOLEAN DEFAULT FALSE,
                priority INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS vlan_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vlan_id INTEGER,
                bytes_in INTEGER,
                bytes_out INTEGER,
                packets_in INTEGER,
                packets_out INTEGER,
                bandwidth_usage REAL,
                connected_devices INTEGER,
                timestamp TEXT,
                FOREIGN KEY (vlan_id) REFERENCES vlans (vlan_id)
            );
            
            CREATE TABLE IF NOT EXISTS blacklisted_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT UNIQUE,
                ip_address TEXT,
                vlan_id INTEGER,
                reason TEXT,
                blacklisted_at TEXT,
                FOREIGN KEY (vlan_id) REFERENCES vlans (vlan_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_vlan_stats_timestamp ON vlan_stats(timestamp);
            CREATE INDEX IF NOT EXISTS idx_blacklist_mac ON blacklisted_devices(mac_address);
            """)
    
    def save_vlan(self, vlan: VLANConfig) -> bool:
        """Save or update VLAN configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO vlans 
                (vlan_id, name, description, subnet, gateway, interfaces, 
                 bandwidth_limit, usage_threshold, auto_blacklist, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vlan.vlan_id, vlan.name, vlan.description, vlan.subnet, vlan.gateway,
                    json.dumps(vlan.interfaces), vlan.bandwidth_limit, vlan.usage_threshold,
                    vlan.auto_blacklist, vlan.priority, vlan.created_at, vlan.updated_at
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save VLAN {vlan.vlan_id}: {e}")
            return False
    
    def get_vlan(self, vlan_id: int) -> Optional[VLANConfig]:
        """Retrieve VLAN configuration by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM vlans WHERE vlan_id = ?", (vlan_id,)).fetchone()
                if row:
                    return VLANConfig(
                        vlan_id=row['vlan_id'],
                        name=row['name'],
                        description=row['description'],
                        subnet=row['subnet'],
                        gateway=row['gateway'],
                        interfaces=json.loads(row['interfaces']),
                        bandwidth_limit=row['bandwidth_limit'],
                        usage_threshold=row['usage_threshold'],
                        auto_blacklist=bool(row['auto_blacklist']),
                        priority=row['priority'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
        except Exception as e:
            logger.error(f"Failed to get VLAN {vlan_id}: {e}")
        return None
    
    def list_vlans(self) -> List[VLANConfig]:
        """List all VLAN configurations"""
        vlans = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM vlans ORDER BY vlan_id").fetchall()
                for row in rows:
                    vlans.append(VLANConfig(
                        vlan_id=row['vlan_id'],
                        name=row['name'],
                        description=row['description'],
                        subnet=row['subnet'],
                        gateway=row['gateway'],
                        interfaces=json.loads(row['interfaces']),
                        bandwidth_limit=row['bandwidth_limit'],
                        usage_threshold=row['usage_threshold'],
                        auto_blacklist=bool(row['auto_blacklist']),
                        priority=row['priority'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
        except Exception as e:
            logger.error(f"Failed to list VLANs: {e}")
        return vlans
    
    def delete_vlan(self, vlan_id: int) -> bool:
        """Delete VLAN configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM vlans WHERE vlan_id = ?", (vlan_id,))
                conn.execute("DELETE FROM vlan_stats WHERE vlan_id = ?", (vlan_id,))
                return True
        except Exception as e:
            logger.error(f"Failed to delete VLAN {vlan_id}: {e}")
            return False
    
    def save_stats(self, stats: VLANStats) -> bool:
        """Save VLAN statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT INTO vlan_stats 
                (vlan_id, bytes_in, bytes_out, packets_in, packets_out, 
                 bandwidth_usage, connected_devices, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stats.vlan_id, stats.bytes_in, stats.bytes_out,
                    stats.packets_in, stats.packets_out, stats.bandwidth_usage,
                    stats.connected_devices, stats.timestamp
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save stats for VLAN {stats.vlan_id}: {e}")
            return False
    
    def blacklist_device(self, mac_address: str, ip_address: str, vlan_id: int, reason: str) -> bool:
        """Add device to blacklist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO blacklisted_devices 
                (mac_address, ip_address, vlan_id, reason, blacklisted_at)
                VALUES (?, ?, ?, ?, ?)
                """, (mac_address, ip_address, vlan_id, reason, datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist device {mac_address}: {e}")
            return False

class NetworkInterface:
    """Network interface management"""
    
    @staticmethod
    def create_vlan_interface(interface: str, vlan_id: int) -> bool:
        """Create VLAN interface"""
        try:
            vlan_interface = f"{interface}.{vlan_id}"
            
            # Check if interface already exists
            result = subprocess.run(['ip', 'link', 'show', vlan_interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"VLAN interface {vlan_interface} already exists")
                return True
            
            # Create VLAN interface
            subprocess.run(['ip', 'link', 'add', 'link', interface, 'name', vlan_interface, 
                          'type', 'vlan', 'id', str(vlan_id)], check=True)
            
            # Bring interface up
            subprocess.run(['ip', 'link', 'set', vlan_interface, 'up'], check=True)
            
            logger.info(f"Created VLAN interface {vlan_interface}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create VLAN interface {interface}.{vlan_id}: {e}")
            return False
    
    @staticmethod
    def delete_vlan_interface(interface: str, vlan_id: int) -> bool:
        """Delete VLAN interface"""
        try:
            vlan_interface = f"{interface}.{vlan_id}"
            subprocess.run(['ip', 'link', 'delete', vlan_interface], check=True)
            logger.info(f"Deleted VLAN interface {vlan_interface}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete VLAN interface {interface}.{vlan_id}: {e}")
            return False
    
    @staticmethod
    def configure_ip(interface: str, vlan_id: int, gateway: str, subnet: str) -> bool:
        """Configure IP address for VLAN interface"""
        try:
            vlan_interface = f"{interface}.{vlan_id}"
            
            # Add IP address
            subprocess.run(['ip', 'addr', 'add', f"{gateway}/{subnet.split('/')[1]}", 
                          'dev', vlan_interface], check=True)
            
            logger.info(f"Configured IP {gateway} for {vlan_interface}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure IP for {interface}.{vlan_id}: {e}")
            return False

class ShorewallIntegration:
    """Shorewall firewall integration"""
    
    def __init__(self, config_dir: str = "/etc/shorewall"):
        self.config_dir = Path(config_dir)
    
    def add_vlan_zone(self, vlan: VLANConfig) -> bool:
        """Add VLAN zone to Shorewall configuration"""
        try:
            zones_file = self.config_dir / "zones"
            interfaces_file = self.config_dir / "interfaces"
            
            # Add zone
            zone_name = f"vlan{vlan.vlan_id}"
            with open(zones_file, 'a') as f:
                f.write(f"{zone_name}\tipv4\n")
            
            # Add interfaces
            with open(interfaces_file, 'a') as f:
                for interface in vlan.interfaces:
                    vlan_interface = f"{interface}.{vlan.vlan_id}"
                    f.write(f"{zone_name}\t{vlan_interface}\tdetect\n")
            
            return True
        except Exception as e:
            logger.error(f"Failed to add VLAN zone to Shorewall: {e}")
            return False
    
    def add_bandwidth_rules(self, vlan: VLANConfig) -> bool:
        """Add bandwidth limiting rules"""
        if not vlan.bandwidth_limit:
            return True
        
        try:
            tcdevices_file = self.config_dir / "tcdevices"
            
            with open(tcdevices_file, 'a') as f:
                for interface in vlan.interfaces:
                    vlan_interface = f"{interface}.{vlan.vlan_id}"
                    f.write(f"{vlan_interface}\t{vlan.bandwidth_limit}mbit\t{vlan.bandwidth_limit//10}mbit\n")
            
            return True
        except Exception as e:
            logger.error(f"Failed to add bandwidth rules: {e}")
            return False
    
    def reload_configuration(self) -> bool:
        """Reload Shorewall configuration"""
        try:
            subprocess.run(['shorewall', 'reload'], check=True)
            logger.info("Shorewall configuration reloaded")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reload Shorewall: {e}")
            return False

class VLANMonitor:
    """VLAN monitoring and statistics collection"""
    
    def __init__(self, db: VLANDatabase):
        self.db = db
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("VLAN monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("VLAN monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                vlans = self.db.list_vlans()
                for vlan in vlans:
                    stats = self._collect_vlan_stats(vlan)
                    if stats:
                        self.db.save_stats(stats)
                        self._check_thresholds(vlan, stats)
                
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def _collect_vlan_stats(self, vlan: VLANConfig) -> Optional[VLANStats]:
        """Collect statistics for a VLAN"""
        try:
            total_bytes_in = 0
            total_bytes_out = 0
            total_packets_in = 0
            total_packets_out = 0
            
            for interface in vlan.interfaces:
                vlan_interface = f"{interface}.{vlan.vlan_id}"
                stats = self._get_interface_stats(vlan_interface)
                if stats:
                    total_bytes_in += stats['rx_bytes']
                    total_bytes_out += stats['tx_bytes']
                    total_packets_in += stats['rx_packets']
                    total_packets_out += stats['tx_packets']
            
            # Calculate bandwidth usage (simplified)
            bandwidth_usage = (total_bytes_in + total_bytes_out) * 8 / (1024 * 1024 * 30)  # Mbps over 30 seconds
            
            # Get connected devices count (placeholder - would integrate with device_tracker)
            connected_devices = self._count_connected_devices(vlan)
            
            return VLANStats(
                vlan_id=vlan.vlan_id,
                bytes_in=total_bytes_in,
                bytes_out=total_bytes_out,
                packets_in=total_packets_in,
                packets_out=total_packets_out,
                bandwidth_usage=bandwidth_usage,
                connected_devices=connected_devices,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to collect stats for VLAN {vlan.vlan_id}: {e}")
            return None
    
    def _get_interface_stats(self, interface: str) -> Optional[Dict]:
        """Get interface statistics from /proc/net/dev"""
        try:
            with open('/proc/net/dev', 'r') as f:
                for line in f:
                    if interface in line:
                        parts = line.split()
                        return {
                            'rx_bytes': int(parts[1]),
                            'rx_packets': int(parts[2]),
                            'tx_bytes': int(parts[9]),
                            'tx_packets': int(parts[10])
                        }
        except Exception as e:
            logger.error(f"Failed to get stats for interface {interface}: {e}")
        return None
    
    def _count_connected_devices(self, vlan: VLANConfig) -> int:
        """Count connected devices in VLAN (placeholder for device_tracker integration)"""
        # This would integrate with your device_tracker module
        # For now, return a placeholder value
        return 0
    
    def _check_thresholds(self, vlan: VLANConfig, stats: VLANStats):
        """Check usage thresholds and trigger auto-blacklisting if needed"""
        if not vlan.usage_threshold or not vlan.auto_blacklist:
            return
        
        if vlan.bandwidth_limit:
            usage_percent = (stats.bandwidth_usage / vlan.bandwidth_limit) * 100
            if usage_percent > vlan.usage_threshold:
                logger.warning(f"VLAN {vlan.vlan_id} exceeded usage threshold: {usage_percent:.1f}%")
                # Implement auto-blacklisting logic here
                self._trigger_auto_blacklist(vlan, f"Bandwidth usage exceeded {vlan.usage_threshold}%")
    
    def _trigger_auto_blacklist(self, vlan: VLANConfig, reason: str):
        """Trigger auto-blacklisting for high usage devices"""
        # This would identify and blacklist the highest usage devices
        # Implementation would depend on device_tracker integration
        logger.info(f"Auto-blacklist triggered for VLAN {vlan.vlan_id}: {reason}")

class VLANController:
    """Main VLAN controller class"""
    
    def __init__(self, db_path: str = "/var/lib/lnmt/vlan.db"):
        self.db = VLANDatabase(db_path)
        self.shorewall = ShorewallIntegration()
        self.monitor = VLANMonitor(self.db)
        self.network = NetworkInterface()
    
    def create_vlan(self, vlan_id: int, name: str, description: str, 
                   subnet: str, gateway: str, interfaces: List[str],
                   bandwidth_limit: Optional[int] = None,
                   usage_threshold: Optional[int] = None,
                   auto_blacklist: bool = False,
                   priority: int = 1) -> bool:
        """Create a new VLAN"""
        try:
            # Validate inputs
            if self.db.get_vlan(vlan_id):
                logger.error(f"VLAN {vlan_id} already exists")
                return False
            
            # Validate subnet
            try:
                ipaddress.IPv4Network(subnet)
                ipaddress.IPv4Address(gateway)
            except ValueError as e:
                logger.error(f"Invalid subnet or gateway: {e}")
                return False
            
            # Create VLAN configuration
            vlan = VLANConfig(
                vlan_id=vlan_id,
                name=name,
                description=description,
                subnet=subnet,
                gateway=gateway,
                interfaces=interfaces,
                bandwidth_limit=bandwidth_limit,
                usage_threshold=usage_threshold,
                auto_blacklist=auto_blacklist,
                priority=priority
            )
            
            # Create network interfaces
            success = True
            for interface in interfaces:
                if not self.network.create_vlan_interface(interface, vlan_id):
                    success = False
                    break
                if not self.network.configure_ip(interface, vlan_id, gateway, subnet):
                    success = False
                    break
            
            if not success:
                # Cleanup on failure
                for interface in interfaces:
                    self.network.delete_vlan_interface(interface, vlan_id)
                return False
            
            # Save to database
            if not self.db.save_vlan(vlan):
                return False
            
            # Configure Shorewall
            self.shorewall.add_vlan_zone(vlan)
            self.shorewall.add_bandwidth_rules(vlan)
            self.shorewall.reload_configuration()
            
            logger.info(f"Successfully created VLAN {vlan_id} ({name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create VLAN {vlan_id}: {e}")
            return False
    
    def update_vlan(self, vlan_id: int, **kwargs) -> bool:
        """Update existing VLAN configuration"""
        vlan = self.db.get_vlan(vlan_id)
        if not vlan:
            logger.error(f"VLAN {vlan_id} not found")
            return False
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(vlan, key):
                setattr(vlan, key, value)
        
        vlan.updated_at = datetime.now().isoformat()
        
        # Save updated configuration
        if self.db.save_vlan(vlan):
            logger.info(f"Updated VLAN {vlan_id}")
            return True
        return False
    
    def delete_vlan(self, vlan_id: int) -> bool:
        """Delete VLAN and cleanup resources"""
        vlan = self.db.get_vlan(vlan_id)
        if not vlan:
            logger.error(f"VLAN {vlan_id} not found")
            return False
        
        try:
            # Delete network interfaces
            for interface in vlan.interfaces:
                self.network.delete_vlan_interface(interface, vlan_id)
            
            # Delete from database
            self.db.delete_vlan(vlan_id)
            
            # TODO: Remove from Shorewall configuration
            
            logger.info(f"Deleted VLAN {vlan_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete VLAN {vlan_id}: {e}")
            return False
    
    def list_vlans(self) -> List[VLANConfig]:
        """List all VLANs"""
        return self.db.list_vlans()
    
    def get_vlan(self, vlan_id: int) -> Optional[VLANConfig]:
        """Get VLAN by ID"""
        return self.db.get_vlan(vlan_id)
    
    def start_monitoring(self):
        """Start VLAN monitoring"""
        self.monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop VLAN monitoring"""
        self.monitor.stop_monitoring()
    
    def export_topology(self, output_file: str = "/tmp/vlan_topology.dot") -> bool:
        """Export VLAN topology as Graphviz diagram"""
        try:
            vlans = self.list_vlans()
            
            with open(output_file, 'w') as f:
                f.write("digraph VLAN_Topology {\n")
                f.write("  rankdir=TB;\n")
                f.write("  node [shape=rectangle, style=filled];\n\n")
                
                # Physical interfaces
                interfaces = set()
                for vlan in vlans:
                    interfaces.update(vlan.interfaces)
                
                for interface in interfaces:
                    f.write(f'  "{interface}" [fillcolor=lightblue, label="{interface}\\nPhysical Interface"];\n')
                
                # VLANs
                for vlan in vlans:
                    color = "lightgreen" if vlan.auto_blacklist else "lightyellow"
                    label = f"VLAN {vlan.vlan_id}\\n{vlan.name}\\n{vlan.subnet}"
                    if vlan.bandwidth_limit:
                        label += f"\\n{vlan.bandwidth_limit}Mbps"
                    
                    f.write(f'  "vlan{vlan.vlan_id}" [fillcolor={color}, label="{label}"];\n')
                    
                    # Connections
                    for interface in vlan.interfaces:
                        f.write(f'  "{interface}" -> "vlan{vlan.vlan_id}";\n')
                
                f.write("}\n")
            
            logger.info(f"Exported VLAN topology to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to export topology: {e}")
            return False

# API endpoints (Flask integration)
def create_api_routes(app, controller: VLANController):
    """Create Flask API routes for VLAN management"""
    
    @app.route('/api/vlans', methods=['GET'])
    def list_vlans():
        vlans = controller.list_vlans()
        return {'vlans': [asdict(vlan) for vlan in vlans]}
    
    @app.route('/api/vlans/<int:vlan_id>', methods=['GET'])
    def get_vlan(vlan_id):
        vlan = controller.get_vlan(vlan_id)
        if vlan:
            return {'vlan': asdict(vlan)}
        return {'error': 'VLAN not found'}, 404
    
    @app.route('/api/vlans', methods=['POST'])
    def create_vlan():
        data = request.get_json()
        required_fields = ['vlan_id', 'name', 'subnet', 'gateway', 'interfaces']
        
        if not all(field in data for field in required_fields):
            return {'error': 'Missing required fields'}, 400
        
        success = controller.create_vlan(
            vlan_id=data['vlan_id'],
            name=data['name'],
            description=data.get('description', ''),
            subnet=data['subnet'],
            gateway=data['gateway'],
            interfaces=data['interfaces'],
            bandwidth_limit=data.get('bandwidth_limit'),
            usage_threshold=data.get('usage_threshold'),
            auto_blacklist=data.get('auto_blacklist', False),
            priority=data.get('priority', 1)
        )
        
        if success:
            return {'message': 'VLAN created successfully'}
        return {'error': 'Failed to create VLAN'}, 500
    
    @app.route('/api/vlans/<int:vlan_id>', methods=['PUT'])
    def update_vlan(vlan_id):
        data = request.get_json()
        success = controller.update_vlan(vlan_id, **data)
        
        if success:
            return {'message': 'VLAN updated successfully'}
        return {'error': 'Failed to update VLAN'}, 500
    
    @app.route('/api/vlans/<int:vlan_id>', methods=['DELETE'])
    def delete_vlan(vlan_id):
        success = controller.delete_vlan(vlan_id)
        
        if success:
            return {'message': 'VLAN deleted successfully'}
        return {'error': 'Failed to delete VLAN'}, 500
    
    @app.route('/api/vlans/topology', methods=['GET'])
    def export_topology():
        output_file = '/tmp/vlan_topology.dot'
        if controller.export_topology(output_file):
            return send_file(output_file, as_attachment=True)
        return {'error': 'Failed to export topology'}, 500

if __name__ == "__main__":
    # Example usage
    controller = VLANController()
    
    # Start monitoring
    controller.start_monitoring()
    
    # Create example VLAN
    controller.create_vlan(
        vlan_id=100,
        name="Guest Network",
        description="Isolated guest network",
        subnet="192.168.100.0/24",
        gateway="192.168.100.1",
        interfaces=["eth0"],
        bandwidth_limit=50,  # 50 Mbps
        usage_threshold=80,  # 80%
        auto_blacklist=True
    )
    
    # List VLANs
    vlans = controller.list_vlans()
    for vlan in vlans:
        print(f"VLAN {vlan.vlan_id}: {vlan.name} - {vlan.subnet}")
    
    # Export topology
    controller.export_topology()
    
    try:
        # Keep running
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        controller.stop_monitoring()
        print("VLAN Controller stopped")
