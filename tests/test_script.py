#!/usr/bin/env python3
"""
LNMT Web Dashboard Test Script
Comprehensive testing of all API endpoints and functionality
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional

class LNMTTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
        
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            kwargs['headers'] = headers

        try:
            async with self.session.request(method, url, **kwargs) as response:
                try:
                    data = await response.json()
                except:
                    data = await response.text()
                
                return {
                    'status': response.status,
                    'data': data,
                    'headers': dict(response.headers)
                }
        except Exception as e:
            return {
                'status': 0,
                'data': str(e),
                'headers': {}
            }

    async def test_server_health(self):
        """Test if server is running"""
        response = await self.make_request('GET', '/')
        self.log_test(
            "Server Health Check",
            response['status'] == 200,
            f"Status: {response['status']}"
        )
        return response['status'] == 200

    async def test_authentication(self):
        """Test authentication endpoints"""
        # Test login with valid credentials
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = await self.make_request(
            'POST', 
            '/api/auth/login',
            json=login_data
        )
        
        if response['status'] == 200 and 'access_token' in response['data']:
            self.token = response['data']['access_token']
            self.log_test("Admin Login", True, "Token received")
        else:
            self.log_test("Admin Login", False, f"Status: {response['status']}")
            return False

        # Test getting current user info
        response = await self.make_request('GET', '/api/auth/me')
        self.log_test(
            "Get Current User",
            response['status'] == 200 and 'username' in response['data'],
            f"User: {response['data'].get('username', 'Unknown')}"
        )

        # Test login with invalid credentials
        invalid_login = {
            "username": "invalid",
            "password": "invalid"
        }
        
        response = await self.make_request(
            'POST',
            '/api/auth/login',
            json=invalid_login
        )
        
        self.log_test(
            "Invalid Login Rejection",
            response['status'] == 401,
            f"Status: {response['status']}"
        )

        return True

    async def test_dashboard_api(self):
        """Test dashboard endpoints"""
        response = await self.make_request('GET', '/api/dashboard/summary')
        
        expected_fields = ['total_devices', 'online_devices', 'total_alerts', 'total_vlans']
        has_all_fields = all(field in response['data'] for field in expected_fields)
        
        self.log_test(
            "Dashboard Summary",
            response['status'] == 200 and has_all_fields,
            f"Fields present: {has_all_fields}"
        )

    async def test_devices_api(self):
        """Test device management endpoints"""
        # Get all devices
        response = await self.make_request('GET', '/api/devices')
        self.log_test(
            "Get Devices",
            response['status'] == 200 and isinstance(response['data'], list),
            f"Devices count: {len(response['data']) if isinstance(response['data'], list) else 'N/A'}"
        )

        # Create a test device
        test_device = {
            "hostname": "test-device-01",
            "ip_address": "192.168.100.100",
            "mac_address": "00:11:22:33:44:99",
            "device_type": "workstation"
        }

        response = await self.make_request(
            'POST',
            '/api/devices',
            json=test_device
        )
        
        device_created = response['status'] == 200
        device_id = None
        
        if device_created and isinstance(response['data'], dict):
            device_id = response['data'].get('device_id')
        
        self.log_test(
            "Create Device",
            device_created,
            f"Device ID: {device_id}" if device_id else f"Status: {response['status']}"
        )

        # Delete the test device if it was created
        if device_id:
            response = await self.make_request('DELETE', f'/api/devices/{device_id}')
            self.log_test(
                "Delete Device",
                response['status'] == 200,
                f"Status: {response['status']}"
            )

    async def test_vlans_api(self):
        """Test VLAN management endpoints"""
        response = await self.make_request('GET', '/api/vlans')
        self.log_test(
            "Get VLANs",
            response['status'] == 200 and isinstance(response['data'], list),
            f"VLANs count: {len(response['data']) if isinstance(response['data'], list) else 'N/A'}"
        )

        # Test creating a VLAN
        test_vlan = {
            "vlan_id": 999,
            "name": "Test VLAN",
            "description": "Test VLAN for API testing",
            "subnet": "192.168.999.0/24",
            "gateway": "192.168.999.1"
        }

        response = await self.make_request(
            'POST',
            '/api/vlans',
            json=test_vlan
        )

        vlan_created = response['status'] == 200
        self.log_test(
            "Create VLAN",
            vlan_created,
            f"Status: {response['status']}"
        )

    async def test_dns_api(self):
        """Test DNS management endpoints"""
        response = await self.make_request('GET', '/api/dns')
        self.log_test(
            "Get DNS Records",
            response['status'] == 200 and isinstance(response['data'], list),
            f"DNS records count: {len(response['data']) if isinstance(response['data'], list) else 'N/A'}"
        )

        # Test creating a DNS record
        test_dns = {
            "domain": "test.lnmt.local",
            "record_type": "A",
            "value": "192.168.1.100",
            "ttl": 3600
        }

        response = await self.make_request(
            'POST',
            '/api/dns',
            json=test_dns
        )

        self.log_test(
            "Create DNS Record",
            response['status'] == 200,
            f"Status: {response['status']}"
        )

    async def test_alerts_api(self):
        """Test alerts endpoints"""
        response = await self.make_request('GET', '/api/alerts')
        self.log_test(
            "Get Alerts",
            response['status'] == 200 and isinstance(response['data'], list),
            f"Alerts count: {len(response['data']) if isinstance(response['data'], list) else 'N/A'}"
        )

    async def test_bandwidth_stats(self):
        """Test bandwidth statistics"""
        response = await self.make_request('GET', '/api/stats/bandwidth?hours=24')
        self.log_test(
            "Get Bandwidth Stats",
            response['status'] == 200 and isinstance(response['data'], list),
            f"Data points: {len(response['data']) if isinstance(response['data'], list) else 'N/A'}"
        )

    async def test_unauthorized_access(self):
        """Test unauthorized access protection"""
        # Temporarily remove token
        original_token = self.token
        self.token = None

        response = await self.make_request('GET', '/api/dashboard/summary')
        self.log_test(
            "Unauthorized Access Protection",
            response['status'] == 401,
            f"Status: {response['status']}"
        )

        # Restore token
        self.token = original_token

    async def test_role_based_access(self):
        """Test role-based access control"""
        # Login as regular user
        user_login = {
            "username": "user",
            "password": "user123"
        }

        response = await self.make_request(
            'POST',
            '/api/auth/login',
            json=user_login
        )

        if response['status'] == 200:
            user_token = response['data']['access_token']
            original_token = self.token
            self.token = user_token

            # Test user can access basic endpoints
            response = await self.make_request('GET', '/api/devices')
            self.log_test(
                "User Access - Devices",
                response['status'] == 200,
                f"Status: {response['status']}"
            )

            # Test user cannot create users (admin only)
            new_user = {
                "username": "testuser",
                "email": "test@test.com",
                "password": "password123",
                "role": "user"
            }

            response = await self.make_request(
                'POST',
                '/api/auth/register',
                json=new_user
            )

            self.log_test(
                "User Role Restriction",
                response['status'] == 403,
                f"Status: {response['status']}"
            )

            # Restore admin token
            self.token = original_token

    async def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting LNMT Web Dashboard Tests")
        print("=" * 50)

        start_time = time.time()

        # Test server health first
        if not await self.test_server_health():
            print("❌ Server is not responding. Please start the LNMT web dashboard first.")
            return

        # Authentication tests
        print("\n🔐 Testing Authentication...")
        if not await self.test_authentication():
            print("❌ Authentication failed. Cannot continue with other tests.")
            return

        # API endpoint tests
        print("\n📊 Testing Dashboard API...")
        await self.test_dashboard_api()

        print("\n💻 Testing Devices API...")
        await self.test_devices_api()

        print("\n🌐 Testing VLANs API...")
        await self.test_vlans_api()

        print("\n🔍 Testing DNS API...")
        await self.test_dns_api()

        print("\n⚠️  Testing Alerts API...")
        await self.test_alerts_api()

        print("\n📈 Testing Statistics API...")
        await self.test_bandwidth_stats()

        print("\n🔒 Testing Security...")
        await self.test_unauthorized_access()
        await self.test_role_based_access()

        # Summary
        end_time = time.time()
        duration = end_time - start_time

        print("\n" + "=" * 50)
        print("📋 Test Results Summary")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100
        print(f"📊 Success Rate: {success_rate:.1f}%")

        if self.results['failed'] > 0:
            print("\n❌ Failed Tests:")
            for test in self.results['tests']:
                if not test['passed']:
                    print(f"  - {test['name']}: {test['message']}")

        return self.results['failed'] == 0


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LNMT Web Dashboard Test Suite')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Base URL of the LNMT web dashboard')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()

    async with LNMTTester(args.url) as tester:
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! LNMT Web Dashboard is working correctly.")
            exit(0)
        else:
            print("\n💥 Some tests failed. Please check the LNMT Web Dashboard.")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())