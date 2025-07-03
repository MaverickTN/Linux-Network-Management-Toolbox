#!/usr/bin/env python3
"""
LNMT Demo Data Generator
Generates realistic demo data for LNMT network management toolkit
"""

import json
import csv
import random
import datetime
from typing import Dict, List, Any
import ipaddress
import uuid

class LNMTDemoDataGenerator:
    def __init__(self):
        self.company_names = [
            "TechCorp", "DataSys", "NetFlow", "CloudBase", "DevOps Inc",
            "SysAdmin Co", "NetworkPro", "SecureIT", "FastLink", "ConnectHub"
        ]
        
        self.device_types = [
            "Router", "Switch", "Firewall", "Access Point", "Server", 
            "Workstation", "Printer", "IoT Device", "Camera", "Phone"
        ]
        
        self.manufacturers = [
            "Cisco", "HP", "Dell", "Ubiquiti", "Netgear", "TP-Link", 
            "Aruba", "Juniper", "Fortinet", "Palo Alto"
        ]
        
        self.departments = [
            "IT", "Sales", "Marketing", "HR", "Finance", "Operations",
            "Engineering", "Support", "Management", "Guest"
        ]

    def generate_devices(self, count: int = 25) -> List[Dict]:
        """Generate realistic network devices"""
        devices = []
        base_networks = [
            ipaddress.IPv4Network("192.168.1.0/24"),
            ipaddress.IPv4Network("10.0.0.0/24"),
            ipaddress.IPv4Network("172.16.0.0/24")
        ]
        
        for i in range(count):
            network = random.choice(base_networks)
            ip = str(network.network_address + random.randint(10, 200))
            
            device = {
                "device_id": f"dev_{i+1:03d}",
                "hostname": f"{random.choice(['srv', 'ws', 'rt', 'sw'])}-{i+1:03d}",
                "ip_address": ip,
                "mac_address": self._generate_mac(),
                "device_type": random.choice(self.device_types),
                "manufacturer": random.choice(self.manufacturers),
                "model": f"Model-{random.randint(1000, 9999)}",
                "os_version": f"{random.randint(1, 15)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "department": random.choice(self.departments),
                "location": f"Floor {random.randint(1, 5)}, Room {random.randint(100, 599)}",
                "status": random.choices(["online", "offline", "maintenance"], weights=[80, 15, 5])[0],
                "last_seen": self._random_datetime(-7, 0).isoformat(),
                "first_seen": self._random_datetime(-365, -30).isoformat(),
                "uptime_hours": random.randint(1, 8760),
                "cpu_usage": random.randint(5, 95),
                "memory_usage": random.randint(10, 90),
                "disk_usage": random.randint(15, 85),
                "network_utilization": random.randint(1, 100),
                "open_ports": random.sample(range(21, 65535), random.randint(3, 12)),
                "vulnerabilities": random.randint(0, 5),
                "patch_level": random.choices(["current", "outdated", "critical"], weights=[60, 30, 10])[0],
                "backup_status": random.choices(["success", "failed", "pending"], weights=[70, 20, 10])[0],
                "last_backup": self._random_datetime(-30, 0).isoformat(),
                "tags": random.sample(["production", "development", "critical", "monitored", "secure"], random.randint(1, 3))
            }
            devices.append(device)
        
        return devices

    def generate_vlans(self, count: int = 8) -> List[Dict]:
        """Generate VLAN configurations"""
        vlans = []
        vlan_purposes = [
            ("Management", "192.168.100.0/24", "Network management and admin access"),
            ("Servers", "10.0.10.0/24", "Production servers and services"),
            ("Workstations", "192.168.1.0/24", "Employee workstations and laptops"),
            ("Guest", "172.16.1.0/24", "Guest network access"),
            ("IoT", "10.0.20.0/24", "IoT devices and sensors"),
            ("DMZ", "203.0.113.0/24", "Demilitarized zone for external services"),
            ("VoIP", "10.0.30.0/24", "Voice over IP phones and systems"),
            ("Security", "192.168.200.0/24", "Security cameras and access control")
        ]
        
        for i, (name, network, description) in enumerate(vlan_purposes[:count]):
            vlan = {
                "vlan_id": 100 + i * 10,
                "name": name,
                "description": description,
                "network": network,
                "gateway": str(ipaddress.IPv4Network(network).network_address + 1),
                "dhcp_enabled": random.choice([True, False]),
                "dhcp_range_start": str(ipaddress.IPv4Network(network).network_address + 10),
                "dhcp_range_end": str(ipaddress.IPv4Network(network).network_address + 200),
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "domain": f"{name.lower()}.lnmt.local",
                "access_control": random.choices(["open", "restricted", "secured"], weights=[40, 40, 20])[0],
                "firewall_rules": random.randint(3, 15),
                "devices_count": random.randint(5, 50),
                "bandwidth_limit": f"{random.randint(10, 1000)}Mbps",
                "created_date": self._random_datetime(-180, -1).isoformat(),
                "last_modified": self._random_datetime(-30, 0).isoformat(),
                "status": random.choices(["active", "inactive"], weights=[90, 10])[0]
            }
            vlans.append(vlan)
        
        return vlans

    def generate_users(self, count: int = 30) -> List[Dict]:
        """Generate user accounts and profiles"""
        first_names = ["John", "Jane", "Mike", "Sarah", "David", "Lisa", "Chris", "Amy", "Tom", "Emma"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson"]
        
        users = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}.{last_name.lower()}"
            
            user = {
                "user_id": f"usr_{i+1:03d}",
                "username": username,
                "email": f"{username}@company.com",
                "first_name": first_name,
                "last_name": last_name,
                "department": random.choice(self.departments),
                "role": random.choices(["admin", "operator", "viewer", "guest"], weights=[10, 20, 50, 20])[0],
                "permissions": self._generate_permissions(),
                "status": random.choices(["active", "inactive", "suspended"], weights=[85, 10, 5])[0],
                "last_login": self._random_datetime(-30, 0).isoformat(),
                "login_count": random.randint(1, 500),
                "failed_logins": random.randint(0, 5),
                "password_expires": self._random_datetime(30, 90).isoformat(),
                "two_factor_enabled": random.choices([True, False], weights=[60, 40])[0],
                "created_date": self._random_datetime(-365, -1).isoformat(),
                "devices_managed": random.randint(0, 15),
                "session_timeout": random.choice([30, 60, 120, 240]),
                "preferred_theme": random.choice(["dark", "light", "auto"]),
                "notifications_enabled": random.choice([True, False])
            }
            users.append(user)
        
        return users

    def generate_alerts(self, count: int = 50) -> List[Dict]:
        """Generate system alerts and notifications"""
        alert_types = [
            "Device Offline", "High CPU Usage", "Memory Warning", "Disk Full", 
            "Network Congestion", "Security Breach", "Backup Failed", "Service Down",
            "Configuration Change", "Firmware Update", "License Expiry", "Unauthorized Access"
        ]
        
        severities = ["critical", "high", "medium", "low", "info"]
        
        alerts = []
        for i in range(count):
            alert = {
                "alert_id": f"alert_{i+1:04d}",
                "type": random.choice(alert_types),
                "severity": random.choices(severities, weights=[10, 20, 40, 20, 10])[0],
                "title": f"{random.choice(alert_types)} - {random.choice(['srv', 'ws', 'rt'])}-{random.randint(1, 100):03d}",
                "description": self._generate_alert_description(),
                "device_id": f"dev_{random.randint(1, 25):03d}",
                "source_ip": f"192.168.1.{random.randint(10, 200)}",
                "timestamp": self._random_datetime(-30, 0).isoformat(),
                "status": random.choices(["open", "acknowledged", "resolved", "closed"], weights=[30, 20, 30, 20])[0],
                "assigned_to": f"usr_{random.randint(1, 30):03d}",
                "resolution_time": random.randint(5, 1440) if random.random() > 0.3 else None,
                "escalated": random.choices([True, False], weights=[20, 80])[0],
                "repeat_count": random.randint(1, 10),
                "suppressed": random.choices([True, False], weights=[15, 85])[0],
                "tags": random.sample(["network", "security", "performance", "hardware", "software"], random.randint(1, 3))
            }
            alerts.append(alert)
        
        return alerts

    def generate_sessions(self, count: int = 100) -> List[Dict]:
        """Generate user session data"""
        sessions = []
        for i in range(count):
            start_time = self._random_datetime(-7, 0)
            duration = random.randint(5, 480)  # 5 minutes to 8 hours
            
            session = {
                "session_id": f"sess_{uuid.uuid4().hex[:8]}",
                "user_id": f"usr_{random.randint(1, 30):03d}",
                "start_time": start_time.isoformat(),
                "end_time": (start_time + datetime.timedelta(minutes=duration)).isoformat(),
                "duration_minutes": duration,
                "source_ip": f"192.168.1.{random.randint(10, 200)}",
                "user_agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                ]),
                "login_method": random.choices(["password", "sso", "api_key", "certificate"], weights=[60, 25, 10, 5])[0],
                "actions_performed": random.randint(1, 50),
                "pages_visited": random.randint(1, 20),
                "api_calls": random.randint(0, 100),
                "data_transferred_mb": round(random.uniform(0.1, 100.0), 2),
                "logout_reason": random.choices(["user", "timeout", "admin", "error"], weights=[70, 20, 5, 5])[0],
                "concurrent_sessions": random.randint(1, 3),
                "location": f"{random.choice(['Office', 'Remote', 'Mobile'])} - {random.choice(['US', 'CA', 'UK'])}",
                "risk_score": random.randint(0, 100)
            }
            sessions.append(session)
        
        return sessions

    def generate_policies(self, count: int = 15) -> List[Dict]:
        """Generate security and network policies"""
        policy_types = [
            "Firewall Rule", "Access Control", "Backup Policy", "Password Policy",
            "Network Segmentation", "QoS Policy", "Security Baseline", "Compliance Rule"
        ]
        
        policies = []
        for i in range(count):
            policy = {
                "policy_id": f"pol_{i+1:03d}",
                "name": f"{random.choice(policy_types)} - {random.choice(self.departments)}",
                "type": random.choice(policy_types),
                "description": self._generate_policy_description(),
                "scope": random.choice(["global", "department", "device_specific", "user_group"]),
                "status": random.choices(["active", "draft", "disabled"], weights=[70, 20, 10])[0],
                "priority": random.randint(1, 100),
                "created_by": f"usr_{random.randint(1, 10):03d}",
                "created_date": self._random_datetime(-180, -1).isoformat(),
                "last_modified": self._random_datetime(-30, 0).isoformat(),
                "enforcement": random.choice(["strict", "moderate", "advisory"]),
                "compliance_standard": random.choice(["ISO 27001", "NIST", "GDPR", "HIPAA", "Custom"]),
                "affected_devices": random.randint(1, 25),
                "violations_count": random.randint(0, 10),
                "auto_remediation": random.choices([True, False], weights=[40, 60])[0],
                "review_date": self._random_datetime(30, 90).isoformat(),
                "tags": random.sample(["security", "compliance", "network", "access", "backup"], random.randint(1, 3))
            }
            policies.append(policy)
        
        return policies

    def _generate_mac(self) -> str:
        """Generate a random MAC address"""
        return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])

    def _random_datetime(self, days_ago_min: int, days_ago_max: int) -> datetime.datetime:
        """Generate a random datetime within specified range"""
        days_ago = random.randint(days_ago_min, days_ago_max)
        return datetime.datetime.now() + datetime.timedelta(days=days_ago, 
                                                           hours=random.randint(0, 23),
                                                           minutes=random.randint(0, 59))

    def _generate_permissions(self) -> List[str]:
        """Generate user permissions based on role"""
        all_permissions = [
            "device.view", "device.edit", "device.create", "device.delete",
            "user.view", "user.edit", "user.create", "user.delete",
            "vlan.view", "vlan.edit", "vlan.create", "vlan.delete",
            "alert.view", "alert.acknowledge", "alert.resolve",
            "backup.view", "backup.create", "backup.restore",
            "report.view", "report.create", "report.export",
            "system.config", "system.logs", "system.maintenance"
        ]
        return random.sample(all_permissions, random.randint(3, len(all_permissions)))

    def _generate_alert_description(self) -> str:
        """Generate realistic alert descriptions"""
        descriptions = [
            "Device has been unreachable for over 10 minutes",
            "CPU utilization exceeded 90% threshold for 5 consecutive minutes",
            "Available memory below 10% threshold",
            "Disk usage exceeded 95% capacity on primary partition",
            "Network interface showing high error rates",
            "Multiple failed authentication attempts detected",
            "Scheduled backup job failed with error code 500",
            "Service became unresponsive and was automatically restarted",
            "Unauthorized configuration change detected",
            "Firmware version is outdated and requires security update",
            "Software license will expire in 7 days"
        ]
        return random.choice(descriptions)

    def _generate_policy_description(self) -> str:
        """Generate realistic policy descriptions"""
        descriptions = [
            "Restrict access to management interfaces from untrusted networks",
            "Enforce strong password requirements for all user accounts",
            "Automatically backup critical system configurations daily",
            "Segment guest network traffic from internal resources",
            "Prioritize voice traffic over data traffic during peak hours",
            "Block access to known malicious IP addresses and domains",
            "Require two-factor authentication for administrative access",
            "Log all privileged user activities for compliance auditing"
        ]
        return random.choice(descriptions)

    def save_to_json(self, data: Dict[str, List], filename: str):
        """Save data to JSON file"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def save_to_csv(self, data: List[Dict], filename: str):
        """Save data to CSV file"""
        if not data:
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

def main():
    """Generate all demo data"""
    generator = LNMTDemoDataGenerator()
    
    print("🚀 Generating LNMT demo data...")
    
    # Generate all data sets
    devices = generator.generate_devices(25)
    vlans = generator.generate_vlans(8)
    users = generator.generate_users(30)
    alerts = generator.generate_alerts(50)
    sessions = generator.generate_sessions(100)
    policies = generator.generate_policies(15)
    
    # Combine all data
    demo_data = {
        "devices": devices,
        "vlans": vlans,
        "users": users,
        "alerts": alerts,
        "sessions": sessions,
        "policies": policies,
        "metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "generator_version": "1.0.0",
            "total_records": len(devices) + len(vlans) + len(users) + len(alerts) + len(sessions) + len(policies)
        }
    }
    
    # Save as JSON
    generator.save_to_json(demo_data, "lnmt_demo_data.json")
    
    # Save individual CSV files
    generator.save_to_csv(devices, "demo_devices.csv")
    generator.save_to_csv(vlans, "demo_vlans.csv")
    generator.save_to_csv(users, "demo_users.csv")
    generator.save_to_csv(alerts, "demo_alerts.csv")
    generator.save_to_csv(sessions, "demo_sessions.csv")
    generator.save_to_csv(policies, "demo_policies.csv")
    
    print(f"✅ Generated demo data:")
    print(f"   📱 {len(devices)} devices")
    print(f"   🌐 {len(vlans)} VLANs")
    print(f"   👥 {len(users)} users")
    print(f"   🚨 {len(alerts)} alerts")
    print(f"   🔐 {len(sessions)} sessions")
    print(f"   📋 {len(policies)} policies")
    print(f"   📊 Total: {demo_data['metadata']['total_records']} records")

if __name__ == "__main__":
    main()
