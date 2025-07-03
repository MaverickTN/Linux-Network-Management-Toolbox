# LNMT Integration Connectors Module

The Integration Connectors module enables LNMT to push alerts, events, and reports to external systems including syslog servers, ELK/Splunk stacks, email systems, webhooks, Slack, Discord, and more.

## Features

- **Multiple Connector Types**: Syslog, HTTP/HTTPS webhooks, Email/SMTP, Slack, Discord
- **Flexible Filtering**: Level-based, event type, and tag-based filtering
- **Rate Limiting**: Configurable rate limiting to prevent spam
- **Event Hooks**: Custom callbacks for different event types  
- **Async Operation**: Non-blocking event delivery
- **Error Handling**: Robust error handling and logging
- **CLI Management**: Command-line interface for setup and testing

## Architecture

### Core Components

- **IntegrationEvent**: Standard event structure for all integrations
- **BaseConnector**: Abstract base class for all connector implementations
- **IntegrationConnectorService**: Main service managing all connectors
- **Connector Implementations**: Specific implementations for each service type

### Event Flow

```
Application → Integration Service → Filters → Rate Limits → Connectors → External Systems
                     ↓
                Event Hooks
```

## Configuration

Configuration is done via YAML files. Here's a comprehensive example:

```yaml
connectors:
  # Syslog connector
  local_syslog:
    type: syslog
    enabled: true
    host: localhost
    port: 514
    protocol: udp  # or tcp
    facility: 16   # local0
    filters:
      min_level: warning
      event_types: [system_health, critical_error]
    rate_limit:
      max_per_window: 10
      window: 3600  # 1 hour
  
  # HTTP webhook connector
  webhook_endpoint:
    type: http
    enabled: true
    url: https://api.example.com/webhooks/lnmt
    method: POST
    headers:
      Authorization: Bearer YOUR_TOKEN
      X-Source: LNMT
    timeout: 30
    verify_ssl: true
    auth:
      type: basic
      username: api_user
      password: api_pass
    filters:
      min_level: info
      required_tags: [production]
  
  # Email connector
  email_alerts:
    type: email
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    use_tls: true
    username: your_email@gmail.com
    password: your_app_password
    from_email: lnmt@yourcompany.com
    to_emails:
      - admin@yourcompany.com
      - ops@yourcompany.com
    subject_template: "LNMT Alert: {level} - {title}"
    filters:
      min_level: error
    rate_limit:
      max_per_window: 5
      window: 3600
  
  # Slack connector
  slack_alerts:
    type: slack
    enabled: true
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    channel: "#alerts"
    username: LNMT Bot
    icon_emoji: ":robot_face:"
    filters:
      min_level: warning
      event_types: [system_health, critical_error, threshold_breach]
  
  # Discord connector
  discord_alerts:
    type: discord
    enabled: true
    webhook_url: https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
    username: LNMT
    avatar_url: https://example.com/lnmt-avatar.png
    filters:
      min_level: critical
```

## Usage

### Basic Usage

```python
from services.integration_connectors import (
    IntegrationConnectorService,
    AlertLevel,
    EventType
)

# Initialize service with config
service = IntegrationConnectorService("config.yaml")

# Send an alert
await service.alert(
    level=AlertLevel.ERROR,
    title="High CPU Usage",
    message="CPU usage has exceeded 90% for 5 minutes",
    source="cpu_monitor",
    event_type=EventType.THRESHOLD_BREACH,
    metadata={"cpu_percent": 92.5, "duration": 300},
    tags=["performance", "cpu", "production"]
)
```

### Convenience Functions

```python
from services.integration_connectors import (
    send_critical_alert,
    send_health_alert,
    send_threshold_alert
)

# Critical alert
await send_critical_alert(
    title="Database Connection Lost",
    message="Unable to connect to primary database",
    source="database_service",
    metadata={"connection_string": "postgres://db:5432/lnmt"},
    tags=["database", "critical"]
)

# Health alert
await send_health_alert(
    title="Disk Space Low",
    message="Disk space on /var/log is below 10%",
    source="filesystem_monitor",
    tags=["filesystem", "disk"]
)

# Threshold alert
await send_threshold_alert(
    title="Response Time High",
    message="API response time exceeded threshold",
    source="api_monitor",
    metadata={"response_time": 2.34, "threshold": 2.0}
)
```

### Event Hooks

