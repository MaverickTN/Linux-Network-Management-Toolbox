#!/usr/bin/env python3
"""
LNMT Scheduler Module
A robust, pluggable scheduler for automating polling, backup, reporting, and maintenance jobs.
"""

import asyncio
import threading
import time
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import croniter
from pathlib import Path
import traceback
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from abc import ABC, abstractmethod

# Job Status Enumeration
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

# Job Priority Enumeration
class JobPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: str
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    output: Optional[str] = None
    retry_count: int = 0

@dataclass
class JobConfig:
    """Configuration for a scheduled job"""
    id: str
    name: str
    module: str
    function: str
    schedule: str  # cron expression
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 3600  # seconds
    dependencies: List[str] = None
    enabled: bool = True
    args: List[Any] = None
    kwargs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}

class JobRegistry:
    """Registry for managing job definitions and configurations"""
    
    def __init__(self, db_path: str = "scheduler.db"):
        self.db_path = db_path
        self.jobs: Dict[str, JobConfig] = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database for job storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    module TEXT NOT NULL,
                    function TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    priority INTEGER DEFAULT 2,
                    max_retries INTEGER DEFAULT 3,
                    retry_delay INTEGER DEFAULT 60,
                    timeout INTEGER DEFAULT 3600,
                    dependencies TEXT DEFAULT '[]',
                    enabled BOOLEAN DEFAULT TRUE,
                    args TEXT DEFAULT '[]',
                    kwargs TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    error TEXT,
                    output TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)
    
    def register_job(self, job_config: JobConfig) -> bool:
        """Register a new job or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO jobs 
                    (id, name, module, function, schedule, priority, max_retries, 
                     retry_delay, timeout, dependencies, enabled, args, kwargs, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    job_config.id, job_config.name, job_config.module, job_config.function,
                    job_config.schedule, job_config.priority.value, job_config.max_retries,
                    job_config.retry_delay, job_config.timeout, json.dumps(job_config.dependencies),
                    job_config.enabled, json.dumps(job_config.args), json.dumps(job_config.kwargs)
                ))
            
            self.jobs[job_config.id] = job_config
            return True
        except Exception as e:
            logging.error(f"Failed to register job {job_config.id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[JobConfig]:
        """Get job configuration by ID"""
        if job_id in self.jobs:
            return self.jobs[job_id]
        
        # Load from database if not in memory
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                job_config = self._row_to_job_config(row)
                self.jobs[job_id] = job_config
                return job_config
        
        return None
    
    def get_all_jobs(self) -> List[JobConfig]:
        """Get all registered jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jobs ORDER BY priority DESC, name")
            jobs = []
            for row in cursor.fetchall():
                job_config = self._row_to_job_config(row)
                self.jobs[job_config.id] = job_config
                jobs.append(job_config)
        return jobs
    
    def _row_to_job_config(self, row) -> JobConfig:
        """Convert database row to JobConfig object"""
        return JobConfig(
            id=row[0], name=row[1], module=row[2], function=row[3],
            schedule=row[4], priority=JobPriority(row[5]), max_retries=row[6],
            retry_delay=row[7], timeout=row[8], dependencies=json.loads(row[9]),
            enabled=bool(row[10]), args=json.loads(row[11]), kwargs=json.loads(row[12])
        )
    
    def unregister_job(self, job_id: str) -> bool:
        """Remove a job from the registry"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            
            if job_id in self.jobs:
                del self.jobs[job_id]
            return True
        except Exception as e:
            logging.error(f"Failed to unregister job {job_id}: {e}")
            return False
    
    def save_job_result(self, result: JobResult):
        """Save job execution result to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO job_history 
                    (job_id, status, start_time, end_time, error, output, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.job_id, result.status.value, result.start_time,
                    result.end_time, result.error, result.output, result.retry_count
                ))
        except Exception as e:
            logging.error(f"Failed to save job result for {result.job_id}: {e}")

