# LNMT Authentication Engine

A comprehensive, production-ready authentication system for LNMT with advanced security features including API token management, role-based access control, and two-factor authentication.

## 🚀 Features

### Core Authentication
- **Secure Password Hashing**: PBKDF2 with SHA-256 and random salts (100,000 iterations)
- **Account Security**: Rate limiting, account lockout after failed attempts
- **Session Management**: Flexible integration for CLI, API, and web applications

### Two-Factor Authentication (2FA)
- **TOTP Support**: Compatible with Google Authenticator and Microsoft Authenticator
- **QR Code Generation**: Easy setup with QR codes for mobile apps
- **Backup Codes**: Secure account recovery options
- **Flexible Integration**: Can be enabled/disabled per user

### API Token Management
- **Multiple Tokens**: Up to 5 active tokens per user
- **Token Lifecycle**: Create, list, revoke, and automatic expiration
- **Secure Storage**: Tokens are hashed in database
- **Usage Tracking**: Last used timestamps and audit trail

### Role-Based Access Control (RBAC)
- **Hierarchical Roles**: Admin, Manager, Operator, Viewer, Guest
- **Granular Permissions**: Fine-grained permission system
- **Easy Integration**: Simple permission checks for any operation
- **Flexible Role Management**: Update user roles dynamically

### Audit & Monitoring
- **Comprehensive Logging**: All authentication events logged
- **Dashboard Statistics**: User counts, activity metrics, role distribution
- **Security Monitoring**: Failed login attempts, suspicious activity
- **Audit Trail**: Full history for compliance and security analysis

## 📋 Requirements

```bash
pip install -r requirements.txt
```

### Core Dependencies
- `sqlite3` (built-in): Database storage
- `pyotp>=2.6.0`: TOTP two-factor authentication
- `qrcode[pil]>=7.3.1`: QR code generation for 2FA setup
- `secrets` (built-in): Cryptographically secure random number generation
- `hashlib` (built-in): Password hashing
- `datetime` (built-in): Time handling

### Development Dependencies
- `pytest>=7.0.0`: Testing framework
- `coverage>=6.0`: Test coverage analysis

## 🛠️ Installation

1. **Clone or copy the auth engine files:**
   ```bash
   mkdir lnmt_auth
   cd lnmt_auth
   # Copy core/auth_engine.py and cli/authctl.py
   ```

2. **Install dependencies:**
   ```bash
   pip install pyotp qrcode[pil]
   ```

3. **Initialize the database:**
   ```python
   from core.auth_engine import AuthEngine
   auth = AuthEngine("lnmt.db")  # Creates tables automatically
   ```

## 🔧 Quick Start

### 1. Basic User Management

```python
from core.auth_engine import AuthEngine, UserRole

# Initialize
auth = AuthEngine("lnmt.db")

# Create admin user
admin = auth.create_user(
    username="admin",
    email="admin@company.com",
    password="SecurePassword123!",
    role=UserRole.ADMIN
)

# Create regular user
user = auth.create_user(
    username="alice",
    email="alice@company.com", 
    password="AlicePassword123!",
    role=UserRole.OPERATOR
)
```

### 2. Authentication

```python
# Basic authentication
try:
    user = auth.authenticate_user("alice", "AlicePassword123!")
    print(f"Welcome {user.username}!")
except (InvalidCredentialsError, AccountLockedError) as e:
    print(f"Authentication failed: {e}")
```

### 3. Two-Factor Authentication

```python
# Setup 2FA
secret, qr_url = auth.setup_2fa(user.id)
print(f"Scan this QR code: {qr_url}")

# Enable 2FA (after user scans QR and enters code)
totp_code = input("Enter 6-digit code from authenticator: ")
auth.enable_2fa(user.id, totp_code)

# Authenticate with 2FA
user = auth.authenticate_user("alice", "AlicePassword123!", totp_code)
```

### 4. API Tokens

```python
# Create API token
token = auth.create_api_token(user.id, "Mobile App", expires_days=30)
print(f"API Token: {token}")

# Validate token in API
authenticated_user = auth.validate_api_token(token)
if authenticated_user:
    print(f"Valid token for {authenticated_user.username}")

# List user tokens
tokens = auth.list_user_tokens(user.id)
for token in tokens:
    print(f"Token: {token.name} - Active: {token.is_active}")
```

### 5. Role-Based Access Control

```python
from core.auth_engine import Permission

# Check permissions
if auth.check_permission(user, Permission.USER_CREATE):
    print("User can create other users")

# Require permission (raises exception if denied)
try:
    auth.require_permission(user, Permission.SYSTEM_ADMIN)
    # Perform admin operation
except PermissionDeniedError:
    print("Access denied")
```

