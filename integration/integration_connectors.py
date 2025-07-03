#!/usr/bin/env python3
"""
LNMT Integration Connectors Service
Enables pushing alerts, events, and reports to external systems.
"""

import asyncio
import json
import logging
import smtplib
import socket
import ssl
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urljoin
import aiohttp
import yaml


class AlertLevel(Enum):
    """Alert severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(Enum):
    """Event types for integration hooks"""
    SYSTEM_HEALTH = "system_health"
    THRESHOLD_BREACH = "threshold_breach"
    CRITICAL_ERROR = "critical_error"
    PERFORMANCE_ALERT = "performance_alert"
    SECURITY_EVENT = "security_event"
    CUSTOM = "custom"


@dataclass
class IntegrationEvent:
    """Standard event structure for integrations"""
    event_id: str
    timestamp: datetime
    event_type: EventType
    level: AlertLevel
    source: str
    title: str
    message: str
    metadata: Dict[str, Any]
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class BaseConnector(ABC):
    """Base class for all integration connectors"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(f"lnmt.connectors.{name}")
        self._filters = config.get('filters', {})
        self._rate_limit = config.get('rate_limit', {})
        self._last_sent = {}
    
    @abstractmethod
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event to external system"""
        pass
    
    def should_send(self, event: IntegrationEvent) -> bool:
        """Check if event should be sent based on filters and rate limits"""
        if not self.enabled:
            return False
        
        # Level filtering
        min_level = self._filters.get('min_level')
        if min_level:
            level_order = [AlertLevel.DEBUG, AlertLevel.INFO, AlertLevel.WARNING, 
                          AlertLevel.ERROR, AlertLevel.CRITICAL]
            if level_order.index(event.level) < level_order.index(AlertLevel(min_level)):
                return False
        
        # Event type filtering
        allowed_types = self._filters.get('event_types')
        if allowed_types and event.event_type.value not in allowed_types:
            return False
        
        # Tag filtering
        required_tags = self._filters.get('required_tags', [])
        if required_tags and not all(tag in event.tags for tag in required_tags):
            return False
        
        # Rate limiting
        if self._check_rate_limit(event):
            return False
        
        return True
    
    def _check_rate_limit(self, event: IntegrationEvent) -> bool:
        """Check if rate limit is exceeded"""
        if not self._rate_limit:
            return False
        
        key = f"{event.event_type.value}_{event.level.value}"
        now = time.time()
        
        # Clean old entries
        cutoff = now - self._rate_limit.get('window', 3600)
        self._last_sent = {k: v for k, v in self._last_sent.items() if v > cutoff}
        
        # Check rate limit
        max_per_window = self._rate_limit.get('max_per_window', 10)
        current_count = len([t for t in self._last_sent.values() if t > cutoff])
        
        if current_count >= max_per_window:
            return True
        
        self._last_sent[f"{key}_{now}"] = now
        return False


class SyslogConnector(BaseConnector):
    """Syslog integration connector"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 514)
        self.facility = config.get('facility', 16)  # local0
        self.protocol = config.get('protocol', 'udp')
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event via syslog"""
        try:
            # Map alert levels to syslog priorities
            priority_map = {
                AlertLevel.DEBUG: 7,    # debug
                AlertLevel.INFO: 6,     # info
                AlertLevel.WARNING: 4,  # warning
                AlertLevel.ERROR: 3,    # error
                AlertLevel.CRITICAL: 2  # critical
            }
            
            priority = self.facility * 8 + priority_map[event.level]
            message = f"<{priority}>{event.title}: {event.message}"
            
            if self.protocol.lower() == 'tcp':
                await self._send_tcp(message)
            else:
                await self._send_udp(message)
            
            self.logger.debug(f"Sent syslog message: {event.event_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send syslog message: {e}")
            return False
    
    async def _send_udp(self, message: str):
        """Send via UDP"""
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            await loop.run_in_executor(
                None, sock.sendto, message.encode('utf-8'), (self.host, self.port)
            )
        finally:
            sock.close()
    
    async def _send_tcp(self, message: str):
        """Send via TCP"""
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            writer.write(message.encode('utf-8') + b'\n')
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


class HttpConnector(BaseConnector):
    """HTTP/HTTPS webhook connector"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.url = config['url']
        self.method = config.get('method', 'POST')
        self.headers = config.get('headers', {})
        self.auth = config.get('auth')
        self.timeout = config.get('timeout', 30)
        self.verify_ssl = config.get('verify_ssl', True)
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event via HTTP webhook"""
        try:
            payload = event.to_dict()
            headers = {'Content-Type': 'application/json', **self.headers}
            
            auth = None
            if self.auth:
                if self.auth['type'] == 'basic':
                    auth = aiohttp.BasicAuth(
                        self.auth['username'], 
                        self.auth['password']
                    )
            
            connector = aiohttp.TCPConnector(verify_ssl=self.verify_ssl)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.request(
                    self.method,
                    self.url,
                    json=payload,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status < 400:
                        self.logger.debug(f"Sent HTTP event: {event.event_id}")
                        return True
                    else:
                        self.logger.error(
                            f"HTTP request failed: {response.status} {await response.text()}"
                        )
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send HTTP event: {e}")
            return False


class EmailConnector(BaseConnector):
    """Email/SMTP connector"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.smtp_host = config['smtp_host']
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', True)
        self.from_email = config['from_email']
        self.to_emails = config['to_emails']
        self.subject_template = config.get('subject_template', 
                                         'LNMT Alert: {level} - {title}')
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event via email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.subject_template.format(
                level=event.level.value.upper(),
                title=event.title,
                source=event.source
            )
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create HTML and text versions
            text_body = self._create_text_body(event)
            html_body = self._create_html_body(event)
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)
            
            self.logger.debug(f"Sent email for event: {event.event_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_smtp(self, msg):
        """Send SMTP message (blocking)"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)
    
    def _create_text_body(self, event: IntegrationEvent) -> str:
        """Create plain text email body"""
        return f"""
LNMT Alert

Event ID: {event.event_id}
Timestamp: {event.timestamp}
Level: {event.level.value.upper()}
Type: {event.event_type.value}
Source: {event.source}

Title: {event.title}

Message:
{event.message}

Tags: {', '.join(event.tags)}

Metadata:
{json.dumps(event.metadata, indent=2)}
        """.strip()
    
    def _create_html_body(self, event: IntegrationEvent) -> str:
        """Create HTML email body"""
        level_colors = {
            AlertLevel.DEBUG: '#6c757d',
            AlertLevel.INFO: '#17a2b8',
            AlertLevel.WARNING: '#ffc107',
            AlertLevel.ERROR: '#dc3545',
            AlertLevel.CRITICAL: '#721c24'
        }
        
        color = level_colors.get(event.level, '#6c757d')
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">LNMT Alert - {event.level.value.upper()}</h2>
                </div>
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 5px 5px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="font-weight: bold; padding: 5px;">Event ID:</td><td style="padding: 5px;">{event.event_id}</td></tr>
                        <tr><td style="font-weight: bold; padding: 5px;">Timestamp:</td><td style="padding: 5px;">{event.timestamp}</td></tr>
                        <tr><td style="font-weight: bold; padding: 5px;">Type:</td><td style="padding: 5px;">{event.event_type.value}</td></tr>
                        <tr><td style="font-weight: bold; padding: 5px;">Source:</td><td style="padding: 5px;">{event.source}</td></tr>
                    </table>
                    
                    <h3>{event.title}</h3>
                    <p>{event.message}</p>
                    
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 3px; margin-top: 15px;">
                        <strong>Tags:</strong> {', '.join(event.tags)}<br>
                        <strong>Metadata:</strong>
                        <pre style="background-color: #e9ecef; padding: 10px; border-radius: 3px; overflow-x: auto;">
{json.dumps(event.metadata, indent=2)}
                        </pre>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """


class SlackConnector(BaseConnector):
    """Slack webhook connector"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.webhook_url = config['webhook_url']
        self.channel = config.get('channel')
        self.username = config.get('username', 'LNMT')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event to Slack"""
        try:
            # Map levels to colors and emojis
            level_config = {
                AlertLevel.DEBUG: {'color': '#6c757d', 'emoji': ':mag:'},
                AlertLevel.INFO: {'color': '#17a2b8', 'emoji': ':information_source:'},
                AlertLevel.WARNING: {'color': '#ffc107', 'emoji': ':warning:'},
                AlertLevel.ERROR: {'color': '#dc3545', 'emoji': ':x:'},
                AlertLevel.CRITICAL: {'color': '#721c24', 'emoji': ':rotating_light:'}
            }
            
            config = level_config.get(event.level, level_config[AlertLevel.INFO])
            
            # Create Slack message
            payload = {
                'username': self.username,
                'icon_emoji': self.icon_emoji,
                'attachments': [{
                    'color': config['color'],
                    'title': f"{config['emoji']} {event.title}",
                    'text': event.message,
                    'fields': [
                        {'title': 'Level', 'value': event.level.value.upper(), 'short': True},
                        {'title': 'Type', 'value': event.event_type.value, 'short': True},
                        {'title': 'Source', 'value': event.source, 'short': True},
                        {'title': 'Event ID', 'value': event.event_id, 'short': True},
                        {'title': 'Tags', 'value': ', '.join(event.tags), 'short': False}
                    ],
                    'timestamp': int(event.timestamp.timestamp()),
                    'footer': 'LNMT Integration'
                }]
            }
            
            if self.channel:
                payload['channel'] = self.channel
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.debug(f"Sent Slack message: {event.event_id}")
                        return True
                    else:
                        self.logger.error(f"Slack request failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False


class DiscordConnector(BaseConnector):
    """Discord webhook connector"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.webhook_url = config['webhook_url']
        self.username = config.get('username', 'LNMT')
        self.avatar_url = config.get('avatar_url')
    
    async def send_event(self, event: IntegrationEvent) -> bool:
        """Send event to Discord"""
        try:
            # Map levels to colors
            level_colors = {
                AlertLevel.DEBUG: 0x6c757d,
                AlertLevel.INFO: 0x17a2b8,
                AlertLevel.WARNING: 0xffc107,
                AlertLevel.ERROR: 0xdc3545,
                AlertLevel.CRITICAL: 0x721c24
            }
            
            # Create Discord embed
            embed = {
                'title': event.title,
                'description': event.message,
                'color': level_colors.get(event.level, 0x17a2b8),
                'timestamp': event.timestamp.isoformat(),
                'fields': [
                    {'name': 'Level', 'value': event.level.value.upper(), 'inline': True},
                    {'name': 'Type', 'value': event.event_type.value, 'inline': True},
                    {'name': 'Source', 'value': event.source, 'inline': True},
                    {'name': 'Event ID', 'value': event.event_id, 'inline': False},
                    {'name': 'Tags', 'value': ', '.join(event.tags) or 'None', 'inline': False}
                ],
                'footer': {'text': 'LNMT Integration'}
            }
            
            payload = {
                'username': self.username,
                'embeds': [embed]
            }
            
            if self.avatar_url:
                payload['avatar_url'] = self.avatar_url
            
            # Send to Discord
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:  # Discord returns 204 for success
                        self.logger.debug(f"Sent Discord message: {event.event_id}")
                        return True
                    else:
                        self.logger.error(f"Discord request failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            return False


class IntegrationConnectorService:
    """Main service for managing integration connectors"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("lnmt.integration_connectors")
        self.connectors: Dict[str, BaseConnector] = {}
        self.hooks: Dict[EventType, List[Callable]] = {}
        self.config = {}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            self._initialize_connectors()
            self.logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def _initialize_connectors(self):
        """Initialize connectors from config"""
        connectors_config = self.config.get('connectors', {})
        
        for name, config in connectors_config.items():
            try:
                connector_type = config['type']
                
                if connector_type == 'syslog':
                    connector = SyslogConnector(name, config)
                elif connector_type == 'http':
                    connector = HttpConnector(name, config)
                elif connector_type == 'email':
                    connector = EmailConnector(name, config)
                elif connector_type == 'slack':
                    connector = SlackConnector(name, config)
                elif connector_type == 'discord':
                    connector = DiscordConnector(name, config)
                else:
                    self.logger.error(f"Unknown connector type: {connector_type}")
                    continue
                
                self.connectors[name] = connector
                self.logger.info(f"Initialized {connector_type} connector: {name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize connector {name}: {e}")
    
    async def send_event(self, event: IntegrationEvent, connector_names: Optional[List[str]] = None):
        """Send event to specified connectors or all enabled connectors"""
        if connector_names:
            connectors = [self.connectors[name] for name in connector_names 
                         if name in self.connectors]
        else:
            connectors = list(self.connectors.values())
        
        # Send to all connectors concurrently
        tasks = []
        for connector in connectors:
            if connector.should_send(event):
                tasks.append(connector.send_event(event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            self.logger.debug(f"Sent event {event.event_id} to {success_count}/{len(tasks)} connectors")
    
    def register_hook(self, event_type: EventType, callback: Callable):
        """Register a callback for specific event types"""
        if event_type not in self.hooks:
            self.hooks[event_type] = []
        self.hooks[event_type].append(callback)
    
    async def trigger_hooks(self, event: IntegrationEvent):
        """Trigger registered hooks for event type"""
        hooks = self.hooks.get(event.event_type, []) + self.hooks.get(EventType.CUSTOM, [])
        
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(event)
                else:
                    hook(event)
            except Exception as e:
                self.logger.error(f"Hook failed: {e}")
    
    def create_event(
        self,
        event_type: EventType,
        level: AlertLevel,
        source: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> IntegrationEvent:
        """Create a new integration event"""
        import uuid
        
        return IntegrationEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            source=source,
            title=title,
            message=message,
            metadata=metadata or {},
            tags=tags or []
        )
    
    async def alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "lnmt",
        event_type: EventType = EventType.CUSTOM,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        connectors: Optional[List[str]] = None
    ):
        """Send an alert to connectors"""
        event = self.create_event(
            event_type=event_type,
            level=level,
            source=source,
            title=title,
            message=message,
            metadata=metadata,
            tags=tags
        )
        
        await self.trigger_hooks(event)
        await self.send_event(event, connectors)
    
    def get_connector_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connectors"""
        status = {}
        for name, connector in self.connectors.items():
            status[name] = {
                'type': connector.__class__.__name__,
                'enabled': connector.enabled,
                'filters': connector._filters,
                'rate_limit': connector._rate_limit
            }
        return status


# Global service instance
integration_service = IntegrationConnectorService()


# Convenience functions for other modules
async def send_critical_alert(title: str, message: str, source: str = "lnmt", **kwargs):
    """Send critical alert"""
    await integration_service.alert(
        AlertLevel.CRITICAL, title, message, source, 
        EventType.CRITICAL_ERROR, **kwargs
    )


async def send_health_alert(title: str, message: str, source: str = "lnmt", **kwargs):
    """Send system health alert"""
    await integration_service.alert(
        AlertLevel.WARNING, title, message, source,
        EventType.SYSTEM_HEALTH, **kwargs
    )


async def send_threshold_alert(title: str, message: str, source: str = "lnmt", **kwargs):
    """Send threshold breach alert"""
    await integration_service.alert(
        AlertLevel.ERROR, title, message, source,
        EventType.THRESHOLD_BREACH, **kwargs
    )


if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize service
        service = IntegrationConnectorService()
        
        # Create test event
        event = service.create_event(
            event_type=EventType.SYSTEM_HEALTH,
            level=AlertLevel.WARNING,
            source="test_system",
            title="High CPU Usage",
            message="CPU usage has exceeded 80% for 5 minutes",
            metadata={"cpu_percent": 85.2, "duration": 300},
            tags=["performance", "cpu"]
        )
        
        print("Test event created:")
        print(event.to_json())
    
    asyncio.run(main())