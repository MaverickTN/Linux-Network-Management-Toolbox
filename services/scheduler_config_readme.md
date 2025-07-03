# LNMT Scheduler Module

A robust, pluggable scheduler for automating all polling, backup, reporting, and maintenance jobs for the LNMT (Local Network Management Tools) system.

## Features

- **Pluggable Architecture**: Easy job registration via configuration files or CLI
- **Robust Execution**: Threaded/async execution with retry logic and error handling
- **Dependency Management**: Job dependencies with priority-based execution
- **Comprehensive Logging**: Full job execution history and status tracking
- **CLI Management**: Complete command-line interface for job control
- **Flexible Scheduling**: Cron-based scheduling with timeout controls
- **Database Persistence**: SQLite-based job storage and history tracking

## Quick Start

### 1. Install Dependencies

```bash
pip install croniter tabulate
```

### 2. Basic Usage

```python
from services.scheduler import LNMTScheduler, JobConfig, JobPriority

# Create scheduler
scheduler = LNMTScheduler()

# Register a job
job = JobConfig(
    id="my_job",
    name="My Custom Job",
    module="my_module",
    function="my_function",
    schedule="*/5 * * * *",  # Every 5 minutes
    priority=JobPriority.HIGH
)

scheduler.register_job(job)

# Start scheduler
scheduler.start()
```

### 3. CLI Usage

```bash
# List all jobs
python cli/schedctl.py list

# Add a job
python cli/schedctl.py add --id polling_job --name "Network Polling" \
    --module lnmt.polling --function poll_devices --schedule "*/2 * * * *"

# Run a job immediately
python cli/schedctl.py run polling_job

# Show job status
python cli/schedctl.py show polling_job

# View execution history
python cli/schedctl.py history --job polling_job
```

## Architecture

### Core Components

1. **LNMTScheduler**: Main scheduler orchestrating job execution
2. **JobRegistry**: Manages job definitions and database persistence
3. **JobExecutor**: Handles job execution with timeout and retry logic
4. **DependencyManager**: Resolves job dependencies and execution order
5. **SchedulerCLI**: Command-line interface for job management

### Job Configuration

Jobs are defined using the `JobConfig` class:

```python
@dataclass
class JobConfig:
    id: str                    # Unique job identifier
    name: str                  # Human-readable name
    module: str                # Python module containing job function
    function: str              # Function name to execute
    schedule: str              # Cron expression for scheduling
    priority: JobPriority      # Job priority (LOW, NORMAL, HIGH, CRITICAL)
    max_retries: int = 3       # Maximum retry attempts
    retry_delay: int = 60      # Delay between retries (seconds)
    timeout: int = 3600        # Job timeout (seconds)
    dependencies: List[str]    # List of job IDs this job depends on
    enabled: bool = True       # Whether job is enabled
    args: List[Any]            # Arguments to pass to job function
    kwargs: Dict[str, Any]     # Keyword arguments to pass to job function
```

### Database Schema

The scheduler uses SQLite with two main tables:

- **jobs**: Stores job configurations
- **job_history**: Tracks job execution results

## Example Jobs

The module includes comprehensive example jobs for LNMT:

### Polling Jobs
- **Network Status Polling**: Monitor network device status
- **System Metrics Collection**: Gather system performance data
- **Security Log Analysis**: Analyze security logs for threats

### Backup Jobs
- **Configuration Backup**: Backup network device configurations
- **Data Backup**: Backup monitoring databases
- **Backup Cleanup**: Clean up old backup files

### Reporting Jobs
- **Daily Reports**: Generate daily monitoring reports
- **Weekly Summaries**: Create weekly summary reports
- **Alert Processing**: Process and send notifications

### Maintenance Jobs
- **Database Maintenance**: Optimize database performance
- **Log Rotation**: Rotate and compress log files
- **System Health Check**: Comprehensive system health monitoring

## Configuration File Format

Jobs can be defined in JSON configuration files:

```json
{
  "jobs": [
    {
      "id": "network_poll",
      "name": "Network Device Polling",
      "module": "lnmt.polling",
      "function": "poll_network_devices",
      "schedule": "*/2 * * * *",
      "priority": 3,
      "max_retries": 2,
      "timeout": 300,
      "dependencies": [],
      "enabled": true,
      "args": [],
      "kwargs": {
        "timeout": 30,
        "retries": 3
      }
    }
  ]
}
```

## CLI Reference

### schedctl.py Commands

#### Job Management
- `list [--enabled] [--format json|table]` - List jobs
- `show <job_id>` - Show detailed job information
- `add` - Add new job (from CLI args or file)
- `remove <job_id>` - Remove job
- `enable <job_id>` - Enable job
- `disable <job_id>` - Disable job

