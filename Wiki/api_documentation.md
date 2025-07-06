# LNMT API Documentation

## Overview

The Linux Network Management Toolkit (LNMT) provides a comprehensive REST API for managing network infrastructure. This documentation covers the API specification, client libraries, and usage examples.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Client Libraries](#client-libraries)
4. [API Reference](#api-reference)
5. [Examples](#examples)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- LNMT server running and accessible
- Valid user credentials or API key
- Network access to the LNMT server

### Base URLs

- Production: `https://api.lnmt.local`
- Development: `http://localhost:8080`
- Demo: `https://demo.lnmt.io`

### Quick Start

```bash
# Test server connectivity
curl -k https://api.lnmt.local/api/v1/health

# Login and get token
curl -X POST https://api.lnmt.local/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

## Authentication

LNMT API supports two authentication methods:

### JWT Token Authentication (Recommended)

1. **Login** to obtain a JWT token
2. **Include token** in subsequent requests
3. **Refresh token** before expiration

```bash
# Login
response=$(curl -X POST https://api.lnmt.local/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}')

# Extract token
token=$(echo "$response" | jq -r '.token')

# Use token in requests
curl -H "Authorization: Bearer $token" \
  https://api.lnmt.local/api/v1/devices
```

### API Key Authentication

API keys provide persistent authentication without expiration:

```bash
curl -H "X-API-Key: your-api-key" \
  https://api.lnmt.local/api/v1/devices
```

### Token Refresh

JWT tokens expire after a configured period. Refresh before expiration:

```bash
curl -X POST https://api.lnmt.local/api/v1/auth/refresh \
  -H "Authorization: Bearer $token"
```

## Client Libraries

### Python Client

The Python client provides a comprehensive interface to the LNMT API:

```python
from lnmt_api import LNMTClient

# Create client and login
with LNMTClient("https://api.lnmt.local") as client:
    client.login("admin", "password")
    
    # Get devices
    devices = client.get_devices()
    print(f"Found {devices['total']} devices")
    
    # Create VLAN
    vlan = client.create_vlan(
        vlan_id=100,
        name="Guest Network",
        subnet="192.168.100.0/24"
    )
```

#### Key Features

- **Automatic token management** - handles login, refresh, and logout
- **Error handling** - comprehensive exception hierarchy
- **Type hints** - full typing support for IDE integration
- **Context manager** - automatic cleanup with `with` statements
- **Convenience functions** - high-level operations like `quick_device_scan()`

#### Installation

```bash
# Install dependencies
pip install requests

# Use the client
python -c "from lnmt_api import LNMTClient; print('Client loaded successfully')"
```

### Bash Client

The Bash client provides command-line access to LNMT functionality:

```bash
# Source the client library
source lnmt_api.sh

# Login
lnmt_login "https://api.lnmt.local" "admin" "password"

# Get devices with pretty printing
devices_json=$(lnmt_get_devices)
lnmt_pretty_print_devices "$devices_json"

# Create VLAN
lnmt_create_vlan 200 "IoT Network" "IoT devices" "192.168.200.0/24" "192.168.200.1"

# Logout
lnmt_logout
```

#### Key Features

- **Zero dependencies** - uses standard tools (curl, jq)
- **Pretty printing** - formatted output for humans
- **Configuration persistence** - saves settings to `~/.lnmt/config`
- **Error handling** - proper HTTP status code handling
- **Debug mode** - detailed logging when `LNMT_DEBUG=true`

#### Requirements

```bash
# Install required tools
sudo apt-get install curl jq
# or
brew install curl jq
```

## API Reference

### Core Endpoints

#### Health Check
- `GET /api/v1/health` - System health status (no auth required)
- `GET /api/v1/health/metrics` - Detailed system metrics

#### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/user` - Current user info

#### Device Management
- `GET /api/v1/devices` - List devices
- `POST /api/v1/devices` - Create device
- `GET /api/v1/devices/{id}` - Get device details
- `PUT /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Delete device
- `POST /api/v1/devices/scan` - Start network scan
- `GET /api/v1/devices/scan/{id}` - Get scan status

#### VLAN Management
- `GET /api/v1/vlans` - List VLANs
- `POST /api/v1/vlans` - Create VLAN
- `GET /api/v1/vlans/{id}` - Get VLAN details
- `PUT /api/v1/vlans/{id}` - Update VLAN
- `DELETE /api/v1/vlans/{id}` - Delete VLAN

#### DNS Management
- `GET /api/v1/dns/zones` - List DNS zones
- `POST /api/v1/dns/zones` - Create DNS zone
- `GET /api/v1/dns/zones/{zone}/records` - List DNS records
- `POST /api/v1/dns/zones/{zone}/records` - Create DNS record

#### Reporting
- `GET /api/v1/reports` - Available reports
- `GET /api/v1/reports/{type}` - Generate report

#### Backup/Restore
- `GET /api/v1/backup` - List backups
- `POST /api/v1/backup` - Create backup
- `POST /api/v1/backup/{id}/restore` - Restore backup

#### Scheduler
- `GET /api/v1/scheduler/jobs` - List scheduled jobs
- `POST /api/v1/scheduler/jobs` - Create scheduled job

### Request/Response Formats

All API endpoints use JSON for request and response bodies:

```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer jwt-token-here"
}
```

### Pagination

List endpoints support pagination:

```bash
GET /api/v1/devices?limit=50&offset=100
```

Response includes pagination metadata:

```json
{
  "devices": [...],
  "total": 500,
  "pagination": {
    "limit": 50,
    "offset": 100,
    "has_more": true
  }
}
```

### Filtering

Many endpoints support filtering:

```bash
# Filter devices by status
GET /api/v1/devices?status=online

# Filter by type
GET /api/v1/devices?type=server

# Filter by VLAN
GET /api/v1/devices?vlan=10

# Combine filters
GET /api/v1/devices?status=online&type=server&vlan=10
```

## Examples

### Device Discovery Workflow

```python
# Python example
with LNMTClient(server_url) as client:
    client.login(username, password)
    
    # Start network scan
    scan = client.start_network_scan("192.168.1.0/24")
    
    # Wait for completion
    result = client.wait_for_scan(scan['scan_id'])
    
    # Get discovered devices
    devices = client.get_devices()
    print(f"Discovered {devices['total']} devices")
```

```bash
# Bash example
source lnmt_api.sh
lnmt_login "$server" "$user" "$pass"

# Start scan and wait
scan_result=$(lnmt_start_network_scan "192.168.1.0/24")
scan_id=$(echo "$scan_result" | jq -r '.scan_id')
lnmt_wait_for_scan "$scan_id"

# Show results
devices_json=$(lnmt_get_devices)
lnmt_pretty_print_devices "$devices_json"
```

### VLAN Configuration

```python
# Create VLANs for different network segments
vlans = [
    {"id": 10, "name": "Management", "subnet": "192.168.10.0/24"},
    {"id": 20, "name": "Servers", "subnet": "192.168.20.0/24"},
    {"id": 30, "name": "Workstations", "subnet": "192.168.30.0/24"},
    {"id": 99, "name": "Guest", "subnet": "192.168.99.0/24"}
]

with LNMTClient(server_url) as client:
    client.login(username, password)
    
    for vlan_config in vlans:
        try:
            vlan = client.create_vlan(**vlan_config)
            print(f"Created VLAN {vlan['id']}: {vlan['name']}")
        except LNMTAPIError as e:
            print(f"Failed to create VLAN {vlan_config['id']}: {e}")
```

### Automated Reporting

```bash
#!/bin/bash
# Daily network report script

source lnmt_api.sh
lnmt_login "$LNMT_SERVER" "$USERNAME" "$PASSWORD"

# Generate reports
echo "Generating daily network reports..."

# Device status report
device_report=$(lnmt_generate_report "device_status" "csv" "24h")
echo "$device_report" > "/reports/device_status_$(date +%Y%m%d).csv"

# Network summary
network_report=$(lnmt_generate_report "network_summary" "json" "24h")
echo "$network_report" > "/reports/network_summary_$(date +%Y%m%d).json"

# Create backup
backup_job=$(lnmt_create_backup "true" "true" "true")
echo "Backup job started: $(echo "$backup_job" | jq -r '.job_id')"

lnmt_logout
echo "Daily reports completed"
```

### Bulk Device Management

```python
# Assign devices to VLANs based on IP ranges
def assign_vlans_by_ip():
    with LNMTClient(server_url) as client:
        client.login(username, password)
        
        devices = client.get_devices()['devices']
        updates = 0
        
        for device in devices:
            ip = device['ip_address']
            current_vlan = device.get('vlan_id')
            
            # Determine target VLAN based on IP
            if ip.startswith('192.168.10.'):
                target_vlan = 10
            elif ip.startswith('192.168.20.'):
                target_vlan = 20
            elif ip.startswith('192.168.30.'):
                target_vlan = 30
            else:
                continue
            
            # Update if different
            if current_vlan != target_vlan:
                client.update_device(device['id'], vlan_id=target_vlan)
                print(f"Assigned {device['hostname']} to VLAN {target_vlan}")
                updates += 1
        
        print(f"Updated {updates} devices")

assign_vlans_by_ip()
```

### Monitoring Dashboard

```python
def create_dashboard():
    with LNMTClient(server_url) as client:
        client.login(username, password)
        
        # Collect data
        health = client.get_health_status()
        metrics = client.get_system_metrics()
        devices = client.get_devices()
        vlans = client.get_vlans()
        
        # Calculate statistics
        total_devices = devices['total']
        online_devices = len([d for d in devices['devices'] if d['status'] == 'online'])
        device_types = {}
        for device in devices['devices']:
            dtype = device.get('device_type', 'unknown')
            device_types[dtype] = device_types.get(dtype, 0) + 1
        
        # Display dashboard
        print("┌─────────────────────────────────────────┐")
        print("│               LNMT Dashboard            │")
        print("├─────────────────────────────────────────┤")
        print(f"│ Status: {health['status']:>30} │")
        print(f"│ CPU: {metrics['cpu_usage']:>33.1f}% │")
        print(f"│ Memory: {metrics['memory_usage']:>29.1f}% │")
        print(f"│ Devices: {online_devices}/{total_devices:>22} │")
        print(f"│ VLANs: {len(vlans['vlans']):>30} │")
        print("├─────────────────────────────────────────┤")
        print("│ Device Types:                           │")
        for dtype, count in sorted(device_types.items()):
            print(f"│   {dtype}: {count:>30} │")
        print("└─────────────────────────────────────────┘")
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `202` - Accepted (async operation started)
- `204` - No Content (successful deletion)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (authentication required/failed)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "error": "validation_failed",
  "message": "Invalid VLAN ID: must be between 1 and 4094",
  "details": {
    "field": "vlan_id",
    "value": 5000,
    "constraint": "range"
  }
}
```

### Python Error Handling

```python
from lnmt_api import LNMTAPIError, LNMTAuthenticationError, LNMTNotFoundError

try:
    device = client.get_device("invalid-id")
except LNMTNotFoundError:
    print("Device not found")
except LNMTAuthenticationError:
    print("Authentication failed - please login")
except LNMTAPIError as e:
    print(f"API error: {e}")
    if e.status_code:
        print(f"HTTP {e.status_code}")
    if e.response:
        print(f"Details: {e.response}")
```

### Bash Error Handling

```bash
# Check return codes
if lnmt_get_device "invalid-id" 2>/dev/null; then
    echo "Device found"
else
    echo "Device not found or error occurred"
fi

# Capture and handle errors
if ! result=$(lnmt_create_vlan 5000 "Invalid" 2>&1); then
    echo "VLAN creation failed: $result"
fi
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limits**: 1000 requests per hour per authenticated user
- **Burst limits**: 100 requests per minute
- **Headers**: Response includes rate limit information

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Handling Rate Limits

```python
import time
from lnmt_api import LNMTRateLimitError

def api_call_with_retry(func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except LNMTRateLimitError as e:
            if attempt < max_retries - 1:
                # Extract retry-after from response
                retry_after = e.response.get('retry_after', 60)
                print(f"Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise
```

## Troubleshooting

### Common Issues

#### SSL Certificate Errors

```bash
# Disable SSL verification (development only)
export LNMT_VERIFY_SSL=false

# Or in Python
client = LNMTClient(server_url, verify_ssl=False)
```

#### Connection Timeouts

```python
# Increase timeout
client = LNMTClient(server_url)
client.session.timeout = 60  # 60 seconds
```

#### Authentication Issues

```bash
# Check token expiration
lnmt_get_current_user

# Refresh token if needed
lnmt_refresh_token

# Or re-login
lnmt_logout
lnmt_login "$server" "$user" "$pass"
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Bash client
export LNMT_DEBUG=true
source lnmt_api.sh

# Python client
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Network Connectivity

```bash
# Test basic connectivity
curl -k https://api.lnmt.local/api/v1/health

# Test with specific timeout
curl --connect-timeout 10 --max-time 30 \
  https://api.lnmt.local/api/v1/health

# Check network path
traceroute api.lnmt.local
```

### Configuration Issues

```bash
# Check configuration
echo "Server: $LNMT_BASE_URL"
echo "Token set: $([ -n "$LNMT_TOKEN" ] && echo 'Yes' || echo 'No')"

# Reset configuration
rm -f ~/.lnmt/config
```

## Best Practices

### Security

1. **Use HTTPS** in production environments
2. **Rotate API keys** regularly
3. **Store credentials securely** - use environment variables or secure vaults
4. **Validate SSL certificates** - don't disable verification in production
5. **Monitor API usage** - watch for unusual patterns

### Performance

1. **Use pagination** for large result sets
2. **Cache results** when appropriate
3. **Batch operations** when possible
4. **Implement retry logic** with exponential backoff
5. **Monitor rate limits** and adjust request frequency

### Development

1. **Use version control** for API scripts
2. **Test with development environment** first
3. **Implement proper error handling**
4. **Log API interactions** for debugging
5. **Document custom scripts** and workflows

### Production Deployment

1. **Use configuration files** for server settings
2. **Implement health checks** for API availability
3. **Set up monitoring** and alerting
4. **Create backup procedures** for configurations
5. **Plan for API versioning** and upgrades

## API Versioning

LNMT API uses semantic versioning:

- **Major version** (v1, v2): Breaking changes
- **Minor version** (v1.1, v1.2): Backward-compatible additions
- **Patch version** (v1.1.1): Bug fixes

### Version Headers

```http
Accept: application/vnd.lnmt.v1+json
```

### Deprecation

Deprecated endpoints include warnings:

```http
Warning: 299 - "Endpoint deprecated, use /api/v2/devices instead"
```

## Support

### Documentation

- API Reference: `https://docs.lnmt.io/api`
- User Guide: `https://docs.lnmt.io/guide`
- Examples: `https://github.com/lnmt/examples`

### Community

- GitHub Issues: `https://github.com/lnmt/lnmt/issues`
- Discussions: `https://github.com/lnmt/lnmt/discussions`
- Wiki: `https://github.com/lnmt/lnmt/wiki`

### Commercial Support

For enterprise support and custom development:
- Email: support@lnmt.io
- Documentation: `https://lnmt.io/support`

---

*This documentation is for LNMT API version 2.0.0. For the latest updates, visit the [official documentation](https://docs.lnmt.io).*