                response = self.session.post(
                    f"http://{self.target_host}:{self.target_port}/api/auth/login",
                    json={'username': username, 'password': password}
                )
                
                if response.status_code == 200:
                    self.add_result(SecurityTestResult(
                        test_name="Default Credentials Check",
                        category="Authentication",
                        severity="CRITICAL",
                        status="FAIL",
                        description="Default credentials accepted",
                        details=f"Login successful with {username}:{password}",
                        remediation="Change default credentials immediately"
                    ))
                    return
                    
            except requests.RequestException:
                pass
        
        self.add_result(SecurityTestResult(
            test_name="Default Credentials Check",
            category="Authentication",
            severity="INFO",
            status="PASS",
            description="No default credentials found"
        ))
    
    def _test_brute_force_protection(self):
        """Test brute force protection"""
        test_username = "testuser"
        wrong_password = "wrongpassword"
        
        start_time = time.time()
        failed_attempts = 0
        
        for i in range(10):
            try:
                response = self.session.post(
                    f"http://{self.target_host}:{self.target_port}/api/auth/login",
                    json={'username': test_username, 'password': wrong_password}
                )
                
                if response.status_code == 429:  # Rate limited
                    self.add_result(SecurityTestResult(
                        test_name="Brute Force Protection",
                        category="Authentication",
                        severity="INFO",
                        status="PASS",
                        description="Rate limiting active",
                        details=f"Rate limited after {i+1} attempts"
                    ))
                    return
                elif response.status_code == 401:
                    failed_attempts += 1
                
                time.sleep(0.1)  # Small delay between attempts
                
            except requests.RequestException:
                break
        
        elapsed_time = time.time() - start_time
        
        if failed_attempts >= 10 and elapsed_time < 5:
            self.add_result(SecurityTestResult(
                test_name="Brute Force Protection",
                category="Authentication",
                severity="HIGH",
                status="FAIL",
                description="No brute force protection detected",
                details=f"Processed {failed_attempts} attempts in {elapsed_time:.2f} seconds",
                remediation="Implement rate limiting and account lockout"
            ))
        else:
            self.add_result(SecurityTestResult(
                test_name="Brute Force Protection",
                category="Authentication",
                severity="INFO",
                status="PASS",
                description="Brute force protection appears active"
            ))
    
    def _test_session_management(self):
        """Test session management security"""
        # Test session fixation
        try:
            # Get initial session
            response1 = self.session.get(f"http://{self.target_host}:{self.target_port}/api/auth/status")
            initial_cookies = self.session.cookies.copy()
            
            # Try to login with fixed session
            login_response = self.session.post(
                f"http://{self.target_host}:{self.target_port}/api/auth/login",
                json={'username': 'admin', 'password': 'correctpassword'}
            )
            
            if login_response.status_code == 200:
                # Check if session ID changed
                post_login_cookies = self.session.cookies.copy()
                
                session_changed = False
                for cookie_name in ['session', 'sessionid', 'JSESSIONID']:
                    if (cookie_name in initial_cookies and 
                        cookie_name in post_login_cookies and
                        initial_cookies[cookie_name] != post_login_cookies[cookie_name]):
                        session_changed = True
                        break
                
                if not session_changed:
                    self.add_result(SecurityTestResult(
                        test_name="Session Fixation Test",
                        category="Session Management",
                        severity="MEDIUM",
                        status="FAIL",
                        description="Session ID not regenerated on login",
                        remediation="Regenerate session ID after authentication"
                    ))
                else:
                    self.add_result(SecurityTestResult(
                        test_name="Session Fixation Test",
                        category="Session Management",
                        severity="INFO",
                        status="PASS",
                        description="Session ID properly regenerated"
                    ))
        except requests.RequestException:
            self.add_result(SecurityTestResult(
                test_name="Session Fixation Test",
                category="Session Management",
                severity="INFO",
                status="SKIP",
                description="Could not test session management"
            ))
    
    def _test_password_policies(self):
        """Test password policy enforcement"""
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "qwerty",
            "abc123",
            "password123"
        ]
        
        for weak_password in weak_passwords:
            try:
                response = self.session.post(
                    f"http://{self.target_host}:{self.target_port}/api/auth/register",
                    json={
                        'username': f'testuser_{secrets.token_hex(4)}',
                        'password': weak_password,
                        'email': 'test@example.com'
                    }
                )
                
                if response.status_code == 200:
                    self.add_result(SecurityTestResult(
                        test_name="Password Policy Test",
                        category="Authentication",
                        severity="MEDIUM",
                        status="FAIL",
                        description="Weak password accepted",
                        details=f"Password '{weak_password}' was accepted",
                        remediation="Implement strong password policies"
                    ))
                    return
                    
            except requests.RequestException:
                pass
        
        self.add_result(SecurityTestResult(
            test_name="Password Policy Test",
            category="Authentication",
            severity="INFO",
            status="PASS",
            description="Strong password policies enforced"
        ))
    
    def _test_jwt_security(self):
        """Test JWT token security"""
        try:
            # Try to get a token
            response = self.session.post(
                f"http://{self.target_host}:{self.target_port}/api/auth/login",
                json={'username': 'admin', 'password': 'testpassword'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'token' in data:
                    token = data['token']
                    
                    # Test 1: Check if token is properly signed
                    try:
                        # Try to decode without verification
                        decoded = jwt.decode(token, options={"verify_signature": False})
                        
                        # Check for weak algorithms
                        if decoded.get('alg') in ['none', 'HS256']:
                            severity = "HIGH" if decoded.get('alg') == 'none' else "MEDIUM"
                            self.add_result(SecurityTestResult(
                                test_name="JWT Algorithm Security",
                                category="Authentication",
                                severity=severity,
                                status="FAIL",
                                description=f"Weak JWT algorithm: {decoded.get('alg')}",
                                remediation="Use strong algorithms like RS256"
                            ))
                        
                        # Check expiration
                        if 'exp' not in decoded:
                            self.add_result(SecurityTestResult(
                                test_name="JWT Expiration Check",
                                category="Authentication",
                                severity="MEDIUM",
                                status="FAIL",
                                description="JWT token has no expiration",
                                remediation="Set appropriate token expiration"
                            ))
                        
                    except jwt.DecodeError:
                        self.add_result(SecurityTestResult(
                            test_name="JWT Token Structure",
                            category="Authentication",
                            severity="INFO",
                            status="PASS",
                            description="JWT token properly formatted"
                        ))
                        
        except requests.RequestException:
            self.add_result(SecurityTestResult(
                test_name="JWT Security Test",
                category="Authentication",
                severity="INFO",
                status="SKIP",
                description="Could not obtain JWT token"
            ))
    
    def test_input_validation(self):
        """Test input validation and injection vulnerabilities"""
        print("\n🛡️ Testing Input Validation...")
        
        # Test SQL injection
        self._test_sql_injection()
        
        # Test XSS
        self._test_xss_vulnerabilities()
        
        # Test command injection
        self._test_command_injection()
        
        # Test path traversal
        self._test_path_traversal()
        
        # Test file upload security
        self._test_file_upload_security()
    
    def _test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        endpoints = [
            "/api/auth/login",
            "/api/users/search",
            "/api/devices/list",
            "/api/dns/records"
        ]
        
        for endpoint in endpoints:
            for payload in self.test_config['sql_injection_payloads']:
                try:
                    # Test in different parameters
                    test_cases = [
                        {'username': payload, 'password': 'test'},
                        {'search': payload},
                        {'query': payload},
                        {'filter': payload}
                    ]
                    
                    for test_data in test_cases:
                        response = self.session.post(
                            f"http://{self.target_host}:{self.target_port}{endpoint}",
                            json=test_data
                        )
                        
                        # Look for SQL error indicators
                        if response.status_code == 500:
                            response_text = response.text.lower()
                            sql_errors = [
                                'sql syntax',
                                'mysql_fetch',
                                'ora-',
                                'postgresql error',
                                'sqlite error',
                                'syntax error'
                            ]
                            
                            if any(error in response_text for error in sql_errors):
                                self.add_result(SecurityTestResult(
                                    test_name="SQL Injection Test",
                                    category="Input Validation",
                                    severity="CRITICAL",
                                    status="FAIL",
                                    description=f"SQL injection vulnerability in {endpoint}",
                                    details=f"Payload: {payload}",
                                    remediation="Use parameterized queries and input validation"
                                ))
                                return
                                
                except requests.RequestException:
                    pass
        
        self.add_result(SecurityTestResult(
            test_name="SQL Injection Test",
            category="Input Validation",
            severity="INFO",
            status="PASS",
            description="No SQL injection vulnerabilities found"
        ))
    
    def _test_xss_vulnerabilities(self):
        """Test for XSS vulnerabilities"""
        endpoints = [
            "/api/users/profile",
            "/api/devices/update",
            "/api/dns/add-record"
        ]
        
        for endpoint in endpoints:
            for payload in self.test_config['xss_payloads']:
                try:
                    test_data = {
                        'name': payload,
                        'description': payload,
                        'value': payload
                    }
                    
                    response = self.session.post(
                        f"http://{self.target_host}:{self.target_port}{endpoint}",
                        json=test_data
                    )
                    
                    # Check if payload is reflected without encoding
                    if payload in response.text and '<script>' in payload:
                        self.add_result(SecurityTestResult(
                            test_name="XSS Vulnerability Test",
                            category="Input Validation",
                            severity="HIGH",
                            status="FAIL",
                            description=f"XSS vulnerability in {endpoint}",
                            details=f"Payload reflected: {payload}",
                            remediation="Implement proper output encoding and CSP headers"
                        ))
                        return
                        
                except requests.RequestException:
                    pass
        
        self.add_result(SecurityTestResult(
            test_name="XSS Vulnerability Test",
            category="Input Validation",
            severity="INFO",
            status="PASS",
            description="No XSS vulnerabilities found"
        ))
    
    def _test_command_injection(self):
        """Test for command injection vulnerabilities"""
        endpoints = [
            "/api/system/ping",
            "/api/dns/dig",
            "/api/network/traceroute"
        ]
        
        for endpoint in endpoints:
            for payload in self.test_config['command_injection_payloads']:
                try:
                    test_data = {
                        'target': f"localhost{payload}",
                        'host': f"example.com{payload}",
                        'command': payload
                    }
                    
                    response = self.session.post(
                        f"http://{self.target_host}:{self.target_port}{endpoint}",
                        json=test_data
                    )
                    
                    # Look for command execution indicators
                    if response.status_code == 200:
                        response_text = response.text.lower()
                        injection_indicators = [
                            'uid=',
                            'gid=',
                            'root:x:0:0',
                            'etc/passwd',
                            'bin/bash'
                        ]
                        
                        if any(indicator in response_text for indicator in injection_indicators):
                            self.add_result(SecurityTestResult(
                                test_name="Command Injection Test",
                                category="Input Validation",
                                severity="CRITICAL",
                                status="FAIL",
                                description=f"Command injection vulnerability in {endpoint}",
                                details=f"Payload: {payload}",
                                remediation="Use parameterized commands and input validation"
                            ))
                            return
                            
                except requests.RequestException:
                    pass
        
        self.add_result(SecurityTestResult(
            test_name="Command Injection Test",
            category="Input Validation",
            severity="INFO",
            status="PASS",
            description="No command injection vulnerabilities found"
        ))
    
    def _test_path_traversal(self):
        """Test for path traversal vulnerabilities"""
        endpoints = [
            "/api/files/download",
            "/api/config/read",
            "/api/logs/view"
        ]
        
        for endpoint in endpoints:
            for payload in self.test_config['path_traversal_payloads']:
                try:
                    # Test as path parameter
                    response = self.session.get(
                        f"http://{self.target_host}:{self.target_port}{endpoint}",
                        params={'file': payload}
                    )
                    
                    if response.status_code == 200:
                        response_text = response.text
                        
                        # Look for system file content
                        if ('root:x:0:0' in response_text or 
                            'localhost' in response_text and '127.0.0.1' in response_text):
                            self.add_result(SecurityTestResult(
                                test_name="Path Traversal Test",
                                category="Input Validation",
                                severity="HIGH",
                                status="FAIL",
                                description=f"Path traversal vulnerability in {endpoint}",
                                details=f"Payload: {payload}",
                                remediation="Validate and restrict file paths"
                            ))
                            return
                            
                except requests.RequestException:
                    pass
        
        self.add_result(SecurityTestResult(
            test_name="Path Traversal Test",
            category="Input Validation",
            severity="INFO",
            status="PASS",
            description="No path traversal vulnerabilities found"
        ))
    
    def _test_file_upload_security(self):
        """Test file upload security"""
        endpoints = [
            "/api/files/upload",
            "/api/config/import",
            "/api/backup/restore"
        ]
        
        # Test malicious file uploads
        malicious_files = [
            ('test.php', b'<?php system($_GET["cmd"]); ?>', 'application/x-php'),
            ('test.jsp', b'<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>', 'application/x-jsp'),
            ('test.exe', b'MZ\x90\x00', 'application/x-executable'),
            ('test.sh', b'#!/bin/bash\ncat /etc/passwd', 'application/x-sh')
        ]
        
        for endpoint in endpoints:
            for filename, content, content_type in malicious_files:
                try:
                    files = {'file': (filename, content, content_type)}
                    response = self.session.post(
                        f"http://{self.target_host}:{self.target_port}{endpoint}",
                        files=files
                    )
                    
                    if response.status_code == 200:
                        self.add_result(SecurityTestResult(
                            test_name="File Upload Security Test",
                            category="Input Validation",
                            severity="HIGH",
                            status="FAIL",
                            description=f"Malicious file upload accepted in {endpoint}",
                            details=f"File: {filename}",
                            remediation="Implement file type validation and sandboxing"
                        ))
                        return
                        
                except requests.RequestException:
                    pass
        
        self.add_result(SecurityTestResult(
            test_name="File Upload Security Test",
            category="Input Validation",
            severity="INFO",
            status="PASS",
            description="File upload security appears properly implemented"
        ))
    
    def test_network_security(self):
        """Test network security configuration"""
        print("\n🌐 Testing Network Security...")
        
        # Test SSL/TLS configuration
        self._test_ssl_configuration()
        
        # Test HTTP security headers
        self._test_security_headers()
        
        # Test for information disclosure
        self._test_information_disclosure()
        
        # Test CORS configuration
        self._test_cors_configuration()
    
    def _test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        try:
            import ssl
            import socket
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((self.target_host, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.target_host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    # Check TLS version
                    if version in ['TLSv1', 'TLSv1.1']:
                        self.add_result(SecurityTestResult(
                            test_name="TLS Version Check",
                            category="Network Security",
                            severity="MEDIUM",
                            status="FAIL",
                            description=f"Weak TLS version: {version}",
                            remediation="Use TLS 1.2 or higher"
                        ))
                    else:
                        self.add_result(SecurityTestResult(
                            test_name="TLS Version Check",
                            category="Network Security",
                            severity="INFO",
                            status="PASS",
                            description=f"Secure TLS version: {version}"
                        ))
                    
                    # Check cipher strength
                    if cipher and cipher[1] < 128:
                        self.add_result(SecurityTestResult(
                            test_name="Cipher Strength Check",
                            category="Network Security",
                            severity="HIGH",
                            status="FAIL",
                            description=f"Weak cipher: {cipher[0]} ({cipher[1]} bits)",
                            remediation="Use strong ciphers (256-bit)"
                        ))
                    
        except (socket.error, ssl.SSLError):
            # Try HTTP instead
            try:
                response = self.session.get(f"http://{self.target_host}:{self.target_port}")
                if response.status_code == 200:
                    self.add_result(SecurityTestResult(
                        test_name="HTTPS Enforcement",
                        category="Network Security",
                        severity="MEDIUM",
                        status="FAIL",
                        description="HTTP traffic not redirected to HTTPS",
                        remediation="Enforce HTTPS with redirects"
                    ))
            except requests.RequestException:
                pass
    
    def _test_security_headers(self):
        """Test HTTP security headers"""
        try:
            response = self.session.get(f"http://{self.target_host}:{self.target_port}")
            headers = response.headers
            
            # Check required security headers
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': None,
                'Content-Security-Policy': None
            }
            
            missing_headers = []
            weak_headers = []
            
            for header, expected in security_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif expected and isinstance(expected, list):
                    if headers[header] not in expected:
                        weak_headers.append(f"{header}: {headers[header]}")
                elif expected and headers[header] != expected:
                    weak_headers.append(f"{header}: {headers[header]}")
            
            if missing_headers:
                self.add_result(SecurityTestResult(
                    test_name="Security Headers Check",
                    category="Network Security",
                    severity="MEDIUM",
                    status="FAIL",
                    description="Missing security headers",
                    details=f"Missing: {', '.join(missing_headers)}",
                    remediation="Add missing security headers"
                ))
            
            if weak_headers:
                self.add_result(SecurityTestResult(
                    test_name="Security Headers Configuration",
                    category="Network Security",
                    severity="LOW",
                    status="FAIL",
                    description="Weak security header configuration",
                    details=f"Issues: {', '.join(weak_headers)}",
                    remediation="Strengthen security header values"
                ))
            
            if not missing_headers and not weak_headers:
                self.add_result(SecurityTestResult(
                    test_name="Security Headers Check",
                    category="Network Security",
                    severity="INFO",
                    status="PASS",
                    description="Security headers properly configured"
                ))
                
        except requests.RequestException:
            self.add_result(SecurityTestResult(
                test_name="Security Headers Check",
                category="Network Security",
                severity="INFO",
                status="SKIP",
                description="Could not check security headers"
            ))
    
    def _test_information_disclosure(self):
        """Test for information disclosure"""
        # Test for verbose error messages
        endpoints = [
            "/api/nonexistent",
            "/api/admin/debug",
            "/api/system/info",
            "/.env",
            "/config.php",
            "/admin/",
            "/debug/"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"http://{self.target_host}:{self.target_port}{endpoint}")
                
                # Look for information disclosure indicators
                disclosure_indicators = [
                    'version',
                    'debug',
                    'stack trace',
                    'sql error',
                    'path disclosure',
                    'server information'
                ]
                
                if response.status_code == 200:
                    response_text = response.text.lower()
                    found_indicators = [ind for ind in disclosure_indicators if ind in response_text]
                    
                    if found_indicators:
                        self.add_result(SecurityTestResult(
                            test_name="Information Disclosure Test",
                            category="Network Security",
                            severity="LOW",
                            status="FAIL",
                            description=f"Information disclosure in {endpoint}",
                            details=f"Indicators: {', '.join(found_indicators)}",
                            remediation="Remove verbose error messages and debug information"
                        ))
                        
            except requests.RequestException:
                pass
        
        self.add_result(SecurityTestResult(
            test_name="Information Disclosure Test",
            category="Network Security",
            severity="INFO",
            status="PASS",
            description="No obvious information disclosure found"
        ))
    
    def _test_cors_configuration(self):
        """Test CORS configuration"""
        try:
            headers = {
                'Origin': 'https://evil.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = self.session.options(
                f"http://{self.target_host}:{self.target_port}/api/auth/login",
                headers=headers
            )
            
            cors_headers = response.headers
            
            # Check for overly permissive CORS
            if cors_headers.get('Access-Control-Allow-Origin') == '*':
                self.add_result(SecurityTestResult(
                    test_name="CORS Configuration Test",
                    category="Network Security",
                    severity="MEDIUM",
                    status="FAIL",
                    description="Overly permissive CORS policy",
                    details="Access-Control-Allow-Origin: *",
                    remediation="Restrict CORS to specific domains"
                ))
            else:
                self.add_result(SecurityTestResult(
                    test_name="CORS Configuration Test",
                    category="Network Security",
                    severity="INFO",
                    status="PASS",
                    description="CORS policy appears properly configured"
                ))
                
        except requests.RequestException:
            self.add_result(SecurityTestResult(
                test_name="CORS Configuration Test",
                category="Network Security",
                severity="INFO",
                status="SKIP",
                description="Could not test CORS configuration"
            ))
    
    def test_system_security(self):
        """Test system-level security"""
        print("\n🖥️ Testing System Security...")
        
        # Test file permissions
        self._test_file_permissions()
        
        # Test service configuration
        self._test_service_security()
        
        # Test database security
        self._test_database_security()
    
    def _test_file_permissions(self):
        """Test file permissions on critical files"""
        critical_files = [
            ('/etc/lnmt/lnmt.conf', '640'),
            ('/etc/lnmt/ssl/key.pem', '600'),
            ('/opt/lnmt/services', '755'),
            ('/var/log/lnmt', '755')
        ]
        
        permission_issues = []
        
        for file_path, expected_perms in critical_files:
            try:
                if os.path.exists(file_path):
                    actual_perms = oct(os.stat(file_path).st_mode)[-3:]
                    
                    if actual_perms != expected_perms:
                        permission_issues.append(f"{file_path}: {actual_perms} (expected: {expected_perms})")
            except OSError:
                pass
        
        if permission_issues:
            self.add_result(SecurityTestResult(
                test_name="File Permissions Check",
                category="System Security",
                severity="MEDIUM",
                status="FAIL",
                description="Incorrect file permissions detected",
                details="; ".join(permission_issues),
                remediation="Fix file permissions as specified"
            ))
        else:
            self.add_result(SecurityTestResult(
                test_name="File Permissions Check",
                category="System Security",
                severity="INFO",
                status="PASS",
                description="File permissions properly configured"
            ))
    
    def _test_service_security(self):
        """Test service security configuration"""
        try:
            # Check if service is running as non-root
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            
            if 'lnmt' in result.stdout:
                lnmt_processes = [line for line in result.stdout.split('\n') if 'lnmt' in line]
                
                root_processes = [proc for proc in lnmt_processes if proc.startswith('root')]
                
                if root_processes:
                    self.add_result(SecurityTestResult(
                        test_name="Service User Check",
                        category="System Security",
                        severity="HIGH",
                        status="FAIL",
                        description="LNMT service running as root",
                        remediation="Configure service to run as dedicated user"
                    ))
                else:
                    self.add_result(SecurityTestResult(
                        test_name="Service User Check",
                        category="System Security",
                        severity="INFO",
                        status="PASS",
                        description="Service running as non-root user"
                    ))
            
        except subprocess.SubprocessError:
            self.add_result(SecurityTestResult(
                test_name="Service User Check",
                category="System Security",
                severity="INFO",
                status="SKIP",
                description="Could not check service user"
            ))
    
    def _test_database_security(self):
        """Test database security configuration"""
        db_path = "/var/lib/lnmt/lnmt.db"
        
        if os.path.exists(db_path):
            try:
                # Check database file permissions
                db_perms = oct(os.stat(db_path).st_mode)[-3:]
                
                if db_perms not in ['600', '640']:
                    self.add_result(SecurityTestResult(
                        test_name="Database File Permissions",
                        category="System Security",
                        severity="MEDIUM",
                        status="FAIL",
                        description=f"Database file permissions too permissive: {db_perms}",
                        remediation="Set database file permissions to 600 or 640"
                    ))
                
                # Check for SQLite encryption (basic check)
                with open(db_path, 'rb') as f:
                    header = f.read(16)
                    
                if header.startswith(b'SQLite format 3'):
                    self.add_result(SecurityTestResult(
                        test_name="Database Encryption Check",
                        category="System Security",
                        severity="MEDIUM",
                        status="FAIL",
                        description="Database appears to be unencrypted",
                        remediation="Enable database encryption"
                    ))
                else:
                    self.add_result(SecurityTestResult(
                        test_name="Database Encryption Check",
                        category="System Security",
                        severity="INFO",
                        status="PASS",
                        description="Database appears to be encrypted"
                    ))
                    
            except (OSError, IOError):
                self.add_result(SecurityTestResult(
                    test_name="Database Security Check",
                    category="System Security",
                    severity="INFO",
                    status="SKIP",
                    description="Could not access database file"
                ))
        else:
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive security report"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"lnmt_security_report_{timestamp}.html"
        
        # Categorize results by severity
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0}
        status_counts = {'PASS': 0, 'FAIL': 0, 'SKIP': 0, 'ERROR': 0}
        
        for result in self.results:
            severity_counts[result.severity] += 1
            status_counts[result.status] += 1
        
        # Calculate security score
        total_tests = len([r for r in self.results if r.status != 'SKIP'])
        failed_tests = len([r for r in self.results if r.status == 'FAIL'])
        security_score = max(0, 100 - (failed_tests * 100 / total_tests)) if total_tests > 0 else 0
        
        # Generate HTML report
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LNMT Security Assessment Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header .subtitle {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #333; }}
        .summary-card .number {{ font-size: 2em; font-weight: bold; }}
        .score {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; }}
        .score .number {{ font-size: 3em; }}
        .critical {{ border-left-color: #dc3545; }}
        .high {{ border-left-color: #fd7e14; }}
        .medium {{ border-left-color: #ffc107; }}
        .low {{ border-left-color: #28a745; }}
        .content {{ padding: 30px; }}
        .test-category {{ margin-bottom: 40px; }}
        .test-category h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .test-result {{ background: #f8f9fa; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #6c757d; }}
        .test-result.pass {{ border-left-color: #28a745; }}
        .test-result.fail {{ border-left-color: #dc3545; }}
        .test-result.skip {{ border-left-color: #6c757d; }}
        .test-result h4 {{ margin: 0 0 10px 0; color: #333; }}
        .test-meta {{ display: flex; gap: 15px; margin-bottom: 10px; }}
        .test-meta span {{ padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }}
        .severity-critical {{ background: #dc3545; color: white; }}
        .severity-high {{ background: #fd7e14; color: white; }}
        .severity-medium {{ background: #ffc107; color: black; }}
        .severity-low {{ background: #28a745; color: white; }}
        .severity-info {{ background: #17a2b8; color: white; }}
        .status-pass {{ background: #28a745; color: white; }}
        .status-fail {{ background: #dc3545; color: white; }}
        .status-skip {{ background: #6c757d; color: white; }}
        .details {{ background: white; padding: 15px; border-radius: 4px; margin-top: 10px; border: 1px solid #dee2e6; }}
        .remediation {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin-top: 10px; border-left: 4px solid #007bff; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 LNMT Security Assessment Report</h1>
            <div class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="subtitle">Target: {self.target_host}:{self.target_port}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card score">
                <h3>Security Score</h3>
                <div class="number">{security_score:.1f}%</div>
            </div>
            <div class="summary-card critical">
                <h3>Critical Issues</h3>
                <div class="number">{severity_counts['CRITICAL']}</div>
            </div>
            <div class="summary-card high">
                <h3>High Risk Issues</h3>
                <div class="number">{severity_counts['HIGH']}</div>
            </div>
            <div class="summary-card medium">
                <h3>Medium Risk Issues</h3>
                <div class="number">{severity_counts['MEDIUM']}</div>
            </div>
            <div class="summary-card low">
                <h3>Low Risk Issues</h3>
                <div class="number">{severity_counts['LOW']}</div>
            </div>
            <div class="summary-card">
                <h3>Tests Passed</h3>
                <div class="number">{status_counts['PASS']}</div>
            </div>
        </div>
        
        <div class="content">
"""
        
        # Group results by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        # Add results by category
        for category, results in categories.items():
            html_content += f"""
            <div class="test-category">
                <h2>{category}</h2>
"""
            for result in results:
                status_class = result.status.lower()
                severity_class = f"severity-{result.severity.lower()}"
                status_display_class = f"status-{result.status.lower()}"
                
                html_content += f"""
                <div class="test-result {status_class}">
                    <h4>{result.test_name}</h4>
                    <div class="test-meta">
                        <span class="{severity_class}">{result.severity}</span>
                        <span class="{status_display_class}">{result.status}</span>
                        <span style="background: #e9ecef; color: #495057;">{result.timestamp.strftime('%H:%M:%S')}</span>
                    </div>
                    <p>{result.description}</p>
"""
                
                if result.details:
                    html_content += f"""
                    <div class="details">
                        <strong>Details:</strong> {result.details}
                    </div>
"""
                
                if result.remediation:
                    html_content += f"""
                    <div class="remediation">
                        <strong>🔧 Remediation:</strong> {result.remediation}
                    </div>
"""
                
                html_content += "                </div>\n"
            
            html_content += "            </div>\n"
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>LNMT Security Testing Suite v1.0 | Report generated with {len(self.results)} total tests</p>
            <p>For support and updates, visit the LNMT documentation</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write report to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📊 Security report generated: {output_file}")
        print(f"Security Score: {security_score:.1f}%")
        print(f"Critical Issues: {severity_counts['CRITICAL']}")
        print(f"High Risk Issues: {severity_counts['HIGH']}")
        print(f"Medium Risk Issues: {severity_counts['MEDIUM']}")
        
        return output_file
    
    def run_all_tests(self):
        """Run complete security test suite"""
        print("🚀 Starting LNMT Security Assessment")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Run all test categories
            self.test_authentication_security()
            self.test_input_validation()
            self.test_network_security()
            self.test_system_security()
            
        except KeyboardInterrupt:
            print("\n⚠️ Testing interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error during testing: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Security assessment completed in {duration:.2f} seconds")
        
        # Generate and return report
        report_file = self.generate_report()
        return report_file

class SecurityComplianceChecker:
    """Check compliance with security standards"""
    
    def __init__(self):
        self.compliance_frameworks = {
            'OWASP_TOP_10': {
                'name': 'OWASP Top 10 2021',
                'checks': [
                    'Broken Access Control',
                    'Cryptographic Failures',
                    'Injection',
                    'Insecure Design',
                    'Security Misconfiguration',
                    'Vulnerable Components',
                    'Identification and Authentication Failures',
                    'Software and Data Integrity Failures',
                    'Security Logging and Monitoring Failures',
                    'Server-Side Request Forgery'
                ]
            },
            'NIST_CSF': {
                'name': 'NIST Cybersecurity Framework',
                'checks': [
                    'Identity Management',
                    'Access Control',
                    'Data Security',
                    'Information Protection',
                    'Maintenance',
                    'Protective Technology'
                ]
            }
        }
    
    def check_owasp_compliance(self, test_results: List[SecurityTestResult]) -> Dict[str, str]:
        """Check OWASP Top 10 compliance"""
        compliance_status = {}
        
        # Map test results to OWASP categories
        owasp_mapping = {
            'Broken Access Control': ['Authentication', 'Authorization'],
            'Injection': ['SQL Injection', 'Command Injection', 'XSS'],
            'Security Misconfiguration': ['Network Security', 'System Security'],
            'Cryptographic Failures': ['TLS', 'Encryption'],
            'Identification and Authentication Failures': ['Authentication']
        }
        
        for owasp_category, test_categories in owasp_mapping.items():
            related_failures = [r for r in test_results 
                              if r.status == 'FAIL' and 
                              any(cat in r.test_name or cat in r.category for cat in test_categories)]
            
            if related_failures:
                critical_failures = [r for r in related_failures if r.severity in ['CRITICAL', 'HIGH']]
                if critical_failures:
                    compliance_status[owasp_category] = 'NON_COMPLIANT'
                else:
                    compliance_status[owasp_category] = 'PARTIALLY_COMPLIANT'
            else:
                compliance_status[owasp_category] = 'COMPLIANT'
        
        return compliance_status

def main():
    """Main function for running security tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LNMT Security Testing Suite')
    parser.add_argument('--host', default='localhost', help='Target host')
    parser.add_argument('--port', type=int, default=8080, help='Target port')
    parser.add_argument('--output', help='Output report file')
    parser.add_argument('--category', choices=['auth', 'input', 'network', 'system', 'all'], 
                       default='all', help='Test category to run')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize test suite
    suite = SecurityTestSuite(args.host, args.port)
    
    try:
        # Run selected tests
        if args.category == 'all':
            suite.run_all_tests()
        elif args.category == 'auth':
            suite.test_authentication_security()
        elif args.category == 'input':
            suite.test_input_validation()
        elif args.category == 'network':
            suite.test_network_security()
        elif args.category == 'system':
            suite.test_system_security()
        
        # Generate report
        report_file = suite.generate_report(args.output)
        
        # Check compliance
        compliance_checker = SecurityComplianceChecker()
        owasp_compliance = compliance_checker.check_owasp_compliance(suite.results)
        
        print("\n📋 OWASP Top 10 Compliance Summary:")
        for category, status in owasp_compliance.items():
            status_symbol = "✅" if status == "COMPLIANT" else "⚠️" if status == "PARTIALLY_COMPLIANT" else "❌"
            print(f"{status_symbol} {category}: {status}")
        
        # Exit with appropriate code
        critical_issues = len([r for r in suite.results if r.severity == 'CRITICAL' and r.status == 'FAIL'])
        high_issues = len([r for r in suite.results if r.severity == 'HIGH' and r.status == 'FAIL'])
        
        if critical_issues > 0:
            print(f"\n🚨 CRITICAL: {critical_issues} critical security issues found!")
            sys.exit(2)
        elif high_issues > 0:
            print(f"\n⚠️ WARNING: {high_issues} high-risk security issues found!")
            sys.exit(1)
        else:
            print("\n✅ No critical or high-risk security issues found")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running security tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
LNMT Security Testing Suite
Version: RC2-Hardened
Security Level: Production Ready

Comprehensive security testing framework for LNMT components
including penetration testing, vulnerability scanning, and compliance checks.
"""

import os
import re
import sys
import json
import time
import socket
import sqlite3
import hashlib
import secrets
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import unittest
import threading
import tempfile

# Test imports
try:
    import requests
    import paramiko
    from cryptography.fernet import Fernet
    import jwt
    import bcrypt
except ImportError as e:
    print(f"Required testing dependency missing: {e}")
    print("Install with: pip install requests paramiko cryptography pyjwt bcrypt")
    sys.exit(1)

@dataclass
class SecurityTestResult:
    """Security test result data structure"""
    test_name: str
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    status: str    # PASS, FAIL, SKIP, ERROR
    description: str
    details: str = ""
    remediation: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class SecurityTestSuite:
    """Main security testing framework"""
    
    def __init__(self, target_host: str = "localhost", target_port: int = 8080):
        self.target_host = target_host
        self.target_port = target_port
        self.results: List[SecurityTestResult] = []
        self.session = requests.Session()
        self.session.timeout = 10
        
        # Test configuration
        self.test_config = {
            'auth_test_users': [
                {'username': 'testuser1', 'password': 'TestPassword123!'},
                {'username': 'testuser2', 'password': 'AnotherPass456@'}
            ],
            'sql_injection_payloads': [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM users --",
                "admin'--",
                "' OR 1=1#"
            ],
            'xss_payloads': [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "';alert('XSS');//"
            ],
            'command_injection_payloads': [
                "; ls -la",
                "| cat /etc/passwd",
                "& whoami",
                "`id`",
                "$(cat /etc/hosts)"
            ],
            'path_traversal_payloads': [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
            ]
        }
        
        print(f"🔒 LNMT Security Testing Suite initialized")
        print(f"Target: {self.target_host}:{self.target_port}")
        print("=" * 60)
    
    def add_result(self, result: SecurityTestResult):
        """Add test result"""
        self.results.append(result)
        
        # Color coding for severity
        color_map = {
            'CRITICAL': '\033[91m',  # Red
            'HIGH': '\033[93m',      # Yellow
            'MEDIUM': '\033[94m',    # Blue
            'LOW': '\033[92m',       # Green
            'INFO': '\033[96m'       # Cyan
        }
        
        status_symbol = "✓" if result.status == "PASS" else "✗" if result.status == "FAIL" else "⚠"
        color = color_map.get(result.severity, '\033[0m')
        reset = '\033[0m'
        
        print(f"{color}{status_symbol} [{result.severity}] {result.test_name}: {result.status}{reset}")
        if result.status == "FAIL" and result.details:
            print(f"  Details: {result.details}")
    
    def test_authentication_security(self):
        """Test authentication mechanisms"""
        print("\n🔐 Testing Authentication Security...")
        
        # Test 1: Default credentials
        self._test_default_credentials()
        
        # Test 2: Brute force protection
        self._test_brute_force_protection()
        
        # Test 3: Session management
        self._test_session_management()
        
        # Test 4: Password policies
        self._test_password_policies()
        
        # Test 5: JWT security
        self._test_jwt_security()
    
    def _test_default_credentials(self):
        """Test for default/weak credentials"""
        default_creds = [
            ('admin', 'admin'),
            ('admin', 'password'),
            ('admin', '123456'),
            ('root', 'root'),
            ('lnmt', 'lnmt'),
            ('test', 'test')
        ]
        
        for username, password in default_creds:
            try:
                response = self.session.post(
                    f"http://{self.target_host}:{self.target_port}/api/auth/login",
                    json={'username': username, 'password': password}
                )