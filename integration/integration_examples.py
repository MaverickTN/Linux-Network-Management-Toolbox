#!/usr/bin/env python3
"""
LNMT Integration Connectors Examples
Demonstrates how to use the integration connectors service.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.integration_connectors import (
    IntegrationConnectorService,
    AlertLevel,
    EventType,
    IntegrationEvent,
    send_critical_alert,
    send_health_alert,
    send_threshold_alert
)


async def example_basic_usage():
    """Basic usage example"""
    print("🚀 Example 1: Basic Usage")
    print("-" * 40)
    
    # Initialize service
    service = IntegrationConnectorService()
    
    # Create a basic event
    event = service.create_event(
        event_type=EventType.SYSTEM_HEALTH,
        level=AlertLevel.INFO,
        source="example_app",
        title="Application Started",
        message="The example application has started successfully",
        metadata={
            "version": "1.0.0",
            "startup_time": datetime.now().isoformat(),
            "pid": 12345
        },
        tags=["startup", "info"]
    )
    
    print(f"Created event: {event.event_id}")
    print(f"Event JSON:\n{event.to_json()}")
    
    # Note: Without configuration, no connectors are available
    print("✅ Basic event creation completed")


async def example_with_config():
    """Example with configuration file"""
    print("\n🔧 Example 2: With Configuration")
    print("-" * 40)
    
    # Create sample configuration
    config_data = {
        'connectors': {
            'console_webhook': {
                'type': 'http',
                'enabled': True,
                'url': 'https://httpbin.org/post',  # Test endpoint
                'method': 'POST',
                'timeout': 10,
                'filters': {
                    'min_level': 'info'
                }
            }
        }
    }
    
    # Save config to temporary file
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        # Initialize service with config
        service = IntegrationConnectorService(config_path)
        
        # Send test alert
        await service.alert(
            level=AlertLevel.WARNING,
            title="High Memory Usage",
            message="Memory usage has exceeded 80%",
            source="memory_monitor",
            metadata={"memory_percent": 82.5, "threshold": 80.0},
            tags=["memory", "performance"]
        )
        
        print("✅ Alert sent with configuration")
        
    finally:
        # Clean up
        Path(config_path).unlink()


async def example_convenience_functions():
    """Example using convenience functions"""
    print("\n⚡ Example 3: Convenience Functions")
    print("-" * 40)
    
    # These functions are available for other LNMT modules
    
    # Critical alert
    await send_critical_alert(
        title="Database Connection Lost",
        message="Unable to connect to primary database server",
        source="database_service",
        metadata={"connection_string": "postgres://db:5432/lnmt", "retry_count": 3},
        tags=["database", "critical"]
    )
    print("✅ Critical alert sent")
    
    # Health alert
    await send_health_alert(
        title="Disk Space Low",
        message="Disk space on /var/log is below 10%",
        source="filesystem_monitor",
        metadata={"disk_usage": 92.3, "available_gb": 1.2},
        tags=["filesystem", "disk"]
    )
    print("✅ Health alert sent")
    
    # Threshold alert
    await send_threshold_alert(
        title="Response Time Threshold Exceeded",
        message="Average response time exceeded 2 seconds",
        source="api_monitor",
        metadata={"avg_response_time": 2.34, "threshold": 2.0, "request_count": 150},
        tags=["api", "performance"]
    )
    print("✅ Threshold alert sent")


async def example_custom_hooks():
    """Example with custom event hooks"""
    print("\n🪝 Example 4: Custom Event Hooks")
    print("-" * 40)
    
    service = IntegrationConnectorService()
    
    # Define custom hooks
    async def async_hook(event: IntegrationEvent):
        print(f"🔄 Async hook triggered for: {event.title}")
        # Could perform async operations like logging to database
        await asyncio.sleep(0.1)  # Simulate async work
    
    def sync_hook(event: IntegrationEvent):
        print(f"⚡ Sync hook triggered for: {event.title}")
        # Could perform sync operations like updating counters
    
    # Register hooks
    service.register_hook(EventType.CRITICAL_ERROR, async_hook)
    service.register_hook(EventType.SYSTEM_HEALTH, sync_hook)
    
    # Create and trigger events
    critical_event = service.create_event(
        event_type=EventType.CRITICAL_ERROR,
        level=AlertLevel.CRITICAL,
        source="test_system",
        title="Critical System Failure",
        message="System has encountered a critical error",
        tags=["critical", "system"]
    )
    
    health_event = service.create_event(
        event_type=EventType.SYSTEM_HEALTH,
        level=AlertLevel.INFO,
        source="health_check",
        title="System Health OK",
        message="All systems are functioning normally",
        tags=["health", "status"]
    )
    
    # Trigger hooks
    await service.trigger_hooks(critical_event)
    await service.trigger_hooks(health_event)
    
    print("✅ Custom hooks example completed")


async def example_filtering_and_rate_limiting():
    """Example demonstrating filtering and rate limiting"""
    print("\n🔍 Example 5: Filtering and Rate Limiting")
    print("-" * 40)
    
    # Create service with detailed config
    config_data = {
        'connectors': {
            'filtered_connector': {
                'type': 'http',
                'enabled': True,
                'url': 'https://httpbin.org/post',
                'filters': {
                    'min_level': 'warning',
                    'event_types': ['system_health', 'critical_error'],
                    'required_tags': ['production']
                },
                'rate_limit': {
                    'max_per_window': 2,
                    'window': 60  # 1 minute
                }
            }
        }
    }
    
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        service = IntegrationConnectorService(config_path)
        
        # Test events
        test_events = [
            # Should be filtered out (level too low)
            (EventType.SYSTEM_HEALTH, AlertLevel.INFO, ["production"], "Info message"),
            
            # Should pass (meets criteria)
            (EventType.SYSTEM_HEALTH, AlertLevel.WARNING, ["production"], "Warning message 1"),
            
            # Should pass (meets criteria)
            (EventType.CRITICAL_ERROR, AlertLevel.CRITICAL, ["production"], "Critical message 1"),
            
            # Should be filtered out (missing required tag)
            (EventType.SYSTEM_HEALTH, AlertLevel.ERROR, ["staging"], "Error without prod tag"),
            
            # Should be rate limited (third message in window)
            (EventType.SYSTEM_HEALTH, AlertLevel.WARNING, ["production"], "Warning message 2"),
        ]
        
        print("Testing filtering and rate limiting:")
        for i, (event_type, level, tags, message) in enumerate(test_events, 1):
            event = service.create_event(
                event_type=event_type,
                level=level,
                source="filter_test",
                title=f"Test Event {i}",
                message=message,
                tags=tags
            )
            
            connector = service.connectors['filtered_connector']
            should_send = connector.should_send(event)
            status = "✅ PASS" if should_send else "❌ FILTERED"
            print(f"  Event {i}: {status} - {message}")
    
    finally:
        Path(config_path).unlink()
    
    print("✅ Filtering and rate limiting example completed")


async def example_multiple_connectors():
    """Example with multiple connector types"""
    print("\n🌐 Example 6: Multiple Connector Types")
    print("-" * 40)
    
    # Comprehensive configuration
    config_data = {
        'connectors': {
            'test_syslog': {
                'type': 'syslog',
                'enabled': True,
                'host': 'localhost',
                'port': 514,
                'protocol': 'udp',
                'filters': {'min_level': 'error'}
            },
            'test_webhook': {
                'type': 'http',
                'enabled': True,
                'url': 'https://httpbin.org/post',
                'method': 'POST',
                'headers': {'X-Source': 'LNMT'},
                'filters': {'min_level': 'warning'}
            },
            'test_email': {
                'type': 'email',
                'enabled': False,  # Disabled for demo
                'smtp_host': 'smtp.example.com',
                'smtp_port': 587,
                'from_email': 'lnmt@example.com',
                'to_emails': ['admin@example.com'],
                'filters': {'min_level': 'critical'}
            },
            'test_slack': {
                'type': 'slack',
                'enabled': False,  # Disabled for demo
                'webhook_url': 'https://hooks.slack.com/services/fake/webhook/url',
                'channel': '#alerts',
                'filters': {'min_level': 'warning'}
            }
        }
    }
    
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        service = IntegrationConnectorService(config_path)
        
        # Show connector status
        status = service.get_connector_status()
        print("Configured connectors:")
        for name, info in status.items():
            enabled = "✅" if info['enabled'] else "❌"
            print(f"  {enabled} {name} ({info['type']})")
        
        # Send test alert to all enabled connectors
        await service.alert(
            level=AlertLevel.ERROR,
            title="Multi-Connector Test",
            message="This alert should be sent to all enabled connectors that match the criteria",
            source="multi_test",
            metadata={"test_id": "multi_001", "connectors": list(status.keys())},
            tags=["test", "multi"]
        )
        
        print("✅ Multi-connector alert sent")
        
    finally:
        Path(config_path).unlink()


async def example_error_handling():
    """Example demonstrating error handling"""
    print("\n🚨 Example 7: Error Handling")
    print("-" * 40)
    
    # Config with invalid webhook URL
    config_data = {
        'connectors': {
            'invalid_webhook': {
                'type': 'http',
                'enabled': True,
                'url': 'https://invalid-url-that-does-not-exist.com/webhook',
                'timeout': 5
            },
            'valid_webhook': {
                'type': 'http',
                'enabled': True,
                'url': 'https://httpbin.org/post',
                'timeout': 5
            }
        }
    }
    
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        service = IntegrationConnectorService(config_path)
        
        # Send alert - one connector will fail, one will succeed
        print("Sending alert to both valid and invalid connectors...")
        
        await service.alert(
            level=AlertLevel.WARNING,
            title="Error Handling Test",
            message="Testing how the system handles connector failures",
            source="error_test",
            tags=["test", "error-handling"]
        )
        
        print("✅ Error handling test completed (check logs for details)")
        
    finally:
        Path(config_path).unlink()


async def main():
    """Run all examples"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 LNMT Integration Connectors Examples")
    print("=" * 50)
    
    examples = [
        example_basic_usage,
        example_with_config,
        example_convenience_functions,
        example_custom_hooks,
        example_filtering_and_rate_limiting,
        example_multiple_connectors,
        example_error_handling
    ]
    
    for example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"❌ Example failed: {e}")
        
        # Small delay between examples
        await asyncio.sleep(1)
    
    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())