class JobExecutor:
    """Handles job execution with timeout, retries, and error handling"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_jobs: Dict[str, asyncio.Future] = {}
    
    async def execute_job(self, job_config: JobConfig, registry: JobRegistry) -> JobResult:
        """Execute a single job with proper error handling and retries"""
        result = JobResult(
            job_id=job_config.id,
            status=JobStatus.PENDING,
            start_time=datetime.now()
        )
        
        for attempt in range(job_config.max_retries + 1):
            try:
                result.retry_count = attempt
                result.status = JobStatus.RUNNING
                
                # Import and execute the job function
                module = __import__(job_config.module, fromlist=[job_config.function])
                job_function = getattr(module, job_config.function)
                
                # Execute in thread pool with timeout
                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(
                    self.executor,
                    lambda: job_function(*job_config.args, **job_config.kwargs)
                )
                
                # Wait with timeout
                job_output = await asyncio.wait_for(future, timeout=job_config.timeout)
                
                result.status = JobStatus.COMPLETED
                result.end_time = datetime.now()
                result.output = str(job_output) if job_output else None
                break
                
            except asyncio.TimeoutError:
                error_msg = f"Job {job_config.id} timed out after {job_config.timeout} seconds"
                logging.error(error_msg)
                result.error = error_msg
                result.status = JobStatus.FAILED
                
            except Exception as e:
                error_msg = f"Job {job_config.id} failed: {str(e)}\n{traceback.format_exc()}"
                logging.error(error_msg)
                result.error = error_msg
                result.status = JobStatus.RETRYING if attempt < job_config.max_retries else JobStatus.FAILED
                
                if attempt < job_config.max_retries:
                    logging.info(f"Retrying job {job_config.id} in {job_config.retry_delay} seconds")
                    await asyncio.sleep(job_config.retry_delay)
                else:
                    result.end_time = datetime.now()
        
        # Save result to history
        registry.save_job_result(result)
        return result
    
    def shutdown(self):
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)

class DependencyManager:
    """Manages job dependencies and execution order"""
    
    def __init__(self, registry: JobRegistry):
        self.registry = registry
        self.completed_jobs: set = set()
        self.failed_jobs: set = set()
    
    def can_execute_job(self, job_config: JobConfig) -> bool:
        """Check if job dependencies are satisfied"""
        if not job_config.dependencies:
            return True
        
        for dep_id in job_config.dependencies:
            if dep_id in self.failed_jobs:
                logging.warning(f"Job {job_config.id} cannot run due to failed dependency: {dep_id}")
                return False
            if dep_id not in self.completed_jobs:
                return False
        
        return True
    
    def mark_job_completed(self, job_id: str, success: bool):
        """Mark a job as completed or failed"""
        if success:
            self.completed_jobs.add(job_id)
        else:
            self.failed_jobs.add(job_id)
    
    def get_executable_jobs(self, all_jobs: List[JobConfig]) -> List[JobConfig]:
        """Get list of jobs that can be executed based on dependencies"""
        executable = []
        for job in all_jobs:
            if job.enabled and self.can_execute_job(job):
                executable.append(job)
        
        # Sort by priority
        executable.sort(key=lambda x: x.priority.value, reverse=True)
        return executable

class LNMTScheduler:
    """Main scheduler class that orchestrates job execution"""
    
    def __init__(self, config_file: str = "scheduler_config.json", db_path: str = "scheduler.db"):
        self.config_file = config_file
        self.registry = JobRegistry(db_path)
        self.executor = JobExecutor()
        self.dependency_manager = DependencyManager(self.registry)
        self.running = False
        self.logger = self._setup_logging()
        
        # Load configuration
        self.load_config()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('lnmt_scheduler')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def load_config(self):
        """Load job configurations from file"""
        if not Path(self.config_file).exists():
            self.logger.info(f"Config file {self.config_file} not found, using defaults")
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            for job_data in config.get('jobs', []):
                job_config = JobConfig(
                    id=job_data['id'],
                    name=job_data['name'],
                    module=job_data['module'],
                    function=job_data['function'],
                    schedule=job_data['schedule'],
                    priority=JobPriority(job_data.get('priority', 2)),
                    max_retries=job_data.get('max_retries', 3),
                    retry_delay=job_data.get('retry_delay', 60),
                    timeout=job_data.get('timeout', 3600),
                    dependencies=job_data.get('dependencies', []),
                    enabled=job_data.get('enabled', True),
                    args=job_data.get('args', []),
                    kwargs=job_data.get('kwargs', {})
                )
                self.registry.register_job(job_config)
            
            self.logger.info(f"Loaded {len(config.get('jobs', []))} jobs from config")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
    
    def save_config(self):
        """Save current job configurations to file"""
        try:
            jobs_data = []
            for job in self.registry.get_all_jobs():
                jobs_data.append({
                    'id': job.id,
                    'name': job.name,
                    'module': job.module,
                    'function': job.function,
                    'schedule': job.schedule,
                    'priority': job.priority.value,
                    'max_retries': job.max_retries,
                    'retry_delay': job.retry_delay,
                    'timeout': job.timeout,
                    'dependencies': job.dependencies,
                    'enabled': job.enabled,
                    'args': job.args,
                    'kwargs': job.kwargs
                })
            
            config = {'jobs': jobs_data}
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"Saved {len(jobs_data)} jobs to config")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def register_job(self, job_config: JobConfig) -> bool:
        """Register a new job"""
        return self.registry.register_job(job_config)
    
    def unregister_job(self, job_id: str) -> bool:
        """Unregister a job"""
        return self.registry.unregister_job(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of a job"""
        job = self.registry.get_job(job_id)
        if not job:
            return None
        
        # Get latest execution result
        with sqlite3.connect(self.registry.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, start_time, end_time, error, retry_count
                FROM job_history 
                WHERE job_id = ? 
                ORDER BY start_time DESC 
                LIMIT 1
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'job_id': job_id,
                    'name': job.name,
                    'enabled': job.enabled,
                    'last_status': row[0],
                    'last_run': row[1],
                    'last_end': row[2],
                    'last_error': row[3],
                    'retry_count': row[4]
                }
            else:
                return {
                    'job_id': job_id,
                    'name': job.name,
                    'enabled': job.enabled,
                    'last_status': 'never_run',
                    'last_run': None,
                    'last_end': None,
                    'last_error': None,
                    'retry_count': 0
                }
    
    def get_next_run_time(self, job_config: JobConfig) -> Optional[datetime]:
        """Calculate next run time for a job"""
        try:
            cron = croniter.croniter(job_config.schedule, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            self.logger.error(f"Invalid cron expression for job {job_config.id}: {e}")
            return None
    
    async def run_job_now(self, job_id: str) -> JobResult:
        """Execute a job immediately"""
        job = self.registry.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if not self.dependency_manager.can_execute_job(job):
            raise RuntimeError(f"Job {job_id} dependencies not satisfied")
        
        result = await self.executor.execute_job(job, self.registry)
        self.dependency_manager.mark_job_completed(job_id, result.status == JobStatus.COMPLETED)
        
        return result
    
    async def scheduler_loop(self):
        """Main scheduler loop"""
        self.logger.info("Scheduler started")
        
        while self.running:
            try:
                current_time = datetime.now()
                jobs_to_run = []
                
                # Check which jobs are due to run
                for job in self.registry.get_all_jobs():
                    if not job.enabled:
                        continue
                    
                    next_run = self.get_next_run_time(job)
                    if next_run and next_run <= current_time + timedelta(minutes=1):
                        if self.dependency_manager.can_execute_job(job):
                            jobs_to_run.append(job)
                
                # Execute jobs
                if jobs_to_run:
                    self.logger.info(f"Running {len(jobs_to_run)} scheduled jobs")
                    
                    # Execute jobs in priority order
                    jobs_to_run.sort(key=lambda x: x.priority.value, reverse=True)
                    
                    for job in jobs_to_run:
                        try:
                            result = await self.executor.execute_job(job, self.registry)
                            self.dependency_manager.mark_job_completed(
                                job.id, result.status == JobStatus.COMPLETED
                            )
                            
                            self.logger.info(f"Job {job.id} completed with status: {result.status.value}")
                            
                        except Exception as e:
                            self.logger.error(f"Failed to execute job {job.id}: {e}")
                
                # Sleep for a minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
        
        self.logger.info("Scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        self.running = True
        try:
            asyncio.run(self.scheduler_loop())
        except KeyboardInterrupt:
            self.logger.info("Scheduler interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.executor.shutdown()
        self.save_config()

# Example job functions for LNMT modules
def example_polling_job():
    """Example polling job"""
    print("Executing polling job...")
    time.sleep(2)  # Simulate work
    return "Polling completed successfully"

def example_backup_job():
    """Example backup job"""
    print("Executing backup job...")
    time.sleep(3)  # Simulate work
    return "Backup completed successfully"

def example_reporting_job():
    """Example reporting job"""
    print("Executing reporting job...")
    time.sleep(1)  # Simulate work
    return "Report generated successfully"

# Main entry point
if __name__ == "__main__":
    # Example usage
    scheduler = LNMTScheduler()
    
    # Register example jobs
    polling_job = JobConfig(
        id="polling_job",
        name="Data Polling Job",
        module="__main__",  # This module
        function="example_polling_job",
        schedule="*/5 * * * *",  # Every 5 minutes
        priority=JobPriority.HIGH,
        max_retries=2
    )
    
    backup_job = JobConfig(
        id="backup_job",
        name="Backup Job",
        module="__main__",
        function="example_backup_job",
        schedule="0 2 * * *",  # Daily at 2 AM
        priority=JobPriority.NORMAL,
        dependencies=["polling_job"]  # Depends on polling job
    )
    
    reporting_job = JobConfig(
        id="reporting_job",
        name="Reporting Job",
        module="__main__",
        function="example_reporting_job",
        schedule="0 9 * * 1",  # Every Monday at 9 AM
        priority=JobPriority.LOW,
        dependencies=["backup_job"]
    )
    
    scheduler.register_job(polling_job)
    scheduler.register_job(backup_job)
    scheduler.register_job(reporting_job)
    
    # Start scheduler
    scheduler.start()
