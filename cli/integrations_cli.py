#!/usr/bin/env python3
"""
LNMT Integration Connectors CLI
Command-line interface for managing and testing integration connectors.
"""

import argparse
import asyncio
import json
import logging
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import the integration service
sys.path.append(str(Path(__file__).parent.parent))
from services.integration_connectors import (
    IntegrationConnectorService, 
    AlertLevel, 
    EventType,
    IntegrationEvent
)


class IntegrationsCLI:
    """CLI interface for integration connectors"""
    
    def __init__(self):
        self.service = IntegrationConnectorService()
        self.logger = logging.getLogger("lnmt.integrations_cli")
    
    async def load_config(self, config_path: str) -> bool:
        """Load configuration file"""
        try:
            self.service.load_config(config_path)
            print(f"✅ Configuration loaded from {config_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return False
    
    async def list_connectors(self):
        """List all configured connectors"""
        status = self.service.get_connector_status()
        
        if not status:
            print("No connectors configured.")
            return
        
        print("\n📡 Configured Connectors:")
        print("-" * 50)
        
        for name, info in status.items():
            enabled_status = "✅ Enabled" if info['enabled'] else "❌ Disabled"
            print(f"Name: {name}")
            print(f"Type: {info['type']}")
            print(f"Status: {enabled_status}")
            
            if info['filters']:
                print(f"Filters: {json.dumps(info['filters'], indent=2)}")
            
            if info['rate_limit']:
                print(f"Rate Limit: {json.dumps(info['rate_limit'], indent=2)}")
            
            print("-" * 30)
    
    async def test_connector(self, connector_name: str, test_type: str = "basic"):
        """Test a specific connector"""
        if connector_name not in self.service.connectors:
            print(f"❌ Connector '{connector_name}' not found.")
            return False
        
        print(f"🧪 Testing connector: {connector_name}")
        
        # Create test event
        if test_type == "critical":
            event = self.service.create_event(
                event_type=EventType.CRITICAL_ERROR,
                level=AlertLevel.CRITICAL,
                source="integrations_cli",
                title="Critical Test Alert",
                message="This is a test of the critical alert system. If you receive this, the integration is working correctly.",
                metadata={"test": True, "test_type": "critical"},
                tags=["test", "critical", "cli"]
            )
        elif test_type == "warning":
            event = self.service.create_event(
                event_type=EventType.SYSTEM_HEALTH,
                level=AlertLevel.WARNING,
                source="integrations_cli",
                title="Warning Test Alert",
                message="This is a test warning message. System appears to be functioning normally.",
                metadata={"test": True, "test_type": "warning"},
                tags=["test", "warning", "cli"]
            )
        else:  # basic test
            event = self.service.create_event(
                event_type=EventType.CUSTOM,
                level=AlertLevel.INFO,
                source="integrations_cli",
                title="Basic Test Message",
                message="This is a basic test message from the LNMT integration system.",
                metadata={"test": True, "test_type": "basic"},
                tags=["test", "info", "cli"]
            )
        
        try:
            await self.service.send_event(event, [connector_name])
            print(f"✅ Test message sent successfully to {connector_name}")
            print(f"Event ID: {event.event_id}")
            return True
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    async def test_all_connectors(self, test_type: str = "basic"):
        """Test all enabled connectors"""
        enabled_connectors = [
            name for name, connector in self.service.connectors.items()
            if connector.enabled
        ]
        
        if not enabled_connectors:
            print("No enabled connectors found.")
            return
        
        print(f"🧪 Testing {len(enabled_connectors)} enabled connectors...")
        
        results = {}
        for connector_name in enabled_connectors:
            print(f"\nTesting {connector_name}...")
            results[connector_name] = await self.test_connector(connector_name, test_type)
        
        print("\n📊 Test Results Summary:")
        print("-" * 40)
        for connector_name, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{connector_name}: {status}")
    
    async def send_custom_alert(
        self, 
        level: str, 
        title: str, 
        message: str,
        source: str = "integrations_cli",
        event_type: str = "custom",
        connectors: Optional[str] = None,
        tags: Optional[str] = None,
        metadata: Optional[str] = None
    ):
        """Send a custom alert"""
        try:
            # Parse level
            alert_level = AlertLevel(level.lower())
            
            # Parse event type
            try:
                evt_type = EventType(event_type.lower())
            except ValueError:
                evt_type = EventType.CUSTOM
            
            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
            
            # Parse metadata
            metadata_dict = {}
            if metadata:
                try:
                    metadata_dict = json.loads(metadata)
                except json.JSONDecodeError:
                    print("⚠️  Invalid JSON metadata, using empty dict")
            
            # Parse connectors
            connector_list = None
            if connectors:
                connector_list = [conn.strip() for conn in connectors.split(',')]
            
            # Send alert
            await self.service.alert(
                level=alert_level,
                title=title,
                message=message,
                source=source,
                event_type=evt_type,
                metadata=metadata_dict,
                tags=tag_list,
                connectors=connector_list
            )
            
            print(f"✅ Custom alert sent successfully")
            if connector_list:
                print(f"Sent to connectors: {', '.join(connector_list)}")
            else:
                print("Sent to all enabled connectors")
                
        except ValueError as e:
            print(f"❌ Invalid parameter: {e}")
        except Exception as e:
            print(f"❌ Failed to send alert: {e}")
    
    async def validate_config(self, config_path: str):
        """Validate configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            print(f"🔍 Validating configuration: {config_path}")
            print("-" * 50)
            
            # Check structure
            if 'connectors' not in config:
                print("❌ Missing 'connectors' section")
                return False
            
            connectors = config['connectors']
            if not isinstance(connectors, dict):
                print("❌ 'connectors' must be a dictionary")
                return False
            
            valid_types = ['syslog', 'http', 'email', 'slack', 'discord']
            validation_results = {}
            
            for name, connector_config in connectors.items():
                print(f"\n📋 Validating connector: {name}")
                
                # Check required fields
                if 'type' not in connector_config:
                    print(f"❌ Missing 'type' field")
                    validation_results[name] = False
                    continue
                
                connector_type = connector_config['type']
                if connector_type not in valid_types:
                    print(f"❌ Invalid type '{connector_type}'. Must be one of: {valid_types}")
                    validation_results[name] = False
                    continue
                
                # Type-specific validation
                is_valid = True
                
                if connector_type == 'syslog':
                    required = ['host', 'port']
                    for field in required:
                        if field not in connector_config:
                            print(f"❌ Missing required field for syslog: {field}")
                            is_valid = False
                
                elif connector_type == 'http':
                    if 'url' not in connector_config:
                        print(f"❌ Missing required field for http: url")
                        is_valid = False
                
                elif connector_type == 'email':
                    required = ['smtp_host', 'from_email', 'to_emails']
                    for field in required:
                        if field not in connector_config:
                            print(f"❌ Missing required field for email: {field}")
                            is_valid = False
                
                elif connector_type == 'slack':
                    if 'webhook_url' not in connector_config:
                        print(f"❌ Missing required field for slack: webhook_url")
                        is_valid = False
                
                elif connector_type == 'discord':
                    if 'webhook_url' not in connector_config:
                        print(f"❌ Missing required field for discord: webhook_url")
                        is_valid = False
                
                if is_valid:
                    print(f"✅ Connector {name} is valid")
                
                validation_results[name] = is_valid
            
            # Summary
            print("\n📊 Validation Summary:")
            print("-" * 30)
            all_valid = True
            for name, is_valid in validation_results.items():
                status = "✅ VALID" if is_valid else "❌ INVALID"
                print(f"{name}: {status}")
                if not is_valid:
                    all_valid = False
            
            if all_valid:
                print("\n🎉 Configuration is valid!")
                return True
            else:
                print("\n❌ Configuration has errors")
                return False
                
        except Exception as e:
            print(f"❌ Failed to validate config: {e}")
            return False
    
    def generate_sample_config(self) -> str:
        """Generate sample configuration"""
        sample_config = {
            'connectors': {
                'local_syslog': {
                    'type': 'syslog',
                    'enabled': True,
                    'host': 'localhost',
                    'port': 514,
                    'protocol': 'udp',
                    'facility': 16,
                    'filters': {
                        'min_level': 'warning'
                    }
                },
                'webhook_endpoint': {
                    'type': 'http',
                    'enabled': True,
                    'url': 'https://api.example.com/webhooks/lnmt',
                    'method': 'POST',
                    'headers': {
                        'Authorization': 'Bearer YOUR_TOKEN'
                    },
                    'timeout': 30,
                    'verify_ssl': True,
                    'filters': {
                        'event_types': ['critical_error', 'system_health']
                    }
                },
                'email_alerts': {
                    'type': 'email',
                    'enabled': True,
                    'smtp_host': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'use_tls': True,
                    'username': 'your_email@gmail.com',
                    'password': 'your_app_password',
                    'from_email': 'lnmt@yourcompany.com',
                    'to_emails': ['admin@yourcompany.com', 'ops@yourcompany.com'],
                    'subject_template': 'LNMT Alert: {level} - {title}',
                    'filters': {
                        'min_level': 'error'
                    },
                    'rate_limit': {
                        'max_per_window': 5,
                        'window': 3600
                    }
                },
                'slack_alerts': {
                    'type': 'slack',
                    'enabled': True,
                    'webhook_url': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
                    'channel': '#alerts',
                    'username': 'LNMT Bot',
                    'icon_emoji': ':robot_face:',
                    'filters': {
                        'min_level': 'warning',
                        'required_tags': ['production']
                    }
                },
                'discord_alerts': {
                    'type': 'discord',
                    'enabled': False,
                    'webhook_url': 'https://discord.com/api/webhooks/YOUR/WEBHOOK/URL',
                    'username': 'LNMT',
                    'filters': {
                        'min_level': 'critical'
                    }
                }
            }
        }
        
        return yaml.dump(sample_config, indent=2, default_flow_style=False)
    
    async def monitor_mode(self, config_path: str, interval: int = 30):
        """Run in monitoring mode - periodically check system health"""
        print(f"🔄 Starting monitor mode (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        
        if not await self.load_config(config_path):
            return
        
        try:
            while True:
                # Simulate system health check
                await self.service.alert(
                    level=AlertLevel.INFO,
                    title="System Health Check",
                    message="Periodic system health check - all systems operational",
                    source="monitor",
                    event_type=EventType.SYSTEM_HEALTH,
                    tags=["monitoring", "health"]
                )
                
                print(f"📊 Health check sent at {datetime.now()}")
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitor mode stopped")


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="LNMT Integration Connectors CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate configuration
  %(prog)s validate -c config.yaml
  
  # List connectors
  %(prog)s list -c config.yaml
  
  # Test all connectors
  %(prog)s test-all -c config.yaml
  
  # Test specific connector
  %(prog)s test -c config.yaml -n slack_alerts
  
  # Send custom alert
  %(prog)s alert -c config.yaml -l error -t "High CPU" -m "CPU usage at 90%"
  
  # Generate sample config
  %(prog)s sample-config > config.yaml
  
  # Monitor mode
  %(prog)s monitor -c config.yaml --interval 60
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List configured connectors')
    list_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test specific connector')
    test_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    test_parser.add_argument('-n', '--name', required=True, help='Connector name')
    test_parser.add_argument('-t', '--type', choices=['basic', 'warning', 'critical'], 
                           default='basic', help='Test type')
    
    # Test-all command
    test_all_parser = subparsers.add_parser('test-all', help='Test all enabled connectors')
    test_all_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    test_all_parser.add_argument('-t', '--type', choices=['basic', 'warning', 'critical'], 
                                default='basic', help='Test type')
    
    # Alert command
    alert_parser = subparsers.add_parser('alert', help='Send custom alert')
    alert_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    alert_parser.add_argument('-l', '--level', required=True, 
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            help='Alert level')
    alert_parser.add_argument('-t', '--title', required=True, help='Alert title')
    alert_parser.add_argument('-m', '--message', required=True, help='Alert message')
    alert_parser.add_argument('-s', '--source', default='integrations_cli', help='Alert source')
    alert_parser.add_argument('-e', '--event-type', default='custom', help='Event type')
    alert_parser.add_argument('-n', '--connectors', help='Comma-separated connector names')
    alert_parser.add_argument('--tags', help='Comma-separated tags')
    alert_parser.add_argument('--metadata', help='JSON metadata')
    
    # Sample config command
    sample_config_parser = subparsers.add_parser('sample-config', help='Generate sample configuration')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Run in monitoring mode')
    monitor_parser.add_argument('-c', '--config', required=True, help='Configuration file path')
    monitor_parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create CLI instance
    cli = IntegrationsCLI()
    
    # Execute command
    try:
        if args.command == 'validate':
            success = await cli.validate_config(args.config)
            sys.exit(0 if success else 1)
        
        elif args.command == 'list':
            if await cli.load_config(args.config):
                await cli.list_connectors()
        
        elif args.command == 'test':
            if await cli.load_config(args.config):
                success = await cli.test_connector(args.name, args.type)
                sys.exit(0 if success else 1)
        
        elif args.command == 'test-all':
            if await cli.load_config(args.config):
                await cli.test_all_connectors(args.type)
        
        elif args.command == 'alert':
            if await cli.load_config(args.config):
                await cli.send_custom_alert(
                    level=args.level,
                    title=args.title,
                    message=args.message,
                    source=args.source,
                    event_type=args.event_type,
                    connectors=args.connectors,
                    tags=args.tags,
                    metadata=args.metadata
                )
        
        elif args.command == 'sample-config':
            print(cli.generate_sample_config())
        
        elif args.command == 'monitor':
            await cli.monitor_mode(args.config, args.interval)
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())