## 🖥️ CLI Usage

The `authctl.py` command-line tool provides full management capabilities:

### User Management
```bash
# Create user
python cli/authctl.py user create alice alice@company.com --role operator

# List users
python cli/authctl.py user list --active-only

# Update user role
python cli/authctl.py user update 2 --role admin

# Activate/deactivate user
python cli/authctl.py user update 2 --activate
```

### 2FA Management
```bash
# Setup 2FA for user
python cli/authctl.py user 2fa setup alice

# Check 2FA status
python cli/authctl.py user 2fa status alice

# Disable 2FA
python cli/authctl.py user 2fa disable alice
```

### Token Management
```bash
# Create API token
python cli/authctl.py token create alice "API Access" --expires 90

# List user tokens
python cli/authctl.py token list alice

# Revoke token
python cli/authctl.py token revoke alice 1
```

### Monitoring & Audit
```bash
# View authentication statistics
python cli/authctl.py stats

# View audit log
python cli/authctl.py audit --user alice --limit 50

# View all recent events
python cli/authctl.py audit --limit 100
```

## 🏗️ Architecture

### Database Schema

The authentication engine uses SQLite with three main tables:

- **users**: User accounts, credentials, and settings
- **api_tokens**: API tokens with expiration and usage tracking
- **auth_events**: Comprehensive audit log of all authentication events

### Security Features

1. **Password Security**
   - PBKDF2 with SHA-256 hashing
   - Random salts for each password
   - 100,000 iterations for resistance to brute force

2. **Account Protection**
   - Rate limiting (5 failed attempts)
   - Temporary account lockout (15 minutes)
   - Active/inactive user status

3. **Token Security**
   - Cryptographically secure token generation
   - Hashed storage (SHA-256)
   - Automatic expiration
   - Per-user token limits

4. **Audit Trail**
   - All authentication events logged
   - IP address and user agent tracking
   - Success/failure tracking
   - Detailed event metadata

### Integration Patterns

#### CLI Applications
```python
# CLI authentication workflow
try:
    user = auth.authenticate_user(username, password, totp_code)
    auth.require_permission(user, required_permission)
    # Execute CLI command
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

#### API Applications
```python
# API authentication middleware
def authenticate_request(request):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user = auth.validate_api_token(token)
    if not user:
        return None
    return user

# Permission check for API endpoint
@require_permission(Permission.SYSTEM_READ)
def api_endpoint(request):
    # Handle request
    pass
```

#### Web Applications
```python
# Session-based authentication
def login_user(username, password, totp_code=None):
    user = auth.authenticate_user(username, password, totp_code)
    session['user_id'] = user.id
    return user

def get_current_user():
    user_id = session.get('user_id')
    return auth.get_user_by_id(user_id) if user_id else None
```

## 📊 Role & Permission Matrix

| Role | User Mgmt | Token Mgmt | System Ops | Dashboard |
|------|-----------|------------|------------|-----------|
| **Admin** | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Manager** | ✅ CRUD | ✅ Full | ✅ Read/Write | ✅ Full |
| **Operator** | ✅ Read | ✅ Own tokens | ✅ Read/Write | ✅ View |
| **Viewer** | ✅ Read | ❌ None | ✅ Read only | ✅ View |
| **Guest** | ❌ None | ❌ None | ✅ Read only | ✅ View |

### Available Permissions

- **User Management**: `USER_CREATE`, `USER_READ`, `USER_UPDATE`, `USER_DELETE`
- **Token Management**: `TOKEN_CREATE`, `TOKEN_REVOKE`, `TOKEN_LIST`
- **System Operations**: `SYSTEM_READ`, `SYSTEM_WRITE`, `SYSTEM_ADMIN`
- **Dashboard Access**: `DASHBOARD_VIEW`, `DASHBOARD_ADMIN`

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python -m pytest tests/test_auth_engine.py -v

# Run with coverage
python -m pytest tests/test_auth_engine.py --cov=core.auth_engine --cov-report=html

# Run specific test
python -m pytest tests/test_auth_engine.py::TestAuthEngine::test_2fa_setup_and_authentication -v
```

### Test Coverage
The test suite covers:
- ✅ User creation and management
- ✅ Password authentication and security
- ✅ 2FA setup and validation
- ✅ API token lifecycle
- ✅ Role-based permissions
- ✅ Account lockout and security
- ✅ Audit logging
- ✅ Error handling and edge cases

### Run Examples
```bash
# Interactive examples demonstrating all features
python examples/auth_examples.py
```

## 🔐 Security Best Practices

