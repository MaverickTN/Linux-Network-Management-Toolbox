// tests/performance/load-test.js
// k6 Performance Testing Script for LNMT

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const responseTimeAPI = new Trend('response_time_api');
const responseTimeWeb = new Trend('response_time_web');
const requestCount = new Counter('request_count');

// Test configuration
export const options = {
  scenarios: {
    // Smoke test - basic functionality
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { test_type: 'smoke' },
    },
    
    // Load test - normal usage
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 },
        { duration: '5m', target: 10 },
        { duration: '2m', target: 0 },
      ],
      tags: { test_type: 'load' },
    },
    
    // Stress test - breaking point
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 20 },
        { duration: '2m', target: 50 },
        { duration: '5m', target: 50 },
        { duration: '2m', target: 0 },
      ],
      tags: { test_type: 'stress' },
    },
    
    // Spike test - sudden traffic
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 5 },
        { duration: '30s', target: 5 },
        { duration: '10s', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '10s', target: 5 },
        { duration: '3m', target: 5 },
        { duration: '10s', target: 0 },
      ],
      tags: { test_type: 'spike' },
    },
  },
  
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.05'],
    response_time_api: ['p(95)<300'],
    response_time_web: ['p(95)<800'],
    error_rate: ['rate<0.05'],
  },
};

// Base URL configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

// Test data
const testUsers = [
  { username: 'admin', password: 'admin123' },
  { username: 'user1', password: 'user123' },
  { username: 'test', password: 'test123' },
];

// Authentication token storage
let authToken = '';

export function setup() {
  console.log('Setting up performance tests...');
  
  // Authenticate and get token
  const loginResponse = http.post(`${BASE_URL}/auth/login`, {
    username: testUsers[0].username,
    password: testUsers[0].password,
  });
  
  if (loginResponse.status === 200) {
    const responseBody = JSON.parse(loginResponse.body);
    authToken = responseBody.token;
    console.log('Authentication successful');
  }
  
  return { authToken };
}

export default function(data) {
  const token = data ? data.authToken : authToken;
  
  // Test scenarios based on execution context
  const scenario = __ENV.K6_SCENARIO || 'mixed';
  
  switch (scenario) {
    case 'api_only':
      testAPIEndpoints(token);
      break;
    case 'web_only':
      testWebInterface();
      break;
    case 'auth_flow':
      testAuthenticationFlow();
      break;
    case 'device_management':
      testDeviceManagement(token);
      break;
    case 'dns_management':
      testDNSManagement(token);
      break;
    default:
      testMixedWorkload(token);
  }
  
  requestCount.add(1);
  sleep(Math.random() * 2 + 1); // Random sleep 1-3 seconds
}

function testAPIEndpoints(token) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  
  // Health check
  let response = http.get(`${BASE_URL}/health`);
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
  });
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // API version endpoint
  response = http.get(`${BASE_URL}/api/version`);
  check(response, {
    'version endpoint status is 200': (r) => r.status === 200,
    'version response contains version': (r) => r.body.includes('version'),
  });
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // Device list endpoint
  if (token) {
    response = http.get(`${BASE_URL}/api/devices`, { headers });
    check(response, {
      'devices list status is 200': (r) => r.status === 200,
      'devices response is JSON': (r) => {
        try {
          JSON.parse(r.body);
          return true;
        } catch {
          return false;
        }
      },
    });
    responseTimeAPI.add(response.timings.duration);
    errorRate.add(response.status !== 200);
  }
  
  // DNS records endpoint
  if (token) {
    response = http.get(`${BASE_URL}/api/dns/records`, { headers });
    check(response, {
      'dns records status is 200 or 404': (r) => [200, 404].includes(r.status),
    });
    responseTimeAPI.add(response.timings.duration);
    errorRate.add(![200, 404].includes(response.status));
  }
}

function testWebInterface() {
  // Dashboard page
  let response = http.get(`${BASE_URL}/`);
  check(response, {
    'dashboard loads successfully': (r) => r.status === 200,
    'dashboard contains expected content': (r) => r.body.includes('LNMT'),
    'dashboard response time < 1s': (r) => r.timings.duration < 1000,
  });
  responseTimeWeb.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // Login page
  response = http.get(`${BASE_URL}/login`);
  check(response, {
    'login page loads': (r) => r.status === 200,
    'login form present': (r) => r.body.includes('login') || r.body.includes('username'),
  });
  responseTimeWeb.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // Static assets
  response = http.get(`${BASE_URL}/static/css/dashboard.css`);
  check(response, {
    'CSS loads': (r) => [200, 404].includes(r.status),
  });
  
  response = http.get(`${BASE_URL}/static/js/dashboard.js`);
  check(response, {
    'JavaScript loads': (r) => [200, 404].includes(r.status),
  });
}

