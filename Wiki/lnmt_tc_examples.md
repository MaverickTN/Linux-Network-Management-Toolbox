# LNMT TC/QoS Module Examples and Documentation

## Overview

The LNMT TC/QoS module provides comprehensive traffic control and quality of service management for Linux network interfaces. It supports HTB (Hierarchical Token Bucket), TBF (Token Bucket Filter), and other queueing disciplines with web-based management and CLI tools.

## Example Policy Configurations

### 1. Simple HTB Policy (JSON)

```json
{
  "name": "web_server_policy",
  "description": "Traffic shaping for web server",
  "interface": "eth0",
  "enabled": true,
  "qdiscs": [
    {
      "handle": "1:",
      "parent": "root",
      "kind": "htb",
      "options": {
        "default": "30"
      },
      "enabled": true
    }
  ],
  "classes": [
    {
      "classid": "1:1",
      "parent": "1:",
      "kind": "htb",
      "rate": "100mbit",
      "ceil": "100mbit",
      "enabled": true
    },
    {
      "classid": "1:10",
      "parent": "1:1",
      "kind": "htb",
      "rate": "80mbit",
      "ceil": "100mbit",
      "prio": 1,
      "enabled": true
    },
    {
      "classid": "1:20",
      "parent": "1:1",
      "kind": "htb",
      "rate": "15mbit",
      "ceil": "20mbit",
      "prio": 2,
      "enabled": true
    },
    {
      "classid": "1:30",
      "parent": "1:1",
      "kind": "htb",
      "rate": "5mbit",
      "ceil": "10mbit",
      "prio": 3,
      "enabled": true
    }
  ],
  "filters": [
    {
      "handle": "1:",
      "parent": "1:",
      "protocol": "ip",
      "prio": 1,
      "kind": "u32",
      "match_criteria": {
        "dport": 80
      },
      "flowid": "1:10",
      "enabled": true
    },
    {
      "handle": "2:",
      "parent": "1:",
      "protocol": "ip",
      "prio": 2,
      "kind": "u32",
      "match_criteria": {
        "dport": 443
      },
      "flowid": "1:10",
      "enabled": true
    },
    {
      "handle": "3:",
      "parent": "1:",
      "protocol": "ip",
      "prio": 3,
      "kind": "u32",
      "match_criteria": {
        "dport": 22
      },
      "flowid": "1:20",
      "enabled": true
    }
  ]
}
```

### 2. Enterprise Network Policy (YAML)

```yaml
name: enterprise_policy
description: Enterprise network traffic shaping with QoS
interface: eth0
enabled: true

qdiscs:
  - handle: "1:"
    parent: root
    kind: htb
    options:
      default: "40"
    enabled: true

classes:
  # Root class
  - classid: "1:1"
    parent: "1:"
    kind: htb
    rate: "1gbit"
    ceil: "1gbit"
    enabled: true
  
  # High priority - VoIP and critical services
  - classid: "1:10"
    parent: "1:1"
    kind: htb
    rate: "100mbit"
    ceil: "200mbit"
    prio: 1
    enabled: true
  
  # Medium priority - Web traffic
  - classid: "1:20"
    parent: "1:1"
    kind: htb
    rate: "400mbit"
    ceil: "600mbit"
    prio: 2
    enabled: true
  
  # Normal priority - General traffic
  - classid: "1:30"
    parent: "1:1"
    kind: htb
    rate: "300mbit"
    ceil: "400mbit"
    prio: 3
    enabled: true
  
  # Low priority - Bulk transfers
  - classid: "1:40"
    parent: "1:1"
    kind: htb
    rate: "100mbit"
    ceil: "200mbit"
    prio: 4
    enabled: true

filters:
  # VoIP traffic (SIP, RTP)
  - handle: "10:"
    parent: "1:"
    protocol: ip
    prio: 1
    kind: u32
    match_criteria:
      dport: 5060
    flowid: "1:10"
    enabled: true
  
  - handle: "11:"
    parent: "1:"
    protocol: ip
    prio: 1
    kind: u32
    match_criteria:
      dst: "10.0.0.0/24"
      protocol: 17
    flowid: "1:10"
    enabled: true
  
  # Web traffic
  - handle: "20:"
    parent: "1:"
    protocol: ip
    prio: 2
    kind: u32
    match_criteria:
      dport: 80
    flowid: "1:20"
    enabled: true
  
  - handle: "21:"
    parent: "1:"
    protocol: ip
    prio: 2
    kind: u32
    match_criteria:
      dport: 443
    flowid: "1:20"
    enabled: true
  
  # SSH and management
  - handle: "30:"
    parent: "1:"
    protocol: ip
    prio: 3
    kind: u32
    match_criteria:
      dport: 22
    flowid: "1:30"
    enabled: true
  
  # FTP and bulk transfers
  - handle: "40:"
    parent: "1:"
    protocol: ip
    prio: 4
    kind: u32
    match_criteria:
      dport: 21
    flowid: "1:40"
    enabled: true
```

