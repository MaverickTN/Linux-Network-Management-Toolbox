#!/usr/bin/env python3
"""
LNMT Authentication Engine Test Suite
====================================

Comprehensive test suite for the authentication engine covering:
- User management operations
- Password authentication and security
- 2FA setup and validation
- API token management
- Role-based access control
- Audit logging functionality
- Error handling and edge cases
- Security features (rate limiting, lockouts)

Run with: python -m pytest tests/test_auth_engine.py -v
Or: python tests/test_auth_engine.py
"""

import unittest
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth_engine import (
    AuthEngine, UserRole, Permission, User, APIToken, AuthEvent,
    InvalidCredentialsError, AccountLockedError, TwoFactorRequiredError,
    InvalidTwoFactorError, PermissionDeniedError, TokenLimitExceededError
)

class TestAuthEngine(unittest.TestCase):
    """Test suite for AuthEngine"""
    
    def setUp(self):
        """Set up test database for each test"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.auth = AuthEngine(self.test_db.name)
        
        # Create test users
        self.admin_user = self.auth.create_user(
            "admin", "admin@test.com", "AdminPass123!", UserRole.ADMIN
        )
        self.regular_user = self.auth.create_user(
            "alice", "alice@test.com", "AlicePass123!", UserRole.OPERATOR
        )
        self.viewer_user = self.auth.create_user(
            "bob", "bob@test.com", "BobPass123!", UserRole.VIEWER
        )
    
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.test_db.name)
        except OSError:
            pass
    
    def test_create_user(self):
        """Test user creation"""
        user = self.auth.create_user(
            "testuser", "test@example.com", "TestPass123!", UserRole.MANAGER
        )
        
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, UserRole.MANAGER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.totp_enabled)
        
        # Test duplicate username
        with self.assertRaises(ValueError):
            self.auth.create_user(
                "testuser", "test2@example.com", "TestPass123!", UserRole.VIEWER
            )
        
        # Test duplicate email
        with self.assertRaises(ValueError):
            self.auth.create_user(
                "testuser2", "test@example.com", "TestPass123!", UserRole.VIEWER
            )
    
    def test_password_hashing(self):
        """Test password hashing security"""
        password = "TestPassword123!"
        hash1, salt1 = self.auth._hash_password(password)
        hash2, salt2 = self.auth._hash_password(password)
        
        # Different salts should produce different hashes
        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(salt1, salt2)
        
        # Verification should work
        self.assertTrue(self.auth._verify_password(password, hash1, salt1))
        self.assertTrue(self.auth._verify_password(password, hash2, salt2))
        
        # Wrong password should fail
        self.assertFalse(self.auth._verify_password("wrong", hash1, salt1))
    
    def test_user_authentication(self):
        """Test basic user authentication"""
        # Successful authentication
        user = self.auth.authenticate_user("alice", "AlicePass123!")
        self.assertEqual(user.username, "alice")
        self.assertIsNotNone(user.last_login)
        
        # Invalid username
        with self.assertRaises(InvalidCredentialsError):
            self.auth.authenticate_user("nonexistent", "password")
        
        # Invalid password
        with self.assertRaises(InvalidCredentialsError):
            self.auth.authenticate_user("alice", "wrongpassword")
    
    def test_account_lockout(self):
        """Test account lockout after failed attempts"""
        username = "alice"
        
        # Make multiple failed attempts
        for i in range(self.auth.MAX_FAILED_ATTEMPTS):
            with self.assertRaises(InvalidCredentialsError):
                self.auth.authenticate_user(username, "wrongpassword")
        
        # Next attempt should lock account
        with self.assertRaises(AccountLockedError):
            self.auth.authenticate_user(username, "wrongpassword")
        
        # Even correct password should fail when locked
        with self.assertRaises(AccountLockedError):
            self.auth.authenticate_user(username, "AlicePass123!")
    
    def test_inactive_user_authentication(self):
        """Test authentication of inactive users"""
        # Deactivate user
        self.auth.deactivate_user(self.regular_user.id)
        
        # Authentication should fail
        with self.assertRaises(InvalidCredentialsError):
            self.auth.authenticate_user("alice", "AlicePass123!")
    
    def test_2fa_setup_and_authentication(self):
        """Test 2FA setup and authentication flow"""
        user_id = self.regular_user.id
        
        # Setup 2FA
        secret, qr_url = self.auth.setup_2fa(user_id)
        self.assertIsNotNone(secret)
        self.assertIn("data:image/png;base64,", qr_url)
        
        # Enable 2FA with valid code
        import pyotp
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        
        self.auth.enable_2fa(user_id, current_code)
        
        # Verify 2FA is enabled
        updated_user = self.auth.get_user_by_id(user_id)
        self.assertTrue(updated_user.totp_enabled)
        
        # Authentication without 2FA should fail
        with self.assertRaises(TwoFactorRequiredError):
            self.auth.authenticate_user("alice", "AlicePass123!")
        
        # Authentication with invalid 2FA should fail
        with self.assertRaises(InvalidTwoFactorError):
            self.auth.authenticate_user("alice", "AlicePass123!", "000000")
        
        # Authentication with valid 2FA should succeed
        current_code = totp.now()
        user = self.auth.authenticate_user("alice", "AlicePass123!", current_code)
        self.assertEqual(user.username, "alice")
        
        # Test disabling 2FA
        self.auth.disable_2fa(user_id)
        updated_user = self.auth.get_user_by_id(user_id)
        self.assertFalse(updated_user.totp_enabled)
        self.assertIsNone(updated_user.totp_secret)
    
    def test_2fa_enable_with_invalid_code(self):
        """Test 2FA enable with invalid verification code"""
        user_id = self.regular_user.id
        
        # Setup 2FA
        secret, _ = self.auth.setup_2fa(user_id)
        
        # Try to enable with invalid code
        with self.assertRaises(InvalidTwoFactorError):
            self.auth.enable_2fa(user_id, "000000")
        
        # 2FA should not be enabled
        user = self.auth.get_user_by_id(user_id)
        self.assertFalse(user.totp_enabled)
    
    def test_api_token_creation(self):
        """Test API token creation and validation"""
        user_id = self.regular_user.id
        token_name = "Test Token"
        
        # Create token
        token = self.auth.create_api_token(user_id, token_name, expires_days=30)
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 43)  # URL-safe base64 with 32 bytes
        
        # Validate token
        validated_user = self.auth.validate_api_token(token)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.id, user_id)
        self.assertEqual(validated_user.username, "alice")
    
    def test_api_token_limit(self):
        """Test API token creation limit"""
        user_id = self.regular_user.id
        
        # Create maximum number of tokens
        tokens = []
        for i in range(self.auth.MAX_TOKENS_PER_USER):
            token = self.auth.create_api_token(user_id, f"Token {i+1}")
            tokens.append(token)
        
        # Creating one more should fail
        with self.assertRaises(TokenLimitExceededError):
            self.auth.create_api_token(user_id, "Extra Token")
        
        # Verify all tokens are valid
        for token in tokens:
            user = self.auth.validate_api_token(token)
            self.assertIsNotNone(user)
    
    def test_api_token_revocation(self):
        """Test API token revocation"""
        user_id = self.regular_user.id
        
        # Create token
        token = self.auth.create_api_token(user_id, "Test Token")
        
        # Verify token works
        user = self.auth.validate_api_token(token)
        self.assertIsNotNone(user)
        
        # Get token ID
        tokens = self.auth.list_user_tokens(user_id)
        token_id = tokens[0].id
        
        # Revoke token
        self.auth.revoke_api_token(user_id, token_id)
        
        # Token should no longer validate
        user = self.auth.validate_api_token(token)
        self.assertIsNone(user)
    
    def test_api_token_expiration(self):
        """Test API token expiration"""
        user_id = self.regular_user.id
        
        # Create token that expires immediately
        with patch('core.auth_engine.datetime') as mock_datetime:
            # Mock current time
            now = datetime.now()
            mock_datetime.now.return_value = now
            mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
            
            token = self.auth.create_api_token(user_id, "Test Token", expires_days=0)
            
            # Fast forward time
            future = now + timedelta(days=1)
            mock_datetime.now.return_value = future
            
            # Token should be expired
            user = self.auth.validate_api_token(token)
            self.assertIsNone(user)
    
    def test_invalid_token_validation(self):
        """Test validation of invalid tokens"""
        # Random token should fail
        user = self.auth.validate_api_token("invalid_token_12345")
        self.assertIsNone(user)
        
        # Empty token should fail
        user = self.auth.validate_api_token("")
        self.assertIsNone(user)
    
    def test_list_user_tokens(self):
        """Test listing user tokens"""
        user_id = self.regular_user.id
        
        # Create multiple tokens
        token_names = ["Token 1", "Token 2", "Token 3"]
        for name in token_names:
            self.auth.create_api_token(user_id, name)
        
        # List tokens
        tokens = self.auth.list_user_tokens(user_id)
        self.assertEqual(len(tokens), 3)
        
        # Verify token properties
        for i, token in enumerate(tokens):
            self.assertEqual(token.user_id, user_id)
            self.assertIn(f"Token {i+1}", [t.name for t in tokens])
            self.assertTrue(token.is_active)
            self.assertIsNotNone(token.created_at)
    
    def test_role_based_permissions(self):
        """Test role-based permission system"""
        # Test admin permissions
        admin = self.admin_user
        self.assertTrue(self.auth.check_permission(admin, Permission.USER_CREATE))
        self.assertTrue(self.auth.check_permission(admin, Permission.USER_DELETE))
        self.assertTrue(self.auth.check_permission(admin, Permission.SYSTEM_ADMIN))
        
        # Test operator permissions
        operator = self.regular_user
        self.assertFalse(self.auth.check_permission(operator, Permission.USER_CREATE))
        self.assertFalse(self.auth.check_permission(operator, Permission.USER_DELETE))
        self.assertTrue(self.auth.check_permission(operator, Permission.SYSTEM_READ))
        self.assertTrue(self.auth.check_permission(operator, Permission.TOKEN_CREATE))
        
        # Test viewer permissions
        viewer = self.viewer_user
        self.assertFalse(self.auth.check_permission(viewer, Permission.USER_CREATE))
        self.assertFalse(self.auth.check_permission(viewer, Permission.SYSTEM_WRITE))
        self.assertTrue(self.auth.check_permission(viewer, Permission.SYSTEM_READ))
        self.assertTrue(self.auth.check_permission(viewer, Permission.DASHBOARD_VIEW))
    
    def test_require_permission(self):
        """Test permission requirement enforcement"""
        # Admin should pass all checks
        try:
            self.auth.require_permission(self.admin_user, Permission.USER_CREATE)
            self.auth.require_permission(self.admin_user, Permission.SYSTEM_ADMIN)
        except PermissionDeniedError:
            self.fail("Admin should have all permissions")
        
        # Viewer should fail admin checks
        with self.assertRaises(PermissionDeniedError):
            self.auth.require_permission(self.viewer_user, Permission.USER_CREATE)
        
        with self.assertRaises(PermissionDeniedError):
            self.auth.require_permission(self.viewer_user, Permission.SYSTEM_ADMIN)
    
    def test_user_role_update(self):
        """Test updating user roles"""
        user_id = self.regular_user.id
        
        # Update role
        self.auth.update_user_role(user_id, UserRole.ADMIN)
        
        # Verify role changed
        updated_user = self.auth.get_user_by_id(user_id)
        self.assertEqual(updated_user.role, UserRole.ADMIN)
        
        # Verify new permissions
        self.assertTrue(self.auth.check_permission(updated_user, Permission.USER_CREATE))
        self.assertTrue(self.auth.check_permission(updated_user, Permission.SYSTEM_ADMIN))
    
    def test_user_activation_deactivation(self):
        """Test user activation and deactivation"""
        user_id = self.regular_user.id
        
        # Deactivate user
        self.auth.deactivate_user(user_id)
        user = self.auth.get_user_by_id(user_id)
        self.assertFalse(user.is_active)
        
        # Activate user
        self.auth.activate_user(user_id)
        user = self.auth.get_user_by_id(user_id)
        self.assertTrue(user.is_active)
        self.assertEqual(user.failed_attempts, 0)
        self.assertIsNone(user.locked_until)
    
    def test_list_users(self):
        """Test listing users with pagination"""
        # Create additional users
        for i in range(5):
            self.auth.create_user(f"user{i}", f"user{i}@test.com", "Pass123!", UserRole.VIEWER)
        
        # Test listing all users
        all_users = self.auth.list_users()
        self.assertGreaterEqual(len(all_users), 8)  # 3 original + 5 new
        
        # Test pagination
        page1 = self.auth.list_users(limit=3, offset=0)
        page2 = self.auth.list_users(limit=3, offset=3)
        
        self.assertEqual(len(page1), 3)
        self.assertEqual(len(page2), 3)
        
        # Users should be different
        page1_ids = {u.id for u in page1}
        page2_ids = {u.id for u in page2}
        self.assertTrue(page1_ids.isdisjoint(page2_ids))
    
    def test_get_user_by_username(self):
        """Test getting user by username"""
        user = self.auth.get_user_by_username("alice")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.email, "alice@test.com")
        
        # Non-existent user
        user = self.auth.get_user_by_username("nonexistent")
        self.assertIsNone(user)
    
    def test_get_user_by_id(self):
        """Test getting user by ID"""
        user_id = self.regular_user.id
        user = self.auth.get_user_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, user_id)
        self.assertEqual(user.username, "alice")
        
        # Non-existent user
        user = self.auth.get_user_by_id(99999)
        self.assertIsNone(user)
    
    def test_auth_event_logging(self):
        """Test authentication event logging"""
        # Perform some authentication events
        self.auth.authenticate_user("alice", "AlicePass123!", 
                                  ip_address="192.168.1.100", user_agent="Test Agent")
        
        try:
            self.auth.authenticate_user("alice", "wrongpassword",
                                      ip_address="192.168.1.200", user_agent="Test Agent")
        except InvalidCredentialsError:
            pass
        
        # Get events
        events = self.auth.get_auth_events(limit=10)
        self.assertGreater(len(events), 0)
        
        # Check event properties
        for event in events:
            self.assertIsNotNone(event.event_type)
            self.assertIsInstance(event.success, bool)
            self.assertIsNotNone(event.timestamp)
            self.assertIsInstance(event.details, dict)
        
        # Get events for specific user
        user_events = self.auth.get_auth_events(user_id=self.regular_user.id, limit=5)
        for event in user_events:
            self.assertEqual(event.user_id, self.regular_user.id)
    
    def test_dashboard_stats(self):
        """Test dashboard statistics generation"""
        # Create some tokens and enable 2FA
        self.auth.create_api_token(self.regular_user.id, "Test Token")
        secret, _ = self.auth.setup_2fa(self.regular_user.id)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        self.auth.enable_2fa(self.regular_user.id, current_code)
        
        # Deactivate one user
        self.auth.deactivate_user(self.viewer_user.id)
        
        # Get stats
        stats = self.auth.get_dashboard_stats()
        
        # Verify structure
        self.assertIn('users', stats)
        self.assertIn('tokens', stats)
        self.assertIn('recent_activity', stats)
        self.assertIn('role_distribution', stats)
        
        # Verify user stats
        self.assertEqual(stats['users']['total'], 3)
        self.assertEqual(stats['users']['active'], 2)
        self.assertEqual(stats['users']['with_2fa'], 1)
        
        # Verify token stats
        self.assertEqual(stats['tokens']['active'], 1)
        
        # Verify role distribution
        self.assertIn('admin', stats['role_distribution'])
        self.assertIn('operator', stats['role_distribution'])
        self.assertIn('viewer', stats['role_distribution'])
    
    def test_token_last_used_update(self):
        """Test that token last_used timestamp is updated"""
        user_id = self.regular_user.id
        
        # Create token
        token = self.auth.create_api_token(user_id, "Test Token")
        
        # Get initial token info
        tokens = self.auth.list_user_tokens(user_id)
        initial_token = tokens[0]
        self.assertIsNone(initial_token.last_used)
        
        # Use token
        self.auth.validate_api_token(token)
        
        # Check last_used was updated
        tokens = self.auth.list_user_tokens(user_id)
        updated_token = tokens[0]
        self.assertIsNotNone(updated_token.last_used)
    
    def test_user_deactivation_revokes_tokens(self):
        """Test that deactivating user revokes all tokens"""
        user_id = self.regular_user.id
        
        # Create tokens
        token1 = self.auth.create_api_token(user_id, "Token 1")
        token2 = self.auth.create_api_token(user_id, "Token 2")
        
        # Verify tokens work
        self.assertIsNotNone(self.auth.validate_api_token(token1))
        self.assertIsNotNone(self.auth.validate_api_token(token2))
        
        # Deactivate user
        self.auth.deactivate_user(user_id)
        
        # Tokens should no longer validate
        self.assertIsNone(self.auth.validate_api_token(token1))
        self.assertIsNone(self.auth.validate_api_token(token2))
    
    def test_authentication_with_metadata(self):
        """Test authentication with IP and user agent logging"""
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0 (Test Browser)"
        
        user = self.auth.authenticate_user("alice", "AlicePass123!", 
                                         ip_address=ip_address, user_agent=user_agent)
        self.assertIsNotNone(user)
        
        # Check that metadata was logged
        events = self.auth.get_auth_events(user_id=user.id, limit=1)
        self.assertEqual(len(events), 1)
        
        event = events[0]
        self.assertEqual(event.ip_address, ip_address)
        self.assertEqual(event.user_agent, user_agent)
        self.assertTrue(event.success)
        self.assertEqual(event.event_type, "login_success")

def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAuthEngine)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    import sys
    sys.exit(run_tests())