#### Execution Control
- `run <job_id>` - Execute job immediately
- `history [--job <job_id>] [--limit N]` - Show execution history
- `status` - Show scheduler status

#### Configuration
- `export <file>` - Export job configurations
- `import <file>` - Import job configurations
- `validate` - Validate all job configurations

### Example CLI Sessions

```bash
# Setup example jobs
python cli/schedctl.py import examples/lnmt_jobs.json

# List all jobs
python cli/schedctl.py list
┌─────────────────────┬──────────────────────────┬─────────────────┬──────────┬─────────────┬────────────┬─────────────────────┬─────────┐
│ ID                  │ Name                     │ Schedule        │ Priority │ Status      │ Last Run   │ Next Run            │ Enabled │
├─────────────────────┼──────────────────────────┼─────────────────┼──────────┼─────────────┼────────────┼─────────────────────┼─────────┤
│ alert_processor     │ Alert Processing and...  │ */15 * * * *    │ CRITICAL │ never_run   │ Never      │ 2024-01-15 14:45    │ ✓       │
│ network_status_poll │ Network Status Polling   │ */2 * * * *     │ HIGH     │ never_run   │ Never      │ 2024-01-15 14:32    │ ✓       │
│ system_metrics_poll │ System Metrics Collection│ */5 * * * *     │ HIGH     │ never_run   │ Never      │ 2024-01-15 14:35    │ ✓       │
└─────────────────────┴──────────────────────────┴─────────────────┴──────────┴─────────────┴────────────┴─────────────────────┴─────────┘

# Run a job immediately
python cli/schedctl.py run network_status_poll
Running job 'network_status_poll'...
Job 'network_status_poll' completed with status: completed
Output: {'router-01': {'status': 'online', 'response_time': 15.5, ...}}

# Check job status
python cli/schedctl.py show network_status_poll
=== Job Details: Network Status Polling ===
ID: network_status_poll
Name: Network Status Polling
Module: __main__
Function: LNMTPollingJobs.poll_network_status
Schedule: */2 * * * *
Priority: HIGH
Next Run: 2024-01-15 14:32:00

=== Last Execution ===
Status: completed
Started: 2024-01-15 14:30:15
Ended: 2024-01-15 14:30:17
Retry Count: 0

# View execution history
python cli/schedctl.py history --limit 5
┌─────────────────────┬───────────┬─────────────────────┬─────────────────────┬──────────────────┬─────────┬─────────┐
│ Job ID              │ Status    │ Started             │ Ended               │ Duration         │ Retries │ Error   │
├─────────────────────┼───────────┼─────────────────────┼─────────────────────┼──────────────────┼─────────┼─────────┤
│ network_status_poll │ completed │ 2024-01-15 14:30:15│ 2024-01-15 14:30:17│ 0:00:02.156789   │ 0       │         │
└─────────────────────┴───────────┴─────────────────────┴─────────────────────┴──────────────────┴─────────┴─────────┘
```

## Integration with LNMT Modules

### Module Structure
```
lnmt/
├── services/
│   ├── scheduler.py         # Main scheduler module
│   └── __init__.py
├── cli/
│   ├── schedctl.py          # CLI tool
│   └── __init__.py
├── jobs/
│   ├── polling.py           # Polling job implementations
│   ├── backup.py            # Backup job implementations
│   ├── reporting.py         # Reporting job implementations
│   ├── maintenance.py       # Maintenance job implementations
│   └── __init__.py
├── examples/
│   ├── lnmt_jobs.json       # Example job configurations
│   └── example_jobs_tests.py # Example jobs and tests
└── configs/
    └── scheduler_config.json # Default configuration
```

### Job Implementation Guidelines

1. **Job Functions**: Should be standalone functions that can be imported
2. **Error Handling**: Let scheduler handle retries; focus on business logic
3. **Return Values**: Return meaningful data for logging/monitoring
4. **Arguments**: Use args/kwargs for configurable parameters
5. **Logging**: Use print() or logging for job-specific output

Example job function:
```python
def poll_network_devices(timeout=30, retries=3):
    """Poll network devices and return status"""
    results = {}
    devices = get_device_list()
    
    for device in devices:
        try:
            status = ping_device(device, timeout=timeout)
            results[device] = status
        except Exception as e:
            print(f"Failed to poll {device}: {e}")
            results[device] = {'status': 'failed', 'error': str(e)}
    
    return results
```

## Monitoring and Troubleshooting

### Log Files
- Scheduler logs: Console output with timestamps
- Job execution logs: Stored in database with full error traces
- System logs: Standard Python logging integration

### Common Issues