function testAuthenticationFlow() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  
  // Login attempt
  const response = http.post(`${BASE_URL}/auth/login`, {
    username: user.username,
    password: user.password,
  });
  
  const success = check(response, {
    'login successful': (r) => r.status === 200,
    'login response contains token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return 'token' in body || 'access_token' in body;
      } catch {
        return false;
      }
    },
    'login response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // If login successful, test logout
  if (success && response.status === 200) {
    try {
      const body = JSON.parse(response.body);
      const token = body.token || body.access_token;
      
      const logoutResponse = http.post(`${BASE_URL}/auth/logout`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      check(logoutResponse, {
        'logout successful': (r) => [200, 204].includes(r.status),
      });
      
      responseTimeAPI.add(logoutResponse.timings.duration);
      errorRate.add(![200, 204].includes(logoutResponse.status));
    } catch (e) {
      console.error('Error in logout test:', e);
    }
  }
}

function testDeviceManagement(token) {
  if (!token) return;
  
  const headers = { Authorization: `Bearer ${token}` };
  
  // List devices
  let response = http.get(`${BASE_URL}/api/devices`, { headers });
  check(response, {
    'device list accessible': (r) => r.status === 200,
  });
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(response.status !== 200);
  
  // Create test device
  const testDevice = {
    name: `test-device-${Date.now()}`,
    ip: `192.168.1.${Math.floor(Math.random() * 254) + 1}`,
    mac: generateRandomMAC(),
    type: 'test',
  };
  
  response = http.post(`${BASE_URL}/api/devices`, JSON.stringify(testDevice), {
    headers: { ...headers, 'Content-Type': 'application/json' },
  });
  
  const deviceCreated = check(response, {
    'device creation successful': (r) => [200, 201].includes(r.status),
  });
  
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(![200, 201].includes(response.status));
  
  // If device created, try to delete it
  if (deviceCreated && [200, 201].includes(response.status)) {
    try {
      const deviceData = JSON.parse(response.body);
      const deviceId = deviceData.id;
      
      if (deviceId) {
        const deleteResponse = http.del(`${BASE_URL}/api/devices/${deviceId}`, null, { headers });
        check(deleteResponse, {
          'device deletion successful': (r) => [200, 204].includes(r.status),
        });
        responseTimeAPI.add(deleteResponse.timings.duration);
        errorRate.add(![200, 204].includes(deleteResponse.status));
      }
    } catch (e) {
      console.error('Error in device cleanup:', e);
    }
  }
}

function testDNSManagement(token) {
  if (!token) return;
  
  const headers = { Authorization: `Bearer ${token}` };
  
  // List DNS records
  let response = http.get(`${BASE_URL}/api/dns/records`, { headers });
  check(response, {
    'DNS records accessible': (r) => [200, 404].includes(r.status),
  });
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(![200, 404].includes(response.status));
  
  // Create test DNS record
  const testRecord = {
    name: `test-${Date.now()}.example.com`,
    type: 'A',
    value: `192.168.1.${Math.floor(Math.random() * 254) + 1}`,
    ttl: 300,
  };
  
  response = http.post(`${BASE_URL}/api/dns/records`, JSON.stringify(testRecord), {
    headers: { ...headers, 'Content-Type': 'application/json' },
  });
  
  check(response, {
    'DNS record creation': (r) => [200, 201, 404, 501].includes(r.status), // 404/501 if not implemented
  });
  
  responseTimeAPI.add(response.timings.duration);
  errorRate.add(![200, 201, 404, 501].includes(response.status));
}

function testMixedWorkload(token) {
  const scenarios = [
    () => testAPIEndpoints(token),
    () => testWebInterface(),
    () => testAuthenticationFlow(),
  ];
  
  if (token) {
    scenarios.push(
      () => testDeviceManagement(token),
      () => testDNSManagement(token)
    );
  }
  
  // Randomly select and execute a scenario
  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();
}

// Utility functions
function generateRandomMAC() {
  const chars = '0123456789ABCDEF';
  let mac = '';
  for (let i = 0; i < 6; i++) {
    if (i > 0) mac += ':';
    mac += chars[Math.floor(Math.random() * 16)];
    mac += chars[Math.floor(Math.random() * 16)];
  }
  return mac;
}

export function teardown(data) {
  console.log('Performance test teardown completed');
}

// Handle check failures
export function handleSummary(data) {
  const summary = {
    test_duration: data.metrics.iteration_duration.values.avg,
    request_count: data.metrics.http_reqs.count,
    error_rate: data.metrics.http_req_failed.rate,
    response_time_p95: data.metrics.http_req_duration.values['p(95)'],
    response_time_p99: data.metrics.http_req_duration.values['p(99)'],
    throughput: data.metrics.http_reqs.rate,
  };
  
  return {
    'performance-results.json': JSON.stringify(summary, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}