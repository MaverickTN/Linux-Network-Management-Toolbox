#!/usr/bin/env python3
"""
Advanced LNMT Integration Test Suite
Tests cross-module functionality, data flow, and system-wide scenarios
"""

import pytest
import asyncio
import tempfile
import json
import sqlite3
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests
import subprocess
import os
import signal

class TestDNSVLANIntegration:
    """Integration tests between DNS Manager and VLAN Controller"""
    
    @pytest.fixture
    def dns_vlan_system(self):
        """Setup integrated DNS and VLAN system"""
        system = Mock()
        system.dns_manager = Mock()
        system.vlan_controller = Mock()
        system.device_tracker = Mock()
        
        # Mock DNS records storage
        system.dns_records = {}
        system.vlan_assignments = {}
        system.device_registry = {}
        
        return system

    def test_vlan_dns_record_creation(self, dns_vlan_system):
        """Test automatic DNS record creation when devices join VLANs"""
        # Device joins VLAN
        device_id = "aa:bb:cc:dd:ee:ff"
        vlan_id = 100
        device_ip = "192.168.100.50"
        
        # Simulate device joining VLAN
        dns_vlan_system.vlan_controller.assign_device_to_vlan(device_id, vlan_id)
        dns_vlan_system.device_tracker.update_device_ip(device_id, device_ip)
        
        # Should trigger DNS record creation
        expected_hostname = f"device-{device_id.replace(':', '-')}.vlan{vlan_id}.local"
        dns_vlan_system.dns_manager.add_record.assert_called_with(expected_hostname, device_ip)

    def test_vlan_isolation_dns_resolution(self, dns_vlan_system):
        """Test DNS resolution respects VLAN isolation"""
        # Setup devices in different VLANs
        vlan_100_device = {"mac": "aa:bb:cc:dd:ee:01", "ip": "192.168.100.10", "vlan": 100}
        vlan_200_device = {"mac": "aa:bb:cc:dd:ee:02", "ip": "192.168.200.10", "vlan": 200}
        
        # Device in VLAN 100 tries to resolve device in VLAN 200
        dns_vlan_system.vlan_controller.get_device_vlan.return_value = 100
        
        result = dns_vlan_system.dns_manager.resolve_hostname(
            "device-aa-bb-cc-dd-ee-02.vlan200.local",
            requesting_device="aa:bb:cc:dd:ee:01"
        )
        
        # Should be blocked due to VLAN isolation
        assert result is None or result == "BLOCKED", "DNS resolution should respect VLAN isolation"

    def test_cross_vlan_dns_with_routing_rules(self, dns_vlan_system):
        """Test DNS resolution with explicit cross-VLAN routing rules"""
        # Setup routing rule allowing VLAN 100 -> VLAN 200
        dns_vlan_system.vlan_controller.add_routing_rule(100, 200, "allow")
        
        # Device in VLAN 100 resolves device in VLAN 200
        dns_vlan_system.vlan_controller.get_device_vlan.return_value = 100
        dns_vlan_system.vlan_controller.check_routing_allowed.return_value = True
        
        result = dns_vlan_system.dns_manager.resolve_hostname(
            "device-aa-bb-cc-dd-ee-02.vlan200.local",
            requesting_device="aa:bb:cc:dd:ee:01"
        )
        
        # Should succeed with routing rule
        assert result == "192.168.200.10", "DNS resolution should work with routing rules"

    def test_dns_record_cleanup_on_vlan_change(self, dns_vlan_system):
        """Test DNS record cleanup when device changes VLANs"""
        device_id = "aa:bb:cc:dd:ee:ff"
        old_vlan = 100
        new_vlan = 200
        
        # Device moves from VLAN 100 to VLAN 200
        old_hostname = f"device-{device_id.replace(':', '-')}.vlan{old_vlan}.local"
        new_hostname = f"device-{device_id.replace(':', '-')}.vlan{new_vlan}.local"
        
        dns_vlan_system.vlan_controller.move_device_to_vlan(device_id, old_vlan, new_vlan)
        
        # Should remove old DNS record and create new one
        dns_vlan_system.dns_manager.remove_record.assert_called_with(old_hostname)
        dns_vlan_system.dns_manager.add_record.assert_called_with(new_hostname, "192.168.200.50")

