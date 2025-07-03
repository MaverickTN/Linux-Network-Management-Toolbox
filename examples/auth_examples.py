#!/usr/bin/env python3
"""
LNMT Authentication Engine Examples
==================================

This file demonstrates how to use the LNMT authentication engine
for various common scenarios:

1. Basic user management
2. Password authentication with 2FA
3. API token management  
4. Role-based access control
5. Audit logging and monitoring
6. Integration patterns for CLI and web apps

Run with: python examples/auth_examples.py
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth_engine import (
    AuthEngine, UserRole, Permission, User, APIToken,
    InvalidCredentialsError, AccountLockedError, TwoFactorRequiredError,
    InvalidTwoFactorError, PermissionDeniedError, TokenLimitExceededError
)

def example_basic_user_management():
    """Example 1: Basic user management operations"""
    print("=" * 60)
    print("Example 1: Basic User Management")
    print("=" * 60)
    
    # Initialize auth engine with test database
    auth = AuthEngine("example_auth.db")
    
    try:
        # Create admin user
        admin = auth.create_user(
            username="admin",
            email="admin@company.com", 
            password="SecureAdminPass123!",
            role=UserRole.ADMIN
        )
        print(f"✓ Created admin user: {admin.username} (ID: {admin.id})")
        
        # Create regular users with different roles
        users_to_create = [
            ("alice", "alice@company.com", "AlicePass123!", UserRole.MANAGER),
            ("bob", "bob@company.com", "BobPass123!", UserRole.OPERATOR),
            ("charlie", "charlie@company.com", "CharliePass123!", UserRole.VIEWER),
            ("guest", "guest@company.com", "GuestPass123!", UserRole.GUEST)
        ]
        
        created_users = []
        for username, email, password, role in users_to_create:
            user = auth.create_user(username, email, password, role)
            created_users.append(user)
            print(f"✓ Created user: {username} ({role.value})")
        
        # List all users
        print("\nUser List:")
        all_users = auth.list_users()
        for user in all_users:
            status = "Active" if user.is_active else "Inactive"
            print(f"  {user.id}: {user.username} <{user.email}> - {user.role.value} ({status})")
        
        # Update user role
        alice = auth.get_user_by_username("alice")
        print(f"\nUpdating Alice's role from {alice.role.value} to admin...")
        auth.update_user_role(alice.id, UserRole.ADMIN)
        print("✓ Role updated")
        
        # Deactivate user
        print("\nDeactivating guest user...")
        guest = auth.get_user_by_username("guest")
        auth.deactivate_user(guest.id)
        print("✓ User deactivated")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_authentication_with_2fa():
    """Example 2: Authentication with 2FA setup"""
    print("\n" + "=" * 60)
    print("Example 2: Authentication with 2FA")
    print("=" * 60)
    
    auth = AuthEngine("example_auth.db")
    
    try:
        # Get existing user
        alice = auth.get_user_by_username("alice")
        if not alice:
            print("✗ Alice user not found (run example 1 first)")
            return
        
        # Setup 2FA for Alice
        print("Setting up 2FA for Alice...")
        secret, qr_url = auth.setup_2fa(alice.id)
        print(f"✓ 2FA secret generated: {secret}")
        print(f"✓ QR code available at: {qr_url[:50]}...")
        
        # Simulate enabling 2FA (normally user would scan QR code)
        import pyotp
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        print(f"Current TOTP code: {current_code}")
        
        auth.enable_2fa(alice.id, current_code)
        print("✓ 2FA enabled for Alice")
        
        # Test authentication without 2FA (should fail)
        print("\nTesting authentication without 2FA...")
        try:
            auth.authenticate_user("alice", "AlicePass123!")
            print("✗ Authentication should have failed")
        except TwoFactorRequiredError:
            print("✓ 2FA required as expected")
        
        # Test authentication with 2FA
        print("\nTesting authentication with 2FA...")
        current_code = totp.now()
        authenticated_user = auth.authenticate_user("alice", "AlicePass123!", current_code)
        print(f"✓ Authentication successful for {authenticated_user.username}")
        
        # Test invalid 2FA code
        print("\nTesting invalid 2FA code...")
        try:
            auth.authenticate_user("alice", "AlicePass123!", "000000")
            print("✗ Authentication should have failed")
        except InvalidTwoFactorError:
            print("✓ Invalid 2FA code rejected as expected")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_api_token_management():
    """Example 3: API token management"""
    print("\n" + "=" * 60)
    print("Example 3: API Token Management")
    print("=" * 60)
    
    auth = AuthEngine("example_auth.db")
    
    try:
        # Get existing user
        bob = auth.get_user_by_username("bob")
        if not bob:
            print("✗ Bob user not found (run example 1 first)")
            return
        
        # Create multiple API tokens
        token_names = [
            "Mobile App Access",
            "CI/CD Pipeline", 
            "External Integration",
            "Development Testing"
        ]
        
        created_tokens = []
        for name in token_names:
            token = auth.create_api_token(bob.id, name, expires_days=30)
            created_tokens.append(token)
            print(f"✓ Created token: {name}")
            print(f"  Token: {token[:20]}...")
        
        # Try to create too many tokens (should fail)
        print("\nTesting token limit...")
        try:
            auth.create_api_token(bob.id, "Extra Token", expires_days=30)
            print("✗ Should have hit token limit")
        except TokenLimitExceededError:
            print("✓ Token limit enforced correctly")
        
        # List user tokens
        print(f"\nTokens for {bob.username}:")
        tokens = auth.list_user_tokens(bob.id)
        for token in tokens:
            status = "Active" if token.is_active else "Revoked"
            expires = token.expires_at.strftime("%Y-%m-%d") if token.expires_at else "Never"
            print(f"  {token.id}: {token.name} - {status} (expires: {expires})")
        
        # Validate token
        print("\nValidating API token...")
        test_token = created_tokens[0]
        validated_user = auth.validate_api_token(test_token)
        if validated_user:
            print(f"✓ Token valid for user: {validated_user.username}")
        else:
            print("✗ Token validation failed")
        
        # Revoke token
        print("\nRevoking token...")
        first_token = tokens[0]
        auth.revoke_api_token(bob.id, first_token.id)
        print(f"✓ Revoked token: {first_token.name}")
        
        # Try to validate revoked token
        revoked_user = auth.validate_api_token(test_token)
        if revoked_user:
            print("✗ Revoked token should not validate")
        else:
            print("✓ Revoked token correctly rejected")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_role_based_access_control():
    """Example 4: Role-based access control"""
    print("\n" + "=" * 60)
    print("Example 4: Role-Based Access Control")
    print("=" * 60)
    
    auth = AuthEngine("example_auth.db")
    
    try:
        # Get users with different roles
        admin = auth.get_user_by_username("admin")
        alice = auth.get_user_by_username("alice")  # Now admin after role update
        bob = auth.get_user_by_username("bob")      # Operator
        charlie = auth.get_user_by_username("charlie")  # Viewer
        
        if not all([admin, alice, bob, charlie]):
            print("✗ Some users not found (run example 1 first)")
            return
        
        # Test permissions for different roles
        test_permissions = [
            Permission.USER_CREATE,
            Permission.USER_DELETE,
            Permission.TOKEN_CREATE,
            Permission.SYSTEM_ADMIN,
            Permission.DASHBOARD_VIEW
        ]
        
        users_to_test = [
            ("Admin", admin),
            ("Alice (Admin)", alice),
            ("Bob (Operator)", bob),
            ("Charlie (Viewer)", charlie)
        ]
        
        print("Permission Matrix:")
        print(f"{'User':<15} {'Role':<10} {'USER_CREATE':<12} {'USER_DELETE':<12} {'TOKEN_CREATE':<13} {'SYSTEM_ADMIN':<13} {'DASHBOARD_VIEW'}")
        print("-" * 95)
        
        for name, user in users_to_test:
            permissions = []
            for perm in test_permissions:
                has_perm = auth.check_permission(user, perm)
                permissions.append("✓" if has_perm else "✗")
            
            print(f"{name:<15} {user.role.value:<10} {permissions[0]:<12} {permissions[1]:<12} {permissions[2]:<13} {permissions[3]:<13} {permissions[4]}")
        
        # Test permission enforcement
        print("\nTesting permission enforcement...")
        
        # Admin should be able to create users
        try:
            auth.require_permission(admin, Permission.USER_CREATE)
            print("✓ Admin can create users")
        except PermissionDeniedError:
            print("✗ Admin should be able to create users")
        
        # Viewer should not be able to delete users
        try:
            auth.require_permission(charlie, Permission.USER_DELETE)
            print("✗ Viewer should not be able to delete users")
        except PermissionDeniedError:
            print("✓ Viewer correctly denied user deletion")
        
        # Operator should be able to create tokens but not manage users
        try:
            auth.require_permission(bob, Permission.TOKEN_CREATE)
            print("✓ Operator can create tokens")
        except PermissionDeniedError:
            print("✗ Operator should be able to create tokens")
        
        try:
            auth.require_permission(bob, Permission.USER_DELETE)
            print("✗ Operator should not be able to delete users")
        except PermissionDeniedError:
            print("✓ Operator correctly denied user deletion")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_audit_logging():
    """Example 5: Audit logging and monitoring"""
    print("\n" + "=" * 60)
    print("Example 5: Audit Logging and Monitoring")
    print("=" * 60)
    
    auth = AuthEngine("example_auth.db")
    
    try:
        # Generate some authentication events
        print("Generating authentication events...")
        
        # Successful login
        alice = auth.get_user_by_username("alice")
        if alice and alice.totp_enabled:
            import pyotp
            totp = pyotp.TOTP(alice.totp_secret)
            current_code = totp.now()
            auth.authenticate_user("alice", "AlicePass123!", current_code, 
                                 ip_address="192.168.1.100", user_agent="Mozilla/5.0...")
        
        # Failed login attempts
        try:
            auth.authenticate_user("alice", "wrongpassword", 
                                 ip_address="192.168.1.200", user_agent="curl/7.68.0")
        except (InvalidCredentialsError, TwoFactorRequiredError):
            pass
        
        try:
            auth.authenticate_user("nonexistent", "password",
                                 ip_address="10.0.0.50", user_agent="Python/3.9")
        except InvalidCredentialsError:
            pass
        
        # Get audit events
        print("\nRecent authentication events:")
        events = auth.get_auth_events(limit=10)
        
        for event in events[-5:]:  # Show last 5 events
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = "SUCCESS" if event.success else "FAILED"
            user_info = f"User {event.user_id}" if event.user_id else "Unknown user"
            
            print(f"  {timestamp} - {event.event_type} - {status}")
            print(f"    {user_info}")
            if event.ip_address:
                print(f"    IP: {event.ip_address}")
            if event.details:
                print(f"    Details: {event.details}")
            print()
        
        # Get dashboard statistics
        print("Dashboard Statistics:")
        stats = auth.get_dashboard_stats()
        
        print(f"  Users: {stats['users']['active']}/{stats['users']['total']} active")
        print(f"  Locked accounts: {stats['users']['locked']}")
        print(f"  Users with 2FA: {stats['users']['with_2fa']}")
        print(f"  Active tokens: {stats['tokens']['active']}")
        print(f"  Successful logins (24h): {stats['recent_activity']['successful_logins_24h']}")
        print(f"  Failed logins (24h): {stats['recent_activity']['failed_logins_24h']}")
        
        print("\n  Role Distribution:")
        for role, count in stats['role_distribution'].items():
            print(f"    {role.upper()}: {count}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def example_integration_patterns():
    """Example 6: Integration patterns for CLI and web apps"""
    print("\n" + "=" * 60)
    print("Example 6: Integration Patterns")
    print("=" * 60)
    
    auth = AuthEngine("example_auth.db")
    
    try:
        # Simulate CLI authentication workflow
        print("CLI Authentication Workflow:")
        print("1. User provides credentials")
        
        # Simulate user input (in real CLI, this would be getpass)
        username = "alice"
        password = "AlicePass123!"
        
        try:
            # First attempt - will require 2FA
            user = auth.authenticate_user(username, password, 
                                        ip_address="127.0.0.1", user_agent="LNMT CLI v1.0")
            print(f"✓ Authenticated: {user.username}")
        except TwoFactorRequiredError:
            print("2. 2FA required, prompting user for code")
            
            # Simulate 2FA code entry
            alice = auth.get_user_by_username("alice")
            if alice and alice.totp_enabled:
                import pyotp
                totp = pyotp.TOTP(alice.totp_secret)
                totp_code = totp.now()
                print(f"   User enters code: {totp_code}")
                
                user = auth.authenticate_user(username, password, totp_code,
                                            ip_address="127.0.0.1", user_agent="LNMT CLI v1.0")
                print(f"✓ Authenticated with 2FA: {user.username}")
        
        # Simulate API authentication workflow
        print("\nAPI Authentication Workflow:")
        print("1. Client provides API token in header")
        
        # Get a valid token
        bob = auth.get_user_by_username("bob")
        if bob:
            tokens = auth.list_user_tokens(bob.id)
            active_tokens = [t for t in tokens if t.is_active]
            
            if active_tokens:
                # Simulate API request with token
                api_token = "your_actual_token_here"  # In real usage, this would be the actual token
                print(f"   Authorization: Bearer {api_token[:20]}...")
                
                # Validate token (in real API, you'd use the actual token)
                # For demo, we'll just show the pattern
                print("2. Server validates token")
                user = auth.validate_api_token("dummy")  # This will return None for demo
                if user:
                    print(f"✓ Token valid for user: {user.username}")
                    print("3. Check permissions for requested operation")
                    
                    if auth.check_permission(user, Permission.SYSTEM_READ):
                        print("✓ Permission granted")
                    else:
                        print("✗ Permission denied")
                else:
                    print("✗ Invalid token (expected for demo)")
        
        # Simulate session management
        print("\nWeb App Session Workflow:")
        print("1. User logs in via web form")
        print("2. Server creates session and stores user ID")
        print("3. Subsequent requests validate session")
        print("4. Permission checks for each protected resource")
        
        # Example session validation function
        def validate_session(session_user_id: int, required_permission: Permission) -> bool:
            """Example session validation for web apps"""
            user = auth.get_user_by_id(session_user_id)
            if not user or not user.is_active:
                return False
            
            return auth.check_permission(user, required_permission)
        
        # Test session validation
        alice = auth.get_user_by_username("alice")
        if alice:
            can_admin = validate_session(alice.id, Permission.SYSTEM_ADMIN)
            print(f"✓ Alice can access admin functions: {can_admin}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def cleanup_example_database():
    """Clean up example database"""
    import os
    try:
        if os.path.exists("example_auth.db"):
            os.remove("example_auth.db")
            print("\n✓ Cleaned up example database")
    except Exception as e:
        print(f"✗ Failed to clean up: {e}")

def main():
    """Run all examples"""
    print("LNMT Authentication Engine Examples")
    print("==================================")
    print()
    print("This script demonstrates the key features of the LNMT auth engine.")
    print("It will create a temporary database and show various authentication")
    print("scenarios including user management, 2FA, tokens, and RBAC.")
    print()
    
    input("Press Enter to continue...")
    
    try:
        # Run examples in order
        example_basic_user_management()
        example_authentication_with_2fa() 
        example_api_token_management()
        example_role_based_access_control()
        example_audit_logging()
        example_integration_patterns()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print()
        print("Key takeaways:")
        print("- User management with role-based permissions")
        print("- Secure password hashing with PBKDF2")
        print("- TOTP-based 2FA with QR code generation")
        print("- API token management with expiration")
        print("- Comprehensive audit logging")
        print("- Flexible integration patterns")
        print()
        print("Next steps:")
        print("- Review the auth_engine.py implementation")
        print("- Try the CLI tool: python cli/authctl.py --help")
        print("- Integrate with your application using the patterns shown")
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_example_database()

if __name__ == '__main__':
    main()