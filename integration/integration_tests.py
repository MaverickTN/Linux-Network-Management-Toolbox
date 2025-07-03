#!/usr/bin/env python3
"""
LNMT Integration Connectors Test Suite
Comprehensive tests for the integration connectors service.
"""

import asyncio
import json
import pytest
import tempfile
import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.integration_connectors import (
    IntegrationConnectorService,
    AlertLevel,
    EventType,
    IntegrationEvent,
    SyslogConnector,
    HttpConnector,
    EmailConnector,
    SlackConnector,
    DiscordConnector
)


class TestIntegrationEvent:
    """Test IntegrationEvent class"""
    
    def test_event_creation(self):
        """Test creating an event"""
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.SYSTEM_HEALTH,
            level=AlertLevel.WARNING,
            source="test_source",
            title="Test Event",
            message="This is a test event",
            metadata={"key": "value"},
            tags=["test", "unit"]
        )
        
        assert event.event_id == "test-123"
        assert event.event_type == EventType.SYSTEM_HEALTH
        assert event.level == AlertLevel.WARNING
        assert event.source == "test_source"
        assert "test" in event.tags
    
    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        timestamp = datetime.now()
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=timestamp,
            event_type=EventType.CRITICAL_ERROR,
            level=AlertLevel.CRITICAL,
            source="test_source",
            title="Test Event",
            message="Test message",
            metadata={"key": "value"},
            tags=["test"]
        )
        
        event_dict = event.to_dict()
        
        assert event_dict['event_id'] == "test-123"
        assert event_dict['timestamp'] == timestamp.isoformat()
        assert event_dict['event_type'] == "critical_error"
        assert event_dict['level'] == "critical"
        assert event_dict['metadata']['key'] == "value"
    
    def test_event_to_json(self):
        """Test converting event to JSON"""
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.CUSTOM,
            level=AlertLevel.INFO,
            source="test_source",
            title="Test Event",
            message="Test message",
            metadata={},
            tags=[]
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed['event_id'] == "test-123"
        assert parsed['event_type'] == "custom"


class TestBaseConnector:
    """Test BaseConnector functionality"""
    
    def create_test_connector(self, config=None):
        """Create a test connector"""
        if config is None:
            config = {'enabled': True}
        
        class TestConnector(SyslogConnector):
            async def send_event(self, event):
                return True
        
        return TestConnector("test_connector", config)
    
    def create_test_event(self, level=AlertLevel.INFO, event_type=EventType.CUSTOM, tags=None):
        """Create a test event"""
        return IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            source="test_source",
            title="Test Event",
            message="Test message",
            metadata={},
            tags=tags or []
        )
    
    def test_should_send_enabled(self):
        """Test should_send with enabled connector"""
        connector = self.create_test_connector({'enabled': True})
        event = self.create_test_event()
        
        assert connector.should_send(event) is True
    
    def test_should_send_disabled(self):
        """Test should_send with disabled connector"""
        connector = self.create_test_connector({'enabled': False})
        event = self.create_test_event()
        
        assert connector.should_send(event) is False
    
    def test_level_filtering(self):
        """Test level-based filtering"""
        config = {
            'enabled': True,
            'filters': {'min_level': 'warning'}
        }
        connector = self.create_test_connector(config)
        
        # Should be filtered out
        info_event = self.create_test_event(AlertLevel.INFO)
        assert connector.should_send(info_event) is False
        
        # Should pass
        warning_event = self.create_test_event(AlertLevel.WARNING)
        assert connector.should_send(warning_event) is True
        
        # Should pass
        error_event = self.create_test_event(AlertLevel.ERROR)
        assert connector.should_send(error_event) is True
    
    def test_event_type_filtering(self):
        """Test event type filtering"""
        config = {
            'enabled': True,
            'filters': {'event_types': ['system_health', 'critical_error']}
        }
        connector = self.create_test_connector(config)
        
        # Should pass
        health_event = self.create_test_event(event_type=EventType.SYSTEM_HEALTH)
        assert connector.should_send(health_event) is True
        
        # Should be filtered out
        custom_event = self.create_test_event(event_type=EventType.CUSTOM)
        assert connector.should_send(custom_event) is False
    
    def test_tag_filtering(self):
        """Test tag-based filtering"""
        config = {
            'enabled': True,
            'filters': {'required_tags': ['production', 'critical']}
        }
        connector = self.create_test_connector(config)
        
        # Should be filtered out (missing tags)
        event_no_tags = self.create_test_event(tags=[])
        assert connector.should_send(event_no_tags) is False
        
        # Should be filtered out (partial tags)
        event_partial_tags = self.create_test_event(tags=['production'])
        assert connector.should_send(event_partial_tags) is False
        
        # Should pass (all required tags)
        event_all_tags = self.create_test_event(tags=['production', 'critical', 'extra'])
        assert connector.should_send(event_all_tags) is True


