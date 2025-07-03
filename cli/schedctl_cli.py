#!/usr/bin/env python3
"""
LNMT Scheduler Control CLI (schedctl.py)
Command-line interface for managing LNMT scheduler jobs.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from tabulate import tabulate
import sqlite3
from typing import List, Dict, Optional

# Import scheduler components
from services.scheduler import (
    LNMTScheduler, JobConfig, JobPriority, JobStatus, JobRegistry
)

class SchedulerCLI:
    """Command-line interface for LNMT Scheduler"""
    
    def __init__(self, config_file: str = "scheduler_config.json", db_path: str = "scheduler.db"):
        self.scheduler = LNMTScheduler(config_file, db_path)
        self.registry = self.scheduler.registry
    
    def list_jobs(self, enabled_only: bool = False, format_output: str = "table") -> None:
        """List all registered jobs"""
        jobs = self.registry.get_all_jobs()
        
        if enabled_only:
            jobs = [job for job in jobs if job.enabled]
        
        if not jobs:
            print("No jobs found.")
            return
        
        if format_output == "json":
            jobs_data = []
            for job in jobs:
                job_status = self.scheduler.get_job_status(job.id)
                next_run = self.scheduler.get_next_run_time(job)
                
                jobs_data.append({
                    "id": job.id,
                    "name": job.name,
                    "module": job.module,
                    "function": job.function,
                    "schedule": job.schedule,
                    "priority": job.priority.name,
                    "enabled": job.enabled,
                    "dependencies": job.dependencies,
                    "last_status": job_status.get("last_status") if job_status else "unknown",
                    "next_run": next_run.isoformat() if next_run else None
                })
            
            print(json.dumps(jobs_data, indent=2))
            
        else:
            # Table format
            headers = ["ID", "Name", "Schedule", "Priority", "Status", "Last Run", "Next Run", "Enabled"]
            rows = []
            
            for job in jobs:
                job_status = self.scheduler.get_job_status(job.id)
                next_run = self.scheduler.get_next_run_time(job)
                
                last_run = "Never"
                if job_status and job_status.get("last_run"):
                    last_run = datetime.fromisoformat(job_status["last_run"]).strftime("%Y-%m-%d %H:%M")
                
                next_run_str = "Unknown"
                if next_run:
                    next_run_str = next_run.strftime("%Y-%m-%d %H:%M")
                
                status = job_status.get("last_status", "never_run") if job_status else "unknown"
                
                rows.append([
                    job.id,
                    job.name[:30] + "..." if len(job.name) > 30 else job.name,
                    job.schedule,
                    job.priority.name,
                    status,
                    last_run,
                    next_run_str,
                    "✓" if job.enabled else "✗"
                ])
            
            print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    def show_job(self, job_id: str) -> None:
        """Show detailed information about a specific job"""
        job = self.registry.get_job(job_id)
        if not job:
            print(f"Job '{job_id}' not found.")
            return
        
        job_status = self.scheduler.get_job_status(job_id)
        next_run = self.scheduler.get_next_run_time(job)
        
        print(f"\n=== Job Details: {job.name} ===")
        print(f"ID: {job.id}")
        print(f"Name: {job.name}")
        print(f"Module: {job.module}")
        print(f"Function: {job.function}")
        print(f"Schedule: {job.schedule}")
        print(f"Priority: {job.priority.name}")
        print(f"Max Retries: {job.max_retries}")
        print(f"Retry Delay: {job.retry_delay}s")
        print(f"Timeout: {job.timeout}s")
        print(f"Dependencies: {', '.join(job.dependencies) if job.dependencies else 'None'}")
        print(f"Enabled: {'Yes' if job.enabled else 'No'}")
        print(f"Arguments: {job.args}")
        print(f"Keyword Arguments: {job.kwargs}")
        
        if next_run:
            print(f"Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("Next Run: Unable to calculate")
        
        if job_status:
            print(f"\n=== Last Execution ===")
            print(f"Status: {job_status.get('last_status', 'N/A')}")
            if job_status.get('last_run'):
                print(f"Started: {datetime.fromisoformat(job_status['last_run']).strftime('%Y-%m-%d %H:%M:%S')}")
            if job_status.get('last_end'):
                print(f"Ended: {datetime.fromisoformat(job_status['last_end']).strftime('%Y-%m-%d %H:%M:%S')}")
            if job_status.get('last_error'):
                print(f"Error: {job_status['last_error']}")
            print(f"Retry Count: {job_status.get('retry_count', 0)}")
    
    def add_job(self, job_data: Dict) -> None:
        """Add a new job"""
        try:
            # Validate required fields
            required_fields = ['id', 'name', 'module', 'function', 'schedule']
            for field in required_fields:
                if field not in job_data:
                    print(f"Error: Missing required field '{field}'")
                    return
            
            # Create job config
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
            
            # Register job
            if self.scheduler.register_job(job_config):
                print(f"Job '{job_config.id}' added successfully.")
                self.scheduler.save_config()
            else:
                print(f"Failed to add job '{job_config.id}'.")
                
        except Exception as e:
            print(f"Error adding job: {e}")
    
    def remove_job(self, job_id: str) -> None:
        """Remove a job"""
        if not self.registry.get_job(job_id):
            print(f"Job '{job_id}' not found.")
            return
        
        if self.scheduler.unregister_job(job_id):
            print(f"Job '{job_id}' removed successfully.")
            self.scheduler.save_config()
        else:
            print(f"Failed to remove job '{job_id}'.")
    
    def enable_job(self, job_id: str) -> None:
        """Enable a job"""
        job = self.registry.get_job(job_id)
        if not job:
            print(f"Job '{job_id}' not found.")
            return
        
        job.enabled = True
        if self.scheduler.register_job(job):
            print(f"Job '{job_id}' enabled.")
            self.scheduler.save_config()
        else:
            print(f"Failed to enable job '{job_id}'.")
    
    def disable_job(self, job_id: str) -> None:
        """Disable a job"""
        job = self.registry.get_job(job_id)
        if not job:
            print(f"Job '{job_id}' not found.")
            return
        
        job.enabled = False
        if self.scheduler.register_job(job):
            print(f"Job '{job_id}' disabled.")
            self.scheduler.save_config()
        else:
            print(f"Failed to disable job '{job_id}'.")
    
    def run_job(self, job_id: str) -> None:
        """Run a job immediately"""
        job = self.registry.get_job(job_id)
        if not job:
            print(f"Job '{job_id}' not found.")
            return
        
        print(f"Running job '{job_id}'...")
        
        try:
            # Run job synchronously for CLI
            result = asyncio.run(self.scheduler.run_job_now(job_id))
            
            print(f"Job '{job_id}' completed with status: {result.status.value}")
            if result.output:
                print(f"Output: {result.output}")
            if result.error:
                print(f"Error: {result.error}")
                
        except Exception as e:
            print(f"Failed to run job '{job_id}': {e}")
    
    def show_history(self, job_id: Optional[str] = None, limit: int = 10) -> None:
        """Show job execution history"""
        with sqlite3.connect(self.registry.db_path) as conn:
            if job_id:
                cursor = conn.execute("""
                    SELECT job_id, status, start_time, end_time, error, retry_count
                    FROM job_history 
                    WHERE job_id = ?
                    ORDER BY start_time DESC 
                    LIMIT ?
                """, (job_id, limit))
            else:
                cursor = conn.execute("""
                    SELECT job_id, status, start_time, end_time, error, retry_count
                    FROM job_history 
                    ORDER BY start_time DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            
            if not rows:
                print("No execution history found.")
                return
            
            headers = ["Job ID", "Status", "Started", "Ended", "Duration", "Retries", "Error"]
            table_rows = []
            
            for row in rows:
                job_id, status, start_time, end_time, error, retry_count = row
                
                start_dt = datetime.fromisoformat(start_time)
                start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                
                if end_time:
                    end_dt = datetime.fromisoformat(end_time)
                    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                    duration = str(end_dt - start_dt)
                else:
                    end_str = "Running"
                    duration = "N/A"
                
                error_str = error[:50] + "..." if error and len(error) > 50 else (error or "")
                
                table_rows.append([
                    job_id,
                    status,
                    start_str,
                    end_str,
                    duration,
                    retry_count,
                    error_str
                ])
            
            print(tabulate(table_rows, headers=headers, tablefmt="grid"))
    
    def show_status(self) -> None:
        """Show overall scheduler status"""
        jobs = self.registry.get_all_jobs()
        enabled_jobs = [job for job in jobs if job.enabled]
        
        print("=== LNMT Scheduler Status ===")
        print(f"Total Jobs: {len(jobs)}")
        print(f"Enabled Jobs: {len(enabled_jobs)}")
        print(f"Disabled Jobs: {len(jobs) - len(enabled_jobs)}")
        
        # Count jobs by priority
        priority_counts = {}
        for job in enabled_jobs:
            priority_counts[job.priority.name] = priority_counts.get(job.priority.name, 0) + 1
        
        print("\n=== Jobs by Priority ===")
        for priority, count in priority_counts.items():
            print(f"{priority}: {count}")
        
        # Show recent activity
        print("\n=== Recent Activity ===")
        self.show_history(limit=5)
    
    def export_config(self, output_file: str) -> None:
        """Export job configurations to file"""
        try:
            jobs = self.registry.get_all_jobs()
            jobs_data = []
            
            for job in jobs:
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
            
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"Configuration exported to '{output_file}' ({len(jobs_data)} jobs)")
            
        except Exception as e:
            print(f"Failed to export configuration: {e}")
    
    def import_config(self, input_file: str) -> None:
        """Import job configurations from file"""
        try:
            if not Path(input_file).exists():
                print(f"File '{input_file}' not found.")
                return
            
            with open(input_file, 'r') as f:
                config = json.load(f)
            
            jobs_data = config.get('jobs', [])
            imported_count = 0
            
            for job_data in jobs_data:
                try:
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
                    
                    if self.scheduler.register_job(job_config):
                        imported_count += 1
                    else:
                        print(f"Warning: Failed to import job '{job_data['id']}'")
                        
                except Exception as e:
                    print(f"Warning: Skipping invalid job config: {e}")
            
            if imported_count > 0:
                self.scheduler.save_config()
                print(f"Successfully imported {imported_count} jobs from '{input_file}'")
            else:
                print("No jobs were imported.")
                
        except Exception as e:
            print(f"Failed to import configuration: {e}")
    
    def validate_jobs(self) -> None:
        """Validate all job configurations"""
        jobs = self.registry.get_all_jobs()
        valid_jobs = 0
        invalid_jobs = []
        
        for job in jobs:
            issues = []
            
            # Validate cron expression
            try:
                import croniter
                croniter.croniter(job.schedule)
            except Exception as e:
                issues.append(f"Invalid cron expression: {e}")
            
            # Validate module and function
            try:
                module = __import__(job.module, fromlist=[job.function])
                if not hasattr(module, job.function):
                    issues.append(f"Function '{job.function}' not found in module '{job.module}'")
            except ImportError:
                issues.append(f"Module '{job.module}' not found")
            except Exception as e:
                issues.append(f"Module validation error: {e}")
            
            # Validate dependencies
            for dep_id in job.dependencies:
                if not self.registry.get_job(dep_id):
                    issues.append(f"Dependency '{dep_id}' not found")
            
            if issues:
                invalid_jobs.append((job.id, issues))
            else:
                valid_jobs += 1
        
        print(f"=== Job Validation Results ===")
        print(f"Valid Jobs: {valid_jobs}")
        print(f"Invalid Jobs: {len(invalid_jobs)}")
        
        if invalid_jobs:
            print("\n=== Issues Found ===")
            for job_id, issues in invalid_jobs:
                print(f"\nJob '{job_id}':")
                for issue in issues:
                    print(f"  - {issue}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LNMT Scheduler Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  schedctl.py list                          # List all jobs
  schedctl.py list --enabled               # List only enabled jobs
  schedctl.py show polling_job             # Show job details
  schedctl.py run backup_job               # Run job immediately
  schedctl.py enable/disable job_id        # Enable/disable job
  schedctl.py add --file job_config.json   # Add job from file
  schedctl.py history --job polling_job    # Show job history
  schedctl.py status                       # Show scheduler status
        """
    )
    
    parser.add_argument('--config', default='scheduler_config.json',
                       help='Scheduler configuration file')
    parser.add_argument('--db', default='scheduler.db',
                       help='Scheduler database file')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List jobs')
    list_parser.add_argument('--enabled', action='store_true',
                           help='Show only enabled jobs')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table',
                           help='Output format')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show job details')
    show_parser.add_argument('job_id', help='Job ID to show')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add job')
    add_parser.add_argument('--file', help='JSON file with job configuration')
    add_parser.add_argument('--id', help='Job ID')
    add_parser.add_argument('--name', help='Job name')
    add_parser.add_argument('--module', help='Python module')
    add_parser.add_argument('--function', help='Function name')
    add_parser.add_argument('--schedule', help='Cron expression')
    add_parser.add_argument('--priority', type=int, choices=[1,2,3,4], default=2,
                           help='Job priority (1=LOW, 2=NORMAL, 3=HIGH, 4=CRITICAL)')
    add_parser.add_argument('--retries', type=int, default=3,
                           help='Maximum retries')
    add_parser.add_argument('--timeout', type=int, default=3600,
                           help='Timeout in seconds')
    add_parser.add_argument('--deps', nargs='*', default=[],
                           help='Job dependencies')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove job')
    remove_parser.add_argument('job_id', help='Job ID to remove')
    
    # Enable/Disable commands
    enable_parser = subparsers.add_parser('enable', help='Enable job')
    enable_parser.add_argument('job_id', help='Job ID to enable')
    
    disable_parser = subparsers.add_parser('disable', help='Disable job')
    disable_parser.add_argument('job_id', help='Job ID to disable')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run job immediately')
    run_parser.add_argument('job_id', help='Job ID to run')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show execution history')
    history_parser.add_argument('--job', help='Show history for specific job')
    history_parser.add_argument('--limit', type=int, default=10,
                               help='Maximum number of records')
    
    # Status command
    subparsers.add_parser('status', help='Show scheduler status')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('output_file', help='Output file path')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import configuration')
    import_parser.add_argument('input_file', help='Input file path')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate job configurations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = SchedulerCLI(args.config, args.db)
    
    try:
        if args.command == 'list':
            cli.list_jobs(args.enabled, args.format)
            
        elif args.command == 'show':
            cli.show_job(args.job_id)
            
        elif args.command == 'add':
            if args.file:
                # Add from file
                with open(args.file, 'r') as f:
                    job_data = json.load(f)
                cli.add_job(job_data)
            else:
                # Add from command line arguments
                if not all([args.id, args.name, args.module, args.function, args.schedule]):
                    print("Error: Missing required arguments for job creation")
                    print("Required: --id, --name, --module, --function, --schedule")
                    return
                
                job_data = {
                    'id': args.id,
                    'name': args.name,
                    'module': args.module,
                    'function': args.function,
                    'schedule': args.schedule,
                    'priority': args.priority,
                    'max_retries': args.retries,
                    'timeout': args.timeout,
                    'dependencies': args.deps
                }
                cli.add_job(job_data)
                
        elif args.command == 'remove':
            cli.remove_job(args.job_id)
            
        elif args.command == 'enable':
            cli.enable_job(args.job_id)
            
        elif args.command == 'disable':
            cli.disable_job(args.job_id)
            
        elif args.command == 'run':
            cli.run_job(args.job_id)
            
        elif args.command == 'history':
            cli.show_history(args.job, args.limit)
            
        elif args.command == 'status':
            cli.show_status()
            
        elif args.command == 'export':
            cli.export_config(args.output_file)
            
        elif args.command == 'import':
            cli.import_config(args.input_file)
            
        elif args.command == 'validate':
            cli.validate_jobs()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()