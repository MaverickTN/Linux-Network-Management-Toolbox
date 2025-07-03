#!/usr/bin/env python3
"""
LNMT Performance Optimizations
Optimized versions of key LNMT components with performance improvements
"""

import sqlite3
import asyncio
import aiohttp
import asyncpg
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from threading import Lock
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache, wraps
import weakref
import redis
from contextlib import asynccontextmanager
import multiprocessing as mp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Optimized database operations with connection pooling and query optimization"""
    
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connection_pool = []
        self.pool_lock = Lock()
        self.query_cache = {}
        self.cache_lock = Lock()
        self.stats = {'queries': 0, 'cache_hits': 0, 'cache_misses': 0}
        self._init_connection_pool()
        self._create_indexes()
        
    def _init_connection_pool(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            conn.execute("PRAGMA cache_size=10000")  # Increase cache size
            conn.execute("PRAGMA temp_store=memory")  # Store temp tables in memory
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety vs performance
            self.connection_pool.append(conn)
    
    def _create_indexes(self):
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)",
            "CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_health_logs_timestamp ON health_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_health_logs_device_id ON health_logs(device_id)",
            "CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_enabled ON scheduler_jobs(enabled)",
            "CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_next_run ON scheduler_jobs(next_run)",
        ]
        
        with self.get_connection() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                except sqlite3.Error as e:
                    logger.warning(f"Index creation failed: {e}")
            conn.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool (context manager)"""
        conn = None
        try:
            with self.pool_lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    # Create new connection if pool is empty
                    conn = sqlite3.connect(self.db_path, check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL")
            
            yield conn
            
        finally:
            if conn:
                with self.pool_lock:
                    if len(self.connection_pool) < self.pool_size:
                        self.connection_pool.append(conn)
                    else:
                        conn.close()
    
    def execute_cached_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query with caching"""
        cache_key = f"{query}:{params}"
        
        with self.cache_lock:
            if cache_key in self.query_cache:
                self.stats['cache_hits'] += 1
                return self.query_cache[cache_key]
        
        # Execute query
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
        
        # Cache results (limit cache size)
        with self.cache_lock:
            if len(self.query_cache) < 1000:  # Limit cache size
                self.query_cache[cache_key] = results
            self.stats['cache_misses'] += 1
            self.stats['queries'] += 1
        
        return results
    
    def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Optimized bulk insert using executemany"""
        if not data:
            return 0
        
        # Prepare SQL
        columns = list(data[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert data to tuples
        values = [tuple(row[col] for col in columns) for row in data]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, values)
            conn.commit()
            return cursor.rowcount

class AsyncDeviceTracker:
    """Optimized device tracker using async operations"""
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self.device_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,  # Connection pool limit
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def ping_device(self, ip: str) -> Dict[str, Any]:
        """Async ping device with caching"""
        # Check cache first
        cache_key = f"ping:{ip}"
        if cache_key in self.device_cache:
            cached_time, cached_result = self.device_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_result
        
        async with self.semaphore:
            try:
                start_time = time.time()
                async with self.session.get(f"http://{ip}", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    end_time = time.time()
                    result = {
                        'ip': ip,
                        'status': 'online',
                        'response_time': end_time - start_time,
                        'timestamp': time.time()
                    }
            except Exception as e:
                result = {
                    'ip': ip,
                    'status': 'offline',
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # Cache result
        self.device_cache[cache_key] = (time.time(), result)
        return result
    
    async def scan_network_range(self, network: str, concurrent_limit: int = None) -> List[Dict[str, Any]]:
        """Scan network range with optimized concurrency"""
        if concurrent_limit:
            semaphore = asyncio.Semaphore(concurrent_limit)
        else:
            semaphore = self.semaphore
        
        # Generate IP list (simplified for demonstration)
        base_ip = network.rsplit('.', 1)[0]
        ip_list = [f"{base_ip}.{i}" for i in range(1, 255)]
        
        # Create tasks
        tasks = []
        for ip in ip_list:
            task = self.ping_device(ip)
            tasks.append(task)
        
        # Execute with progress tracking
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            if completed % 50 == 0:
                logger.info(f"Scanned {completed}/{len(ip_list)} devices")
        
        return results

class OptimizedScheduler:
    """High-performance job scheduler with threading and async support"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.job_queue = asyncio.Queue()
        self.running_jobs = {}
        self.job_stats = {}
        self.lock = threading.Lock()
        
    async def add_job(self, job_id: str, coro_func, *args, **kwargs):
        """Add job to queue"""
        job = {
            'id': job_id,
            'function': coro_func,
            'args': args,
            'kwargs': kwargs,
            'created_at': time.time(),
            'status': 'pending'
        }
        await self.job_queue.put(job)
        logger.info(f"Job {job_id} added to queue")
    
    async def process_jobs(self):
        """Process jobs from queue"""
        while True:
            try:
                job = await self.job_queue.get()
                
                # Check if job is already running
                with self.lock:
                    if job['id'] in self.running_jobs:
                        logger.warning(f"Job {job['id']} is already running")
                        continue
                    
                    self.running_jobs[job['id']] = job
                
                # Execute job
                asyncio.create_task(self._execute_job(job))
                
            except Exception as e:
                logger.error(f"Error processing job: {e}")
    
    async def _execute_job(self, job: Dict[str, Any]):
        """Execute individual job"""
        job_id = job['id']
        start_time = time.time()
        
        try:
            job['status'] = 'running'
            
            # Execute job function
            if asyncio.iscoroutinefunction(job['function']):
                result = await job['function'](*job['args'], **job['kwargs'])
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.thread_pool, 
                    job['function'], 
                    *job['args']
                )
            
            execution_time = time.time() - start_time
            
            # Update stats
            with self.lock:
                self.job_stats[job_id] = {
                    'status': 'completed',
                    'execution_time': execution_time,
                    'result': result,
                    'completed_at': time.time()
                }
                
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]
            
            logger.info(f"Job {job_id} completed in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            with self.lock:
                self.job_stats[job_id] = {
                    'status': 'failed',
                    'execution_time': execution_time,
                    'error': str(e),
                    'failed_at': time.time()
                }
                
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]
            
            logger.error(f"Job {job_id} failed after {execution_time:.2f}s: {e}")

class CachedReportEngine:
    """Report engine with Redis caching and optimized aggregations"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = None
        self.redis_url = redis_url
        self.cache_ttl = 3600  # 1 hour
        self.db_optimizer = None
        
    async def __aenter__(self):
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to memory cache.")
            self.redis_client = None
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_cache_key(self, report_type: str, params: Dict[str, Any]) -> str:
        """Generate cache key for report"""
        param_str = json.dumps(params, sort_keys=True)
        return f"report:{report_type}:{hash(param_str)}"
    
    async def get_cached_report(self, report_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached report if available"""
        if not self.redis_client:
            return None
        
        cache_key = self._get_cache_key(report_type, params)
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        return None
    
    async def cache_report(self, report_type: str, params: Dict[str, Any], data: Dict[str, Any]):
        """Cache report data"""
        if not self.redis_client:
            return
        
        cache_key = self._get_cache_key(report_type, params)
        
        try:
            await self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    async def generate_device_health_report(self, time_range: int = 24) -> Dict[str, Any]:
        """Generate optimized device health report"""
        params = {'time_range': time_range}
        
        # Check cache first
        cached_report = await self.get_cached_report('device_health', params)
        if cached_report:
            return cached_report
        
        # Generate report
        start_time = time.time()
        
        # Use optimized SQL query with proper indexing
        query = """
        SELECT 
            d.id,
            d.name,
            d.ip,
            COUNT(h.id) as health_checks,
            AVG(CASE WHEN h.status = 'online' THEN 1 ELSE 0 END) as uptime_ratio,
            MAX(h.timestamp) as last_check
        FROM devices d
        LEFT JOIN health_logs h ON d.id = h.device_id
        WHERE h.timestamp > ? OR h.timestamp IS NULL
        GROUP BY d.id, d.name, d.ip
        ORDER BY uptime_ratio DESC
        """
        
        cutoff_time = time.time() - (time_range * 3600)
        
        # Execute query (assuming db_optimizer is available)
        if self.db_optimizer:
            results = self.db_optimizer.execute_cached_query(query, (cutoff_time,))
        else:
            # Fallback to direct execution
            results = []
        
        # Process results
        devices = []
        for row in results:
            devices.append({
                'id': row[0],
                'name': row[1],
                'ip': row[2],
                'health_checks': row[3],
                'uptime_ratio': row[4] or 0,
                'last_check': row[5]
            })
        
        report = {
            'generated_at': time.time(),
            'generation_time': time.time() - start_time,
            'time_range_hours': time_range,
            'total_devices': len(devices),
            'devices': devices,
            'summary': {
                'avg_uptime': sum(d['uptime_ratio'] for d in devices) / len(devices) if devices else 0,
                'total_health_checks': sum(d['health_checks'] for d in devices),
                'devices_online': len([d for d in devices if d['uptime_ratio'] > 0.9])
            }
        }
        
        # Cache the report
        await self.cache_report('device_health', params, report)
        
        return report

# Performance testing utilities
class PerformanceTester:
    """Test performance improvements"""
    
    @staticmethod
    async def benchmark_device_scanning():
        """Benchmark device scanning performance"""
        print("Benchmarking device scanning...")
        
        # Test with different concurrency levels
        concurrency_levels = [10, 25, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"Testing with concurrency level: {concurrency}")
            
            async with AsyncDeviceTracker(max_concurrent=concurrency) as tracker:
                start_time = time.time()
                
                # Simulate scanning 100 devices
                tasks = []
                for i in range(100):
                    ip = f"192.168.1.{i + 1}"
                    tasks.append(tracker.ping_device(ip))
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                # Calculate statistics
                successful = len([r for r in responses if isinstance(r, dict) and 'error' not in r])
                total_time = end_time - start_time
                
                results[concurrency] = {
                    'total_time': total_time,
                    'successful_pings': successful,
                    'pings_per_second': 100 / total_time,
                    'success_rate': successful / 100
                }
                
                print(f"  Time: {total_time:.2f}s, Success: {successful}/100, Rate: {100/total_time:.1f} pings/s")
        
        return results
    
    @staticmethod
    async def benchmark_database_operations():
        """Benchmark database operations"""
        print("Benchmarking database operations...")
        
        # Create test database
        test_db = ":memory:"
        optimizer = DatabaseOptimizer(test_db)
        
        # Create test tables
        with optimizer.get_connection() as conn:
            conn.execute("""
                CREATE TABLE devices (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    ip TEXT,
                    status TEXT,
                    last_seen REAL
                )
            """)
            conn.execute("""
                CREATE TABLE health_logs (
                    id INTEGER PRIMARY KEY,
                    device_id INTEGER,
                    status TEXT,
                    timestamp REAL,
                    FOREIGN KEY (device_id) REFERENCES devices (id)
                )
            """)
            conn.commit()
        
        # Test bulk insert performance
        print("Testing bulk insert performance...")
        devices_data = []
        for i in range(1000):
            devices_data.append({
                'id': i,
                'name': f'Device_{i}',
                'ip': f'192.168.1.{i % 254 + 1}',
                'status': 'online' if i % 3 == 0 else 'offline',
                'last_seen': time.time() - (i * 10)
            })
        
        start_time = time.time()
        inserted = optimizer.bulk_insert('devices', devices_data)
        bulk_insert_time = time.time() - start_time
        
        print(f"  Bulk inserted {inserted} devices in {bulk_insert_time:.3f}s")
        
        # Test query performance with and without cache
        test_query = "SELECT * FROM devices WHERE status = 'online' ORDER BY last_seen DESC LIMIT 50"
        
        # First run (cache miss)
        start_time = time.time()
        results1 = optimizer.execute_cached_query(test_query)
        first_query_time = time.time() - start_time
        
        # Second run (cache hit)
        start_time = time.time()
        results2 = optimizer.execute_cached_query(test_query)
        cached_query_time = time.time() - start_time
        
        print(f"  Query time (first): {first_query_time:.4f}s, cached: {cached_query_time:.4f}s")
        print(f"  Cache speedup: {first_query_time / cached_query_time:.1f}x")
        print(f"  Cache stats: {optimizer.stats}")
        
        return {
            'bulk_insert_time': bulk_insert_time,
            'records_inserted': inserted,
            'first_query_time': first_query_time,
            'cached_query_time': cached_query_time,
            'cache_speedup': first_query_time / cached_query_time if cached_query_time > 0 else 0,
            'cache_stats': optimizer.stats
        }
    
    @staticmethod
    async def benchmark_scheduler():
        """Benchmark scheduler performance"""
        print("Benchmarking scheduler performance...")
        
        scheduler = OptimizedScheduler(max_workers=4)
        
        # Start job processor
        processor_task = asyncio.create_task(scheduler.process_jobs())
        
        # Add test jobs
        async def test_job(job_id: int, duration: float = 0.1):
            await asyncio.sleep(duration)
            return f"Job {job_id} completed"
        
        # Add 100 jobs
        start_time = time.time()
        for i in range(100):
            await scheduler.add_job(f"test_job_{i}", test_job, i, 0.05)
        
        # Wait for all jobs to complete
        while len(scheduler.running_jobs) > 0 or not scheduler.job_queue.empty():
            await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        
        # Cancel processor
        processor_task.cancel()
        
        # Calculate statistics
        completed_jobs = len([s for s in scheduler.job_stats.values() if s['status'] == 'completed'])
        failed_jobs = len([s for s in scheduler.job_stats.values() if s['status'] == 'failed'])
        avg_execution_time = sum(s['execution_time'] for s in scheduler.job_stats.values()) / len(scheduler.job_stats)
        
        print(f"  Processed 100 jobs in {total_time:.2f}s")
        print(f"  Completed: {completed_jobs}, Failed: {failed_jobs}")
        print(f"  Average execution time: {avg_execution_time:.3f}s")
        print(f"  Jobs per second: {100 / total_time:.1f}")
        
        return {
            'total_time': total_time,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'avg_execution_time': avg_execution_time,
            'jobs_per_second': 100 / total_time
        }

# Memory optimization utilities
class MemoryOptimizer:
    """Memory optimization utilities"""
    
    @staticmethod
    def optimize_data_structures():
        """Optimize data structures for memory efficiency"""
        import sys
        
        # Use __slots__ for classes to reduce memory overhead
        class OptimizedDevice:
            __slots__ = ['id', 'name', 'ip', 'status', 'last_seen']
            
            def __init__(self, id, name, ip, status, last_seen):
                self.id = id
                self.name = name
                self.ip = ip
                self.status = status
                self.last_seen = last_seen
        
        # Compare memory usage
        regular_devices = []
        optimized_devices = []
        
        # Create regular dict-based devices
        for i in range(1000):
            regular_devices.append({
                'id': i,
                'name': f'Device_{i}',
                'ip': f'192.168.1.{i % 254 + 1}',
                'status': 'online' if i % 3 == 0 else 'offline',
                'last_seen': time.time() - (i * 10)
            })
        
        # Create optimized devices
        for i in range(1000):
            optimized_devices.append(OptimizedDevice(
                id=i,
                name=f'Device_{i}',
                ip=f'192.168.1.{i % 254 + 1}',
                status='online' if i % 3 == 0 else 'offline',
                last_seen=time.time() - (i * 10)
            ))
        
        regular_size = sys.getsizeof(regular_devices) + sum(sys.getsizeof(d) for d in regular_devices)
        optimized_size = sys.getsizeof(optimized_devices) + sum(sys.getsizeof(d) for d in optimized_devices)
        
        return {
            'regular_size_bytes': regular_size,
            'optimized_size_bytes': optimized_size,
            'memory_savings': regular_size - optimized_size,
            'savings_percentage': ((regular_size - optimized_size) / regular_size) * 100
        }
    
    @staticmethod
    def implement_object_pooling():
        """Implement object pooling for frequently created objects"""
        
        class DevicePool:
            def __init__(self, size=100):
                self.pool = []
                self.in_use = set()
                
                # Pre-allocate objects
                for _ in range(size):
                    self.pool.append({'id': None, 'name': None, 'ip': None, 'status': None, 'last_seen': None})
            
            def get_device(self):
                if self.pool:
                    device = self.pool.pop()
                    self.in_use.add(id(device))
                    return device
                else:
                    # Create new if pool is empty
                    device = {'id': None, 'name': None, 'ip': None, 'status': None, 'last_seen': None}
                    self.in_use.add(id(device))
                    return device
            
            def return_device(self, device):
                if id(device) in self.in_use:
                    # Reset device data
                    for key in device:
                        device[key] = None
                    
                    self.pool.append(device)
                    self.in_use.remove(id(device))
        
        # Test object pooling performance
        pool = DevicePool(50)
        
        # Without pooling
        start_time = time.time()
        for i in range(1000):
            device = {'id': i, 'name': f'Device_{i}', 'ip': f'192.168.1.{i % 254 + 1}', 
                     'status': 'online', 'last_seen': time.time()}
            # Simulate processing
            _ = device['id'] + 1
        no_pool_time = time.time() - start_time
        
        # With pooling
        start_time = time.time()
        for i in range(1000):
            device = pool.get_device()
            device.update({'id': i, 'name': f'Device_{i}', 'ip': f'192.168.1.{i % 254 + 1}', 
                          'status': 'online', 'last_seen': time.time()})
            # Simulate processing
            _ = device['id'] + 1
            pool.return_device(device)
        pool_time = time.time() - start_time
        
        return {
            'without_pooling_time': no_pool_time,
            'with_pooling_time': pool_time,
            'speedup': no_pool_time / pool_time if pool_time > 0 else 0
        }

# Configuration optimization
class ConfigOptimizer:
    """System configuration optimizations"""
    
    @staticmethod
    def get_optimal_thread_count():
        """Calculate optimal thread count based on system resources"""
        cpu_count = mp.cpu_count()
        
        # For I/O bound tasks (like network operations)
        io_bound_threads = min(cpu_count * 4, 100)
        
        # For CPU bound tasks
        cpu_bound_threads = cpu_count
        
        # For mixed workloads
        mixed_threads = min(cpu_count * 2, 50)
        
        return {
            'cpu_cores': cpu_count,
            'io_bound_optimal': io_bound_threads,
            'cpu_bound_optimal': cpu_bound_threads,
            'mixed_workload_optimal': mixed_threads
        }
    
    @staticmethod
    def get_memory_recommendations():
        """Get memory optimization recommendations"""
        import psutil
        
        memory = psutil.virtual_memory()
        
        # Calculate recommended cache sizes based on available memory
        total_mb = memory.total / (1024 * 1024)
        available_mb = memory.available / (1024 * 1024)
        
        recommendations = {
            'total_memory_mb': total_mb,
            'available_memory_mb': available_mb,
            'sqlite_cache_size': min(int(available_mb * 0.1), 100),  # 10% of available or 100MB max
            'redis_maxmemory_mb': min(int(available_mb * 0.2), 500),  # 20% of available or 500MB max
            'connection_pool_size': min(int(total_mb / 100), 50),  # Scale with memory
            'worker_processes': min(mp.cpu_count(), int(total_mb / 500))  # 1 process per 500MB
        }
        
        return recommendations

# Main benchmark runner
async def run_all_benchmarks():
    """Run all performance benchmarks"""
    print("=" * 60)
    print("LNMT Performance Benchmark Suite")
    print("=" * 60)
    
    results = {}
    
    # Device scanning benchmark
    print("\n1. Device Scanning Benchmark")
    print("-" * 30)
    try:
        results['device_scanning'] = await PerformanceTester.benchmark_device_scanning()
    except Exception as e:
        print(f"Device scanning benchmark failed: {e}")
        results['device_scanning'] = {'error': str(e)}
    
    # Database operations benchmark
    print("\n2. Database Operations Benchmark")
    print("-" * 30)
    try:
        results['database'] = await PerformanceTester.benchmark_database_operations()
    except Exception as e:
        print(f"Database benchmark failed: {e}")
        results['database'] = {'error': str(e)}
    
    # Scheduler benchmark
    print("\n3. Scheduler Benchmark")
    print("-" * 30)
    try:
        results['scheduler'] = await PerformanceTester.benchmark_scheduler()
    except Exception as e:
        print(f"Scheduler benchmark failed: {e}")
        results['scheduler'] = {'error': str(e)}
    
    # Memory optimization tests
    print("\n4. Memory Optimization Tests")
    print("-" * 30)
    try:
        memory_results = MemoryOptimizer.optimize_data_structures()
        pooling_results = MemoryOptimizer.implement_object_pooling()
        
        results['memory_optimization'] = {
            'data_structures': memory_results,
            'object_pooling': pooling_results
        }
        
        print(f"  Data structure optimization: {memory_results['savings_percentage']:.1f}% memory saved")
        print(f"  Object pooling speedup: {pooling_results['speedup']:.1f}x")
        
    except Exception as e:
        print(f"Memory optimization tests failed: {e}")
        results['memory_optimization'] = {'error': str(e)}
    
    # System configuration analysis
    print("\n5. System Configuration Analysis")
    print("-" * 30)
    try:
        thread_config = ConfigOptimizer.get_optimal_thread_count()
        memory_config = ConfigOptimizer.get_memory_recommendations()
        
        results['system_config'] = {
            'threading': thread_config,
            'memory': memory_config
        }
        
        print(f"  CPU cores: {thread_config['cpu_cores']}")
        print(f"  Recommended I/O threads: {thread_config['io_bound_optimal']}")
        print(f"  Recommended connection pool size: {memory_config['connection_pool_size']}")
        
    except Exception as e:
        print(f"System configuration analysis failed: {e}")
        results['system_config'] = {'error': str(e)}
    
    # Save results
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n\nBenchmark results saved to: benchmark_results.json")
    return results

if __name__ == "__main__":
    # Run benchmarks
    asyncio.run(run_all_benchmarks())