class TestAuthenticationServiceIntegration:
    """Integration tests for authentication across all services"""
    
    @pytest.fixture
    def auth_integrated_system(self):
        """Setup system with authentication integration"""
        system = Mock()
        system.auth_engine = Mock()
        system.web_app = Mock()
        system.dns_manager = Mock()
        system.vlan_controller = Mock()
        system.backup_service = Mock()
        system.scheduler = Mock()
        
        # Mock session storage
        system.active_sessions = {}
        system.permissions = {}
        
        return system

    def test_unified_authentication_flow(self, auth_integrated_system):
        """Test authentication flow across web UI and CLI"""
        username = "admin_user"
        password = "secure_password"
        
        # Web login
        web_session = auth_integrated_system.auth_engine.authenticate_web(username, password)
        assert web_session.success, "Web authentication should succeed"
        
        # CLI should accept same session token
        cli_auth = auth_integrated_system.auth_engine.validate_cli_token(web_session.token)
        assert cli_auth.success, "CLI should accept web session token"
        
        # API endpoints should accept same token
        api_auth = auth_integrated_system.auth_engine.validate_api_token(web_session.token)
        assert api_auth.success, "API should accept web session token"

    def test_permission_propagation(self, auth_integrated_system):
        """Test permission changes propagate across all services"""
        user_id = "test_user"
        
        # Grant DNS management permission
        auth_integrated_system.auth_engine.grant_permission(user_id, "dns_management")
        
        # Should be able to access DNS management endpoints
        dns_access = auth_integrated_system.dns_manager.check_user_access(user_id)
        assert dns_access, "DNS access should be granted"
        
        # Should NOT be able to access VLAN management
        vlan_access = auth_integrated_system.vlan_controller.check_user_access(user_id)
        assert not vlan_access, "VLAN access should be denied"
        
        # Revoke permission
        auth_integrated_system.auth_engine.revoke_permission(user_id, "dns_management")
        
        # Access should be immediately revoked
        dns_access_after = auth_integrated_system.dns_manager.check_user_access(user_id)
        assert not dns_access_after, "DNS access should be revoked"

    def test_session_timeout_enforcement(self, auth_integrated_system):
        """Test session timeout is enforced across all services"""
        # Create session with short timeout
        session = auth_integrated_system.auth_engine.create_session("user", timeout=1)  # 1 second
        
        # Should work initially
        assert auth_integrated_system.web_app.validate_session(session.token)
        assert auth_integrated_system.dns_manager.validate_session(session.token)
        
        # Wait for timeout
        time.sleep(2)
        
        # Should be expired in all services
        assert not auth_integrated_system.web_app.validate_session(session.token)
        assert not auth_integrated_system.dns_manager.validate_session(session.token)
        assert not auth_integrated_system.vlan_controller.validate_session(session.token)

    def test_concurrent_session_limits(self, auth_integrated_system):
        """Test concurrent session limits are enforced"""
        username = "limited_user"
        max_sessions = 3
        
        auth_integrated_system.auth_engine.set_max_concurrent_sessions(username, max_sessions)
        
        # Create maximum allowed sessions
        sessions = []
        for i in range(max_sessions):
            session = auth_integrated_system.auth_engine.authenticate(username, "password")
            sessions.append(session.token)
            assert session.success, f"Session {i+1} should succeed"
        
        # Additional session should fail or invalidate oldest
        new_session = auth_integrated_system.auth_engine.authenticate(username, "password")
        
        if new_session.success:
            # If new session succeeds, oldest should be invalidated
            oldest_valid = auth_integrated_system.auth_engine.validate_token(sessions[0])
            assert not oldest_valid, "Oldest session should be invalidated"
        else:
            assert new_session.error_code == "MAX_SESSIONS_EXCEEDED"