1. **Job Not Running**: Check if job is enabled and dependencies are satisfied
2. **Import Errors**: Verify module paths and function names
3. **Timeout Issues**: Adjust timeout values for long-running jobs
4. **Database Locked**: Ensure only one scheduler instance is running
5. **Dependency Loops**: Validate job dependencies don't create cycles

### Debugging Commands

```bash
# Validate all job configurations
python cli/schedctl.py validate

# Check scheduler status
python cli/schedctl.py status

# View recent job failures
python cli/schedctl.py history --limit 20 | grep failed

# Test job execution
python cli/schedctl.py run <job_id>
```

## Performance Considerations

### Scalability
- **Concurrent Jobs**: Limited by ThreadPoolExecutor (default: 5 workers)
- **Database**: SQLite suitable for moderate job volumes (< 1000 jobs)
- **Memory Usage**: Job history grows over time; implement cleanup

### Optimization Tips
1. **Job Frequency**: Balance polling frequency with system load
2. **Timeout Values**: Set appropriate timeouts to prevent hanging jobs
3. **Retry Logic**: Use exponential backoff for failing jobs
4. **Dependencies**: Minimize dependency chains to reduce complexity
5. **Cleanup**: Regularly clean old job history records

### Resource Management
```python
# Example configuration for high-volume environments
scheduler = LNMTScheduler(
    max_workers=10,          # Increase worker threads
    cleanup_days=30,         # Cleanup old history
    max_concurrent_jobs=20   # Limit concurrent execution
)
```

## Security Considerations

### Access Control
- **File Permissions**: Secure configuration and database files
- **Code Execution**: Jobs execute with scheduler privileges
- **Network Access**: Jobs may access network resources

### Best Practices
1. **Input Validation**: Validate all job parameters
2. **Error Handling**: Don't expose sensitive information in logs
3. **Privilege Separation**: Run scheduler with minimal required privileges
4. **Audit Logging**: Track job execution and configuration changes

## Advanced Features

### Custom Job Types

Create specialized job classes for complex scenarios:

```python
class LNMTPollingJob(JobConfig):
    """Specialized job for LNMT polling tasks"""
    
    def __init__(self, device_type: str, **kwargs):
        super().__init__(**kwargs)
        self.device_type = device_type
        self.kwargs['device_type'] = device_type

# Usage
router_poll = LNMTPollingJob(
    id="router_poll",
    name="Router Polling",
    device_type="router",
    module="lnmt.polling",
    function="poll_devices",
    schedule="*/1 * * * *"
)
```

### Dynamic Job Creation

Jobs can be created dynamically based on discovered resources:

```python
def create_device_polling_jobs(scheduler):
    """Create polling jobs for discovered devices"""
    devices = discover_network_devices()
    
    for device in devices:
        job = JobConfig(
            id=f"poll_{device['name']}",
            name=f"Poll {device['name']}",
            module="lnmt.polling",
            function="poll_single_device",
            schedule="*/5 * * * *",
            kwargs={'device_id': device['id']}
        )
        scheduler.register_job(job)
```

### Job Chaining and Workflows

Complex workflows can be implemented using dependencies:

```python
# Data collection workflow
jobs = [
    JobConfig(id="collect_data", ...),
    JobConfig(id="process_data", dependencies=["collect_data"], ...),
    JobConfig(id="generate_report", dependencies=["process_data"], ...),
    JobConfig(id="send_report", dependencies=["generate_report"], ...)
]
```

### Event-Driven Jobs

Integrate with external event systems:

```python
def webhook_triggered_job(event_data):
    """Job triggered by webhook/event"""
    if event_data.get('alert_level') == 'critical':
        # Handle critical alert
        return handle_critical_alert(event_data)
    else:
        # Handle normal event
        return handle_normal_event(event_data)
```

## API Reference

### Core Classes

#### LNMTScheduler
Main scheduler class for job orchestration.

**Methods:**
- `register_job(job_config: JobConfig) -> bool`
- `unregister_job(job_id: str) -> bool`
- `run_job_now(job_id: str) -> JobResult`
- `get_job_status(job_id: str) -> Dict`
- `start()` - Start scheduler loop
- `stop()` - Stop scheduler

#### JobConfig
Job configuration dataclass.

**Fields:**
- `id: str` - Unique identifier
- `name: str` - Display name
- `module: str` - Python module
- `function: str` - Function name
- `schedule: str` - Cron expression
- `priority: JobPriority` - Execution priority
- `max_retries: int` - Retry attempts
- `timeout: int` - Execution timeout
- `dependencies: List[str]` - Job dependencies

#### JobResult
Result of job execution.

