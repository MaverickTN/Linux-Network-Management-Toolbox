#!/usr/bin/env python3
"""
LNMT Performance Profiling Suite
Comprehensive profiling toolkit for LNMT modules
"""

import cProfile
import pstats
import psutil
import time
import threading
import asyncio
import sqlite3
import json
import sys
import os
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Callable
import tracemalloc
import gc
import resource

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    module_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    function_calls: int
    db_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    concurrent_operations: int = 0

class LNMTProfiler:
    """Main profiling class for LNMT components"""
    
    def __init__(self, output_dir: str = "./profiling_results"):
        self.output_dir = output_dir
        self.metrics: List[PerformanceMetrics] = []
        self.active_profiles = {}
        self.db_query_count = 0
        self.setup_output_directory()
        
    def setup_output_directory(self):
        """Create output directory for profiling results"""
        os.makedirs(self.output_dir, exist_ok=True)
        
    @contextmanager
    def profile_context(self, module_name: str):
        """Context manager for profiling code blocks"""
        # Start memory tracking
        tracemalloc.start()
        
        # Get initial system metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_time = time.perf_counter()
        
        # Start CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            yield self
        finally:
            # Stop profiling
            profiler.disable()
            
            # Calculate metrics
            end_time = time.perf_counter()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent = process.cpu_percent()
            
            # Get memory snapshot
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Count function calls
            stats = pstats.Stats(profiler)
            total_calls = stats.total_calls
            
            # Create metrics object
            metrics = PerformanceMetrics(
                module_name=module_name,
                execution_time=end_time - initial_time,
                memory_usage_mb=max(final_memory - initial_memory, peak / 1024 / 1024),
                cpu_percent=cpu_percent,
                function_calls=total_calls,
                db_queries=self.db_query_count
            )
            
            self.metrics.append(metrics)
            
            # Save detailed profiling data
            stats_file = os.path.join(self.output_dir, f"{module_name}_profile.stats")
            stats.dump_stats(stats_file)
            
            # Reset counters
            self.db_query_count = 0
            
    def profile_function(self, func_name: str = None):
        """Decorator for profiling individual functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = func_name or f"{func.__module__}.{func.__name__}"
                with self.profile_context(name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
        
    def profile_database_operations(self, db_path: str):
        """Profile database operations and query performance"""
        results = {}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test common queries
            test_queries = [
                ("SELECT COUNT(*) FROM devices", "device_count"),
                ("SELECT * FROM devices LIMIT 100", "device_list_100"),
                ("SELECT * FROM health_logs ORDER BY timestamp DESC LIMIT 50", "recent_health_logs"),
                ("SELECT device_id, COUNT(*) FROM health_logs GROUP BY device_id", "health_summary"),
            ]
            
            for query, test_name in test_queries:
                start_time = time.perf_counter()
                try:
                    cursor.execute(query)
                    results_count = len(cursor.fetchall())
                    end_time = time.perf_counter()
                    
                    results[test_name] = {
                        'execution_time': end_time - start_time,
                        'results_count': results_count,
                        'query': query
                    }
                except sqlite3.Error as e:
                    results[test_name] = {'error': str(e), 'query': query}
                    
            conn.close()
            
        except Exception as e:
            results['connection_error'] = str(e)
            
        return results
        
    def profile_api_endpoints(self, base_url: str = "http://localhost:5000"):
        """Profile API endpoint performance"""
        import requests
        
        endpoints = [
            ("/api/devices", "GET"),
            ("/api/health", "GET"),
            ("/api/reports", "GET"),
            ("/api/scheduler/jobs", "GET"),
        ]
        
        results = {}
        
        for endpoint, method in endpoints:
            url = f"{base_url}{endpoint}"
            timings = []
            
            # Test each endpoint 5 times
            for i in range(5):
                try:
                    start_time = time.perf_counter()
                    if method == "GET":
                        response = requests.get(url, timeout=10)
                    end_time = time.perf_counter()
                    
                    timings.append({
                        'response_time': end_time - start_time,
                        'status_code': response.status_code,
                        'content_length': len(response.content)
                    })
                    
                except requests.RequestException as e:
                    timings.append({'error': str(e)})
                    
            results[endpoint] = {
                'method': method,
                'timings': timings,
                'avg_response_time': sum(t.get('response_time', 0) for t in timings) / len(timings)
            }
            
        return results
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return {"error": "No profiling data available"}
            
        # Calculate summary statistics
        total_time = sum(m.execution_time for m in self.metrics)
        avg_memory = sum(m.memory_usage_mb for m in self.metrics) / len(self.metrics)
        total_calls = sum(m.function_calls for m in self.metrics)
        
        # Find bottlenecks
        slowest_module = max(self.metrics, key=lambda m: m.execution_time)
        highest_memory = max(self.metrics, key=lambda m: m.memory_usage_mb)
        
        report = {
            'summary': {
                'total_modules_profiled': len(self.metrics),
                'total_execution_time': total_time,
                'average_memory_usage_mb': avg_memory,
                'total_function_calls': total_calls
            },
            'bottlenecks': {
                'slowest_module': {
                    'name': slowest_module.module_name,
                    'time': slowest_module.execution_time,
                    'calls': slowest_module.function_calls
                },
                'highest_memory_module': {
                    'name': highest_memory.module_name,
                    'memory_mb': highest_memory.memory_usage_mb
                }
            },
            'detailed_metrics': [asdict(m) for m in self.metrics],
            'recommendations': self._generate_recommendations()
        }
        
        return report
        
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on profiling data"""
        recommendations = []
        
        for metric in self.metrics:
            # High execution time
            if metric.execution_time > 1.0:
                recommendations.append(
                    f"Consider optimizing {metric.module_name}: execution time {metric.execution_time:.2f}s is high"
                )
                
            # High memory usage
            if metric.memory_usage_mb > 100:
                recommendations.append(
                    f"Memory optimization needed for {metric.module_name}: using {metric.memory_usage_mb:.2f}MB"
                )
                
            # High function call count might indicate inefficient algorithms
            if metric.function_calls > 10000:
                recommendations.append(
                    f"Algorithm review suggested for {metric.module_name}: {metric.function_calls} function calls"
                )
                
        return recommendations
        
    def save_report(self, filename: str = "performance_report.json"):
        """Save performance report to file"""
        report = self.generate_report()
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        return filepath

