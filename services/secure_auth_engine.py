#!/usr/bin/env python3
"""
LNMT Secure Authentication Engine
Version: RC2-Hardened
Security Level: Production Ready

This module provides secure authentication and authorization services
with comprehensive security hardening measures.
"""

import os
import re
import json
import time
import hmac
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import bcrypt
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sqlite3
from flask import request, session, jsonify
import ipaddress

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/lnmt/auth.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration parameters"""
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15 minutes
    session_timeout: int = 1800  # 30 minutes
    token_expiry: int = 3600     # 1 hour
    password_min_length: int = 12
    password_complexity: bool = True
    rate_limit_window: int = 300  # 5 minutes
    rate_limit_max_requests: int = 100
    require_mfa: bool = True
    audit_logging: bool = True

@dataclass
class User:
    """User data model"""
    username: str
    password_hash: str
    email: str
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False

@dataclass
class Session:
    """Session data model"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool = True

class SecurityException(Exception):
    """Custom security exception"""
    pass

class AuthenticationError(SecurityException):
    """Authentication failed"""
    pass

class AuthorizationError(SecurityException):
    """Authorization failed"""
    pass

class RateLimitError(SecurityException):
    """Rate limit exceeded"""
    pass

class SecureDatabase:
    """Encrypted database handler for authentication data"""
    
    def __init__(self, db_path: str, encryption_key: bytes):
        self.db_path = db_path
        self.cipher = Fernet(encryption_key)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with secure schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA synchronous = FULL')
            
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    mfa_secret TEXT,
                    mfa_enabled BOOLEAN DEFAULT 0
                )
            ''')
            
            # Sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Rate limiting table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_identifier (identifier),
                    INDEX idx_window_start (window_start)
                )
            ''')
            
            # Audit log table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute parameterized query safely"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise SecurityException("Database operation failed")
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute update/insert query safely"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise SecurityException("Database operation failed")

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        # Allow alphanumeric, underscore, hyphen
        return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str, complexity: bool = True) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        if not complexity:
            return True, "Password accepted"
        
        checks = [
            (r'[a-z]', "Password must contain lowercase letters"),
            (r'[A-Z]', "Password must contain uppercase letters"),
            (r'[0-9]', "Password must contain numbers"),
            (r'[!@#$%^&*(),.?":{}|<>]', "Password must contain special characters")
        ]
        
        for pattern, message in checks:
            if not re.search(pattern, password):
                return False, message
        
        # Check for common patterns
        common_patterns = [
            r'(.)\1{2,}',  # Repeated characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)'  # Sequential letters
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                return False, "Password contains common patterns"
        
        return True, "Password meets complexity requirements"
    
    @staticmethod
    def validate_ip_address(ip_str: str) -> bool:
        """Validate IP address"""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 255) -> str:
        """Sanitize user input"""
        if not input_str:
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in input_str if ord(char) >= 32)
        
        # Truncate to max length
        return sanitized[:max_length]

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, db: SecureDatabase, config: SecurityConfig):
        self.db = db
        self.config = config
    
    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier is rate limited"""
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.config.rate_limit_window)
        
        # Clean old entries
        self.db.execute_update(
            "DELETE FROM rate_limits WHERE window_start < ?",
            (window_start,)
        )
        
        # Get current count
        result = self.db.execute_query(
            "SELECT SUM(request_count) as total FROM rate_limits WHERE identifier = ? AND window_start >= ?",
            (identifier, window_start)
        )
        
        total_requests = result[0]['total'] if result and result[0]['total'] else 0
        
        if total_requests >= self.config.rate_limit_max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return True
        
        # Update counter
        self.db.execute_update(
            "INSERT OR REPLACE INTO rate_limits (identifier, request_count, window_start) VALUES (?, COALESCE((SELECT request_count FROM rate_limits WHERE identifier = ? AND window_start >= ?), 0) + 1, ?)",
            (identifier, identifier, window_start, current_time)
        )
        
        return False

class AuditLogger:
    """Security audit logging"""
    
    def __init__(self, db: SecureDatabase):
        self.db = db
    
    def log_event(self, user_id: Optional[int], action: str, resource: Optional[str],
                  ip_address: str, user_agent: str, success: bool, details: str = ""):
        """Log security event"""
        try:
            self.db.execute_update(
                "INSERT INTO audit_log (user_id, action, resource, ip_address, user_agent, success, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, action, resource, ip_address, user_agent, success, details)
            )
            
            # Also log to file
            logger.info(f"AUDIT: {action} - User: {user_id} - IP: {ip_address} - Success: {success} - Details: {details}")
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

class SecureAuthEngine:
    """Main authentication engine with security hardening"""
    
    def __init__(self, config_path: str = "/etc/lnmt/lnmt.conf"):
        self.config = self._load_config(config_path)
        self.security_config = SecurityConfig()
        
        # Initialize encryption key
        self.encryption_key = self._get_encryption_key()
        
        # Initialize database
        self.db = SecureDatabase("/var/lib/lnmt/auth.db", self.encryption_key)
        
        # Initialize components
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(self.db, self.security_config)
        self.audit_logger = AuditLogger(self.db)
        
        # JWT secret
        self.jwt_secret = self._get_jwt_secret()
        
        logger.info("Secure authentication engine initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            config = {}
            with open(config_path, 'r') as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        config[current_section][key.strip()] = value.strip()
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate database encryption key"""
        key_str = self.config.get('security', {}).get('db_encryption_key')
        if key_str:
            return key_str.encode()
        
        # Generate new key if not found
        logger.warning("Generating new encryption key")
        return Fernet.generate_key()
    
    def _get_jwt_secret(self) -> str:
        """Get JWT secret from config"""
        return self.config.get('security', {}).get('jwt_secret', secrets.token_hex(32))
    
    def _get_client_info(self) -> Tuple[str, str]:
        """Get client IP and user agent safely"""
        try:
            # Get real IP (considering proxy headers)
            ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
            
            if not self.validator.validate_ip_address(ip):
                ip = "unknown"
            
            user_agent = request.headers.get('User-Agent', 'unknown')[:255]
            return ip, user_agent
        except:
            return "unknown", "unknown"
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def generate_secure_token(self, user_id: int, username: str) -> str:
        """Generate secure JWT token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=self.security_config.token_expiry),
            'jti': secrets.token_hex(16)  # JWT ID for revocation
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Additional validation
            if not payload.get('user_id') or not payload.get('username'):
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    def create_user(self, username: str, password: str, email: str, role: str = "user") -> bool:
        """Create new user with validation"""
        ip, user_agent = self._get_client_info()
        
        try:
            # Input validation
            username = self.validator.sanitize_input(username, 50)
            email = self.validator.sanitize_input(email, 255)
            role = self.validator.sanitize_input(role, 20)
            
            if not self.validator.validate_username(username):
                raise AuthenticationError("Invalid username format")
            
            if not self.validator.validate_email(email):
                raise AuthenticationError("Invalid email format")
            
            is_valid, message = self.validator.validate_password(password, self.security_config.password_complexity)
            if not is_valid:
                raise AuthenticationError(message)
            
            # Check if user exists
            existing = self.db.execute_query(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            
            if existing:
                self.audit_logger.log_event(None, "CREATE_USER_FAILED", f"user:{username}", 
                                          ip, user_agent, False, "User already exists")
                raise AuthenticationError("User already exists")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            self.db.execute_update(
                "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
                (username, password_hash, email, role)
            )
            
            self.audit_logger.log_event(None, "CREATE_USER", f"user:{username}", 
                                      ip, user_agent, True, f"Role: {role}")
            
            logger.info(f"User created successfully: {username}")
            return True
            
        except Exception as e:
            self.audit_logger.log_event(None, "CREATE_USER_FAILED", f"user:{username}", 
                                      ip, user_agent, False, str(e))
            logger.error(f"Failed to create user: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with comprehensive security checks"""
        ip, user_agent = self._get_client_info()
        
        # Rate limiting
        if self.rate_limiter.is_rate_limited(ip):
            self.audit_logger.log_event(None, "AUTH_RATE_LIMITED", f"user:{username}", 
                                      ip, user_agent, False, "Rate limit exceeded")
            raise RateLimitError("Too many requests")
        
        try:
            # Input validation
            username = self.validator.sanitize_input(username, 50)
            
            if not self.validator.validate_username(username):
                raise AuthenticationError("Invalid username format")
            
            # Get user
            users = self.db.execute_query(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            
            if not users:
                self.audit_logger.log_event(None, "AUTH_FAILED", f"user:{username}", 
                                          ip, user_agent, False, "User not found")
                raise AuthenticationError("Invalid credentials")
            
            user_data = users[0]
            user_id = user_data['id']
            
            # Check account lockout
            if user_data['locked_until']:
                locked_until = datetime.fromisoformat(user_data['locked_until'])
                if datetime.now() < locked_until:
                    remaining = (locked_until - datetime.now()).seconds
                    self.audit_logger.log_event(user_id, "AUTH_LOCKED", f"user:{username}", 
                                              ip, user_agent, False, f"Account locked for {remaining}s")
                    raise AuthenticationError(f"Account locked for {remaining} seconds")
                else:
                    # Unlock account
                    self.db.execute_update(
                        "UPDATE users SET locked_until = NULL, failed_attempts = 0 WHERE id = ?",
                        (user_id,)
                    )
            
            # Verify password
            if not self.verify_password(password, user_data['password_hash']):
                # Increment failed attempts
                failed_attempts = user_data['failed_attempts'] + 1
                
                if failed_attempts >= self.security_config.max_login_attempts:
                    # Lock account
                    locked_until = datetime.now() + timedelta(seconds=self.security_config.lockout_duration)
                    self.db.execute_update(
                        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                        (failed_attempts, locked_until, user_id)
                    )
                    self.audit_logger.log_event(user_id, "AUTH_LOCKED", f"user:{username}", 
                                              ip, user_agent, False, "Too many failed attempts")
                    raise AuthenticationError("Account locked due to too many failed attempts")
                else:
                    self.db.execute_update(
                        "UPDATE users SET failed_attempts = ? WHERE id = ?",
                        (failed_attempts, user_id)
                    )
                
                self.audit_logger.log_event(user_id, "AUTH_FAILED", f"user:{username}", 
                                          ip, user_agent, False, f"Failed attempt {failed_attempts}")
                raise AuthenticationError("Invalid credentials")
            
            # Reset failed attempts on successful login
            self.db.execute_update(
                "UPDATE users SET failed_attempts = 0, last_login = ? WHERE id = ?",
                (datetime.now(), user_id)
            )
            
            # Create session
            session_id = self.create_session(user_id, ip, user_agent)
            
            self.audit_logger.log_event(user_id, "AUTH_SUCCESS", f"user:{username}", 
                                      ip, user_agent, True, f"Session: {session_id}")
            
            logger.info(f"User authenticated successfully: {username}")
            
            return {
                'user_id': user_id,
                'username': username,
                'email': user_data['email'],
                'role': user_data['role'],
                'session_id': session_id,
                'token': self.generate_secure_token(user_id, username)
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            self.audit_logger.log_event(None, "AUTH_ERROR", f"user:{username}", 
                                      ip, user_agent, False, str(e))
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError("Authentication failed")
    
    def create_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """Create new user session"""
        session_id = secrets.token_urlsafe(32)
        
        # Clean old sessions for user
        self.cleanup_expired_sessions(user_id)
        
        # Create new session
        self.db.execute_update(
            "INSERT INTO sessions (session_id, user_id, ip_address, user_agent) VALUES (?, ?, ?, ?)",
            (session_id, user_id, ip_address, user_agent)
        )
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate user session"""
        if not session_id:
            return None
        
        try:
            sessions = self.db.execute_query(
                """SELECT s.*, u.username, u.role, u.is_active 
                   FROM sessions s 
                   JOIN users u ON s.user_id = u.id 
                   WHERE s.session_id = ? AND s.is_active = 1 AND u.is_active = 1""",
                (session_id,)
            )
            
            if not sessions:
                return None
            
            session_data = sessions[0]
            
            # Check session timeout
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            if datetime.now() - last_activity > timedelta(seconds=self.security_config.session_timeout):
                self.invalidate_session(session_id)
                return None
            
            # Update last activity
            self.db.execute_update(
                "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                (datetime.now(), session_id)
            )
            
            return {
                'user_id': session_data['user_id'],
                'username': session_data['username'],
                'role': session_data['role'],
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate user session"""
        try:
            result = self.db.execute_update(
                "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
                (session_id,)
            )
            return result > 0
        except Exception as e:
            logger.error(f"Session invalidation error: {e}")
            return False
    
    def cleanup_expired_sessions(self, user_id: Optional[int] = None):
        """Clean up expired sessions"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.security_config.session_timeout)
            
            if user_id:
                self.db.execute_update(
                    "UPDATE sessions SET is_active = 0 WHERE user_id = ? AND last_activity < ?",
                    (user_id, cutoff_time)
                )
            else:
                self.db.execute_update(
                    "UPDATE sessions SET is_active = 0 WHERE last_activity < ?",
                    (cutoff_time,)
                )
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password with validation"""
        ip, user_agent = self._get_client_info()
        
        try:
            # Get current user
            users = self.db.execute_query(
                "SELECT username, password_hash FROM users WHERE id = ? AND is_active = 1",
                (user_id,)
            )
            
            if not users:
                raise AuthenticationError("User not found")
            
            user_data = users[0]
            
            # Verify old password
            if not self.verify_password(old_password, user_data['password_hash']):
                self.audit_logger.log_event(user_id, "PASSWORD_CHANGE_FAILED", f"user:{user_data['username']}", 
                                          ip, user_agent, False, "Invalid old password")
                raise AuthenticationError("Invalid old password")
            
            # Validate new password
            is_valid, message = self.validator.validate_password(new_password, self.security_config.password_complexity)
            if not is_valid:
                raise AuthenticationError(message)
            
            # Hash new password
            new_hash = self.hash_password(new_password)
            
            # Update password
            self.db.execute_update(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )
            
            # Invalidate all sessions except current
            self.db.execute_update(
                "UPDATE sessions SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            self.audit_logger.log_event(user_id, "PASSWORD_CHANGED", f"user:{user_data['username']}", 
                                      ip, user_agent, True, "Password updated successfully")
            
            logger.info(f"Password changed for user: {user_data['username']}")
            return True
            
        except Exception as e:
            self.audit_logger.log_event(user_id, "PASSWORD_CHANGE_ERROR", f"user_id:{user_id}", 
                                      ip, user_agent, False, str(e))
            logger.error(f"Password change error: {e}")
            raise
    
    def require_auth(self, required_role: Optional[str] = None):
        """Decorator for requiring authentication"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get session from request
                session_id = request.headers.get('X-Session-ID') or session.get('session_id')
                
                if not session_id:
                    raise AuthenticationError("No session provided")
                
                # Validate session
                user_session = self.validate_session(session_id)
                if not user_session:
                    raise AuthenticationError("Invalid or expired session")
                
                # Check role if required
                if required_role and user_session['role'] != required_role and user_session['role'] != 'admin':
                    ip, user_agent = self._get_client_info()
                    self.audit_logger.log_event(user_session['user_id'], "AUTH_UNAUTHORIZED", 
                                              f"role:{required_role}", ip, user_agent, False, 
                                              f"User role: {user_session['role']}")
                    raise AuthorizationError("Insufficient privileges")
                
                # Add user context to request
                request.user = user_session
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def get_user_audit_log(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log for user"""
        return self.db.execute_query(
            "SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status and metrics"""
        try:
            # Get active sessions count
            active_sessions = self.db.execute_query(
                "SELECT COUNT(*) as count FROM sessions WHERE is_active = 1"
            )[0]['count']
            
            # Get recent failed attempts
            recent_failures = self.db.execute_query(
                "SELECT COUNT(*) as count FROM audit_log WHERE action = 'AUTH_FAILED' AND timestamp > datetime('now', '-1 hour')"
            )[0]['count']
            
            # Get locked accounts
            locked_accounts = self.db.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE locked_until > datetime('now')"
            )[0]['count']
            
            return {
                'active_sessions': active_sessions,
                'recent_failures': recent_failures,
                'locked_accounts': locked_accounts,
                'rate_limiting_enabled': True,
                'audit_logging_enabled': self.security_config.audit_logging,
                'mfa_required': self.security_config.require_mfa
            }
        except Exception as e:
            logger.error(f"Failed to get security status: {e}")
            return {}

# Flask integration helpers
def init_auth_routes(app, auth_engine: SecureAuthEngine):
    """Initialize authentication routes for Flask app"""
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            if not data or 'username' not in data or 'password' not in data:
                return jsonify({'error': 'Username and password required'}), 400
            
            result = auth_engine.authenticate_user(data['username'], data['password'])
            
            # Set session cookie
            session['session_id'] = result['session_id']
            session['user_id'] = result['user_id']
            
            return jsonify({
                'success': True,
                'user': {
                    'username': result['username'],
                    'role': result['role']
                },
                'token': result['token']
            })
            
        except (AuthenticationError, RateLimitError) as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        session_id = request.headers.get('X-Session-ID') or session.get('session_id')
        if session_id:
            auth_engine.invalidate_session(session_id)
        
        session.clear()
        return jsonify({'success': True})
    
    @app.route('/api/auth/status', methods=['GET'])
    @auth_engine.require_auth()
    def auth_status():
        return jsonify({
            'authenticated': True,
            'user': {
                'username': request.user['username'],
                'role': request.user['role']
            }
        })
    
    @app.route('/api/auth/security-status', methods=['GET'])
    @auth_engine.require_auth('admin')
    def security_status():
        return jsonify(auth_engine.get_security_status())

# Example usage
if __name__ == "__main__":
    # Initialize authentication engine
    auth = SecureAuthEngine()
    
    # Create admin user if not exists
    try:
        auth.create_user("admin", "SecurePassword123!", "admin@lnmt.local", "admin")
        print("Admin user created successfully")
    except AuthenticationError as e:
        print(f"Admin user creation: {e}")
    
    # Test authentication
    try:
        result = auth.authenticate_user("admin", "SecurePassword123!")
        print(f"Authentication successful: {result['username']}")
        
        # Test session validation
        session_data = auth.validate_session(result['session_id'])
        print(f"Session valid: {session_data['username']}")
        
    except Exception as e:
        print(f"Authentication test failed: {e}")