**Fields:**
- `job_id: str` - Job identifier
- `status: JobStatus` - Execution status
- `start_time: datetime` - Start timestamp
- `end_time: datetime` - End timestamp
- `error: str` - Error message if failed
- `output: str` - Job output
- `retry_count: int` - Number of retries

### Enumerations

#### JobStatus
- `PENDING` - Job queued for execution
- `RUNNING` - Job currently executing
- `COMPLETED` - Job finished successfully
- `FAILED` - Job failed after retries
- `CANCELLED` - Job was cancelled
- `RETRYING` - Job is being retried

#### JobPriority
- `LOW` (1) - Low priority jobs
- `NORMAL` (2) - Standard priority
- `HIGH` (3) - High priority jobs
- `CRITICAL` (4) - Critical system jobs

## Testing

### Unit Tests

Run the test suite:

```bash
python examples/example_jobs_tests.py test
```

### Integration Tests

Test with real LNMT modules:

```bash
# Create test environment
python examples/example_jobs_tests.py demo

# Run specific job tests
python -m pytest tests/test_scheduler.py -v
```

### Performance Tests

Load testing with multiple jobs:

```python
def load_test_scheduler():
    """Load test with 100 concurrent jobs"""
    scheduler = LNMTScheduler()
    
    # Create 100 test jobs
    for i in range(100):
        job = JobConfig(
            id=f"load_test_{i}",
            name=f"Load Test Job {i}",
            module="__main__",
            function="quick_test_job",
            schedule="*/1 * * * *"
        )
        scheduler.register_job(job)
    
    # Monitor execution
    start_time = time.time()
    # ... run jobs and measure performance
```

## Migration Guide

### From Cron

Converting existing cron jobs:

```bash
# Old cron entry
0 2 * * * /usr/local/bin/backup_configs.sh

# New LNMT scheduler job
{
  "id": "config_backup",
  "name": "Configuration Backup",
  "module": "lnmt.backup",
  "function": "backup_configurations",
  "schedule": "0 2 * * *",
  "priority": 2,
  "timeout": 3600
}
```

### From Other Schedulers

Migration checklist:
1. ✅ Inventory existing jobs and schedules
2. ✅ Create corresponding JobConfig objects
3. ✅ Test job functions individually
4. ✅ Validate dependencies and timing
5. ✅ Implement monitoring and alerting
6. ✅ Gradual rollout with fallback plan

## Deployment

### Production Setup

1. **System Service**: Run scheduler as systemd service
2. **Monitoring**: Integrate with system monitoring
3. **Backups**: Regular database backups
4. **Logging**: Centralized log collection
5. **High Availability**: Consider clustering for critical environments

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "services/scheduler.py"]
```

### Systemd Service

```ini
[Unit]
Description=LNMT Scheduler
After=network.target

[Service]
Type=simple
User=lnmt
WorkingDirectory=/opt/lnmt
ExecStart=/usr/bin/python3 /opt/lnmt/services/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Configuration Examples

### Basic Configuration

```json
{
  "jobs": [
    {
      "id": "basic_poll",
      "name": "Basic Network Poll",
      "module": "lnmt.polling",
      "function": "poll_devices",
      "schedule": "*/5 * * * *",
      "priority": 2,
      "enabled": true
    }
  ]
}
```

### Advanced Configuration

```json
{
  "jobs": [
    {
      "id": "advanced_monitoring",
      "name": "Advanced Network Monitoring",
      "module": "lnmt.monitoring",
      "function": "comprehensive_check",
      "schedule": "*/10 * * * *",
      "priority": 3,
      "max_retries": 5,
      "retry_delay": 30,
      "timeout": 600,
      "dependencies": ["basic_poll"],
      "enabled": true,
      "args": [],
      "kwargs": {
        "deep_scan": true,
        "timeout": 300,
        "protocols": ["snmp", "ssh", "http"]
      }
    }
  ]
}
```

## Support and Contributing

### Getting Help
- Check the troubleshooting section
- Review example jobs and tests
- Use CLI validation tools
- Enable debug logging

### Contributing
1. Follow Python PEP 8 style guidelines
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure backward compatibility

### Reporting Issues
When reporting issues, include:
- Scheduler version and Python version
- Job configuration causing issues
- Full error messages and stack traces
- Steps to reproduce the problem

---

## License

This LNMT Scheduler module is part of the Local Network Management Tools suite. See LICENSE file for details.

## Changelog

### v1.0.0 (Current)
- ✅ Initial release with core scheduling functionality
- ✅ Job registration and execution
- ✅ Dependency management
- ✅ CLI interface
- ✅ Database persistence
- ✅ Comprehensive example jobs
- ✅ Full test suite