### Password Requirements
- Minimum 8 characters
- Mix of uppercase, lowercase, numbers, symbols
- No common dictionary words
- Regular password rotation

### 2FA Recommendations
- Enable 2FA for all admin and manager accounts
- Use backup codes for account recovery
- Regular 2FA device management and updates

### Token Management
- Regular token rotation (30-90 days)
- Revoke unused or suspicious tokens
- Monitor token usage patterns
- Use descriptive token names

### Monitoring & Alerting
- Monitor failed login attempts
- Alert on account lockouts
- Track suspicious authentication patterns
- Regular audit log reviews

## 🤝 Integration Examples

### Flask Web Application
```python
from flask import Flask, session, request
from core.auth_engine import AuthEngine, Permission

app = Flask(__name__)
auth = AuthEngine("app.db")

@app.route('/api/users')
def list_users():
    user = get_current_user()
    if not user:
        return {'error': 'Unauthorized'}, 401
    
    auth.require_permission(user, Permission.USER_READ)
    users = auth.list_users()
    return {'users': [{'id': u.id, 'username': u.username} for u in users]}

def get_current_user():
    user_id = session.get('user_id')
    return auth.get_user_by_id(user_id) if user_id else None
```

### FastAPI Application
```python
from fastapi import FastAPI, HTTPException, Depends, Header
from core.auth_engine import AuthEngine, Permission

app = FastAPI()
auth = AuthEngine("app.db")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.replace('Bearer ', '')
    user = auth.validate_api_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user

@app.get("/api/users")
async def list_users(user: User = Depends(get_current_user)):
    auth.require_permission(user, Permission.USER_READ)
    users = auth.list_users()
    return {"users": [{"id": u.id, "username": u.username} for u in users]}
```

### Django Integration
```python
# middleware.py
from django.http import JsonResponse
from core.auth_engine import AuthEngine

auth = AuthEngine("django.db")

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # API token authentication
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].replace('Bearer ', '')
            user = auth.validate_api_token(token)
            request.auth_user = user
        else:
            request.auth_user = None
        
        return self.get_response(request)

# decorators.py
from functools import wraps
from django.http import JsonResponse

def require_permission(permission):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.auth_user:
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            
            try:
                auth.require_permission(request.auth_user, permission)
                return view_func(request, *args, **kwargs)
            except PermissionDeniedError:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        return wrapper
    return decorator
```

## 📈 Performance & Scalability

### Database Optimization
- Indexed columns for fast lookups (username, email, token_hash)
- Efficient pagination for large user lists
- Automatic cleanup of expired tokens and old audit logs

### Memory Usage
- Minimal memory footprint
- Connection pooling for high-traffic applications
- Efficient token validation without full user data loading

### Recommended Limits
- **Users**: Tested with 100,000+ users
- **Tokens**: 5 per user (configurable)
- **Audit Events**: Automatic cleanup after 1 year (configurable)
- **Failed Attempts**: 5 attempts before lockout (configurable)

## 🔧 Configuration

### Environment Variables
```bash
# Database configuration
LNMT_DB_PATH="production.db"

# Security settings
LNMT_MAX_FAILED_ATTEMPTS=5
LNMT_LOCKOUT_DURATION_MINUTES=15
LNMT_TOKEN_VALIDITY_DAYS=30
LNMT_MAX_TOKENS_PER_USER=5

# Audit settings
LNMT_AUDIT_RETENTION_DAYS=365
LNMT_LOG_LEVEL="INFO"
```

### Customization Options
```python
# Custom configuration
auth = AuthEngine("custom.db")
auth.MAX_FAILED_ATTEMPTS = 3
auth.LOCKOUT_DURATION = timedelta(minutes=30)
auth.TOKEN_VALIDITY_DAYS = 90
auth.MAX_TOKENS_PER_USER = 10
```

## 🚨 Error Handling

### Exception Hierarchy
```python
AuthenticationError (base)
├── InvalidCredentialsError
├── AccountLockedError
├── TwoFactorRequiredError
├── InvalidTwoFactorError
├── PermissionDeniedError
└── TokenLimitExceededError
```

### Error Handling Patterns
```python
try:
    user = auth.authenticate_user(username, password, totp_code)
except InvalidCredentialsError:
    return "Invalid username or password"
except AccountLockedError as e:
    return f"Account locked: {e}"
except TwoFactorRequiredError:
    return "Please provide 2FA code"
except InvalidTwoFactorError:
    return "Invalid 2FA code"
```

## 📚 API Reference

### Core Methods