class TestBackupIntegrationWorkflows:
    """Integration tests for backup service with other modules"""
    
    @pytest.fixture
    def backup_integrated_system(self):
        """Setup backup integration test environment"""
        system = Mock()
        system.backup_service = Mock()
        system.dns_manager = Mock()
        system.vlan_controller = Mock()
        system.device_tracker = Mock()
        system.auth_engine = Mock()
        system.scheduler = Mock()
        
        return system

    def test_comprehensive_system_backup(self, backup_integrated_system):
        """Test complete system backup including all module data"""
        backup_id = "full_system_backup_001"
        
        # Trigger comprehensive backup
        backup_result = backup_integrated_system.backup_service.create_full_backup(backup_id)
        
        # Should include data from all modules
        expected_components = [
            "dns_records",
            "vlan_configurations", 
            "device_registry",
            "user_accounts",
            "system_configuration",
            "scheduled_jobs"
        ]
        
        for component in expected_components:
            assert component in backup_result.components, f"Backup should include {component}"

    def test_selective_module_backup(self, backup_integrated_system):
        """Test selective backup of specific modules"""
        # Backup only DNS and VLAN data
        modules = ["dns_manager", "vlan_controller"]
        backup_result = backup_integrated_system.backup_service.create_selective_backup(modules)
        
        # Should only include specified modules
        assert "dns_records" in backup_result.components
        assert "vlan_configurations" in backup_result.components
        assert "device_registry" not in backup_result.components

    def test_backup_consistency_across_modules(self, backup_integrated_system):
        """Test backup consistency when data spans multiple modules"""
        # Setup related data across modules
        device_mac = "aa:bb:cc:dd:ee:ff"
        device_ip = "192.168.100.50"
        vlan_id = 100
        hostname = "test-device.local"
        
        # Device exists in multiple systems
        backup_integrated_system.device_tracker.register_device(device_mac, {"ip": device_ip})
        backup_integrated_system.vlan_controller.assign_device(device_mac, vlan_id)
        backup_integrated_system.dns_manager.add_record(hostname, device_ip)
        
        # Create backup
        backup_result = backup_integrated_system.backup_service.create_full_backup("consistency_test")
        
        # Verify cross-references are maintained
        assert backup_result.verify_cross_references(), "Backup should maintain data consistency"

    def test_restore_with_conflict_resolution(self, backup_integrated_system):
        """Test restore process with conflicting data"""
        # Current system state
        current_dns_records = {"host1.local": "192.168.1.100"}
        backup_dns_records = {"host1.local": "192.168.1.200", "host2.local": "192.168.1.150"}
        
        # Restore with conflicts
        restore_options = {
            "conflict_resolution": "merge",
            "prefer_backup": True
        }
        
        restore_result = backup_integrated_system.backup_service.restore_backup(
            "test_backup", **restore_options
        )
        
        # Should handle conflicts according to policy
        assert restore_result.success, "Restore should succeed with conflict resolution"
        assert restore_result.conflicts_resolved > 0, "Should report resolved conflicts"

    def test_incremental_backup_integration(self, backup_integrated_system):
        """Test incremental backups across integrated modules"""
        # Create initial full backup
        full_backup = backup_integrated_system.backup_service.create_full_backup("initial")
        
        # Make changes across modules
        backup_integrated_system.dns_manager.add_record("new-host.local", "192.168.1.201")
        backup_integrated_system.vlan_controller.create_vlan(300)
        backup_integrated_system.device_tracker.register_device("new:mac:address", {})
        
        # Create incremental backup
        incremental_backup = backup_integrated_system.backup_service.create_incremental_backup(
            "incremental_001", base_backup="initial"
        )
        
        # Should only include changed data
        assert incremental_backup.size < full_backup.size, "Incremental should be smaller"
        assert "new-host.local" in incremental_backup.dns_changes
        assert 300 in incremental_backup.vlan_changes