class TestSyslogConnector:
    """Test SyslogConnector"""
    
    @pytest.mark.asyncio
    async def test_syslog_udp_send(self):
        """Test UDP syslog sending"""
        config = {
            'enabled': True,
            'host': 'localhost',
            'port': 514,
            'protocol': 'udp'
        }
        
        connector = SyslogConnector("test_syslog", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.SYSTEM_HEALTH,
            level=AlertLevel.WARNING,
            source="test_source",
            title="Test Syslog",
            message="Test syslog message",
            metadata={},
            tags=[]
        )
        
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            
            result = await connector.send_event(event)
            
            assert result is True
            mock_sock.sendto.assert_called_once()
            mock_sock.close.assert_called_once()


class TestHttpConnector:
    """Test HttpConnector"""
    
    @pytest.mark.asyncio
    async def test_http_send_success(self):
        """Test successful HTTP send"""
        config = {
            'enabled': True,
            'url': 'https://httpbin.org/post',
            'method': 'POST',
            'timeout': 30
        }
        
        connector = HttpConnector("test_http", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.CUSTOM,
            level=AlertLevel.INFO,
            source="test_source",
            title="Test HTTP",
            message="Test HTTP message",
            metadata={"test": True},
            tags=["http", "test"]
        )
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
            
            result = await connector.send_event(event)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_http_send_failure(self):
        """Test HTTP send failure"""
        config = {
            'enabled': True,
            'url': 'https://invalid-url.com',
            'timeout': 5
        }
        
        connector = HttpConnector("test_http", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.CUSTOM,
            level=AlertLevel.INFO,
            source="test_source",
            title="Test HTTP",
            message="Test HTTP message",
            metadata={},
            tags=[]
        )
        
        with patch('aiohttp.ClientSession.request', side_effect=Exception("Connection failed")):
            result = await connector.send_event(event)
            assert result is False


class TestEmailConnector:
    """Test EmailConnector"""
    
    def test_text_body_creation(self):
        """Test creating text email body"""
        config = {
            'enabled': True,
            'smtp_host': 'smtp.example.com',
            'from_email': 'test@example.com',
            'to_emails': ['admin@example.com']
        }
        
        connector = EmailConnector("test_email", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.CRITICAL_ERROR,
            level=AlertLevel.CRITICAL,
            source="test_source",
            title="Critical Test",
            message="This is a critical test",
            metadata={"severity": "high"},
            tags=["critical"]
        )
        
        text_body = connector._create_text_body(event)
        
        assert "LNMT Alert" in text_body
        assert "test-123" in text_body
        assert "Critical Test" in text_body
        assert "critical" in text_body.lower()
    
    def test_html_body_creation(self):
        """Test creating HTML email body"""
        config = {
            'enabled': True,
            'smtp_host': 'smtp.example.com',
            'from_email': 'test@example.com',
            'to_emails': ['admin@example.com']
        }
        
        connector = EmailConnector("test_email", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.SYSTEM_HEALTH,
            level=AlertLevel.WARNING,
            source="test_source",
            title="Warning Test",
            message="This is a warning test",
            metadata={"value": 85},
            tags=["warning"]
        )
        
        html_body = connector._create_html_body(event)
        
        assert "<html>" in html_body
        assert "LNMT Alert" in html_body
        assert "Warning Test" in html_body
        assert "#ffc107" in html_body  # Warning color