```python
# Register custom hooks
async def critical_hook(event):
    print(f"Critical event: {event.title}")
    # Could trigger additional actions like paging

def audit_hook(event):
    # Log to audit system
    audit_logger.info(f"Event: {event.event_id}")

service.register_hook(EventType.CRITICAL_ERROR, critical_hook)
service.register_hook(EventType.SECURITY_EVENT, audit_hook)
```

### Integration with Other LNMT Modules

```python
# In your LNMT module
from services.integration_connectors import send_health_alert

class HealthMonitor:
    async def check_system_health(self):
        if self.cpu_usage > 80:
            await send_health_alert(
                title="High CPU Usage",
                message=f"CPU usage at {self.cpu_usage}%",
                source="health_monitor",
                metadata={"cpu_usage": self.cpu_usage},
                tags=["performance", "cpu"]
            )
```

## CLI Usage

The `integrations_ctl.py` CLI provides management and testing capabilities:

### Generate Sample Configuration

```bash
./cli/integrations_ctl.py sample-config > config.yaml
```

### Validate Configuration

```bash
./cli/integrations_ctl.py validate -c config.yaml
```

### List Configured Connectors

```bash
./cli/integrations_ctl.py list -c config.yaml
```

### Test Connectors

```bash
# Test specific connector
./cli/integrations_ctl.py test -c config.yaml -n slack_alerts

# Test all connectors
./cli/integrations_ctl.py test-all -c config.yaml

# Test with different severity
./cli/integrations_ctl.py test -c config.yaml -n email_alerts -t critical
```

### Send Custom Alerts

```bash
./cli/integrations_ctl.py alert \
  -c config.yaml \
  -l error \
  -t "Custom Alert" \
  -m "This is a custom test alert" \
  --tags "test,custom" \
  --metadata '{"test_id": "001"}'
```

### Monitor Mode

```bash
# Run continuous monitoring (sends periodic health checks)
./cli/integrations_ctl.py monitor -c config.yaml --interval 60
```

## Connector Types

### Syslog Connector

Sends events to syslog servers via UDP or TCP.

**Configuration:**
```yaml
syslog_connector:
  type: syslog
  enabled: true
  host: localhost
  port: 514
  protocol: udp  # or tcp
  facility: 16   # syslog facility (default: local0)
```

**Features:**
- UDP and TCP support
- Configurable syslog facility
- Automatic priority mapping from alert levels

### HTTP Connector

Sends events to HTTP/HTTPS endpoints as JSON webhooks.

**Configuration:**
```yaml
http_connector:
  type: http
  enabled: true
  url: https://api.example.com/webhook
  method: POST
  headers:
    Authorization: Bearer TOKEN
    Content-Type: application/json
  timeout: 30
  verify_ssl: true
  auth:
    type: basic
    username: user
    password: pass
```

**Features:**
- Custom headers and authentication
- Configurable HTTP methods
- SSL verification control
- Request timeout handling

### Email Connector

Sends events via SMTP as formatted emails.

**Configuration:**
```yaml
email_connector:
  type: email
  enabled: true
  smtp_host: smtp.gmail.com
  smtp_port: 587
  use_tls: true
  username: sender@example.com
  password: app_password
  from_email: alerts@example.com
  to_emails: [admin@example.com]
  subject_template: "Alert: {level} - {title}"
```

**Features:**
- HTML and plain text email bodies
- Customizable subject templates
- Multiple recipients
- TLS/SSL support

### Slack Connector

Sends formatted messages to Slack channels via webhooks.

**Configuration:**
```yaml
slack_connector:
  type: slack
  enabled: true
  webhook_url: https://hooks.slack.com/services/...
  channel: "#alerts"
  username: LNMT Bot
  icon_emoji: ":robot_face:"
```

**Features:**
- Rich message formatting with colors
- Custom channel targeting
- Attachment-based layout
- Emoji and username customization

### Discord Connector

Sends rich embeds to Discord channels via webhooks.

**Configuration:**
```yaml
discord_connector:
  type: discord
  enabled: true
  webhook_url: https://discord.com/api/webhooks/...
  username: LNMT
  avatar_url: https://example.com/avatar.png
```

**Features:**
- Rich embed formatting
- Color-coded by alert level
- Custom avatar and username
- Structured field layout

## Filtering and Rate Limiting

### Level Filtering

Filter events by minimum alert level:

```yaml
filters:
  min_level: warning  # Only warning, error, critical
```

Alert level hierarchy: `debug < info < warning < error < critical`

### Event Type Filtering

Filter by specific event types:

```yaml
filters:
  event_types:
    - system_health
    - critical_error
    - threshold_breach
```

