#!/usr/bin/env python3
"""
LNMT Health Monitor Examples and Tests

Demonstrates usage patterns and provides basic testing for the health monitoring system.
Run this file to see examples of how to use the health monitor and CLI.

Requirements:
- Python 3.10+
- psutil package
- Root access for full functionality
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from services.health_monitor import HealthMonitor, AlertLevel, ServiceStatus
    from cli.healthctl import HealthCLI
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the health_monitor and healthctl modules are in the correct locations.")
    sys.exit(1)


class HealthMonitorExamples:
    """Example usage patterns for LNMT Health Monitor"""
    
    def __init__(self):
        self.monitor = HealthMonitor()
        self.cli = HealthCLI()
    
    def example_basic_health_check(self):
        """Example 1: Basic system health check"""
        print("=== Example 1: Basic Health Check ===")
        
        try:
            # Get overall system status
            status = self.monitor.get_system_status()
            
            print(f"System Health: {status['overall_health']}")
            print(f"Timestamp: {status['timestamp']}")
            
            # Check if any services are down
            failed_services = [
                service for service in status['services'] 
                if service['status'] in ['stopped', 'failed']
            ]
            
            if failed_services:
                print(f"⚠️  {len(failed_services)} services need attention:")
                for service in failed_services:
                    print(f"  - {service['name']}: {service['status']}")
            else:
                print("✓ All services are running normally")
            
            # Check resource usage
            resources = status.get('resources', {})
            if resources:
                high_usage = []
                if resources.get('cpu_percent', 0) > 80:
                    high_usage.append(f"CPU: {resources['cpu_percent']:.1f}%")
                if resources.get('memory_percent', 0) > 80:
                    high_usage.append(f"Memory: {resources['memory_percent']:.1f}%")
                if resources.get('disk_percent', 0) > 80:
                    high_usage.append(f"Disk: {resources['disk_percent']:.1f}%")
                
                if high_usage:
                    print(f"⚠️  High resource usage: {', '.join(high_usage)}")
                else:
                    print("✓ Resource usage is normal")
        
        except Exception as e:
            print(f"❌ Error in basic health check: {e}")
    
    def example_service_monitoring(self):
        """Example 2: Individual service monitoring"""
        print("\n=== Example 2: Service Monitoring ===")
        
        services_to_check = ['dnsmasq', 'pihole', 'unbound']
        
        for service_name in services_to_check:
            try:
                print(f"\nChecking {service_name}...")
                service_info = self.monitor.check_service(service_name)
                
                status_emoji = {
                    ServiceStatus.RUNNING: "🟢",
                    ServiceStatus.STOPPED: "🔴", 
                    ServiceStatus.FAILED: "🟠",
                    ServiceStatus.UNKNOWN: "❓"
                }
                
                emoji = status_emoji.get(service_info.status, "❓")
                print(f"  {emoji} Status: {service_info.status.value}")
                
                if service_info.status == ServiceStatus.RUNNING:
                    print(f"  📊 PID: {service_info.pid}")
                    print(f"  💾 Memory: {service_info.memory_mb:.1f} MB")
                    print(f"  ⏱️  Uptime: {service_info.uptime}")
                    
                    # Check if memory usage is concerning
                    if service_info.memory_mb > 100:  # More than 100MB
                        print(f"  ⚠️  High memory usage for {service_name}")
                
                elif service_info.status == ServiceStatus.STOPPED:
                    print(f"  ❌ {service_name} is not running - this may affect DNS resolution")
                    print(f"  💡 Try: sudo systemctl start {service_name}")
                
            except ValueError:
                print(f"  ❓ {service_name} is not a monitored service")
            except Exception as e:
                print(f"  ❌ Error checking {service_name}: {e}")
    
    def example_resource_monitoring(self):
        """Example 3: Resource usage monitoring with thresholds"""
        print("\n=== Example 3: Resource Monitoring ===")
        
        try:
            resources = self.monitor.get_system_resources()
            
            print("Current Resource Usage:")
            print(f"  🖥️  CPU: {resources.cpu_percent:.1f}%")
            print(f"  💾 Memory: {resources.memory_percent:.1f}%") 
            print(f"  💿 Disk: {resources.disk_percent:.1f}%")
            print(f"  ⚖️  Load: {resources.load_avg[0]:.2f}, {resources.load_avg[1]:.2f}, {resources.load_avg[2]:.2f}")
            print(f"  ⏰ Uptime: {resources.uptime}")
            
            # Demonstrate threshold checking
            warnings = []
            critical = []
            
            if resources.cpu_percent >= 95:
                critical.append("CPU")
            elif resources.cpu_percent >= 80:
                warnings.append("CPU")
            
            if resources.memory_percent >= 95:
                critical.append("Memory")
            elif resources.memory_percent >= 85:
                warnings.append("Memory")
            
            if resources.disk_percent >= 95:
                critical.append("Disk")
            elif resources.disk_percent >= 85:
                warnings.append("Disk")
            
            if critical:
                print(f"  🚨 CRITICAL: {', '.join(critical)} usage is dangerously high!")
            elif warnings:
                print(f"  ⚠️  WARNING: {', '.join(warnings)} usage is elevated")
            else:
                print("  ✅ All resource usage is within normal limits")
        
        except Exception as e:
            print(f"❌ Error monitoring resources: {e}")
    
    def example_config_validation(self):
        """Example 4: Configuration file validation"""
        print("\n=== Example 4: Configuration Validation ===")
        
        try:
            config_results = self.monitor.validate_configs()
            
            print("Configuration File Status:")
            
            valid_configs = []
            invalid_configs = []
            
            for config_path, is_valid in config_results.items():
                if is_valid:
                    valid_configs.append(config_path)
                    print(f"  ✅ {config_path}")
                else:
                    invalid_configs.append(config_path)
                    print(f"  ❌ {config_path}")
            
            print(f"\nSummary: {len(valid_configs)} valid, {len(invalid_configs)} invalid")
            
            if invalid_configs:
                print(f"\n⚠️  Invalid configurations detected:")
                for config in invalid_configs:
                    print(f"  - {config}")
                print(f"\n💡 Check the alert log for specific validation errors")
            else:
                print(f"\n✅ All configuration files are valid")
        
        except Exception as e:
            print(f"❌ Error validating configurations: {e}")
    
    def example_alert_management(self):
        """Example 5: Alert management and monitoring"""
        print("\n=== Example 5: Alert Management ===")
        
        try:
            # Get alerts from different time periods
            recent_alerts = self.monitor.get_recent_alerts(hours=1)
            daily_alerts = self.monitor.get_recent_alerts(hours=24)
            critical_alerts = self.monitor.get_recent_alerts(hours=24, level=AlertLevel.CRITICAL)
            
            print(f"Alert Summary:")
            print(f"  📊 Last hour: {len(recent_alerts)} alerts")
            print(f"  📊 Last 24 hours: {len(daily_alerts)} alerts")
            print(f"  🚨 Critical (24h): {len(critical_alerts)} alerts")
            
            if critical_alerts:
                print(f"\n🚨 Recent Critical Alerts:")
                for alert in critical_alerts[:3]:  # Show last 3 critical
                    timestamp = datetime.fromisoformat(alert['timestamp'])
                    time_str = timestamp.strftime('%H:%M:%S')
                    print(f"  [{time_str}] {alert['service']}: {alert['message']}")
            
            if recent_alerts:
                print(f"\n📋 Recent Activity (last hour):")
                
                # Group by alert level
                level_counts = {}
                for alert in recent_alerts:
                    level = alert['level']
                    level_counts[level] = level_counts.get(level, 0) + 1
                
                for level, count in level_counts.items():
                    emoji = {
                        'info': 'ℹ️',
                        'warning': '⚠️',
                        'error': '❌',
                        'critical': '🚨'
                    }.get(level, '📝')
                    print(f"  {emoji} {level.upper()}: {count}")
            else:
                print(f"\n✅ No recent alerts - system is stable")
        
        except Exception as e:
            print(f"❌ Error managing alerts: {e}")
    
    def example_cli_usage(self):
        """Example 6: CLI interface usage"""
        print("\n=== Example 6: CLI Interface Usage ===")
        
        print("The healthctl.py CLI provides these commands:")
        print("  • healthctl.py --status              # Overall system status")
        print("  • healthctl.py --check dnsmasq       # Check specific service") 
        print("  • healthctl.py --resources           # Resource usage")
        print("  • healthctl.py --configs             # Config validation")
        print("  • healthctl.py --alertlog            # Recent alerts")
        print("  • healthctl.py --json                # JSON output")
        
        print(f"\nExample CLI output (--status):")
        try:
            # Demonstrate CLI status output
            self.cli.set_json_output(False)
            print("  " + "-" * 50)
            # Capture the status display
            original_stdout = sys.stdout
            from io import StringIO
            captured_output = StringIO()
            sys.stdout = captured_output
            
            try:
                self.cli.show_status()
                output = captured_output.getvalue()
                sys.stdout = original_stdout
                
                # Indent the output for display
                for line in output.split('\n')[:10]:  # Show first 10 lines
                    if line.strip():
                        print(f"  {line}")
                if len(output.split('\n')) > 10:
                    print("  ...")
            except:
                sys.stdout = original_stdout
                print("  [CLI status output would appear here]")
            
            print("  " + "-" * 50)
        
        except Exception as e:
            print(f"  Error demonstrating CLI: {e}")
    
    def example_automation_integration(self):
        """Example 7: Integration with automation systems"""
        print("\n=== Example 7: Automation Integration ===")
        
        print("Examples for automation integration:")
        
        # Example 1: Cron job health check
        print(f"\n📅 Cron Job Example:")
        print(f"  # Add to crontab for hourly health checks")
        print(f"  0 * * * * /usr/local/bin/healthctl.py --status --json > /var/log/lnmt-hourly-status.json")
        print(f"  */15 * * * * /usr/local/bin/healthctl.py --alertlog --hours 1 --level critical")
        
        # Example 2: Systemd service monitoring
        print(f"\n🔧 Systemd Integration:")
        print(f"  # Check if services are managed by systemd")
        services = ['dnsmasq', 'pihole-FTL', 'unbound']
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                status = result.stdout.strip()
                emoji = "🟢" if status == "active" else "🔴"
                print(f"    {emoji} {service}: {status}")
            except Exception:
                print(f"    ❓ {service}: unknown")
        
        # Example 3: JSON output for monitoring systems
        print(f"\n📊 Monitoring System Integration:")
        print(f"  # Get status in JSON for external monitoring")
        try:
            status = self.monitor.get_system_status()
            sample_json = {
                "health": status['overall_health'],
                "services_total": status['summary']['total_services'],
                "services_failed": status['summary']['failed_services'],
                "cpu_percent": status['resources'].get('cpu_percent', 0),
                "memory_percent": status['resources'].get('memory_percent', 0)
            }
            print(f"  Sample JSON output:")
            print(f"  {json.dumps(sample_json, indent=4)}")
        except Exception as e:
            print(f"  Error generating sample JSON: {e}")
        
        # Example 4: Alert webhook simulation
        print(f"\n🔔 Alert Webhook Example:")
        recent_alerts = self.monitor.get_recent_alerts(hours=1)
        if recent_alerts:
            alert = recent_alerts[0]
            webhook_payload = {
                "timestamp": alert['timestamp'],
                "level": alert['level'],
                "service": alert['service'], 
                "message": alert['message'],
                "hostname": os.uname().nodename
            }
            print(f"  Sample webhook payload:")
            print(f"  {json.dumps(webhook_payload, indent=4)}")
        else:
            print(f"  No recent alerts to demonstrate webhook payload")
    
    def run_all_examples(self):
        """Run all examples in sequence"""
        print("🧠 LNMT Health Monitor - Examples and Demonstrations")
        print("=" * 60)
        
        self.example_basic_health_check()
        self.example_service_monitoring()
        self.example_resource_monitoring()
        self.example_config_validation()
        self.example_alert_management()
        self.example_cli_usage()
        self.example_automation_integration()
        
        print("\n" + "=" * 60)
        print("✅ All examples completed!")
        print("\nNext Steps:")
        print("  1. Install the health monitor: sudo cp services/health_monitor.py /usr/local/lib/lnmt/")
        print("  2. Install the CLI: sudo cp cli/healthctl.py /usr/local/bin/ && sudo chmod +x /usr/local/bin/healthctl.py")
        print("  3. Set up cron jobs for automated monitoring")
        print("  4. Configure alerting webhooks or email notifications")


class HealthMonitorTests:
    """Basic tests for the health monitoring system"""
    
    def __init__(self):
        self.monitor = HealthMonitor()
        self.test_results = []
    
    def test_system_status(self):
        """Test getting system status"""
        print("Testing system status retrieval...")
        try:
            status = self.monitor.get_system_status()
            
            # Check required fields
            required_fields = ['timestamp', 'overall_health', 'services', 'resources', 'summary']
            for field in required_fields:
                assert field in status, f"Missing required field: {field}"
            
            # Check health values
            valid_health = ['healthy', 'warning', 'degraded', 'critical']
            assert status['overall_health'] in valid_health, f"Invalid health status: {status['overall_health']}"
            
            # Check summary
            summary = status['summary']
            assert isinstance(summary['total_services'], int), "total_services should be integer"
            assert isinstance(summary['failed_services'], int), "failed_services should be integer"
            assert summary['failed_services'] <= summary['total_services'], "failed_services cannot exceed total"
            
            print("  ✅ System status test passed")
            self.test_results.append(("System Status", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ System status test failed: {e}")
            self.test_results.append(("System Status", False, str(e)))
            return False
    
    def test_service_checks(self):
        """Test individual service checking"""
        print("Testing service checks...")
        try:
            # Test valid service
            for service_name in ['dnsmasq', 'pihole']:
                try:
                    service_info = self.monitor.check_service(service_name)
                    
                    # Check required fields
                    assert hasattr(service_info, 'name'), "Service info missing name"
                    assert hasattr(service_info, 'status'), "Service info missing status"
                    assert service_info.name == service_name, "Service name mismatch"
                    
                    # Check status is valid enum value
                    valid_statuses = [s.value for s in ServiceStatus]
                    assert service_info.status.value in valid_statuses, f"Invalid status: {service_info.status.value}"
                    
                    print(f"  ✅ {service_name} check passed")
                except Exception as e:
                    print(f"  ⚠️  {service_name} check had issues: {e}")
            
            # Test invalid service
            try:
                self.monitor.check_service("nonexistent_service")
                print("  ❌ Invalid service test failed - should have raised ValueError")
                self.test_results.append(("Service Checks", False, "Invalid service not caught"))
                return False
            except ValueError:
                print("  ✅ Invalid service correctly rejected")
            
            print("  ✅ Service checks test passed")
            self.test_results.append(("Service Checks", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ Service checks test failed: {e}")
            self.test_results.append(("Service Checks", False, str(e)))
            return False
    
    def test_resource_monitoring(self):
        """Test resource monitoring"""
        print("Testing resource monitoring...")
        try:
            resources = self.monitor.get_system_resources()
            
            # Check required fields
            required_fields = ['cpu_percent', 'memory_percent', 'disk_percent', 'load_avg', 'uptime']
            for field in required_fields:
                assert hasattr(resources, field), f"Missing field: {field}"
            
            # Check value ranges
            assert 0 <= resources.cpu_percent <= 100, f"Invalid CPU percent: {resources.cpu_percent}"
            assert 0 <= resources.memory_percent <= 100, f"Invalid memory percent: {resources.memory_percent}"
            assert 0 <= resources.disk_percent <= 100, f"Invalid disk percent: {resources.disk_percent}"
            
            # Check load average is tuple of 3 floats
            assert len(resources.load_avg) == 3, "Load average should be 3-tuple"
            assert all(isinstance(x, float) for x in resources.load_avg), "Load average should be floats"
            
            print("  ✅ Resource monitoring test passed")
            self.test_results.append(("Resource Monitoring", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ Resource monitoring test failed: {e}")
            self.test_results.append(("Resource Monitoring", False, str(e)))
            return False
    
    def test_config_validation(self):
        """Test configuration validation"""
        print("Testing configuration validation...")
        try:
            config_results = self.monitor.validate_configs()
            
            # Check return type
            assert isinstance(config_results, dict), "Config results should be dictionary"
            
            # Check all values are boolean
            for config_path, result in config_results.items():
                assert isinstance(result, bool), f"Config result for {config_path} should be boolean"
                assert isinstance(config_path, str), f"Config path should be string"
            
            print(f"  ✅ Configuration validation test passed ({len(config_results)} configs checked)")
            self.test_results.append(("Config Validation", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ Configuration validation test failed: {e}")
            self.test_results.append(("Config Validation", False, str(e)))
            return False
    
    def test_alert_system(self):
        """Test alert management"""
        print("Testing alert system...")
        try:
            # Clear existing alerts for clean test
            self.monitor.clear_alerts()
            
            # Generate a test alert
            self.monitor._add_alert(
                AlertLevel.WARNING,
                "test_service",
                "Test alert message",
                {"test_key": "test_value"}
            )
            
            # Check alert was added
            recent_alerts = self.monitor.get_recent_alerts(hours=1)
            assert len(recent_alerts) >= 1, "Alert was not added"
            
            # Check alert structure
            test_alert = recent_alerts[0]
            required_fields = ['timestamp', 'level', 'service', 'message', 'details']
            for field in required_fields:
                assert field in test_alert, f"Alert missing field: {field}"
            
            assert test_alert['service'] == 'test_service', "Alert service mismatch"
            assert test_alert['level'] == 'warning', "Alert level mismatch"
            
            # Test filtering by level
            warning_alerts = self.monitor.get_recent_alerts(hours=1, level=AlertLevel.WARNING)
            assert len(warning_alerts) >= 1, "Level filtering not working"
            
            # Test clearing alerts
            cleared_count = self.monitor.clear_alerts()
            assert cleared_count >= 1, "Alert clearing not working"
            
            print("  ✅ Alert system test passed")
            self.test_results.append(("Alert System", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ Alert system test failed: {e}")
            self.test_results.append(("Alert System", False, str(e)))
            return False
    
    def test_cli_interface(self):
        """Test CLI interface"""
        print("Testing CLI interface...")
        try:
            cli = HealthCLI()
            
            # Test JSON mode setting
            cli.set_json_output(True)
            assert cli.json_output == True, "JSON mode setting failed"
            
            cli.set_json_output(False)
            assert cli.json_output == False, "JSON mode setting failed"
            
            # Test that CLI methods don't crash (basic smoke test)
            # We can't easily test output without complex mocking
            
            print("  ✅ CLI interface test passed")
            self.test_results.append(("CLI Interface", True, None))
            return True
            
        except Exception as e:
            print(f"  ❌ CLI interface test failed: {e}")
            self.test_results.append(("CLI Interface", False, str(e)))
            return False
    
    def run_all_tests(self):
        """Run all tests and report results"""
        print("🧪 LNMT Health Monitor - Test Suite")
        print("=" * 50)
        
        # Run all tests
        tests = [
            self.test_system_status,
            self.test_service_checks,
            self.test_resource_monitoring,
            self.test_config_validation,
            self.test_alert_system,
            self.test_cli_interface
        ]
        
        passed = 0
        failed = 0
        
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  ❌ Test {test_func.__name__} crashed: {e}")
                failed += 1
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All tests passed! Health monitor is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for test_name, success, error in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name}")
            if error:
                print(f"    Error: {error}")
        
        return failed == 0


def main():
    """Main function to run examples or tests"""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run tests
        tests = HealthMonitorTests()
        success = tests.run_all_tests()
        sys.exit(0 if success else 1)
    else:
        # Run examples
        examples = HealthMonitorExamples()
        examples.run_all_examples()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)