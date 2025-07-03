#!/usr/bin/env python3
"""
LNMT Web API & CLI Performance Profiler
Specialized profiling for web endpoints and CLI commands
"""

import asyncio
import aiohttp
import subprocess
import time
import json
import statistics
import concurrent.futures
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import psutil
import threading
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIEndpointMetrics:
    """Metrics for API endpoint performance"""
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    content_length: int
    memory_usage_mb: float
    cpu_percent: float
    timestamp: float

@dataclass
class CLICommandMetrics:
    """Metrics for CLI command performance"""
    command: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_percent: float
    return_code: int
    stdout_length: int
    stderr_length: int
    timestamp: float

class WebAPIProfiler:
    """Profiler for LNMT Web API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.metrics: List[APIEndpointMetrics] = []
        self.session = None
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def profile_endpoint(self, endpoint: str, method: str = "GET", 
                              payload: Dict = None, headers: Dict = None) -> APIEndpointMetrics:
        """Profile a single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        # Get initial system metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.perf_counter()
        cpu_before = process.cpu_percent()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    content = await response.read()
                    status_code = response.status
                    content_length = len(content)
            elif method.upper() == "POST":
                async with self.session.post(url, json=payload, headers=headers) as response:
                    content = await response.read()
                    status_code = response.status
                    content_length = len(content)
            elif method.upper() == "PUT":
                async with self.session.put(url, json=payload, headers=headers) as response:
                    content = await response.read()
                    status_code = response.status
                    content_length = len(content)
            elif method.upper() == "DELETE":
                async with self.session.delete(url, headers=headers) as response:
                    content = await response.read()
                    status_code = response.status
                    content_length = len(content)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except Exception as e:
            logger.error(f"Error profiling {method} {endpoint}: {e}")
            status_code = 0
            content_length = 0
        
        end_time = time.perf_counter()
        
        # Calculate final metrics
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_after = process.cpu_percent()
        
        metrics = APIEndpointMetrics(
            endpoint=endpoint,
            method=method.upper(),
            response_time_ms=(end_time - start_time) * 1000,
            status_code=status_code,
            content_length=content_length,
            memory_usage_mb=final_memory - initial_memory,
            cpu_percent=(cpu_before + cpu_after) / 2,
            timestamp=time.time()
        )
        
        self.metrics.append(metrics)
        return metrics
    
    async def load_test_endpoint(self, endpoint: str, method: str = "GET", 
                               concurrent_requests: int = 10, total_requests: int = 100,
                               payload: Dict = None) -> Dict[str, Any]:
        """Load test an API endpoint"""
        logger.info(f"Load testing {method} {endpoint} with {concurrent_requests} concurrent requests")
        
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def make_request():
            async with semaphore:
                return await self.profile_endpoint(endpoint, method, payload)
        
        # Create tasks
        tasks = [make_request() for _ in range(total_requests)]
        
        # Execute load test
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()
        
        # Process results
        successful_requests = [r for r in results if isinstance(r, APIEndpointMetrics) and r.status_code == 200]
        failed_requests = [r for r in results if not isinstance(r, APIEndpointMetrics) or r.status_code != 200]
        
        if successful_requests:
            response_times = [r.response_time_ms for r in successful_requests]
            
            load_test_results = {
                'endpoint': endpoint,
                'method': method,
                'total_requests': total_requests,
                'concurrent_requests': concurrent_requests,
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'total_time_seconds': end_time - start_time,
                'requests_per_second': total_requests / (end_time - start_time),
                'response_time_stats': {
                    'min_ms': min(response_times),
                    'max_ms': max(response_times),
                    'mean_ms': statistics.mean(response_times),
                    'median_ms': statistics.median(response_times),
                    'p95_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                    'p99_ms': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
                }
            }
        else:
            load_test_results = {
                'endpoint': endpoint,
                'method': method,
                'total_requests': total_requests,
                'successful_requests': 0,
                'failed_requests': total_requests,
                'error': 'All requests failed'
            }
        
        return load_test_results