Available event types:
- `system_health`
- `threshold_breach`
- `critical_error`
- `performance_alert`
- `security_event`
- `custom`

### Tag Filtering

Require specific tags to be present:

```yaml
filters:
  required_tags:
    - production
    - critical
```

### Rate Limiting

Prevent spam by limiting events per time window:

```yaml
rate_limit:
  max_per_window: 10
  window: 3600  # 1 hour in seconds
```

## Event Structure

All events follow a standard structure:

```python
@dataclass
class IntegrationEvent:
    event_id: str           # Unique event identifier
    timestamp: datetime     # When the event occurred
    event_type: EventType   # Type of event
    level: AlertLevel       # Severity level
    source: str            # Source system/component
    title: str             # Short event title
    message: str           # Detailed message
    metadata: Dict         # Additional structured data
    tags: List[str]        # Event tags for filtering
```

## Integration Examples

### Health Monitoring

```python
class SystemHealthMonitor:
    def __init__(self):
        self.integration_service = IntegrationConnectorService("config.yaml")
    
    async def check_disk_space(self):
        usage = self.get_disk_usage()
        if usage > 90:
            await self.integration_service.alert(
                level=AlertLevel.CRITICAL,
                title="Disk Space Critical",
                message=f"Disk usage at {usage}% - immediate action required",
                source="disk_monitor",
                event_type=EventType.THRESHOLD_BREACH,
                metadata={
                    "disk_usage": usage,
                    "threshold": 90,
                    "available_gb": self.get_available_space()
                },
                tags=["filesystem", "critical", "production"]
            )
```

### Application Monitoring

```python
class ApplicationMonitor:
    async def on_application_error(self, error):
        await send_critical_alert(
            title="Application Error",
            message=f"Unhandled exception: {str(error)}",
            source="application",
            metadata={
                "error_type": error.__class__.__name__,
                "stack_trace": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            },
            tags=["application", "error", "production"]
        )
    
    async def on_performance_issue(self, metric, value, threshold):
        await send_threshold_alert(
            title=f"{metric} Threshold Exceeded",
            message=f"{metric} is {value}, exceeding threshold of {threshold}",
            source="performance_monitor",
            metadata={
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "severity": "high" if value > threshold * 1.5 else "medium"
            },
            tags=["performance", metric.lower(), "monitoring"]
        )
```

### Security Monitoring

```python
class SecurityMonitor:
    async def on_failed_login_attempts(self, ip, attempts):
        if attempts > 5:
            await self.integration_service.alert(
                level=AlertLevel.ERROR,
                title="Multiple Failed Login Attempts",
                message=f"IP {ip} has failed {attempts} login attempts",
                source="security_monitor",
                event_type=EventType.SECURITY_EVENT,
                metadata={
                    "ip_address": ip,
                    "attempt_count": attempts,
                    "time_window": "1 hour",
                    "action_taken": "IP blocked"
                },
                tags=["security", "login", "intrusion"]
            )
```

## Error Handling and Logging

The integration system includes comprehensive error handling:

- **Connector Failures**: Individual connector failures don't affect others
- **Retry Logic**: Automatic retries for transient failures
- **Logging**: Detailed logging for debugging and monitoring
- **Graceful Degradation**: System continues working even if some connectors fail

### Logging Configuration

```python
import logging

# Configure logging for integration connectors
logging.getLogger("lnmt.integration_connectors").setLevel(logging.INFO)
logging.getLogger("lnmt.connectors").setLevel(logging.DEBUG)
```

## Security Considerations

### Webhook Security

- Use HTTPS endpoints when possible
- Validate SSL certificates (`verify_ssl: true`)
- Use proper authentication (API keys, basic auth)
- Consider IP whitelisting on webhook endpoints

### Email Security

- Use app-specific passwords for Gmail
- Enable TLS encryption
- Avoid sending sensitive data in email bodies
- Consider using encrypted email services

### Configuration Security

- Store sensitive data (passwords, tokens) in environment variables
- Use proper file permissions on configuration files
- Consider using secret management systems
- Rotate API keys and passwords regularly

## Performance Considerations

### Async Operations

All connectors operate asynchronously to prevent blocking:

```python
# Multiple connectors are called concurrently
await asyncio.gather(
    connector1.send_event(event),
    connector2.send_event(event),
    connector3.send_event(event)
)
```

### Rate Limiting

Rate limiting prevents overwhelming external systems:

- Configurable per connector
- Based on event type and level
- Sliding window algorithm
- Automatic cleanup of old rate limit data

### Memory Usage

- Events are not stored permanently
- Rate limit data is cleaned up automatically
- Connection pooling for HTTP connectors
- Efficient JSON serialization

## Testing

### Unit Tests

Run the test suite:

```bash
cd tests
python -m pytest test_integration_connectors.py -v
```

### Integration Tests

Test with real services:

```bash
# Test specific connector
./cli/integrations_ctl.py test -c config.yaml -n slack_alerts -t warning

# Test all connectors
./cli/integrations_ctl.py test-all -c config.yaml
```

### Load Testing

For high-volume environments, test with realistic loads:

```python
async def load_test():
    service = IntegrationConnectorService("config.yaml")
    
    # Send 1000 events concurrently
    tasks = []
    for i in range(1000):
        task = service.alert(
            level=AlertLevel.INFO,
            title=f"Load Test Event {i}",
            message="Load testing the integration system",
            source="load_test",
            tags=["test", "load"]
        )
        tasks.append(task)
    
    await asyncio.gather(*tasks)
```

## Troubleshooting

### Common Issues

**Configuration Validation Errors**
```bash
# Validate your configuration
./cli/integrations_ctl.py validate -c config.yaml
```

**Connector Not Sending Events**
- Check if connector is enabled
- Verify filters aren't blocking events
- Check rate limits
- Review logs for errors

**Network/Authentication Issues**
- Test connectivity to external services
- Verify API keys and credentials
- Check firewall rules
- Validate SSL certificates

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Monitor connector health:

```python
# Check connector status
status = service.get_connector_status()
for name, info in status.items():
    print(f"{name}: {'OK' if info['enabled'] else 'DISABLED'}")
```

## Extending the System

### Custom Connectors

Create custom connectors by extending `BaseConnector`:

```python
from services.integration_connectors import BaseConnector

class CustomConnector(BaseConnector):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.custom_config = config.get('custom_setting')
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        try:
            # Implement your custom sending logic
            await self.send_to_custom_service(event)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send: {e}")
            return False
    
    async def send_to_custom_service(self, event):
        # Your implementation here
        pass
```

### Custom Event Types

Add custom event types:

```python
class CustomEventType(Enum):
    DEPLOYMENT = "deployment"
    BACKUP_COMPLETE = "backup_complete"
    MAINTENANCE = "maintenance"
```

## API Reference

### IntegrationConnectorService

**Methods:**
- `load_config(config_path: str)` - Load configuration from file
- `alert(...)` - Send alert to connectors
- `send_event(event, connectors)` - Send event to specific connectors
- `create_event(...)` - Create new event
- `register_hook(event_type, callback)` - Register event hook
- `get_connector_status()` - Get status of all connectors

### BaseConnector

**Methods:**
- `send_event(event)` - Send event (abstract)
- `should_send(event)` - Check if event should be sent

### IntegrationEvent

**Properties:**
- `event_id` - Unique identifier
- `timestamp` - Event timestamp
- `event_type` - Type of event
- `level` - Alert level
- `source` - Source system
- `title` - Event title
- `message` - Event message
- `metadata` - Additional data
- `tags` - Event tags

**Methods:**
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string

## Best Practices

1. **Configuration Management**
   - Use version control for configuration files
   - Separate configs for different environments
   - Use environment variables for secrets

2. **Event Design**
   - Use descriptive titles and messages
   - Include relevant metadata
   - Use consistent tagging schemes
   - Set appropriate alert levels

3. **Filtering**
   - Configure appropriate filters to reduce noise
   - Use rate limiting to prevent spam
   - Test filters thoroughly

4. **Monitoring**
   - Monitor connector health
   - Set up alerts for connector failures
   - Review logs regularly

5. **Security**
   - Use secure authentication methods
   - Encrypt sensitive configuration data
   - Regularly rotate credentials
   - Validate webhook endpoints

6. **Performance**
   - Use async operations
   - Configure appropriate timeouts
   - Monitor resource usage
   - Test under realistic loads

## Conclusion

The LNMT Integration Connectors module provides a powerful, flexible system for pushing alerts and events to external systems. With support for multiple connector types, comprehensive filtering, rate limiting, and robust error handling, it can handle the alerting needs of any LNMT deployment.

The modular design allows for easy extension and customization, while the CLI tools provide convenient management and testing capabilities. By following the configuration examples and best practices outlined in this documentation, you can quickly set up reliable alerting for your LNMT system.