### 3. VLAN-based QoS Policy

```json
{
  "name": "vlan_qos_policy",
  "description": "VLAN-based traffic shaping",
  "interface": "eth0.100",
  "enabled": true,
  "qdiscs": [
    {
      "handle": "1:",
      "parent": "root",
      "kind": "htb",
      "options": {
        "default": "999"
      },
      "enabled": true
    }
  ],
  "classes": [
    {
      "classid": "1:1",
      "parent": "1:",
      "kind": "htb",
      "rate": "100mbit",
      "ceil": "100mbit",
      "enabled": true
    },
    {
      "classid": "1:100",
      "parent": "1:1",
      "kind": "htb",
      "rate": "60mbit",
      "ceil": "80mbit",
      "prio": 1,
      "enabled": true
    },
    {
      "classid": "1:200",
      "parent": "1:1",
      "kind": "htb",
      "rate": "30mbit",
      "ceil": "40mbit",
      "prio": 2,
      "enabled": true
    },
    {
      "classid": "1:999",
      "parent": "1:1",
      "kind": "htb",
      "rate": "10mbit",
      "ceil": "20mbit",
      "prio": 3,
      "enabled": true
    }
  ],
  "filters": [
    {
      "handle": "100:",
      "parent": "1:",
      "protocol": "ip",
      "prio": 1,
      "kind": "u32",
      "match_criteria": {
        "src": "192.168.100.0/24"
      },
      "flowid": "1:100",
      "enabled": true
    },
    {
      "handle": "200:",
      "parent": "1:",
      "protocol": "ip",
      "prio": 2,
      "kind": "u32",
      "match_criteria": {
        "src": "192.168.200.0/24"
      },
      "flowid": "1:200",
      "enabled": true
    }
  ]
}
```

## CLI Usage Examples

### Basic Operations

```bash
# List all interfaces
tcctl interfaces

# List all policies
tcctl policies

# Create policy from configuration file
tcctl create-policy web_policy config.json

# Test policy before applying (dry run)
tcctl test web_policy

# Apply policy to interface
tcctl apply web_policy

# Show current TC status for interface
tcctl status eth0

# Show TC statistics for interface
tcctl stats eth0

# Remove TC configuration from interface
tcctl remove eth0
```

### Advanced Operations

```bash
# Export policy to YAML
tcctl export web_policy yaml

# Import policy from file
tcctl import policy.yaml

# Monitor interface in real-time
tcctl monitor eth0 --interval 5

# Create HTB policy using wizard
tcctl htb-wizard

# Rollback interface to previous configuration
tcctl rollback eth0

# Clean up old statistics
tcctl cleanup

# Show detailed policy information
tcctl show web_policy

# Delete policy
tcctl delete web_policy
```

## Web API Examples

### Get Interfaces

```bash
curl -X GET http://localhost:8080/api/interfaces
```

