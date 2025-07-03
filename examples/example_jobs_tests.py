#!/usr/bin/env python3
"""
Example LNMT Jobs and Test Suite
Demonstrates scheduler integration with various LNMT module jobs.
"""

import unittest
import asyncio
import tempfile
import shutil
import json
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.scheduler import (
    LNMTScheduler, JobConfig, JobPriority, JobStatus, JobRegistry
)

# =============================================================================
# EXAMPLE LNMT MODULE JOBS
# =============================================================================

class LNMTPollingJobs:
    """Example polling jobs for various LNMT modules"""
    
    @staticmethod
    def poll_network_status():
        """Poll network devices and update status"""
        print("Polling network devices...")
        
        # Simulate network polling
        devices = ['router-01', 'switch-01', 'firewall-01', 'ap-01']
        status_results = {}
        
        for device in devices:
            # Simulate ping/SNMP check
            time.sleep(0.1)
            status_results[device] = {
                'status': 'online',
                'response_time': 15.5,
                'last_seen': datetime.now().isoformat()
            }
        
        # Would normally save to database
        print(f"Polled {len(devices)} devices")
        return status_results
    
    @staticmethod
    def poll_system_metrics():
        """Poll system metrics from monitored hosts"""
        print("Collecting system metrics...")
        
        metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 68.7,
            'disk_usage': 34.1,
            'network_io': {'in': 1024000, 'out': 512000},
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Collected metrics: CPU {metrics['cpu_usage']}%, Memory {metrics['memory_usage']}%")
        return metrics
    
    @staticmethod
    def poll_security_logs():
        """Poll and analyze security logs"""
        print("Analyzing security logs...")
        
        # Simulate log analysis
        time.sleep(0.5)
        
        findings = {
            'failed_logins': 3,
            'suspicious_ips': ['192.168.1.100', '10.0.0.50'],
            'alerts_generated': 1,
            'last_scan': datetime.now().isoformat()
        }
        
        print(f"Security scan complete: {findings['failed_logins']} failed logins, {len(findings['suspicious_ips'])} suspicious IPs")
        return findings