#### User Management
```python
# Create user
create_user(username: str, email: str, password: str, role: UserRole) -> User

# Authenticate user
authenticate_user(username: str, password: str, totp_code: str = None, 
                 ip_address: str = None, user_agent: str = None) -> User

# Get user
get_user_by_id(user_id: int) -> Optional[User]
get_user_by_username(username: str) -> Optional[User]

# Update user
update_user_role(user_id: int, new_role: UserRole)
activate_user(user_id: int)
deactivate_user(user_id: int)

# List users
list_users(limit: int = 100, offset: int = 0) -> List[User]
```

#### 2FA Management
```python
# Setup 2FA
setup_2fa(user_id: int) -> Tuple[str, str]  # Returns (secret, qr_url)

# Enable/disable 2FA
enable_2fa(user_id: int, totp_code: str)
disable_2fa(user_id: int)
```

#### Token Management
```python
# Create token
create_api_token(user_id: int, token_name: str, expires_days: int = 30) -> str

# Validate token
validate_api_token(token: str) -> Optional[User]

# Manage tokens
list_user_tokens(user_id: int) -> List[APIToken]
revoke_api_token(user_id: int, token_id: int)
```

#### Permissions
```python
# Check permissions
check_permission(user: User, permission: Permission) -> bool
require_permission(user: User, permission: Permission)  # Raises PermissionDeniedError
```

#### Audit & Statistics
```python
# Get audit events
get_auth_events(user_id: int = None, limit: int = 100, offset: int = 0) -> List[AuthEvent]

# Get dashboard statistics
get_dashboard_stats() -> Dict[str, Any]
```

## 🔄 Migration & Deployment

### Database Migration
The authentication engine automatically creates and updates database schema. For production deployments:

1. **Backup existing database**
2. **Test migration in staging environment**
3. **Run migration during maintenance window**
4. **Verify all functionality post-migration**

### Production Deployment Checklist

- [ ] Secure database file permissions (600 or 640)
- [ ] Enable database WAL mode for better concurrency
- [ ] Set up automated database backups
- [ ] Configure log rotation for audit events
- [ ] Set up monitoring for authentication failures
- [ ] Enable rate limiting at web server level
- [ ] Use HTTPS for all authentication endpoints
- [ ] Set secure session/token storage
- [ ] Configure proper CORS headers
- [ ] Set up intrusion detection monitoring

### High Availability Setup
```python
# Master-slave database replication
class HAAuthEngine:
    def __init__(self, master_db: str, slave_db: str):
        self.master = AuthEngine(master_db)
        self.slave = AuthEngine(slave_db)
    
    def authenticate_user(self, *args, **kwargs):
        # Write operations go to master
        return self.master.authenticate_user(*args, **kwargs)
    
    def get_user_by_id(self, user_id: int):
        # Read operations can use slave
        return self.slave.get_user_by_id(user_id)
```

## 🆘 Troubleshooting

### Common Issues

#### Database Locked Errors
```bash
# Solution: Enable WAL mode
sqlite3 lnmt.db "PRAGMA journal_mode=WAL;"
```

#### 2FA Setup Issues
```python
# Check system time synchronization
import time
current_time = int(time.time())
print(f"System time: {current_time}")

# Verify TOTP window
totp = pyotp.TOTP(secret)
print(f"Valid codes: {[totp.at(current_time + i*30) for i in range(-1, 2)]}")
```

#### Token Validation Failures
```python
# Debug token validation
def debug_token_validation(auth, token):
    token_hash = auth._hash_token(token)
    print(f"Token hash: {token_hash}")
    
    # Check database directly
    with sqlite3.connect(auth.db_path) as conn:
        row = conn.execute("SELECT * FROM api_tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        print(f"Database result: {row}")
```

### Performance Issues

#### Slow Authentication
- Check database indexes
- Monitor disk I/O
- Consider connection pooling
- Profile PBKDF2 iterations

#### High Memory Usage
- Implement user data caching
- Optimize audit log retention
- Use pagination for large datasets

## 📄 License

This authentication engine is part of the LNMT project. Please refer to the main project license for usage terms and conditions.

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/auth-enhancement`
3. **Add tests for new functionality**
4. **Ensure all tests pass**: `pytest tests/`
5. **Submit pull request with detailed description**

### Development Setup
```bash
git clone <repository>
cd lnmt_auth
pip install -r requirements-dev.txt
pre-commit install
```

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include comprehensive docstrings
- Maintain test coverage above 95%
- Add security considerations for new features

## 📞 Support

For questions, issues, or feature requests:

1. **Check existing documentation** and examples
2. **Search existing issues** in the repository
3. **Create detailed bug reports** with reproduction steps
4. **Submit feature requests** with use case descriptions

---

**🔐 LNMT Authentication Engine** - Secure, scalable, and production-ready authentication for modern applications.