class TestSchedulerServiceIntegration:
    """Integration tests for scheduler with all LNMT services"""
    
    @pytest.fixture
    def scheduler_integrated_system(self):
        """Setup scheduler integration environment"""
        system = Mock()
        system.scheduler = Mock()
        system.backup_service = Mock()
        system.health_monitor = Mock()
        system.dns_manager = Mock()
        system.vlan_controller = Mock()
        system.device_tracker = Mock()
        system.report_engine = Mock()
        
        # Mock job queue and execution engine
        system.job_queue = []
        system.running_jobs = {}
        
        return system

    def test_scheduled_backup_workflow(self, scheduler_integrated_system):
        """Test scheduled backup jobs with proper service coordination"""
        # Schedule daily backup job
        job_config = {
            "id": "daily_backup",
            "schedule": "0 2 * * *",  # 2 AM daily
            "task": "backup_service.create_full_backup",
            "parameters": {"retention_days": 30}
        }
        
        scheduler_integrated_system.scheduler.add_job(**job_config)
        
        # Simulate job execution
        scheduler_integrated_system.scheduler.execute_job("daily_backup")
        
        # Should coordinate with backup service
        scheduler_integrated_system.backup_service.create_full_backup.assert_called_once()
        
        # Should handle job completion
        assert scheduler_integrated_system.scheduler.get_job_status("daily_backup") == "completed"

    def test_health_monitoring_scheduled_tasks(self, scheduler_integrated_system):
        """Test scheduled health monitoring across all services"""
        # Schedule health checks for all services
        health_jobs = [
            {"id": "health_dns", "schedule": "*/5 * * * *", "service": "dns_manager"},
            {"id": "health_vlan", "schedule": "*/5 * * * *", "service": "vlan_controller"},
            {"id": "health_devices", "schedule": "*/5 * * * *", "service": "device_tracker"}
        ]
        
        for job in health_jobs:
            scheduler_integrated_system.scheduler.add_health_check(**job)
        
        # Execute health checks
        scheduler_integrated_system.scheduler.run_health_checks()
        
        # Should check all services
        scheduler_integrated_system.health_monitor.check_service.assert_called()
        call_count = scheduler_integrated_system.health_monitor.check_service.call_count
        assert call_count >= len(health_jobs), "Should check all scheduled services"

    def test_cascading_job_dependencies(self, scheduler_integrated_system):
        """Test job dependencies and cascading execution"""
        # Setup dependent jobs
        jobs = [
            {"id": "device_scan", "task": "device_tracker.scan_network"},
            {"id": "vlan_update", "task": "vlan_controller.update_assignments", "depends_on": ["device_scan"]},
            {"id": "dns_sync", "task": "dns_manager.sync_records", "depends_on": ["vlan_update"]},
            {"id": "backup_after_sync", "task": "backup_service.create_backup", "depends_on": ["dns_sync"]}
        ]
        
        for job in jobs:
            scheduler_integrated_system.scheduler.add_job(**job)
        
        # Execute job chain
        scheduler_integrated_system.scheduler.execute_job_chain("device_scan")
        
        # Should execute in dependency order
        execution_order = scheduler_integrated_system.scheduler.get_execution_order()
        expected_order = ["device_scan", "vlan_update", "dns_sync", "backup_after_sync"]
        assert execution_order == expected_order, "Jobs should execute in dependency order"

    def test_job_failure_recovery(self, scheduler_integrated_system):
        """Test job failure handling and recovery mechanisms"""
        # Setup job that will fail
        scheduler_integrated_system.backup_service.create_full_backup.side_effect = Exception("Disk full")
        
        job_config = {
            "id": "failing_backup",
            "task": "backup_service.create_full_backup",
            "retry_count": 3,
            "retry_delay": 1
        }
        
        scheduler_integrated_system.scheduler.add_job(**job_config)
        
        # Execute job
        result = scheduler_integrated_system.scheduler.execute_job("failing_backup")
        
        # Should retry according to configuration
        assert result.status == "failed_after_retries"
        assert result.attempt_count == 3, "Should retry 3 times"
        
        # Should notify health monitor of failure
        scheduler_integrated_system.health_monitor.report_job_failure.assert_called_with("failing_backup")

    def test_resource_contention_management(self, scheduler_integrated_system):
        """Test resource contention management between scheduled jobs"""
        # Schedule resource-intensive jobs
        intensive_jobs = [
            {"id": "full_backup", "resource_requirements": {"disk_io": "high", "cpu": "medium"}},
            {"id": "network_scan", "resource_requirements": {"network": "high", "cpu": "high"}},
            {"id": "report_generation", "resource_requirements": {"cpu": "high", "memory": "high"}}
        ]
        
        for job in intensive_jobs:
            scheduler_integrated_system.scheduler.add_job(**job)
        
        # Try to execute all simultaneously
        scheduler_integrated_system.scheduler.execute_concurrent_jobs(
            ["full_backup", "network_scan", "report_generation"]
        )
        
        # Should manage resource conflicts
        running_jobs = scheduler_integrated_system.scheduler.get_running_jobs()
        
        # Should not run conflicting jobs simultaneously
        cpu_intensive_running = sum(1 for job in running_jobs.values() 
                                   if job.get("resource_requirements", {}).get("cpu") == "high")
        assert cpu_intensive_running <= 1, "Should limit CPU-intensive jobs"