class CLIProfiler:
    """Profiler for LNMT CLI commands"""
    
    def __init__(self, cli_base_path: str = "./"):
        self.cli_base_path = cli_base_path
        self.metrics: List[CLICommandMetrics] = []
        
    def profile_command(self, command: List[str], timeout: int = 30) -> CLICommandMetrics:
        """Profile a single CLI command"""
        logger.info(f"Profiling CLI command: {' '.join(command)}")
        
        # Get initial system metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.perf_counter()
        cpu_before = process.cpu_percent()
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                cwd=self.cli_base_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return_code = result.returncode
            stdout_length = len(result.stdout)
            stderr_length = len(result.stderr)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            return_code = -1
            stdout_length = 0
            stderr_length = 0
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return_code = -1
            stdout_length = 0
            stderr_length = 0
        
        end_time = time.perf_counter()
        
        # Calculate final metrics
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_after = process.cpu_percent()
        
        metrics = CLICommandMetrics(
            command=' '.join(command),
            execution_time_ms=(end_time - start_time) * 1000,
            memory_usage_mb=final_memory - initial_memory,
            cpu_percent=(cpu_before + cpu_after) / 2,
            return_code=return_code,
            stdout_length=stdout_length,
            stderr_length=stderr_length,
            timestamp=time.time()
        )
        
        self.metrics.append(metrics)
        return metrics
    
    def batch_profile_commands(self, commands: List[List[str]], max_workers: int = 4) -> List[CLICommandMetrics]:
        """Profile multiple CLI commands in parallel"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_command = {executor.submit(self.profile_command, cmd): cmd for cmd in commands}
            
            for future in concurrent.futures.as_completed(future_to_command):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Command failed: {e}")
        
        return results

class LNMTEndpointProfiler:
    """Comprehensive profiler for all LNMT endpoints and commands"""
    
    def __init__(self, base_url: str = "http://localhost:5000", cli_path: str = "./"):
        self.base_url = base_url
        self.cli_path = cli_path
        self.web_profiler = None
        self.cli_profiler = CLIProfiler(cli_path)
        
    async def profile_all_endpoints(self) -> Dict[str, Any]:
        """Profile all LNMT API endpoints"""
        async with WebAPIProfiler(self.base_url) as profiler:
            self.web_profiler = profiler
            
            # Define endpoints to test based on LNMT manifest
            endpoints_to_test = [
                ("/api/devices", "GET"),
                ("/api/devices", "POST"),
                ("/api/devices/1", "GET"),
                ("/api/devices/1", "PUT"),
                ("/api/devices/1", "DELETE"),
                ("/api/health", "GET"),
                ("/api/health/summary", "GET"),
                ("/api/reports", "GET"),
                ("/api/reports/generate", "POST"),
                ("/api/scheduler/jobs", "GET"),
                ("/api/scheduler/jobs", "POST"),
                ("/api/scheduler/jobs/1", "GET"),
                ("/api/scheduler/jobs/1", "PUT"),
                ("/api/scheduler/jobs/1", "DELETE"),
                ("/api/vlan", "GET"),
                ("/api/vlan", "POST"),
                ("/api/auth/login", "POST"),
                ("/api/auth/logout", "POST"),
                ("/api/backup", "GET"),
                ("/api/backup", "POST"),
                ("/", "GET"),  # Dashboard
                ("/devices", "GET"),  # Devices page
                ("/login", "GET"),  # Login page
            ]
            
            results = {}
            
            for endpoint, method in endpoints_to_test:
                try:
                    # Prepare test payload for POST/PUT requests
                    payload = self._get_test_payload(endpoint, method)
                    
                    # Profile individual request
                    metrics = await profiler.profile_endpoint(endpoint, method, payload)
                    
                    # Load test critical endpoints
                    if self._is_critical_endpoint(endpoint, method):
                        load_test_result = await profiler.load_test_endpoint(
                            endpoint, method, concurrent_requests=5, total_requests=25, payload=payload
                        )
                        results[f"{method} {endpoint}"] = {
                            'single_request': asdict(metrics),
                            'load_test': load_test_result
                        }
                    else:
                        results[f"{method} {endpoint}"] = {
                            'single_request': asdict(metrics)
                        }
                        
                except Exception as e:
                    logger.error(f"Failed to profile {method} {endpoint}: {e}")
                    results[f"{method} {endpoint}"] = {'error': str(e)}
                
                # Brief pause between tests
                await asyncio.sleep(0.1)
            
            return results
    
    def profile_all_cli_commands(self) -> Dict[str, Any]:
        """Profile all LNMT CLI commands"""
        # Define CLI commands to test based on LNMT manifest
        cli_commands = [
            # Auth CLI
            ["python", "cli/authctl_cli.py", "--help"],
            ["python", "cli/authctl_cli.py", "status"],
            
            # Device Tracker CLI
            ["python", "cli/device_tracker_cli.py", "--help"],
            ["python", "cli/device_tracker_cli.py", "scan"],
            ["python", "cli/device_tracker_cli.py", "list"],
            ["python", "cli/device_tracker_cli.py", "status"],
            
            # Health CLI
            ["python", "cli/healthctl_cli.py", "--help"],
            ["python", "cli/healthctl_cli.py", "check"],
            ["python", "cli/healthctl_cli.py", "report"],
            
            # Backup CLI
            ["python", "cli/backup_cli.py", "--help"],
            ["python", "cli/backup_cli.py", "list"],
            ["python", "cli/backup_cli.py", "status"],
            
            # Scheduler CLI
            ["python", "cli/schedctl_cli.py", "--help"],
            ["python", "cli/schedctl_cli.py", "list"],
            ["python", "cli/schedctl_cli.py", "status"],
            
            # VLAN CLI
            ["python", "cli/vlanctl_cli.py", "--help"],
            ["python", "cli/vlanctl_cli.py", "list"],
            ["python", "cli/vlanctl_cli.py", "status"],
            
            # Report CLI
            ["python", "cli/reportctl_cli.py", "--help"],
            ["python", "cli/reportctl_cli.py", "generate"],
            ["python", "cli/reportctl_cli.py", "list"],
            
            # Integrations CLI
            ["python", "cli/integrations_cli.py", "--help"],
            ["python", "cli/integrations_cli.py", "status"],
        ]
        
        logger.info(f"Profiling {len(cli_commands)} CLI commands...")
        
        # Profile commands
        results = {}
        command_metrics = self.cli_profiler.batch_profile_commands(cli_commands, max_workers=2)
        
        # Organize results
        for metrics in command_metrics:
            results[metrics.command] = asdict(metrics)
        
        # Calculate summary statistics
        successful_commands = [m for m in command_metrics if m.return_code == 0]
        failed_commands = [m for m in command_metrics if m.return_code != 0]
        
        if successful_commands:
            execution_times = [m.execution_time_ms for m in successful_commands]
            memory_usage = [m.memory_usage_mb for m in successful_commands]
            
            summary = {
                'total_commands': len(command_metrics),
                'successful_commands': len(successful_commands),
                'failed_commands': len(failed_commands),
                'execution_time_stats': {
                    'min_ms': min(execution_times),
                    'max_ms': max(execution_times),
                    'mean_ms': statistics.mean(execution_times),
                    'median_ms': statistics.median(execution_times)
                },
                'memory_usage_stats': {
                    'min_mb': min(memory_usage),
                    'max_mb': max(memory_usage),
                    'mean_mb': statistics.mean(memory_usage),
                    'median_mb': statistics.median(memory_usage)
                }
            }
        else:
            summary = {
                'total_commands': len(command_metrics),
                'successful_commands': 0,
                'failed_commands': len(failed_commands),
                'error': 'All commands failed'
            }
        
        results['_summary'] = summary
        return results
    
    def _get_test_payload(self, endpoint: str, method: str) -> Optional[Dict]:
        """Get appropriate test payload for POST/PUT requests"""
        if method not in ['POST', 'PUT']:
            return None
            
        # Define test payloads for different endpoints
        payloads = {
            '/api/devices': {
                'name': 'test_device',
                'ip': '192.168.1.100',
                'mac': '00:11:22:33:44:55',
                'type': 'workstation'
            },
            '/api/scheduler/jobs': {
                'name': 'test_job',
                'schedule': '0 0 * * *',
                'command': 'echo "test"',
                'enabled': True
            },
            '/api/reports/generate': {
                'type': 'device_health',
                'time_range': 24,
                'format': 'json'
            },
            '/api/auth/login': {
                'username': 'test_user',
                'password': 'test_password'
            },
            '/api/vlan': {
                'name': 'test_vlan',
                'vlan_id': 100,
                'description': 'Test VLAN'
            },
            '/api/backup': {
                'name': 'test_backup',
                'type': 'full',
                'compression': True
            }
        }
        
        # Return payload if endpoint matches
        for endpoint_pattern, payload in payloads.items():
            if endpoint.startswith(endpoint_pattern):
                return payload
        
        return {}
    
    def _is_critical_endpoint(self, endpoint: str, method: str) -> bool:
        """Determine if endpoint should receive load testing"""
        critical_endpoints = [
            ('/api/devices', 'GET'),
            ('/api/health', 'GET'),
            ('/api/reports', 'GET'),
            ('/api/scheduler/jobs', 'GET'),
            ('/', 'GET'),
            ('/devices', 'GET')
        ]
        
        return (endpoint, method) in critical_endpoints
    
    async def run_comprehensive_profile(self) -> Dict[str, Any]:
        """Run complete profiling suite"""
        logger.info("Starting comprehensive LNMT performance profiling...")
        
        results = {
            'profiling_started': time.time(),
            'system_info': self._get_system_info()
        }
        
        # Profile API endpoints
        logger.info("Profiling API endpoints...")
        try:
            api_results = await self.profile_all_endpoints()
            results['api_endpoints'] = api_results
            
            # Calculate API summary
            successful_endpoints = []
            failed_endpoints = []
            
            for endpoint, data in api_results.items():
                if 'error' in data:
                    failed_endpoints.append(endpoint)
                else:
                    successful_endpoints.append(endpoint)
            
            results['api_summary'] = {
                'total_endpoints': len(api_results),
                'successful_endpoints': len(successful_endpoints),
                'failed_endpoints': len(failed_endpoints),
                'success_rate': len(successful_endpoints) / len(api_results) if api_results else 0
            }
            
        except Exception as e:
            logger.error(f"API profiling failed: {e}")
            results['api_endpoints'] = {'error': str(e)}
        
        # Profile CLI commands
        logger.info("Profiling CLI commands...")
        try:
            cli_results = self.profile_all_cli_commands()
            results['cli_commands'] = cli_results
        except Exception as e:
            logger.error(f"CLI profiling failed: {e}")
            results['cli_commands'] = {'error': str(e)}
        
        # Generate recommendations
        results['recommendations'] = self._generate_performance_recommendations(results)
        results['profiling_completed'] = time.time()
        results['total_profiling_time'] = results['profiling_completed'] - results['profiling_started']
        
        return results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for profiling context"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'disk_usage_gb': psutil.disk_usage('/').total / (1024**3),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'python_version': f"{subprocess.check_output(['python', '--version'], text=True).strip()}"
            }
        except Exception as e:
            return {'error': f"Failed to get system info: {e}"}
    
    def _generate_performance_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Analyze API performance
        if 'api_endpoints' in results and isinstance(results['api_endpoints'], dict):
            slow_endpoints = []
            high_memory_endpoints = []
            
            for endpoint, data in results['api_endpoints'].items():
                if 'single_request' in data:
                    metrics = data['single_request']
                    if metrics.get('response_time_ms', 0) > 1000:  # > 1 second
                        slow_endpoints.append((endpoint, metrics['response_time_ms']))
                    if metrics.get('memory_usage_mb', 0) > 50:  # > 50MB
                        high_memory_endpoints.append((endpoint, metrics['memory_usage_mb']))
            
            if slow_endpoints:
                recommendations.append(
                    f"Optimize slow API endpoints: {', '.join([f'{ep} ({time:.0f}ms)' for ep, time in slow_endpoints[:3]])}"
                )
            
            if high_memory_endpoints:
                recommendations.append(
                    f"Reduce memory usage for endpoints: {', '.join([f'{ep} ({mem:.1f}MB)' for ep, mem in high_memory_endpoints[:3]])}"
                )
        
        # Analyze CLI performance
        if 'cli_commands' in results and isinstance(results['cli_commands'], dict):
            summary = results['cli_commands'].get('_summary', {})
            
            if summary.get('failed_commands', 0) > 0:
                recommendations.append(
                    f"Fix {summary['failed_commands']} failing CLI commands"
                )
            
            exec_stats = summary.get('execution_time_stats', {})
            if exec_stats.get('max_ms', 0) > 5000:  # > 5 seconds
                recommendations.append(
                    f"Optimize slow CLI commands (max: {exec_stats['max_ms']:.0f}ms)"
                )
        
        # System-level recommendations
        system_info = results.get('system_info', {})
        if isinstance(system_info, dict):
            memory_usage_ratio = 1 - (system_info.get('memory_available_gb', 0) / system_info.get('memory_total_gb', 1))
            
            if memory_usage_ratio > 0.8:  # > 80% memory usage
                recommendations.append(
                    "System memory usage is high (>80%) - consider adding more RAM or optimizing memory usage"
                )
            
            if system_info.get('cpu_count', 4) < 4:
                recommendations.append(
                    "Consider increasing CPU cores for better parallel processing performance"
                )
        
        # General recommendations
        recommendations.extend([
            "Implement response caching for frequently accessed endpoints",
            "Consider database connection pooling to reduce connection overhead",
            "Add request/response compression to reduce bandwidth usage",
            "Implement async operations for I/O bound tasks",
            "Consider adding a reverse proxy (nginx) for static content delivery"
        ])
        
        return recommendations

# Standalone profiling utilities
class PerformanceReportGenerator:
    """Generate comprehensive performance reports"""
    
    @staticmethod
    def generate_html_report(results: Dict[str, Any], output_file: str = "lnmt_performance_report.html"):
        """Generate HTML performance report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>LNMT Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 3px; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .error { color: #dc3545; }
        .recommendation { background: #e3f2fd; padding: 10px; margin: 5px 0; border-left: 4px solid #2196f3; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f2f2f2; }
        .chart { width: 100%; height: 300px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>LNMT Performance Profiling Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Total Profiling Time: {total_time:.2f} seconds</p>
    </div>
    
    <div class="section">
        <h2>System Information</h2>
        {system_info_html}
    </div>
    
    <div class="section">
        <h2>API Endpoints Performance</h2>
        {api_performance_html}
    </div>
    
    <div class="section">
        <h2>CLI Commands Performance</h2>
        {cli_performance_html}
    </div>
    
    <div class="section">
        <h2>Performance Recommendations</h2>
        {recommendations_html}
    </div>
</body>
</html>
        """
        
        # Generate HTML sections
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results.get('profiling_completed', time.time())))
        total_time = results.get('total_profiling_time', 0)
        
        # System info
        system_info = results.get('system_info', {})
        system_info_html = "<div class='metric'>" + "</div><div class='metric'>".join([
            f"<strong>{k.replace('_', ' ').title()}:</strong> {v}" for k, v in system_info.items() if not k == 'error'
        ]) + "</div>"
        
        # API performance
        api_summary = results.get('api_summary', {})
        api_performance_html = f"""
        <div class="metric"><strong>Total Endpoints:</strong> {api_summary.get('total_endpoints', 0)}</div>
        <div class="metric success"><strong>Successful:</strong> {api_summary.get('successful_endpoints', 0)}</div>
        <div class="metric error"><strong>Failed:</strong> {api_summary.get('failed_endpoints', 0)}</div>
        <div class="metric"><strong>Success Rate:</strong> {api_summary.get('success_rate', 0)*100:.1f}%</div>
        """
        
        # CLI performance
        cli_summary = results.get('cli_commands', {}).get('_summary', {})
        cli_performance_html = f"""
        <div class="metric"><strong>Total Commands:</strong> {cli_summary.get('total_commands', 0)}</div>
        <div class="metric success"><strong>Successful:</strong> {cli_summary.get('successful_commands', 0)}</div>
        <div class="metric error"><strong>Failed:</strong> {cli_summary.get('failed_commands', 0)}</div>
        """
        
        if 'execution_time_stats' in cli_summary:
            exec_stats = cli_summary['execution_time_stats']
            cli_performance_html += f"""
            <div class="metric"><strong>Avg Execution Time:</strong> {exec_stats.get('mean_ms', 0):.1f}ms</div>
            <div class="metric"><strong>Max Execution Time:</strong> {exec_stats.get('max_ms', 0):.1f}ms</div>
            """
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        recommendations_html = "".join([f"<div class='recommendation'>{rec}</div>" for rec in recommendations])
        
        # Generate final HTML
        html_content = html_template.format(
            timestamp=timestamp,
            total_time=total_time,
            system_info_html=system_info_html,
            api_performance_html=api_performance_html,
            cli_performance_html=cli_performance_html,
            recommendations_html=recommendations_html
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file

# Main execution
async def main():
    """Main profiling execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LNMT Performance Profiler')
    parser.add_argument('--base-url', default='http://localhost:5000', help='Base URL for API testing')
    parser.add_argument('--cli-path', default='./', help='Path to CLI scripts')
    parser.add_argument('--output', default='lnmt_performance_results.json', help='Output file for results')
    parser.add_argument('--html-report', action='store_true', help='Generate HTML report')
    parser.add_argument('--api-only', action='store_true', help='Profile API endpoints only')
    parser.add_argument('--cli-only', action='store_true', help='Profile CLI commands only')
    
    args = parser.parse_args()
    
    # Initialize profiler
    profiler = LNMTEndpointProfiler(args.base_url, args.cli_path)
    
    if args.api_only:
        logger.info("Profiling API endpoints only...")
        results = {
            'profiling_started': time.time(),
            'system_info': profiler._get_system_info(),
            'api_endpoints': await profiler.profile_all_endpoints()
        }
        results['profiling_completed'] = time.time()
    elif args.cli_only:
        logger.info("Profiling CLI commands only...")
        results = {
            'profiling_started': time.time(),
            'system_info': profiler._get_system_info(),
            'cli_commands': profiler.profile_all_cli_commands()
        }
        results['profiling_completed'] = time.time()
    else:
        # Run comprehensive profiling
        results = await profiler.run_comprehensive_profile()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {args.output}")
    
    # Generate HTML report if requested
    if args.html_report:
        html_file = PerformanceReportGenerator.generate_html_report(results)
        logger.info(f"HTML report generated: {html_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("LNMT PERFORMANCE PROFILING SUMMARY")
    print("="*60)
    
    if 'api_summary' in results:
        api_summary = results['api_summary']
        print(f"API Endpoints: {api_summary['successful_endpoints']}/{api_summary['total_endpoints']} successful")
    
    if 'cli_commands' in results and '_summary' in results['cli_commands']:
        cli_summary = results['cli_commands']['_summary']
        print(f"CLI Commands: {cli_summary['successful_commands']}/{cli_summary['total_commands']} successful")
    
    if 'recommendations' in results:
        print(f"\nTop Recommendations:")
        for i, rec in enumerate(results['recommendations'][:3], 1):
            print(f"{i}. {rec}")
    
    print(f"\nTotal profiling time: {results.get('total_profiling_time', 0):.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
            