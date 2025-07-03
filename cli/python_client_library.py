#!/usr/bin/env python3
"""
LNMT Python API Client Library

A comprehensive Python client for the Linux Network Management Toolkit (LNMT) REST API.
Provides easy-to-use methods for all LNMT functionality including device management,
VLAN configuration, DNS management, and system monitoring.

Example usage:
    from lnmt_api import LNMTClient
    
    client = LNMTClient("https://api.lnmt.local")
    client.login("admin", "password")
    
    devices = client.get_devices()
    for device in devices:
        print(f"{device['hostname']}: {device['ip_address']}")
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import logging
from urllib.parse import urljoin, urlencode


class LNMTAPIError(Exception):
    """Base exception for LNMT API errors"""
    def __init__(self, message: str, status_code: int = None, response: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class LNMTAuthenticationError(LNMTAPIError):
    """Authentication-related errors"""
    pass


class LNMTNotFoundError(LNMTAPIError):
    """Resource not found errors"""
    pass


class LNMTRateLimitError(LNMTAPIError):
    """Rate limiting errors"""
    pass


class LNMTClient:
    """
    LNMT API Client
    
    Main client class for interacting with the LNMT REST API.
    Handles authentication, request management, and provides methods
    for all API endpoints.
    """
    
    def __init__(self, base_url: str, api_key: str = None, verify_ssl: bool = True):
        """
        Initialize LNMT client
        
        Args:
            base_url: Base URL of the LNMT server (e.g., "https://api.lnmt.local")
            api_key: Optional API key for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = None
        self.token_expires = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'LNMT-Python-Client/2.0.0'
        })
        
        # Set API key if provided
        if api_key:
            self.session.headers['X-API-Key'] = api_key
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     params: Dict = None, files: Dict = None, 
                     auth_required: bool = True) -> Union[Dict, List]:
        """
        Make HTTP request to LNMT API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            files: Files to upload
            auth_required: Whether authentication is required
            
        Returns:
            Response data (dict or list)
            
        Raises:
            LNMTAPIError: For API errors
            LNMTAuthenticationError: For authentication errors
            LNMTNotFoundError: For 404 errors
            LNMTRateLimitError: For rate limiting errors
        """
        # Check if token needs refresh
        if auth_required and self.token and self.token_expires:
            if datetime.now() > self.token_expires:
                self.logger.info("Token expired, refreshing...")
                self.refresh_token()
        
        # Build URL
        url = urljoin(self.base_url, endpoint)
        
        # Prepare request kwargs
        kwargs = {
            'params': params,
            'timeout': 30
        }
        
        # Handle request body
        if files:
            kwargs['files'] = files
            if data:
                kwargs['data'] = data
        elif data:
            kwargs['json'] = data
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method, url, **kwargs)
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise LNMTAuthenticationError(
                    "Authentication failed", 
                    response.status_code, 
                    response.json() if response.content else None
                )
            elif response.status_code == 404:
                raise LNMTNotFoundError(
                    "Resource not found", 
                    response.status_code,
                    response.json() if response.content else None
                )
            elif response.status_code == 429:
                raise LNMTRateLimitError(
                    "Rate limit exceeded", 
                    response.status_code,
                    response.json() if response.content else None
                )
            elif not response.ok:
                error_data = response.json() if response.content else {}
                raise LNMTAPIError(
                    f"API request failed: {response.status_code}", 
                    response.status_code, 
                    error_data
                )
            
            # Return response data
            if response.status_code == 204:  # No content
                return None
            
            if response.content:
                return response.json()
            return None
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise LNMTAPIError(f"Request failed: {e}")
    
    # Authentication Methods
    def login(self, username: str, password: str, remember_me: bool = False) -> Dict:
        """
        Authenticate with username and password
        
        Args:
            username: Username
            password: Password  
            remember_me: Whether to extend token lifetime
            
        Returns:
            Authentication response with token info
        """
        data = {
            'username': username,
            'password': password,
            'remember_me': remember_me
        }
        
        response = self._make_request('POST', '/api/v1/auth/login', data, auth_required=False)
        
        # Store token
        self.token = response['token']
        self.session.headers['Authorization'] = f'Bearer {self.token}'
        
        # Calculate token expiration
        expires_in = response.get('expires_in', 3600)  # Default 1 hour
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
        
        self.logger.info(f"Successfully authenticated as {username}")
        return response
    
    def logout(self) -> None:
        """Logout and invalidate current token"""
        if self.token:
            try:
                self._make_request('POST', '/api/v1/auth/logout')
            except LNMTAPIError:
                pass  # Ignore errors during logout
            
            # Clear token
            self.token = None
            self.token_expires = None
            if 'Authorization' in self.session.headers:
                del self.session.headers['Authorization']
            
            self.logger.info("Successfully logged out")
    
    def refresh_token(self) -> Dict:
        """Refresh JWT token"""
        response = self._make_request('POST', '/api/v1/auth/refresh')
        
        # Update token
        self.token = response['token']
        self.session.headers['Authorization'] = f'Bearer {self.token}'
        
        # Update expiration
        expires_in = response.get('expires_in', 3600)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        
        self.logger.info("Token refreshed successfully")
        return response
    
    def get_current_user(self) -> Dict:
        """Get current user information"""
        return self._make_request('GET', '/api/v1/auth/user')
    
    # Device Management Methods
    def get_devices(self, status: str = None, device_type: str = None, 
                   vlan: int = None, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get list of devices
        
        Args:
            status: Filter by device status (online, offline, unknown)
            device_type: Filter by device type
            vlan: Filter by VLAN ID
            limit: Maximum number of devices to return
            offset: Number of devices to skip
            
        Returns:
            Dict with devices list and pagination info
        """
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        if device_type:
            params['type'] = device_type
        if vlan:
            params['vlan'] = vlan
            
        return self._make_request('GET', '/api/v1/devices', params=params)
    
    def get_device(self, device_id: str) -> Dict:
        """Get specific device by ID"""
        return self._make_request('GET', f'/api/v1/devices/{device_id}')
    
    def create_device(self, ip_address: str, hostname: str = None, 
                     mac_address: str = None, device_type: str = None,
                     vlan_id: int = None, tags: List[str] = None) -> Dict:
        """
        Create new device
        
        Args:
            ip_address: Device IP address (required)
            hostname: Device hostname
            mac_address: Device MAC address
            device_type: Type of device
            vlan_id: VLAN ID
            tags: List of tags
            
        Returns:
            Created device data
        """
        data = {'ip_address': ip_address}
        if hostname:
            data['hostname'] = hostname
        if mac_address:
            data['mac_address'] = mac_address
        if device_type:
            data['device_type'] = device_type
        if vlan_id:
            data['vlan_id'] = vlan_id
        if tags:
            data['tags'] = tags
            
        return self._make_request('POST', '/api/v1/devices', data)
    
    def update_device(self, device_id: str, hostname: str = None,
                     device_type: str = None, vlan_id: int = None,
                     tags: List[str] = None) -> Dict:
        """Update existing device"""
        data = {}
        if hostname:
            data['hostname'] = hostname
        if device_type:
            data['device_type'] = device_type
        if vlan_id:
            data['vlan_id'] = vlan_id
        if tags:
            data['tags'] = tags
            
        return self._make_request('PUT', f'/api/v1/devices/{device_id}', data)
    
    def delete_device(self, device_id: str) -> None:
        """Delete device"""
        self._make_request('DELETE', f'/api/v1/devices/{device_id}')
    
    def start_network_scan(self, subnet: str = None, aggressive: bool = False) -> Dict:
        """
        Start network discovery scan
        
        Args:
            subnet: Network subnet to scan (e.g., "192.168.1.0/24")
            aggressive: Use aggressive scanning mode
            
        Returns:
            Scan job information
        """
        data = {'aggressive': aggressive}
        if subnet:
            data['subnet'] = subnet
            
        return self._make_request('POST', '/api/v1/devices/scan', data)
    
    def get_scan_status(self, scan_id: str) -> Dict:
        """Get network scan status"""
        return self._make_request('GET', f'/api/v1/devices/scan/{scan_id}')
    
    # VLAN Management Methods
    def get_vlans(self) -> Dict:
        """Get list of all VLANs"""
        return self._make_request('GET', '/api/v1/vlans')
    
    def get_vlan(self, vlan_id: int) -> Dict:
        """Get specific VLAN by ID"""
        return self._make_request('GET', f'/api/v1/vlans/{vlan_id}')
    
    def create_vlan(self, vlan_id: int, name: str, description: str = None,
                   subnet: str = None, gateway: str = None) -> Dict:
        """
        Create new VLAN
        
        Args:
            vlan_id: VLAN ID (1-4094)
            name: VLAN name
            description: VLAN description
            subnet: VLAN subnet (CIDR notation)
            gateway: Gateway IP address
            
        Returns:
            Created VLAN data
        """
        data = {'id': vlan_id, 'name': name}
        if description:
            data['description'] = description
        if subnet:
            data['subnet'] = subnet
        if gateway:
            data['gateway'] = gateway
            
        return self._make_request('POST', '/api/v1/vlans', data)
    
    def update_vlan(self, vlan_id: int, name: str = None, description: str = None,
                   subnet: str = None, gateway: str = None) -> Dict:
        """Update existing VLAN"""
        data = {}
        if name:
            data['name'] = name
        if description:
            data['description'] = description
        if subnet:
            data['subnet'] = subnet
        if gateway:
            data['gateway'] = gateway
            
        return self._make_request('PUT', f'/api/v1/vlans/{vlan_id}', data)
    
    def delete_vlan(self, vlan_id: int) -> None:
        """Delete VLAN"""
        self._make_request('DELETE', f'/api/v1/vlans/{vlan_id}')
    
    # DNS Management Methods
    def get_dns_zones(self) -> Dict:
        """Get list of DNS zones"""
        return self._make_request('GET', '/api/v1/dns/zones')
    
    def create_dns_zone(self, name: str, zone_type: str, master_ip: str = None) -> Dict:
        """
        Create DNS zone
        
        Args:
            name: Zone name
            zone_type: Zone type (master, slave, forward)
            master_ip: Master server IP (for slave zones)
        """
        data = {'name': name, 'type': zone_type}
        if master_ip:
            data['master_ip'] = master_ip
            
        return self._make_request('POST', '/api/v1/dns/zones', data)
    
    def get_dns_records(self, zone_name: str) -> Dict:
        """Get DNS records for a zone"""
        return self._make_request('GET', f'/api/v1/dns/zones/{zone_name}/records')
    
    def create_dns_record(self, zone_name: str, name: str, record_type: str,
                         value: str, ttl: int = 3600, priority: int = None) -> Dict:
        """
        Create DNS record
        
        Args:
            zone_name: DNS zone name
            name: Record name
            record_type: Record type (A, AAAA, CNAME, MX, etc.)
            value: Record value
            ttl: Time to live
            priority: Priority (for MX records)
        """
        data = {
            'name': name,
            'type': record_type,
            'value': value,
            'ttl': ttl
        }
        if priority:
            data['priority'] = priority
            
        return self._make_request('POST', f'/api/v1/dns/zones/{zone_name}/records', data)
    
    # Reporting Methods
    def get_available_reports(self) -> Dict:
        """Get list of available reports"""
        return self._make_request('GET', '/api/v1/reports')
    
    def generate_report(self, report_type: str, format: str = 'json', 
                       period: str = '24h') -> Union[Dict, str]:
        """
        Generate system report
        
        Args:
            report_type: Type of report (network_summary, device_status, etc.)
            format: Output format (json, csv, pdf)
            period: Time period (1h, 24h, 7d, 30d)
            
        Returns:
            Report data (format depends on requested format)
        """
        params = {'format': format, 'period': period}
        return self._make_request('GET', f'/api/v1/reports/{report_type}', params=params)
    
    # Health Monitoring Methods
    def get_health_status(self) -> Dict:
        """Get system health status"""
        return self._make_request('GET', '/api/v1/health', auth_required=False)
    
    def get_system_metrics(self) -> Dict:
        """Get detailed system metrics"""
        return self._make_request('GET', '/api/v1/health/metrics')
    
    # Backup/Restore Methods
    def create_backup(self, include_configs: bool = True, include_data: bool = True,
                     compression: bool = True) -> Dict:
        """
        Create system backup
        
        Args:
            include_configs: Include configuration files
            include_data: Include data files
            compression: Enable compression
            
        Returns:
            Backup job information
        """
        data = {
            'include_configs': include_configs,
            'include_data': include_data,
            'compression': compression
        }
        return self._make_request('POST', '/api/v1/backup', data)
    
    def get_backups(self) -> Dict:
        """Get list of available backups"""
        return self._make_request('GET', '/api/v1/backup')
    
    def restore_backup(self, backup_id: str) -> Dict:
        """Restore from backup"""
        return self._make_request('POST', f'/api/v1/backup/{backup_id}/restore')
    
    # Scheduler Methods
    def get_scheduled_jobs(self) -> Dict:
        """Get list of scheduled jobs"""
        return self._make_request('GET', '/api/v1/scheduler/jobs')
    
    def create_scheduled_job(self, name: str, job_type: str, schedule: str,
                           description: str = None, enabled: bool = True,
                           parameters: Dict = None) -> Dict:
        """
        Create scheduled job
        
        Args:
            name: Job name
            job_type: Job type (backup, scan, report, maintenance)
            schedule: Cron expression
            description: Job description
            enabled: Whether job is enabled
            parameters: Job-specific parameters
            
        Returns:
            Created job data
        """
        data = {
            'name': name,
            'type': job_type,
            'schedule': schedule,
            'enabled': enabled
        }
        if description:
            data['description'] = description
        if parameters:
            data['parameters'] = parameters
            
        return self._make_request('POST', '/api/v1/scheduler/jobs', data)
    
    # Utility Methods
    def wait_for_scan(self, scan_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict:
        """
        Wait for network scan to complete
        
        Args:
            scan_id: Scan ID to wait for
            timeout: Maximum time to wait (seconds)
            poll_interval: How often to check status (seconds)
            
        Returns:
            Final scan status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_scan_status(scan_id)
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            time.sleep(poll_interval)
        
        raise LNMTAPIError(f"Scan {scan_id} did not complete within {timeout} seconds")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - logout if authenticated"""
        if self.token:
            self.logout()


# Convenience functions for common operations
def quick_device_scan(base_url: str, username: str, password: str, 
                     subnet: str = None) -> List[Dict]:
    """
    Quick device scan - login, scan, wait for results, logout
    
    Args:
        base_url: LNMT server URL
        username: Username
        password: Password
        subnet: Subnet to scan
        
    Returns:
        List of discovered devices
    """
    with LNMTClient(base_url) as client:
        client.login(username, password)
        
        # Start scan
        scan_result = client.start_network_scan(subnet)
        scan_id = scan_result['scan_id']
        
        # Wait for completion
        final_status = client.wait_for_scan(scan_id)
        
        if final_status['status'] == 'failed':
            raise LNMTAPIError(f"Scan failed: {final_status.get('error_message', 'Unknown error')}")
        
        # Get updated device list
        devices_result = client.get_devices()
        return devices_result['devices']


def export_device_inventory(base_url: str, username: str, password: str, 
                          filename: str = None) -> str:
    """
    Export device inventory to CSV
    
    Args:
        base_url: LNMT server URL
        username: Username  
        password: Password
        filename: Output filename (optional)
        
    Returns:
        CSV data as string
    """
    with LNMTClient(base_url) as client:
        client.login(username, password)
        
        # Generate device status report in CSV format
        csv_data = client.generate_report('device_status', format='csv')
        
        if filename:
            with open(filename, 'w') as f:
                f.write(csv_data)
        
        return csv_data


if __name__ == '__main__':
    # Example usage
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python lnmt_api.py <server_url> <username> <password>")
        sys.exit(1)
    
    server_url = sys.argv[1]
    username = sys.argv[2] 
    password = sys.argv[3]
    
    # Enable debug logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        with LNMTClient(server_url) as client:
            # Login
            print(f"Connecting to {server_url}...")
            auth_result = client.login(username, password)
            print(f"Authenticated as: {auth_result['user']['username']}")
            
            # Get system health
            health = client.get_health_status()
            print(f"System status: {health['status']}")
            
            # List devices
            devices_result = client.get_devices(limit=10)
            print(f"\nFound {devices_result['total']} devices:")
            for device in devices_result['devices']:
                status_icon = "🟢" if device['status'] == 'online' else "🔴"
                print(f"  {status_icon} {device['hostname']} ({device['ip_address']})")
            
            # List VLANs
            vlans_result = client.get_vlans()
            print(f"\nConfigured VLANs: {len(vlans_result['vlans'])}")
            for vlan in vlans_result['vlans']:
                print(f"  VLAN {vlan['id']}: {vlan['name']}")
    
    except LNMTAPIError as e:
        print(f"API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)