class TestWebAPIIntegration:
    """Integration tests for web application with backend services"""
    
    @pytest.fixture
    def web_integrated_system(self):
        """Setup web application integration environment"""
        system = Mock()
        system.web_app = Mock()
        system.auth_engine = Mock()
        system.dns_manager = Mock()
        system.vlan_controller = Mock()
        system.device_tracker = Mock()
        system.backup_service = Mock()
        system.report_engine = Mock()
        
        return system

    def test_api_authentication_flow(self, web_integrated_system):
        """Test API authentication integration with auth engine"""
        # Mock HTTP request
        with patch('flask.request') as mock_request:
            mock_request.headers = {"Authorization": "Bearer valid_token"}
            mock_request.json = {"action": "list_devices"}
            
            # Auth engine validates token
            web_integrated_system.auth_engine.validate_api_token.return_value = {
                "valid": True, "user_id": "api_user", "permissions": ["device_read"]
            }
            
            # API endpoint processes request
            response = web_integrated_system.web_app.api_endpoint("/api/devices", mock_request)
            
            # Should validate token and process request
            web_integrated_system.auth_engine.validate_api_token.assert_called_with("valid_token")
            assert response.status_code == 200

    def test_real_time_updates_integration(self, web_integrated_system):
        """Test real-time updates from services to web UI"""
        # Setup WebSocket connection mock
        websocket_clients = []
        
        def mock_emit(event, data):
            websocket_clients.append({"event": event, "data": data})
        
        web_integrated_system.web_app.socketio.emit = mock_emit
        
        # Trigger events in backend services
        web_integrated_system.device_tracker.device_connected("aa:bb:cc:dd:ee:ff")
        web_integrated_system.vlan_controller.vlan_created(500)
        web_integrated_system.dns_manager.record_added("new-host.local", "192.168.1.100")
        
        # Should emit WebSocket events to UI
        events = [client["event"] for client in websocket_clients]
        assert "device_connected" in events
        assert "vlan_created" in events
        assert "dns_record_added" in events

    def test_api_rate_limiting_integration(self, web_integrated_system):
        """Test API rate limiting with authentication system"""
        user_id = "rate_limited_user"
        
        # Setup rate limiting
        web_integrated_system.auth_engine.get_rate_limit.return_value = {"requests_per_minute": 10}
        
        # Make requests up to limit
        for i in range(10):
            response = web_integrated_system.web_app.api_request(
                "/api/devices", user_id=user_id
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"
        
        # Next request should be rate limited
        response = web_integrated_system.web_app.api_request("/api/devices", user_id=user_id)
        assert response.status_code == 429, "Should be rate limited"

    def test_file_upload_integration(self, web_integrated_system):
        """Test file upload integration with backup and configuration services"""
        # Mock file upload
        with tempfile.NamedTemporaryFile(suffix='.json') as config_file:
            config_data = {"dns_servers": ["8.8.8.8", "8.8.4.4"], "vlans": [100, 200]}
            json.dump(config_data, config_file)
            config_file.flush()
            
            # Upload configuration file
            result = web_integrated_system.web_app.upload_configuration(config_file.name)
            
            # Should validate and apply configuration
            assert result.success, "Configuration upload should succeed"
            web_integrated_system.dns_manager.update_servers.assert_called_with(["8.8.8.8", "8.8.4.4"])
            web_integrated_system.vlan_controller.ensure_vlans_exist.assert_called_with([100, 200])

class TestSystemWideFailureScenarios:
    """Test system behavior under various failure conditions"""
    
    @pytest.fixture
    def failure_test_system(self):
        """Setup system for failure testing"""
        system = Mock()
        
        # All major components
        system.components = {
            "auth_engine": Mock(),
            "dns_manager": Mock(),
            "vlan_controller": Mock(),
            "device_tracker": Mock(),
            "backup_service": Mock(),
            "scheduler": Mock(),
            "web_app": Mock(),
            "health_monitor": Mock()
        }
        
        return system

    def test_database_failure_cascade(self, failure_test_system):
        """Test system behavior when database becomes unavailable"""
        # Simulate database failure
        db_error = Exception("Connection to database lost")
        
        for component_name, component in failure_test_system.components.items():
            component.database_operation.side_effect = db_error
        
        # System should degrade gracefully
        health_status = failure_test_system.components["health_monitor"].check_system_health()
        
        assert health_status.status == "degraded", "System should report degraded status"
        assert "database" in health_status.failed_components
        
        # Critical operations should fail safely
        for component in failure_test_system.components.values():
            result = component.perform_critical_operation()
            assert not result.success, "Critical operations should fail safely"
            assert result.error_type == "database_unavailable"

    def test_network_partition_handling(self, failure_test_system):
        """Test behavior during network partitions"""
        # Simulate network partition
        network_error = Exception("Network unreachable")
        
        # External services become unavailable
        failure_test_system.components["dns_manager"].external_dns_query.side_effect = network_error
        failure_test_system.components["backup_service"].remote_backup.side_effect = network_error
        
        # Should continue with local operations
        local_result = failure_test_system.components["device_tracker"].scan_local_network()
        assert local_result.success, "Local operations should continue"
        
        # Should queue operations for retry
        retry_queue = failure_test_system.components["scheduler"].get_retry_queue()
        assert len(retry_queue) > 0, "Failed operations should be queued for retry"

    def test_memory_exhaustion_protection(self, failure_test_system):
        """Test system protection against memory exhaustion"""
        # Simulate high memory usage
        for component in failure_test_system.components.values():
            component.get_memory_usage.return_value = 0.95  # 95% memory usage
        
        # System should activate protection mechanisms
        failure_test_system.components["health_monitor"].check_memory_usage()
        
        # Should limit new operations
        result = failure_test_system.components["backup_service"].create_full_backup("emergency")
        assert not result.success, "Should prevent memory-intensive operations"
        assert result.error_code == "MEMORY_PROTECTION_ACTIVE"

    def test_cascading_failure_prevention(self, failure_test_system):
        """Test prevention of cascading failures across services"""
        # One service fails
        failure_test_system.components["dns_manager"].status = "failed"
        
        # Other services should isolate the failure
        dependent_services = ["vlan_controller", "device_tracker"]
        
        for service_name in dependent_services:
            service = failure_test_system.components[service_name]
            result = service.operate_with_dns_dependency()
            
            # Should operate in degraded mode, not fail completely
            assert result.status in ["success", "degraded"], f"{service_name} should not cascade fail"

    def test_service_restart_coordination(self, failure_test_system):
        """Test coordinated service restart procedures"""
        # Restart sequence for critical service
        restart_service = "auth_engine"
        
        # Should notify all dependent services
        failure_test_system.components["auth_engine"].restart()
        
        dependent_services = ["web_app", "dns_manager", "vlan_controller"]
        for service_name in dependent_services:
            service = failure_test_system.components[service_name]
            service.handle_auth_service_restart.assert_called_once()
        
        # Should re-establish connections in proper order
        restart_order = failure_test_system.components["scheduler"].get_restart_order()
        assert restart_order[0] == "auth_engine", "Auth should restart first"

class TestPerformanceIntegration:
    """Performance testing across integrated components"""
    
    @pytest.fixture
    def performance_test_system(self):
        """Setup system for performance testing"""
        system = Mock()
        system.metrics_collector = Mock()
        
        # Performance counters
        system.metrics = {
            "request_count": 0,
            "response_times": [],
            "error_count": 0,
            "memory_usage": [],
            "cpu_usage": []
        }
        
        return system

    def test_high_load_device_tracking(self, performance_test_system):
        """Test device tracking performance under high load"""
        device_count = 1000
        devices = [f"aa:bb:cc:dd:ee:{i:02x}" for i in range(device_count)]
        
        start_time = time.time()
        
        # Simulate high-frequency device updates
        for device_mac in devices:
            performance_test_system.device_tracker.update_device_status(
                device_mac, {"status": "active", "last_seen": time.time()}
            )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should handle high load efficiently
        throughput = device_count / processing_time
        assert throughput > 100, f"Should process >100 devices/second, got {throughput:.2f}"

    def test_concurrent_api_requests(self, performance_test_system):
        """Test API performance under concurrent load"""
        import threading
        import queue
        
        request_count = 100
        concurrent_threads = 10
        results = queue.Queue()
        
        def make_api_request():
            start = time.time()
            response = performance_test_system.web_app.api_request("/api/devices")
            end = time.time()
            results.put({"response": response, "time": end - start})
        
        # Launch concurrent requests
        threads = []
        for _ in range(request_count):
            thread = threading.Thread(target=make_api_request)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Analyze results
        response_times = []
        success_count = 0
        
        while not results.empty():
            result = results.get()
            response_times.append(result["time"])
            if result["response"].status_code == 200:
                success_count += 1
        
        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        success_rate = success_count / request_count
        
        assert avg_response_time < 1.0, f"Average response time should be <1s, got {avg_response_time:.3f}s"
        assert success_rate > 0.95, f"Success rate should be >95%, got {success_rate:.2%}"

    def test_memory_leak_detection(self, performance_test_system):
        """Test for memory leaks during extended operation"""
        initial_memory = performance_test_system.get_memory_usage()
        
        # Perform extended operations
        for cycle in range(100):
            # Simulate typical operation cycle
            performance_test_system.device_tracker.scan_network()
            performance_test_system.dns_manager.resolve_pending_queries()
            performance_test_system.vlan_controller.update_port_assignments()
            performance_test_system.backup_service.cleanup_old_backups()
            
            # Collect memory metrics
            current_memory = performance_test_system.get_memory_usage()
            performance_test_system.metrics["memory_usage"].append(current_memory)
        
        final_memory = performance_test_system.get_memory_usage()
        memory_growth = final_memory - initial_memory
        
        # Should not have significant memory growth
        memory_growth_percent = (memory_growth / initial_memory) * 100
        assert memory_growth_percent < 10, f"Memory growth should be <10%, got {memory_growth_percent:.1f}%"

class TestSecurityIntegration:
    """Security testing across integrated components"""
    
    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation across service boundaries"""
        # User with limited permissions
        limited_user = {"id": "user123", "permissions": ["device_read"]}
        
        # Attempt to escalate privileges through service interactions
        escalation_attempts = [
            # Through DNS service
            ("dns_manager.add_admin_record", {"record": "admin.local", "ip": "127.0.0.1"}),
            # Through VLAN service  
            ("vlan_controller.create_admin_vlan", {"vlan_id": 1, "admin": True}),
            # Through backup service
            ("backup_service.restore_admin_backup", {"backup_id": "admin_restore"}),
            # Through scheduler
            ("scheduler.add_admin_job", {"job": "grant_admin_access"})
        ]
        
        for service_method, params in escalation_attempts:
            with pytest.raises(PermissionError):
                # Should reject privilege escalation attempts
                service, method = service_method.split('.')
                getattr(Mock(), method)(**params, user=limited_user)

    def test_data_isolation_between_services(self):
        """Test that services properly isolate sensitive data"""
        # Setup services with different security contexts
        services = {
            "dns_manager": Mock(security_level="medium"),
            "auth_engine": Mock(security_level="high"), 
            "backup_service": Mock(security_level="high"),
            "web_app": Mock(security_level="medium")
        }
        
        # High-security data should not leak to medium-security services
        sensitive_data = {"password_hash": "secret123", "api_key": "sensitive_key"}
        
        services["auth_engine"].store_sensitive_data(sensitive_data)
        
        # Medium-security services should not have access
        dns_data = services["dns_manager"].get_available_data()
        web_data = services["web_app"].get_available_data()
        
        assert "password_hash" not in dns_data
        assert "api_key" not in web_data

if __name__ == "__main__":
    # Run integration tests with appropriate markers
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-m", "integration",
        "--maxfail=5"
    ])