# Example usage and test harness
def simulate_device_tracker_workload():
    """Simulate device tracker service workload"""
    devices = []
    for i in range(1000):
        devices.append({
            'id': i,
            'ip': f"192.168.1.{i % 254 + 1}",
            'mac': f"00:11:22:33:44:{i:02x}",
            'status': 'online' if i % 3 == 0 else 'offline',
            'last_seen': time.time() - (i * 10)
        })
    
    # Simulate processing
    online_devices = [d for d in devices if d['status'] == 'online']
    time.sleep(0.1)  # Simulate network delay
    
    return len(online_devices)

def simulate_scheduler_workload():
    """Simulate scheduler service workload"""
    jobs = []
    for i in range(100):
        jobs.append({
            'id': i,
            'name': f"job_{i}",
            'schedule': f"0 {i % 24} * * *",
            'enabled': True,
            'last_run': time.time() - (i * 3600)
        })
    
    # Simulate job scheduling logic
    active_jobs = [j for j in jobs if j['enabled']]
    time.sleep(0.05)
    
    return len(active_jobs)

def simulate_report_engine_workload():
    """Simulate report engine workload"""
    data_points = []
    for i in range(5000):
        data_points.append({
            'timestamp': time.time() - (i * 60),
            'device_id': i % 100,
            'metric': 'cpu_usage',
            'value': (i * 17) % 100
        })
    
    # Simulate report generation
    aggregated = {}
    for point in data_points:
        device_id = point['device_id']
        if device_id not in aggregated:
            aggregated[device_id] = []
        aggregated[device_id].append(point['value'])
    
    # Calculate averages
    averages = {k: sum(v) / len(v) for k, v in aggregated.items()}
    time.sleep(0.2)  # Simulate report rendering
    
    return len(averages)

if __name__ == "__main__":
    # Initialize profiler
    profiler = LNMTProfiler()
    
    # Profile key components
    print("Profiling LNMT components...")
    
    with profiler.profile_context("device_tracker_service"):
        result1 = simulate_device_tracker_workload()
        print(f"Device tracker processed {result1} devices")
    
    with profiler.profile_context("scheduler_service"):
        result2 = simulate_scheduler_workload()
        print(f"Scheduler managed {result2} jobs")
    
    with profiler.profile_context("report_engine"):
        result3 = simulate_report_engine_workload()
        print(f"Report engine aggregated {result3} devices")
    
    # Generate and save report
    report_path = profiler.save_report()
    print(f"\nPerformance report saved to: {report_path}")
    
    # Display summary
    report = profiler.generate_report()
    print(f"\nSummary:")
    print(f"Total execution time: {report['summary']['total_execution_time']:.2f}s")
    print(f"Average memory usage: {report['summary']['average_memory_usage_mb']:.2f}MB")
    print(f"Slowest module: {report['bottlenecks']['slowest_module']['name']}")
    
    if report['recommendations']:
        print(f"\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")