Response:
```json
[
  {
    "name": "eth0",
    "type": "ethernet",
    "state": "UP",
    "mtu": 1500,
    "mac_address": "00:11:22:33:44:55",
    "ip_addresses": ["192.168.1.100"],
    "speed": 1000,
    "duplex": "Full"
  }
]
```

### Create HTB Policy

```bash
curl -X POST http://localhost:8080/api/policies/htb \
  -H "Content-Type: application/json" \
  -d '{
    "name": "simple_htb",
    "interface": "eth0",
    "total_rate": "100mbit",
    "classes": [
      {
        "rate": "80mbit",
        "ceil": "100mbit",
        "prio": 1,
        "match": {"dport": 80}
      },
      {
        "rate": "20mbit",
        "ceil": "30mbit",
        "prio": 2,
        "match": {"dport": 22}
      }
    ]
  }'
```

### Apply Policy

```bash
curl -X POST http://localhost:8080/api/policies/simple_htb/apply
```

### Get Statistics

```bash
curl -X GET http://localhost:8080/api/interfaces/eth0/statistics
```

Response:
```json
{
  "interface": "eth0",
  "timestamp": "2025-01-01T12:00:00",
  "qdisc_stats": [
    {
      "bytes_sent": 1234567890,
      "packets_sent": 987654,
      "drops": 123,
      "overlimits": 45,
      "requeues": 0
    }
  ],
  "class_stats": [
    {
      "bytes_sent": 987654321,
      "packets_sent": 654321,
      "drops": 12,
      "overlimits": 5,
      "requeues": 0
    }
  ]
}
```

## Integration with LNMT Scheduler

### Time-based Policy Changes

```python
from datetime import datetime, time
from tc_service import TCManager

def apply_business_hours_policy():
    """Apply different policies based on time of day"""
    tc_manager = TCManager()
    current_time = datetime.now().time()
    
    # Business hours: 8 AM - 6 PM
    business_start = time(8, 0)
    business_end = time(18, 0)
    
    if business_start <= current_time <= business_end:
        # Apply business hours policy - prioritize work traffic
        tc_manager.apply_policy("business_hours_policy")
    else:
        # Apply after hours policy - allow bulk transfers
        tc_manager.apply_policy("after_hours_policy")

# Schedule with LNMT scheduler
# This would be integrated with the main LNMT scheduler
```

### Load-based Policy Adjustment

```python
import psutil
from tc_service import TCManager

def adjust_policy_based_on_load():
    """Adjust QoS policies based on system load"""
    tc_manager = TCManager()
    
    # Get current system load
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    # Adjust policies based on load
    if cpu_percent > 80 or memory_percent > 85:
        # High load - apply strict QoS
        tc_manager.apply_policy("high_load_policy")
    elif cpu_percent > 50 or memory_percent > 60:
        # Medium load - apply balanced QoS
        tc_manager.apply_policy("balanced_policy")
    else:
        # Low load - apply relaxed QoS
        tc_manager.apply_policy("low_load_policy")
```

## Common QoS Scenarios

### 1. Web Server Traffic Shaping

```yaml
name: web_server_qos
description: Optimize for web server performance
interface: eth0
classes:
  - name: http_traffic
    rate: 80mbit
    ceil: 100mbit
    prio: 1
    match: {dport: 80}
  - name: https_traffic
    rate: 80mbit
    ceil: 100mbit
    prio: 1
    match: {dport: 443}
  - name: ssh_management
    rate: 10mbit
    ceil: 20mbit
    prio: 2
    match: {dport: 22}
```

### 2. Office Network QoS

```yaml
name: office_network_qos
description: Office network with VoIP priority
interface: eth0
classes:
  - name: voip_traffic
    rate: 20mbit
    ceil: 30mbit
    prio: 1
    match: {dst: "10.0.1.0/24"}  # VoIP subnet
  - name: business_apps
    rate: 50mbit
    ceil: 70mbit
    prio: 2
    match: {dst: "10.0.2.0/24"}  # Business apps subnet
  - name: internet_browsing
    rate: 30mbit
    ceil: 50mbit
    prio: 3
    match: {dst: "0.0.0.0/0"}    # Default internet traffic
```

