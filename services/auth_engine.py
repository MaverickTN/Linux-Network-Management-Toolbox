"""
LNMT Authentication Engine
==========================

Comprehensive authentication system with:
- API token management (up to 5 per user)
- Role-based access control (RBAC)
- 2FA with TOTP (Google/Microsoft Authenticator)
- Audit logging
- Session management

Security Features:
- PBKDF2 password hashing with salt
- Time-based one-time passwords (RFC 6238)
- Rate limiting for auth attempts
- Secure token generation and validation
- Comprehensive audit trail
"""

import sqlite3
import secrets
import hashlib
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pyotp
import qrcode
from io import BytesIO
import base64

# Configure logging for security events
logging.basicConfig(level=logging.INFO)
auth_logger = logging.getLogger('lnmt.auth')

class UserRole(Enum):
    """User role definitions with hierarchical permissions"""
    ADMIN = "admin"          # Full system access
    MANAGER = "manager"      # User management, read/write operations
    OPERATOR = "operator"    # Read/write operations, no user management
    VIEWER = "viewer"        # Read-only access
    GUEST = "guest"         # Limited read access

class Permission(Enum):
    """Granular permission system"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Token management
    TOKEN_CREATE = "token:create"
    TOKEN_REVOKE = "token:revoke"
    TOKEN_LIST = "token:list"
    
    # System operations
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"
    
    # Dashboard access
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_ADMIN = "dashboard:admin"

# Role-permission mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p for p in Permission],  # All permissions
    UserRole.MANAGER: [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
        Permission.TOKEN_CREATE, Permission.TOKEN_REVOKE, Permission.TOKEN_LIST,
        Permission.SYSTEM_READ, Permission.SYSTEM_WRITE,
        Permission.DASHBOARD_VIEW, Permission.DASHBOARD_ADMIN
    ],
    UserRole.OPERATOR: [
        Permission.USER_READ, Permission.TOKEN_CREATE, Permission.TOKEN_REVOKE,
        Permission.TOKEN_LIST, Permission.SYSTEM_READ, Permission.SYSTEM_WRITE,
        Permission.DASHBOARD_VIEW
    ],
    UserRole.VIEWER: [
        Permission.USER_READ, Permission.SYSTEM_READ, Permission.DASHBOARD_VIEW
    ],
    UserRole.GUEST: [
        Permission.SYSTEM_READ, Permission.DASHBOARD_VIEW
    ]
}

@dataclass
class User:
    """User data model"""
    id: Optional[int]
    username: str
    email: str
    password_hash: str
    salt: str
    role: UserRole
    totp_secret: Optional[str]
    totp_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    failed_attempts: int
    locked_until: Optional[datetime]

@dataclass
class APIToken:
    """API token data model"""
    id: Optional[int]
    user_id: int
    token_hash: str
    name: str
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool

@dataclass
class AuthEvent:
    """Authentication event for audit logging"""
    id: Optional[int]
    user_id: Optional[int]
    event_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    details: Dict[str, Any]
    timestamp: datetime

class AuthenticationError(Exception):
    """Base authentication exception"""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Invalid username/password"""
    pass

class AccountLockedError(AuthenticationError):
    """Account is temporarily locked"""
    pass

class TwoFactorRequiredError(AuthenticationError):
    """2FA token required"""
    pass

class InvalidTwoFactorError(AuthenticationError):
    """Invalid 2FA token"""
    pass

class PermissionDeniedError(AuthenticationError):
    """Insufficient permissions"""
    pass

class TokenLimitExceededError(AuthenticationError):
    """User has reached token limit"""
    pass