class TestSlackConnector:
    """Test SlackConnector"""
    
    @pytest.mark.asyncio
    async def test_slack_send_success(self):
        """Test successful Slack send"""
        config = {
            'enabled': True,
            'webhook_url': 'https://hooks.slack.com/test',
            'channel': '#alerts',
            'username': 'LNMT'
        }
        
        connector = SlackConnector("test_slack", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.THRESHOLD_BREACH,
            level=AlertLevel.ERROR,
            source="test_source",
            title="Threshold Exceeded",
            message="Response time threshold exceeded",
            metadata={"response_time": 2.5},
            tags=["performance"]
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await connector.send_event(event)
            
            assert result is True
            mock_post.assert_called_once()


class TestDiscordConnector:
    """Test DiscordConnector"""
    
    @pytest.mark.asyncio
    async def test_discord_send_success(self):
        """Test successful Discord send"""
        config = {
            'enabled': True,
            'webhook_url': 'https://discord.com/api/webhooks/test',
            'username': 'LNMT'
        }
        
        connector = DiscordConnector("test_discord", config)
        event = IntegrationEvent(
            event_id="test-123",
            timestamp=datetime.now(),
            event_type=EventType.SECURITY_EVENT,
            level=AlertLevel.CRITICAL,
            source="security_monitor",
            title="Security Alert",
            message="Suspicious activity detected",
            metadata={"ip": "192.168.1.100"},
            tags=["security", "intrusion"]
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 204  # Discord success status
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await connector.send_event(event)
            
            assert result is True


class TestIntegrationConnectorService:
    """Test IntegrationConnectorService"""
    
    def create_test_config(self):
        """Create test configuration"""
        return {
            'connectors': {
                'test_http': {
                    'type': 'http',
                    'enabled': True,
                    'url': 'https://httpbin.org/post',
                    'filters': {'min_level': 'info'}
                },
                'test_syslog': {
                    'type': 'syslog',
                    'enabled': True,
                    'host': 'localhost',
                    'port': 514,
                    'filters': {'min_level': 'warning'}
                },
                'disabled_email': {
                    'type': 'email',
                    'enabled': False,
                    'smtp_host': 'smtp.example.com',
                    'from_email': 'test@example.com',
                    'to_emails': ['admin@example.com']
                }
            }
        }
    
    def test_service_initialization(self):
        """Test service initialization"""
        service = IntegrationConnectorService()
        assert len(service.connectors) == 0
        assert len(service.hooks) == 0
    
    def test_load_config(self):
        """Test loading configuration"""
        config = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            service = IntegrationConnectorService()
            service.load_config(config_path)
            
            assert len(service.connectors) == 3
            assert 'test_http' in service.connectors
            assert 'test_syslog' in service.connectors
            assert 'disabled_email' in service.connectors
            
            # Check enabled/disabled status
            assert service.connectors['test_http'].enabled is True
            assert service.connectors['disabled_email'].enabled is False
            
        finally:
            Path(config_path).unlink()
    
    def test_create_event(self):
        """Test event creation"""
        service = IntegrationConnectorService()
        
        event = service.create_event(
            event_type=EventType.PERFORMANCE_ALERT,
            level=AlertLevel.WARNING,
            source="test_service",
            title="Performance Issue",
            message="High latency detected",
            metadata={"latency": 1.5},
            tags=["performance"]
        )
        
        assert event.event_type == EventType.PERFORMANCE_ALERT
        assert event.level == AlertLevel.WARNING
        assert event.source == "test_service"
        assert event.title == "Performance Issue"
        assert "performance" in event.tags
        assert event.metadata["latency"] == 1.5
    
    def test_register_hooks(self):
        """Test hook registration"""
        service = IntegrationConnectorService()
        
        def test_hook(event):
            pass
        
        service.register_hook(EventType.CRITICAL_ERROR, test_hook)
        
        assert EventType.CRITICAL_ERROR in service.hooks
        assert test_hook in service.hooks[EventType.CRITICAL_ERROR]
    
    @pytest.mark.asyncio
    async def test_trigger_hooks(self):
        """Test hook triggering"""
        service = IntegrationConnectorService()
        
        hook_called = {'sync': False, 'async': False}
        
        def sync_hook(event):
            hook_called['sync'] = True
        
        async def async_hook(event):
            hook_called['async'] = True
        
        service.register_hook(EventType.SYSTEM_HEALTH, sync_hook)
        service.register_hook(EventType.SYSTEM_HEALTH, async_hook)
        
        event = service.create_event(
            event_type=EventType.SYSTEM_HEALTH,
            level=AlertLevel.INFO,
            source="test",
            title="Test",
            message="Test message"
        )
        
        await service.trigger_hooks(event)
        
        assert hook_called['sync'] is True
        assert hook_called['async'] is True
    
    def test_get_connector_status(self):
        """Test getting connector status"""
        config = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            service = IntegrationConnectorService(config_path)
            status = service.get_connector_status()
            
            assert len(status) == 3
            assert status['test_http']['enabled'] is True
            assert status['disabled_email']['enabled'] is False
            assert status['test_http']['type'] == 'HttpConnector'
            
        finally:
            Path(config_path).unlink()
    
    @pytest.mark.asyncio
    async def test_send_event_to_specific_connectors(self):
        """Test sending event to specific connectors"""
        config = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            service = IntegrationConnectorService(config_path)
            
            event = service.create_event(
                event_type=EventType.CUSTOM,
                level=AlertLevel.INFO,
                source="test",
                title="Test Event",
                message="Test message"
            )
            
            # Mock the send_event method for connectors
            with patch.object(service.connectors['test_http'], 'send_event', return_value=True) as mock_http:
                with patch.object(service.connectors['test_syslog'], 'send_event', return_value=True) as mock_syslog:
                    
                    # Send to specific connector
                    await service.send_event(event, ['test_http'])
                    
                    mock_http.assert_called_once()
                    mock_syslog.assert_not_called()
                    
        finally:
            Path(config_path).unlink()


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_send_critical_alert(self):
        """Test send_critical_alert function"""
        from services.integration_connectors import send_critical_alert, integration_service
        
        with patch.object(integration_service, 'alert') as mock_alert:
            await send_critical_alert("Test Critical", "Critical message", "test_source")
            
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            assert call_args[1]['level'] == AlertLevel.CRITICAL
            assert call_args[1]['title'] == "Test Critical"
            assert call_args[1]['event_type'] == EventType.CRITICAL_ERROR
    
    @pytest.mark.asyncio
    async def test_send_health_alert(self):
        """Test send_health_alert function"""
        from services.integration_connectors import send_health_alert, integration_service
        
        with patch.object(integration_service, 'alert') as mock_alert:
            await send_health_alert("Health Issue", "Health message", "health_monitor")
            
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            assert call_args[1]['level'] == AlertLevel.WARNING
            assert call_args[1]['event_type'] == EventType.SYSTEM_HEALTH
    
    @pytest.mark.asyncio
    async def test_send_threshold_alert(self):
        """Test send_threshold_alert function"""
        from services.integration_connectors import send_threshold_alert, integration_service
        
        with patch.object(integration_service, 'alert') as mock_alert:
            await send_threshold_alert("Threshold Breach", "Threshold message", "monitor")
            
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            assert call_args[1]['level'] == AlertLevel.ERROR
            assert call_args[1]['event_type'] == EventType.THRESHOLD_BREACH


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