### 3. Gaming Network Optimization

```yaml
name: gaming_network_qos
description: Optimize for gaming with low latency
interface: eth0
classes:
  - name: gaming_traffic
    rate: 50mbit
    ceil: 80mbit
    prio: 1
    burst: 15k
    match: {dport: [27015, 7777, 25565]}  # Game ports
  - name: voice_chat
    rate: 10mbit
    ceil: 20mbit
    prio: 1
    match: {dport: [3478, 50000]}  # Discord, TeamSpeak
  - name: streaming
    rate: 30mbit
    ceil: 40mbit
    prio: 2
    match: {dport: [1935, 8080]}  # Streaming ports
```

## Troubleshooting

### Common Issues

1. **Policy Application Fails**
   ```bash
   # Check interface exists and is up
   tcctl interfaces
   
   # Test policy before applying
   tcctl test policy_name
   
   # Check system logs
   journalctl -u lnmt-tc -f
   ```

2. **No Traffic Matching Filters**
   ```bash
   # Verify filter configuration
   tcctl show policy_name
   
   # Check traffic flow
   tcpdump -i eth0 -n
   
   # View TC statistics
   tcctl stats eth0
   ```

3. **Performance Issues**
   ```bash
   # Check for drops and overlimits
   tcctl stats eth0
   
   # Monitor system resources
   htop
   iotop
   
   # Adjust class rates if needed
   tcctl export policy_name
   # Edit and re-import
   ```

### Debug Mode

```bash
# Enable debug logging
export TC_DEBUG=1
tcctl apply policy_name

# View detailed logs
tail -f /var/log/lnmt/tc.log
```

## Performance Tuning

### Optimal Class Configuration

```json
{
  "classes": [
    {
      "classid": "1:10",
      "rate": "80mbit",
      "ceil": "100mbit",
      "burst": "15k",      // Buffer for bursts
      "cburst": "2k",      // Ceiling burst
      "quantum": 1514      // Packet size for fairness
    }
  ]
}
```

### Network Buffer Tuning

```bash
# Increase network buffers for high-throughput scenarios
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf
sysctl -p
```

## Integration Examples

### With Monitoring Systems

```python
# Prometheus metrics export
from prometheus_client import Gauge, start_http_server
from tc_service import TCManager

# Create metrics
tc_bytes_sent = Gauge('tc_bytes_sent_total', 'Total bytes sent', ['interface', 'class'])
tc_packets_sent = Gauge('tc_packets_sent_total', 'Total packets sent', ['interface', 'class'])
tc_drops = Gauge('tc_drops_total', 'Total drops', ['interface', 'class'])

def collect_tc_metrics():
    tc_manager = TCManager()
    interfaces = tc_manager.discover_interfaces()
    
    for interface in interfaces:
        stats = tc_manager.get_statistics(interface.name)
        
        for i, stat in enumerate(stats.get('class_stats', [])):
            tc_bytes_sent.labels(interface=interface.name, class_id=f'class_{i}').set(stat.get('bytes_sent', 0))
            tc_packets_sent.labels(interface=interface.name, class_id=f'class_{i}').set(stat.get('packets_sent', 0))
            tc_drops.labels(interface=interface.name, class_id=f'class_{i}').set(stat.get('drops', 0))

# Start metrics server
start_http_server(8000)
```

### With Configuration Management

```python
# Ansible integration example
- name: Apply TC policy
  uri:
    url: "http://{{ inventory_hostname }}:8080/api/policies/{{ policy_name }}/apply"
    method: POST
  delegate_to: localhost

- name: Wait for policy application
  uri:
    url: "http://{{ inventory_hostname }}:8080/api/interfaces/{{ interface_name }}/status"
    method: GET
  register: tc_status
  until: tc_status.json.qdiscs | length > 0
  retries: 5
  delay: 2
```

This comprehensive TC/QoS module provides enterprise-grade traffic control capabilities with modern web management, CLI tools, and extensive integration options for the LNMT platform.