class LNMTBackupJobs:
    """Example backup jobs for LNMT data"""
    
    @staticmethod
    def backup_network_configs():
        """Backup network device configurations"""
        print("Backing up network configurations...")
        
        devices = ['router-01', 'switch-01', 'firewall-01']
        backup_info = {}
        
        for device in devices:
            # Simulate config backup
            time.sleep(0.2)
            backup_file = f"/backups/{device}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.cfg"
            backup_info[device] = {
                'backup_file': backup_file,
                'size_kb': 156,
                'timestamp': datetime.now().isoformat()
            }
        
        print(f"Backed up {len(devices)} device configurations")
        return backup_info
    
    @staticmethod
    def backup_monitoring_data():
        """Backup monitoring database"""
        print("Backing up monitoring data...")
        
        # Simulate database backup
        time.sleep(1.0)
        
        backup_info = {
            'backup_file': f"/backups/monitoring-{datetime.now().strftime('%Y%m%d')}.sql",
            'size_mb': 245.7,
            'records_backed_up': 15430,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Database backup complete: {backup_info['records_backed_up']} records, {backup_info['size_mb']} MB")
        return backup_info
    
    @staticmethod
    def cleanup_old_backups():
        """Clean up backups older than retention period"""
        print("Cleaning up old backups...")
        
        # Simulate cleanup
        time.sleep(0.3)
        
        cleanup_info = {
            'files_deleted': 12,
            'space_freed_mb': 892.3,
            'retention_days': 30,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Cleanup complete: {cleanup_info['files_deleted']} files deleted, {cleanup_info['space_freed_mb']} MB freed")
        return cleanup_info

class LNMTReportingJobs:
    """Example reporting jobs for LNMT"""
    
    @staticmethod
    def generate_daily_report():
        """Generate daily network monitoring report"""
        print("Generating daily report...")
        
        # Simulate report generation
        time.sleep(0.8)
        
        report_data = {
            'report_file': f"/reports/daily-{datetime.now().strftime('%Y%m%d')}.pdf",
            'devices_monitored': 24,
            'alerts_generated': 7,
            'uptime_percentage': 99.2,
            'top_alerts': ['High CPU on server-01', 'Network timeout on switch-02'],
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Daily report generated: {report_data['devices_monitored']} devices, {report_data['uptime_percentage']}% uptime")
        return report_data
    
    @staticmethod
    def generate_weekly_summary():
        """Generate weekly summary report"""
        print("Generating weekly summary...")
        
        time.sleep(1.2)
        
        summary_data = {
            'report_file': f"/reports/weekly-{datetime.now().strftime('%Y-W%W')}.pdf",
            'week_start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'week_end': datetime.now().strftime('%Y-%m-%d'),
            'total_incidents': 15,
            'resolved_incidents': 13,
            'avg_response_time_minutes': 8.5,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Weekly summary complete: {summary_data['total_incidents']} incidents, {summary_data['avg_response_time_minutes']} min avg response")
        return summary_data
    
    @staticmethod
    def send_alerts():
        """Send critical alerts via email/SMS"""
        print("Processing and sending alerts...")
        
        # Simulate alert processing
        time.sleep(0.4)
        
        alert_info = {
            'alerts_processed': 3,
            'emails_sent': 2,
            'sms_sent': 1,
            'escalations': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Alerts sent: {alert_info['emails_sent']} emails, {alert_info['sms_sent']} SMS")
        return alert_info

class LNMTMaintenanceJobs:
    """Example maintenance jobs for LNMT system"""
    
    @staticmethod
    def database_maintenance():
        """Perform database maintenance tasks"""
        print("Running database maintenance...")
        
        time.sleep(1.5)
        
        maintenance_info = {
            'tables_optimized': 8,
            'indexes_rebuilt': 12,
            'old_records_purged': 2840,
            'disk_space_freed_mb': 156.7,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Database maintenance complete: {maintenance_info['tables_optimized']} tables optimized, {maintenance_info['disk_space_freed_mb']} MB freed")
        return maintenance_info
    
    @staticmethod
    def log_rotation():
        """Rotate and compress log files"""
        print("Rotating log files...")
        
        time.sleep(0.6)
        
        rotation_info = {
            'files_rotated': 15,
            'files_compressed': 12,
            'compression_ratio': 0.23,
            'disk_space_saved_mb': 445.2,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Log rotation complete: {rotation_info['files_rotated']} files rotated, {rotation_info['disk_space_saved_mb']} MB saved")
        return rotation_info
    
    @staticmethod
    def system_health_check():
        """Perform comprehensive system health check"""
        print("Running system health check...")
        
        time.sleep(2.0)
        
        health_info = {
            'services_checked': 18,
            'services_healthy': 17,
            'services_warning': 1,
            'services_critical': 0,
            'disk_usage_percent': 67,
            'memory_usage_percent': 72,
            'cpu_load_avg': 1.45,
            'issues_found': ['Service mysql-slow showing high latency'],
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Health check complete: {health_info['services_healthy']}/{health_info['services_checked']} services healthy")
        return health_info

# =============================================================================
# JOB CONFIGURATION EXAMPLES
# =============================================================================

def create_example_job_configs():
    """Create example job configurations for LNMT"""
    
    jobs = [
        # Polling Jobs (High frequency, high priority)
        JobConfig(
            id="network_status_poll",
            name="Network Status Polling",
            module="__main__",  # This module for testing
            function="LNMTPollingJobs.poll_network_status",
            schedule="*/2 * * * *",  # Every 2 minutes
            priority=JobPriority.HIGH,
            max_retries=2,
            timeout=300
        ),
        
        JobConfig(
            id="system_metrics_poll",
            name="System Metrics Collection",
            module="__main__",
            function="LNMTPollingJobs.poll_system_metrics",
            schedule="*/5 * * * *",  # Every 5 minutes
            priority=JobPriority.HIGH,
            max_retries=2,
            timeout=180
        ),
        
        JobConfig(
            id="security_logs_poll",
            name="Security Log Analysis",
            module="__main__",
            function="LNMTPollingJobs.poll_security_logs",
            schedule="*/10 * * * *",  # Every 10 minutes
            priority=JobPriority.NORMAL,
            max_retries=3,
            timeout=600
        ),
        
        # Backup Jobs (Daily, depends on polling)
        JobConfig(
            id="config_backup",
            name="Network Configuration Backup",
            module="__main__",
            function="LNMTBackupJobs.backup_network_configs",
            schedule="0 2 * * *",  # Daily at 2 AM
            priority=JobPriority.NORMAL,
            dependencies=["network_status_poll"],
            max_retries=3,
            timeout=1800
        ),
        
        JobConfig(
            id="data_backup",
            name="Monitoring Data Backup",
            module="__main__",
            function="LNMTBackupJobs.backup_monitoring_data",
            schedule="30 2 * * *",  # Daily at 2:30 AM
            priority=JobPriority.NORMAL,
            dependencies=["system_metrics_poll"],
            max_retries=2,
            timeout=3600
        ),
        
        JobConfig(
            id="backup_cleanup",
            name="Backup Cleanup",
            module="__main__",
            function="LNMTBackupJobs.cleanup_old_backups",
            schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
            priority=JobPriority.LOW,
            dependencies=["config_backup", "data_backup"],
            max_retries=2,
            timeout=900
        ),
        
        # Reporting Jobs
        JobConfig(
            id="daily_report",
            name="Daily Monitoring Report",
            module="__main__",
            function="LNMTReportingJobs.generate_daily_report",
            schedule="0 8 * * *",  # Daily at 8 AM
            priority=JobPriority.NORMAL,
            dependencies=["system_metrics_poll", "security_logs_poll"],
            max_retries=2,
            timeout=1200
        ),
        
        JobConfig(
            id="weekly_summary",
            name="Weekly Summary Report",
            module="__main__",
            function="LNMTReportingJobs.generate_weekly_summary",
            schedule="0 9 * * 1",  # Monday at 9 AM
            priority=JobPriority.LOW,
            dependencies=["daily_report"],
            max_retries=2,
            timeout=1800
        ),
        
        JobConfig(
            id="alert_processor",
            name="Alert Processing and Notification",
            module="__main__",
            function="LNMTReportingJobs.send_alerts",
            schedule="*/15 * * * *",  # Every 15 minutes
            priority=JobPriority.CRITICAL,
            max_retries=5,
            retry_delay=30,
            timeout=300
        ),
        
        # Maintenance Jobs
        JobConfig(
            id="db_maintenance",
            name="Database Maintenance",
            module="__main__",
            function="LNMTMaintenanceJobs.database_maintenance",
            schedule="0 1 * * 0",  # Weekly on Sunday at 1 AM
            priority=JobPriority.LOW,
            max_retries=2,
            timeout=7200
        ),
        
        JobConfig(
            id="log_rotation",
            name="Log File Rotation",
            module="__main__",
            function="LNMTMaintenanceJobs.log_rotation",
            schedule="0 0 * * *",  # Daily at midnight
            priority=JobPriority.LOW,
            max_retries=2,
            timeout=900
        ),
        
        JobConfig(
            id="health_check",
            name="System Health Check",
            module="__main__",
            function="LNMTMaintenanceJobs.system_health_check",
            schedule="0 */6 * * *",  # Every 6 hours
            priority=JobPriority.NORMAL,
            max_retries=2,
            timeout=1800
        )
    ]
    
    return jobs

# =============================================================================
# TEST SUITE
# =============================================================================

class TestLNMTScheduler(unittest.TestCase):
    """Test suite for LNMT Scheduler"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.config_file = Path(self.test_dir) / "test_config.json"
        self.db_file = Path(self.test_dir) / "test_scheduler.db"
        
        self.scheduler = LNMTScheduler(
            config_file=str(self.config_file),
            db_path=str(self.db_file)
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.scheduler.stop()
        shutil.rmtree(self.test_dir)
    
    def test_job_registration(self):
        """Test job registration and retrieval"""
        job_config = JobConfig(
            id="test_job",
            name="Test Job",
            module="__main__",
            function="LNMTPollingJobs.poll_network_status",
            schedule="*/5 * * * *",
            priority=JobPriority.NORMAL
        )
        
        # Register job
        self.assertTrue(self.scheduler.register_job(job_config))
        
        # Retrieve job
        retrieved_job = self.scheduler.registry.get_job("test_job")
        self.assertIsNotNone(retrieved_job)
        self.assertEqual(retrieved_job.id, "test_job")
        self.assertEqual(retrieved_job.name, "Test Job")
        self.assertEqual(retrieved_job.priority, JobPriority.NORMAL)
    
    def test_job_execution(self):
        """Test job execution"""
        job_config = JobConfig(
            id="test_exec_job",
            name="Test Execution Job",
            module="__main__",
            function="LNMTPollingJobs.poll_network_status",
            schedule="*/5 * * * *",
            priority=JobPriority.HIGH,
            timeout=30
        )
        
        self.scheduler.register_job(job_config)
        
        # Execute job
        result = asyncio.run(self.scheduler.run_job_now("test_exec_job"))
        
        self.assertEqual(result.job_id, "test_exec_job")
        self.assertEqual(result.status, JobStatus.COMPLETED)
        self.assertIsNotNone(result.start_time)
        self.assertIsNotNone(result.end_time)
        self.assertIsNone(result.error)
    
    def test_job_dependencies(self):
        """Test job dependency resolution"""
        # Create jobs with dependencies
        job1 = JobConfig(
            id="dep_job1",
            name="Dependency Job 1",
            module="__main__",
            function="LNMTPollingJobs.poll_network_status",
            schedule="*/5 * * * *"
        )
        
        job2 = JobConfig(
            id="dep_job2",
            name="Dependency Job 2",
            module="__main__",
            function="LNMTBackupJobs.backup_network_configs",
            schedule="*/10 * * * *",
            dependencies=["dep_job1"]
        )
        
        self.scheduler.register_job(job1)
        self.scheduler.register_job(job2)
        
        # Check dependency resolution
        dep_manager = self.scheduler.dependency_manager
        
        # Job1 should be executable (no dependencies)
        self.assertTrue(dep_manager.can_execute_job(job1))
        
        # Job2 should not be executable initially (dependency not completed)
        self.assertFalse(dep_manager.can_execute_job(job2))
        
        # Mark job1 as completed
        dep_manager.mark_job_completed("dep_job1", True)
        
        # Now job2 should be executable
        self.assertTrue(dep_manager.can_execute_job(job2))
    
    def test_job_retry_logic(self):
        """Test job retry logic on failure"""
        # Create a job that will fail
        job_config = JobConfig(
            id="failing_job",
            name="Failing Job",
            module="nonexistent_module",
            function="nonexistent_function",
            schedule="*/5 * * * *",
            max_retries=2,
            retry_delay=1
        )
        
        self.scheduler.register_job(job_config)
        
        # Execute job and expect failure
        result = asyncio.run(self.scheduler.run_job_now("failing_job"))
        
        self.assertEqual(result.job_id, "failing_job")
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertEqual(result.retry_count, 2)  # Should have retried 2 times
        self.assertIsNotNone(result.error)
    
    def test_job_timeout(self):
        """Test job timeout functionality"""
        # Create a long-running job with short timeout
        def long_running_job():
            time.sleep(5)  # Sleep for 5 seconds
            return "Should not complete"
        
        # Monkey patch for testing
        import __main__
        __main__.long_running_job = long_running_job
        
        job_config = JobConfig(
            id="timeout_job",
            name="Timeout Job",
            module="__main__",
            function="long_running_job",
            schedule="*/5 * * * *",
            timeout=2  # 2 second timeout
        )
        
        self.scheduler.register_job(job_config)
        
        # Execute job and expect timeout
        result = asyncio.run(self.scheduler.run_job_now("timeout_job"))
        
        self.assertEqual(result.job_id, "timeout_job")
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertIn("timed out", result.error.lower())
    
    def test_job_priority_ordering(self):
        """Test job priority ordering"""
        jobs = [
            JobConfig(id="low_job", name="Low Priority", module="__main__",
                     function="LNMTPollingJobs.poll_network_status", schedule="*/5 * * * *",
                     priority=JobPriority.LOW),
            JobConfig(id="high_job", name="High Priority", module="__main__",
                     function="LNMTPollingJobs.poll_network_status", schedule="*/5 * * * *",
                     priority=JobPriority.HIGH),
            JobConfig(id="critical_job", name="Critical Priority", module="__main__",
                     function="LNMTPollingJobs.poll_network_status", schedule="*/5 * * * *",
                     priority=JobPriority.CRITICAL),
            JobConfig(id="normal_job", name="Normal Priority", module="__main__",
                     function="LNMTPollingJobs.poll_network_status", schedule="*/5 * * * *",
                     priority=JobPriority.NORMAL)
        ]
        
        for job in jobs:
            self.scheduler.register_job(job)
        
        # Get executable jobs (should be ordered by priority)
        executable_jobs = self.scheduler.dependency_manager.get_executable_jobs(jobs)
        
        # Verify ordering: CRITICAL > HIGH > NORMAL > LOW
        expected_order = ["critical_job", "high_job", "normal_job", "low_job"]
        actual_order = [job.id for job in executable_jobs]
        
        self.assertEqual(actual_order, expected_order)
    
    def test_config_persistence(self):
        """Test configuration saving and loading"""
        # Create and register jobs
        example_jobs = create_example_job_configs()[:3]  # Use first 3 jobs
        
        for job in example_jobs:
            self.scheduler.register_job(job)
        
        # Save configuration
        self.scheduler.save_config()
        
        # Create new scheduler instance
        new_scheduler = LNMTScheduler(
            config_file=str(self.config_file),
            db_path=str(self.db_file)
        )
        
        # Verify jobs were loaded
        loaded_jobs = new_scheduler.registry.get_all_jobs()
        self.assertEqual(len(loaded_jobs), 3)
        
        job_ids = {job.id for job in loaded_jobs}
        expected_ids = {job.id for job in example_jobs}
        self.assertEqual(job_ids, expected_ids)
        
        new_scheduler.stop()
    
    def test_job_status_tracking(self):
        """Test job status tracking and history"""
        job_config = JobConfig(
            id="status_job",
            name="Status Tracking Job",
            module="__main__",
            function="LNMTPollingJobs.poll_network_status",
            schedule="*/5 * * * *"
        )
        
        self.scheduler.register_job(job_config)
        
        # Execute job
        result = asyncio.run(self.scheduler.run_job_now("status_job"))
        
        # Check job status
        status = self.scheduler.get_job_status("status_job")
        
        self.assertIsNotNone(status)
        self.assertEqual(status['job_id'], "status_job")
        self.assertEqual(status['last_status'], JobStatus.COMPLETED.value)
        self.assertIsNotNone(status['last_run'])
        self.assertEqual(status['retry_count'], 0)
    
    def test_job_validation(self):
        """Test job configuration validation"""
        # Test invalid cron expression
        invalid_job = JobConfig(
            id="invalid_job",
            name="Invalid Job",
            module="__main__",
            function="LNMTPollingJobs.poll_network_status",
            schedule="invalid_cron"  # Invalid cron
        )
        
        self.scheduler.register_job(invalid_job)
        
        # Test next run time calculation (should return None for invalid cron)
        next_run = self.scheduler.get_next_run_time(invalid_job)
        self.assertIsNone(next_run)


class TestJobExamples(unittest.TestCase):
    """Test the example LNMT jobs"""
    
    def test_polling_jobs(self):
        """Test polling job functions"""
        # Test network status polling
        result = LNMTPollingJobs.poll_network_status()
        self.assertIsInstance(result, dict)
        self.assertIn('router-01', result)
        
        # Test system metrics polling
        result = LNMTPollingJobs.poll_system_metrics()
        self.assertIsInstance(result, dict)
        self.assertIn('cpu_usage', result)
        self.assertIn('memory_usage', result)
        
        # Test security log polling
        result = LNMTPollingJobs.poll_security_logs()
        self.assertIsInstance(result, dict)
        self.assertIn('failed_logins', result)
        self.assertIn('suspicious_ips', result)
    
    def test_backup_jobs(self):
        """Test backup job functions"""
        # Test config backup
        result = LNMTBackupJobs.backup_network_configs()
        self.assertIsInstance(result, dict)
        self.assertIn('router-01', result)
        
        # Test data backup
        result = LNMTBackupJobs.backup_monitoring_data()
        self.assertIsInstance(result, dict)
        self.assertIn('backup_file', result)
        self.assertIn('records_backed_up', result)
        
        # Test cleanup
        result = LNMTBackupJobs.cleanup_old_backups()
        self.assertIsInstance(result, dict)
        self.assertIn('files_deleted', result)
    
    def test_reporting_jobs(self):
        """Test reporting job functions"""
        # Test daily report
        result = LNMTReportingJobs.generate_daily_report()
        self.assertIsInstance(result, dict)
        self.assertIn('report_file', result)
        self.assertIn('devices_monitored', result)
        
        # Test weekly summary
        result = LNMTReportingJobs.generate_weekly_summary()
        self.assertIsInstance(result, dict)
        self.assertIn('total_incidents', result)
        
        # Test alert processing
        result = LNMTReportingJobs.send_alerts()
        self.assertIsInstance(result, dict)
        self.assertIn('alerts_processed', result)
    
    def test_maintenance_jobs(self):
        """Test maintenance job functions"""
        # Test database maintenance
        result = LNMTMaintenanceJobs.database_maintenance()
        self.assertIsInstance(result, dict)
        self.assertIn('tables_optimized', result)
        
        # Test log rotation
        result = LNMTMaintenanceJobs.log_rotation()
        self.assertIsInstance(result, dict)
        self.assertIn('files_rotated', result)
        
        # Test health check
        result = LNMTMaintenanceJobs.system_health_check()
        self.assertIsInstance(result, dict)
        self.assertIn('services_checked', result)


# =============================================================================
# INTEGRATION TEST AND DEMO
# =============================================================================

def run_scheduler_demo():
    """Demonstrate the LNMT scheduler with example jobs"""
    print("=== LNMT Scheduler Demo ===\n")
    
    # Create temporary scheduler
    demo_dir = tempfile.mkdtemp()
    config_file = Path(demo_dir) / "demo_config.json"
    db_file = Path(demo_dir) / "demo_scheduler.db"
    
    try:
        scheduler = LNMTScheduler(str(config_file), str(db_file))
        
        # Register example jobs
        example_jobs = create_example_job_configs()
        print(f"Registering {len(example_jobs)} example jobs...")
        
        for job in example_jobs:
            scheduler.register_job(job)
            print(f"  ✓ {job.name} ({job.id})")
        
        print(f"\nJobs registered successfully!")
        
        # Show job dependencies
        print("\n=== Job Dependencies ===")
        for job in example_jobs:
            if job.dependencies:
                print(f"{job.name} depends on: {', '.join(job.dependencies)}")
        
        # Demonstrate running jobs
        print("\n=== Running Sample Jobs ===")
        
        # Run a few jobs to demonstrate
        sample_jobs = ["network_status_poll", "system_metrics_poll", "daily_report"]
        
        for job_id in sample_jobs:
            print(f"\nRunning {job_id}...")
            try:
                result = asyncio.run(scheduler.run_job_now(job_id))
                print(f"  Status: {result.status.value}")
                if result.output:
                    print(f"  Output: {str(result.output)[:100]}...")
                if result.error:
                    print(f"  Error: {result.error}")
                print(f"  Duration: {result.end_time - result.start_time}")
            except Exception as e:
                print(f"  Failed to run: {e}")
        
        # Show job status
        print("\n=== Job Status Summary ===")
        for job_id in sample_jobs:
            status = scheduler.get_job_status(job_id)
            if status:
                print(f"{job_id}: {status['last_status']} (last run: {status['last_run']})")
        
        # Save configuration
        scheduler.save_config()
        print(f"\nConfiguration saved to: {config_file}")
        
        scheduler.stop()
        print("\nDemo completed successfully!")
        
    finally:
        # Cleanup
        shutil.rmtree(demo_dir)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Run demo
        run_scheduler_demo()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run tests
        unittest.main(argv=[''], verbosity=2, exit=False)
    else:
        print("Usage:")
        print("  python example_jobs_tests.py demo  # Run scheduler demo")
        print("  python example_jobs_tests.py test  # Run test suite")
        print("\nExample LNMT Jobs Available:")
        print("  - Network status polling")
        print("  - System metrics collection")
        print("  - Security log analysis")
        print("  - Configuration backups")
        print("  - Data backups")
        print("  - Report generation")
        print("  - System maintenance")
        print("  - Alert processing")
        
        # Show example job configurations
        jobs = create_example_job_configs()
        print(f"\nTotal example jobs: {len(jobs)}")
        
        print("\nJob Schedule Summary:")
        for job in jobs:
            print(f"  {job.name}: {job.schedule} (Priority: {job.priority.name})")