class AuthEngine:
    """
    Core authentication engine with comprehensive security features
    
    Features:
    - Password-based authentication with PBKDF2
    - API token management (max 5 per user)
    - TOTP-based 2FA
    - Role-based access control
    - Rate limiting and account lockout
    - Comprehensive audit logging
    """
    
    MAX_TOKENS_PER_USER = 5
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    TOKEN_VALIDITY_DAYS = 30
    
    def __init__(self, db_path: str = "lnmt.db"):
        """Initialize authentication engine with database"""
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables for authentication"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Users table
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    totp_secret TEXT,
                    totp_enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                );
                
                -- API tokens table
                CREATE TABLE IF NOT EXISTS api_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
                
                -- Authentication events table
                CREATE TABLE IF NOT EXISTS auth_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON api_tokens(user_id);
                CREATE INDEX IF NOT EXISTS idx_tokens_hash ON api_tokens(token_hash);
                CREATE INDEX IF NOT EXISTS idx_auth_events_user_id ON auth_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_auth_events_timestamp ON auth_events(timestamp);
            """)
            
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        Hash password using PBKDF2 with SHA-256
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with 100,000 iterations for security
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, password_hash)
    
    def _generate_token(self) -> str:
        """Generate cryptographically secure API token"""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash API token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _log_auth_event(self, event_type: str, user_id: int = None, 
                       success: bool = True, details: Dict = None,
                       ip_address: str = None, user_agent: str = None):
        """Log authentication event for audit trail"""
        event = AuthEvent(
            id=None,
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details or {},
            timestamp=datetime.now()
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO auth_events 
                (user_id, event_type, ip_address, user_agent, success, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event.user_id, event.event_type, event.ip_address,
                event.user_agent, event.success, json.dumps(event.details),
                event.timestamp
            ))
        
        # Also log to application logger
        level = logging.INFO if success else logging.WARNING
        auth_logger.log(level, f"Auth event: {event_type} - User: {user_id} - Success: {success}")
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = UserRole.VIEWER) -> User:
        """
        Create new user account
        
        Args:
            username: Unique username
            email: User email address
            password: Plain text password (will be hashed)
            role: User role (default: VIEWER)
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If user already exists
        """
        password_hash, salt = self._hash_password(password)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO users 
                    (username, email, password_hash, salt, role, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    username, email, password_hash, salt, role.value,
                    datetime.now(), True
                ))
                
                user_id = cursor.lastrowid
                
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                raise ValueError(f"Username '{username}' already exists")
            elif "email" in str(e):
                raise ValueError(f"Email '{email}' already exists")
            else:
                raise ValueError("User creation failed")
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            role=role,
            totp_secret=None,
            totp_enabled=False,
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            failed_attempts=0,
            locked_until=None
        )
        
        self._log_auth_event("user_created", user_id, details={"username": username, "role": role.value})
        return user
    
    def authenticate_user(self, username: str, password: str, 
                         totp_code: str = None, ip_address: str = None,
                         user_agent: str = None) -> User:
        """
        Authenticate user with password and optional 2FA
        
        Args:
            username: Username
            password: Password
            totp_code: Optional TOTP code for 2FA
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Authenticated User object
            
        Raises:
            InvalidCredentialsError: Invalid username/password
            AccountLockedError: Account is locked
            TwoFactorRequiredError: 2FA required but not provided
            InvalidTwoFactorError: Invalid 2FA code
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT id, username, email, password_hash, salt, role,
                       totp_secret, totp_enabled, created_at, last_login,
                       is_active, failed_attempts, locked_until
                FROM users WHERE username = ?
            """, (username,)).fetchone()
            
            if not row:
                self._log_auth_event(
                    "login_failed", None, False,
                    {"reason": "invalid_username", "username": username},
                    ip_address, user_agent
                )
                raise InvalidCredentialsError("Invalid username or password")
            
            user_data = dict(zip([
                'id', 'username', 'email', 'password_hash', 'salt', 'role',
                'totp_secret', 'totp_enabled', 'created_at', 'last_login',
                'is_active', 'failed_attempts', 'locked_until'
            ], row))
            
            user_id = user_data['id']
            
            # Check if account is locked
            if user_data['locked_until']:
                locked_until = datetime.fromisoformat(user_data['locked_until'])
                if datetime.now() < locked_until:
                    self._log_auth_event(
                        "login_failed", user_id, False,
                        {"reason": "account_locked"},
                        ip_address, user_agent
                    )
                    raise AccountLockedError(f"Account locked until {locked_until}")
                else:
                    # Unlock account
                    conn.execute("""
                        UPDATE users SET failed_attempts = 0, locked_until = NULL
                        WHERE id = ?
                    """, (user_id,))
            
            # Check if account is active
            if not user_data['is_active']:
                self._log_auth_event(
                    "login_failed", user_id, False,
                    {"reason": "account_disabled"},
                    ip_address, user_agent
                )
                raise InvalidCredentialsError("Account is disabled")
            
            # Verify password
            if not self._verify_password(password, user_data['password_hash'], user_data['salt']):
                # Increment failed attempts
                failed_attempts = user_data['failed_attempts'] + 1
                locked_until = None
                
                if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                    locked_until = datetime.now() + self.LOCKOUT_DURATION
                
                conn.execute("""
                    UPDATE users SET failed_attempts = ?, locked_until = ?
                    WHERE id = ?
                """, (failed_attempts, locked_until, user_id))
                
                self._log_auth_event(
                    "login_failed", user_id, False,
                    {"reason": "invalid_password", "failed_attempts": failed_attempts},
                    ip_address, user_agent
                )
                
                if locked_until:
                    raise AccountLockedError(f"Account locked due to too many failed attempts")
                else:
                    raise InvalidCredentialsError("Invalid username or password")
            
            # Check 2FA if enabled
            if user_data['totp_enabled']:
                if not totp_code:
                    self._log_auth_event(
                        "login_failed", user_id, False,
                        {"reason": "2fa_required"},
                        ip_address, user_agent
                    )
                    raise TwoFactorRequiredError("Two-factor authentication required")
                
                totp = pyotp.TOTP(user_data['totp_secret'])
                if not totp.verify(totp_code, valid_window=1):
                    self._log_auth_event(
                        "login_failed", user_id, False,
                        {"reason": "invalid_2fa"},
                        ip_address, user_agent
                    )
                    raise InvalidTwoFactorError("Invalid two-factor authentication code")
            
            # Successful authentication - reset failed attempts and update last login
            conn.execute("""
                UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ?
                WHERE id = ?
            """, (datetime.now(), user_id))
            
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                salt=user_data['salt'],
                role=UserRole(user_data['role']),
                totp_secret=user_data['totp_secret'],
                totp_enabled=bool(user_data['totp_enabled']),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.now(),
                is_active=bool(user_data['is_active']),
                failed_attempts=0,
                locked_until=None
            )
            
            self._log_auth_event(
                "login_success", user_id, True,
                {"username": username},
                ip_address, user_agent
            )
            
            return user
    
    def setup_2fa(self, user_id: int) -> Tuple[str, str]:
        """
        Setup 2FA for user and return secret + QR code
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (secret_key, qr_code_data_url)
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                raise ValueError("User not found")
            
            username = row[0]
            
            # Generate TOTP secret
            secret = pyotp.random_base32()
            
            # Create TOTP URI for QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=username,
                issuer_name="LNMT"
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            qr_code_url = f"data:image/png;base64,{qr_code_data}"
            
            # Store secret (but don't enable yet)
            conn.execute("""
                UPDATE users SET totp_secret = ? WHERE id = ?
            """, (secret, user_id))
            
            self._log_auth_event("2fa_setup_initiated", user_id)
            
            return secret, qr_code_url
    
    def enable_2fa(self, user_id: int, totp_code: str):
        """
        Enable 2FA after verifying TOTP code
        
        Args:
            user_id: User ID
            totp_code: TOTP code to verify
            
        Raises:
            ValueError: User not found or no TOTP secret
            InvalidTwoFactorError: Invalid TOTP code
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT totp_secret FROM users WHERE id = ?
            """, (user_id,)).fetchone()
            
            if not row or not row[0]:
                raise ValueError("User not found or 2FA not set up")
            
            secret = row[0]
            totp = pyotp.TOTP(secret)
            
            if not totp.verify(totp_code, valid_window=1):
                self._log_auth_event("2fa_enable_failed", user_id, False)
                raise InvalidTwoFactorError("Invalid verification code")
            
            # Enable 2FA
            conn.execute("""
                UPDATE users SET totp_enabled = TRUE WHERE id = ?
            """, (user_id,))
            
            self._log_auth_event("2fa_enabled", user_id)
    
    def disable_2fa(self, user_id: int):
        """Disable 2FA for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET totp_enabled = FALSE, totp_secret = NULL
                WHERE id = ?
            """, (user_id,))
            
            self._log_auth_event("2fa_disabled", user_id)
    
    def create_api_token(self, user_id: int, token_name: str, 
                        expires_days: int = None) -> str:
        """
        Create API token for user
        
        Args:
            user_id: User ID
            token_name: Descriptive name for token
            expires_days: Token expiration in days (default: 30)
            
        Returns:
            Generated API token
            
        Raises:
            TokenLimitExceededError: User has too many tokens
        """
        if expires_days is None:
            expires_days = self.TOKEN_VALIDITY_DAYS
            
        with sqlite3.connect(self.db_path) as conn:
            # Check token limit
            count = conn.execute("""
                SELECT COUNT(*) FROM api_tokens 
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,)).fetchone()[0]
            
            if count >= self.MAX_TOKENS_PER_USER:
                raise TokenLimitExceededError(f"Maximum {self.MAX_TOKENS_PER_USER} tokens per user")
            
            # Generate token
            token = self._generate_token()
            token_hash = self._hash_token(token)
            expires_at = datetime.now() + timedelta(days=expires_days)
            
            # Store token
            cursor = conn.execute("""
                INSERT INTO api_tokens 
                (user_id, token_hash, name, created_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, token_hash, token_name, datetime.now(), expires_at, True))
            
            token_id = cursor.lastrowid
            
            self._log_auth_event(
                "token_created", user_id,
                details={"token_id": token_id, "token_name": token_name}
            )
            
            return token
    
    def validate_api_token(self, token: str) -> Optional[User]:
        """
        Validate API token and return associated user
        
        Args:
            token: API token to validate
            
        Returns:
            User object if token is valid, None otherwise
        """
        token_hash = self._hash_token(token)
        
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT t.id, t.user_id, u.username, u.email, u.role,
                       u.is_active, t.expires_at, t.is_active as token_active
                FROM api_tokens t
                JOIN users u ON t.user_id = u.id
                WHERE t.token_hash = ?
            """, (token_hash,)).fetchone()
            
            if not row:
                return None
            
            token_data = dict(zip([
                'token_id', 'user_id', 'username', 'email', 'role',
                'user_active', 'expires_at', 'token_active'
            ], row))
            
            # Check if token is active
            if not token_data['token_active']:
                return None
            
            # Check if user is active
            if not token_data['user_active']:
                return None
            
            # Check expiration
            if token_data['expires_at']:
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                if datetime.now() > expires_at:
                    # Deactivate expired token
                    conn.execute("""
                        UPDATE api_tokens SET is_active = FALSE WHERE id = ?
                    """, (token_data['token_id'],))
                    return None
            
            # Update last used timestamp
            conn.execute("""
                UPDATE api_tokens SET last_used = ? WHERE id = ?
            """, (datetime.now(), token_data['token_id']))
            
            # Return user object (simplified for token auth)
            return User(
                id=token_data['user_id'],
                username=token_data['username'],
                email=token_data['email'],
                password_hash="",  # Not needed for token auth
                salt="",           # Not needed for token auth
                role=UserRole(token_data['role']),
                totp_secret=None,
                totp_enabled=False,
                created_at=datetime.now(),  # Not retrieved for performance
                last_login=None,
                is_active=True,
                failed_attempts=0,
                locked_until=None
            )
    
    def revoke_api_token(self, user_id: int, token_id: int):
        """Revoke specific API token"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE api_tokens SET is_active = FALSE
                WHERE id = ? AND user_id = ?
            """, (token_id, user_id))
            
            self._log_auth_event(
                "token_revoked", user_id,
                details={"token_id": token_id}
            )
    
    def list_user_tokens(self, user_id: int) -> List[APIToken]:
        """List all tokens for user"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, user_id, token_hash, name, created_at,
                       last_used, expires_at, is_active
                FROM api_tokens WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,)).fetchall()
            
            tokens = []
            for row in rows:
                token_data = dict(zip([
                    'id', 'user_id', 'token_hash', 'name', 'created_at',
                    'last_used', 'expires_at', 'is_active'
                ], row))
                
                tokens.append(APIToken(
                    id=token_data['id'],
                    user_id=token_data['user_id'],
                    token_hash=token_data['token_hash'],
                    name=token_data['name'],
                    created_at=datetime.fromisoformat(token_data['created_at']),
                    last_used=datetime.fromisoformat(token_data['last_used']) if token_data['last_used'] else None,
                    expires_at=datetime.fromisoformat(token_data['expires_at']) if token_data['expires_at'] else None,
                    is_active=bool(token_data['is_active'])
                ))
            
            return tokens
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions
    
    def require_permission(self, user: User, permission: Permission):
        """Require user to have specific permission, raise exception if not"""
        if not self.check_permission(user, permission):
            raise PermissionDeniedError(f"Permission denied: {permission.value}")
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT id, username, email, password_hash, salt, role,
                       totp_secret, totp_enabled, created_at, last_login,
                       is_active, failed_attempts, locked_until
                FROM users WHERE username = ?
            """, (username,)).fetchone()
            
            if not row:
                return None
            
            user_data = dict(zip([
                'id', 'username', 'email', 'password_hash', 'salt', 'role',
                'totp_secret', 'totp_enabled', 'created_at', 'last_login',
                'is_active', 'failed_attempts', 'locked_until'
            ], row))
            
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                salt=user_data['salt'],
                role=UserRole(user_data['role']),
                totp_secret=user_data['totp_secret'],
                totp_enabled=bool(user_data['totp_enabled']),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None,
                is_active=bool(user_data['is_active']),
                failed_attempts=user_data['failed_attempts'],
                locked_until=datetime.fromisoformat(user_data['locked_until']) if user_data['locked_until'] else None
            )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT id, username, email, password_hash, salt, role,
                       totp_secret, totp_enabled, created_at, last_login,
                       is_active, failed_attempts, locked_until
                FROM users WHERE id = ?
            """, (user_id,)).fetchone()
            
            if not row:
                return None
            
            user_data = dict(zip([
                'id', 'username', 'email', 'password_hash', 'salt', 'role',
                'totp_secret', 'totp_enabled', 'created_at', 'last_login',
                'is_active', 'failed_attempts', 'locked_until'
            ], row))
            
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                salt=user_data['salt'],
                role=UserRole(user_data['role']),
                totp_secret=user_data['totp_secret'],
                totp_enabled=bool(user_data['totp_enabled']),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None,
                is_active=bool(user_data['is_active']),
                failed_attempts=user_data['failed_attempts'],
                locked_until=datetime.fromisoformat(user_data['locked_until']) if user_data['locked_until'] else None
            )
    
    def update_user_role(self, user_id: int, new_role: UserRole):
        """Update user role"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET role = ? WHERE id = ?
            """, (new_role.value, user_id))
            
            self._log_auth_event(
                "user_role_updated", user_id,
                details={"new_role": new_role.value}
            )
    
    def deactivate_user(self, user_id: int):
        """Deactivate user account"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET is_active = FALSE WHERE id = ?
            """, (user_id,))
            
            # Also deactivate all user tokens
            conn.execute("""
                UPDATE api_tokens SET is_active = FALSE WHERE user_id = ?
            """, (user_id,))
            
            self._log_auth_event("user_deactivated", user_id)
    
    def activate_user(self, user_id: int):
        """Activate user account"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET is_active = TRUE, failed_attempts = 0, locked_until = NULL
                WHERE id = ?
            """, (user_id,))
            
            self._log_auth_event("user_activated", user_id)
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """List all users with pagination"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, username, email, password_hash, salt, role,
                       totp_secret, totp_enabled, created_at, last_login,
                       is_active, failed_attempts, locked_until
                FROM users 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            
            users = []
            for row in rows:
                user_data = dict(zip([
                    'id', 'username', 'email', 'password_hash', 'salt', 'role',
                    'totp_secret', 'totp_enabled', 'created_at', 'last_login',
                    'is_active', 'failed_attempts', 'locked_until'
                ], row))
                
                users.append(User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    salt=user_data['salt'],
                    role=UserRole(user_data['role']),
                    totp_secret=user_data['totp_secret'],
                    totp_enabled=bool(user_data['totp_enabled']),
                    created_at=datetime.fromisoformat(user_data['created_at']),
                    last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None,
                    is_active=bool(user_data['is_active']),
                    failed_attempts=user_data['failed_attempts'],
                    locked_until=datetime.fromisoformat(user_data['locked_until']) if user_data['locked_until'] else None
                ))
            
            return users
    
    def get_auth_events(self, user_id: int = None, limit: int = 100, 
                       offset: int = 0) -> List[AuthEvent]:
        """Get authentication events for audit trail"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                rows = conn.execute("""
                    SELECT id, user_id, event_type, ip_address, user_agent,
                           success, details, timestamp
                    FROM auth_events 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT id, user_id, event_type, ip_address, user_agent,
                           success, details, timestamp
                    FROM auth_events 
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset)).fetchall()
            
            events = []
            for row in rows:
                event_data = dict(zip([
                    'id', 'user_id', 'event_type', 'ip_address', 'user_agent',
                    'success', 'details', 'timestamp'
                ], row))
                
                events.append(AuthEvent(
                    id=event_data['id'],
                    user_id=event_data['user_id'],
                    event_type=event_data['event_type'],
                    ip_address=event_data['ip_address'],
                    user_agent=event_data['user_agent'],
                    success=bool(event_data['success']),
                    details=json.loads(event_data['details']) if event_data['details'] else {},
                    timestamp=datetime.fromisoformat(event_data['timestamp'])
                ))
            
            return events
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get authentication statistics for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            # User statistics
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE").fetchone()[0]
            locked_users = conn.execute("""
                SELECT COUNT(*) FROM users 
                WHERE locked_until IS NOT NULL AND locked_until > datetime('now')
            """).fetchone()[0]
            
            # Token statistics
            total_tokens = conn.execute("SELECT COUNT(*) FROM api_tokens WHERE is_active = TRUE").fetchone()[0]
            
            # 2FA statistics
            users_with_2fa = conn.execute("SELECT COUNT(*) FROM users WHERE totp_enabled = TRUE").fetchone()[0]
            
            # Recent authentication events (last 24 hours)
            recent_logins = conn.execute("""
                SELECT COUNT(*) FROM auth_events 
                WHERE event_type = 'login_success' 
                AND timestamp > datetime('now', '-1 day')
            """).fetchone()[0]
            
            recent_failures = conn.execute("""
                SELECT COUNT(*) FROM auth_events 
                WHERE event_type = 'login_failed' 
                AND timestamp > datetime('now', '-1 day')
            """).fetchone()[0]
            
            # Role distribution
            role_stats = {}
            for role in UserRole:
                count = conn.execute("""
                    SELECT COUNT(*) FROM users WHERE role = ? AND is_active = TRUE
                """, (role.value,)).fetchone()[0]
                role_stats[role.value] = count
            
            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "locked": locked_users,
                    "with_2fa": users_with_2fa
                },
                "tokens": {
                    "active": total_tokens
                },
                "recent_activity": {
                    "successful_logins_24h": recent_logins,
                    "failed_logins_24h": recent_failures
                },
                "role_distribution": role_stats
            }