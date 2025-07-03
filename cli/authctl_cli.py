#!/usr/bin/env python3
"""
LNMT Authentication Controller CLI
=================================

Command-line interface for managing LNMT authentication:
- User management (create, list, update, deactivate)
- API token management (create, list, revoke)
- 2FA setup and management
- Authentication audit logs
- System statistics

Usage Examples:
    authctl user create alice alice@company.com --role operator
    authctl user list --active-only
    authctl user 2fa setup alice
    authctl token create alice "API Access" --expires 90
    authctl token list alice
    authctl audit --user alice --limit 50
    authctl stats
"""

import sys
import os
import argparse
import getpass
import json
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth_engine import (
    AuthEngine, UserRole, Permission, User, APIToken,
    InvalidCredentialsError, AccountLockedError, TwoFactorRequiredError,
    InvalidTwoFactorError, PermissionDeniedError, TokenLimitExceededError
)

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_success(message: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message: str):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message: str):
    """Print info message in blue"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_header(message: str):
    """Print header message in bold"""
    print(f"{Colors.BOLD}{Colors.UNDERLINE}{message}{Colors.END}")

def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display"""
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_role(role: UserRole) -> str:
    """Format role with color"""
    colors = {
        UserRole.ADMIN: Colors.RED,
        UserRole.MANAGER: Colors.MAGENTA,
        UserRole.OPERATOR: Colors.BLUE,
        UserRole.VIEWER: Colors.CYAN,
        UserRole.GUEST: Colors.WHITE
    }
    color = colors.get(role, Colors.WHITE)
    return f"{color}{role.value.upper()}{Colors.END}"

def format_status(is_active: bool) -> str:
    """Format status with color"""
    if is_active:
        return f"{Colors.GREEN}ACTIVE{Colors.END}"
    else:
        return f"{Colors.RED}INACTIVE{Colors.END}"

def confirm_action(message: str) -> bool:
    """Prompt user for confirmation"""
    response = input(f"{message} (y/N): ").strip().lower()
    return response in ['y', 'yes']

class AuthCLI:
    """Authentication CLI controller"""
    
    def __init__(self, db_path: str = "lnmt.db"):
        self.auth_engine = AuthEngine(db_path)
        self.current_user: Optional[User] = None
    
    def authenticate_admin(self) -> bool:
        """Authenticate admin user for sensitive operations"""
        print_header("Administrator Authentication Required")
        
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        try:
            user = self.auth_engine.authenticate_user(username, password)
            
            # Require admin or manager role
            if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
                print_error("Administrative privileges required")
                return False
            
            self.current_user = user
            print_success(f"Authenticated as {username} ({user.role.value})")
            return True
            
        except (InvalidCredentialsError, AccountLockedError) as e:
            print_error(f"Authentication failed: {e}")
            return False
        except TwoFactorRequiredError:
            totp_code = input("2FA Code: ")
            try:
                user = self.auth_engine.authenticate_user(username, password, totp_code)
                if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
                    print_error("Administrative privileges required")
                    return False
                self.current_user = user
                print_success(f"Authenticated as {username} ({user.role.value})")
                return True
            except InvalidTwoFactorError:
                print_error("Invalid 2FA code")
                return False
    
    def cmd_user_create(self, args):
        """Create new user"""
        if not self.authenticate_admin():
            return 1
        
        try:
            # Validate role
            try:
                role = UserRole(args.role)
            except ValueError:
                print_error(f"Invalid role: {args.role}")
                print_info(f"Valid roles: {', '.join([r.value for r in UserRole])}")
                return 1
            
            # Get password
            if args.password:
                password = args.password
                print_warning("Password provided via command line (insecure)")
            else:
                password = getpass.getpass("Password: ")
                password_confirm = getpass.getpass("Confirm password: ")
                
                if password != password_confirm:
                    print_error("Passwords do not match")
                    return 1
            
            # Create user
            user = self.auth_engine.create_user(args.username, args.email, password, role)
            print_success(f"User '{args.username}' created with ID {user.id}")
            
            if args.enable_2fa:
                self._setup_2fa_interactive(user.id)
            
            return 0
            
        except ValueError as e:
            print_error(str(e))
            return 1
        except Exception as e:
            print_error(f"Failed to create user: {e}")
            return 1
    
    def cmd_user_list(self, args):
        """List users"""
        try:
            users = self.auth_engine.list_users(limit=args.limit, offset=args.offset)
            
            if args.active_only:
                users = [u for u in users if u.is_active]
            
            if not users:
                print_info("No users found")
                return 0
            
            print_header(f"Users ({len(users)} found)")
            print()
            
            # Table header
            print(f"{'ID':<4} {'Username':<20} {'Email':<30} {'Role':<12} {'Status':<10} {'2FA':<5} {'Last Login':<20}")
            print("-" * 110)
            
            for user in users:
                status = format_status(user.is_active)
                role = format_role(user.role)
                twofa = f"{Colors.GREEN}YES{Colors.END}" if user.totp_enabled else f"{Colors.RED}NO{Colors.END}"
                last_login = format_datetime(user.last_login)
                
                print(f"{user.id:<4} {user.username:<20} {user.email:<30} {role:<20} {status:<18} {twofa:<13} {last_login}")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to list users: {e}")
            return 1
    
    def cmd_user_update(self, args):
        """Update user"""
        if not self.authenticate_admin():
            return 1
        
        try:
            user = self.auth_engine.get_user_by_id(args.user_id)
            if not user:
                print_error(f"User with ID {args.user_id} not found")
                return 1
            
            print_info(f"Updating user: {user.username} ({user.email})")
            
            if args.role:
                try:
                    new_role = UserRole(args.role)
                    if confirm_action(f"Change role from {user.role.value} to {new_role.value}?"):
                        self.auth_engine.update_user_role(args.user_id, new_role)
                        print_success(f"Role updated to {new_role.value}")
                except ValueError:
                    print_error(f"Invalid role: {args.role}")
                    return 1
            
            if args.activate:
                if confirm_action(f"Activate user {user.username}?"):
                    self.auth_engine.activate_user(args.user_id)
                    print_success("User activated")
            
            if args.deactivate:
                if confirm_action(f"Deactivate user {user.username}?"):
                    self.auth_engine.deactivate_user(args.user_id)
                    print_success("User deactivated")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to update user: {e}")
            return 1
    
    def _setup_2fa_interactive(self, user_id: int):
        """Interactive 2FA setup"""
        try:
            secret, qr_url = self.auth_engine.setup_2fa(user_id)
            
            print_header("Two-Factor Authentication Setup")
            print()
            print("1. Install Google Authenticator or Microsoft Authenticator on your phone")
            print("2. Scan the QR code below or manually enter the secret key")
            print("3. Enter the 6-digit code from your authenticator app")
            print()
            print(f"Secret Key: {Colors.BOLD}{secret}{Colors.END}")
            print(f"QR Code: {qr_url}")
            print()
            
            # Verify setup
            for attempt in range(3):
                totp_code = input("Enter 6-digit code from authenticator: ")
                
                try:
                    self.auth_engine.enable_2fa(user_id, totp_code)
                    print_success("Two-factor authentication enabled successfully!")
                    return True
                except InvalidTwoFactorError:
                    remaining = 2 - attempt
                    if remaining > 0:
                        print_error(f"Invalid code. {remaining} attempts remaining.")
                    else:
                        print_error("Too many invalid attempts. 2FA setup cancelled.")
                        return False
            
        except Exception as e:
            print_error(f"Failed to setup 2FA: {e}")
            return False
    
    def cmd_user_2fa(self, args):
        """Manage user 2FA"""
        if not self.authenticate_admin():
            return 1
        
        try:
            user = self.auth_engine.get_user_by_username(args.username)
            if not user:
                print_error(f"User '{args.username}' not found")
                return 1
            
            if args.action == 'setup':
                if user.totp_enabled:
                    if not confirm_action(f"User {args.username} already has 2FA enabled. Reset?"):
                        return 0
                
                if self._setup_2fa_interactive(user.id):
                    return 0
                else:
                    return 1
            
            elif args.action == 'disable':
                if not user.totp_enabled:
                    print_info(f"User {args.username} does not have 2FA enabled")
                    return 0
                
                if confirm_action(f"Disable 2FA for user {args.username}?"):
                    self.auth_engine.disable_2fa(user.id)
                    print_success("Two-factor authentication disabled")
                
            elif args.action == 'status':
                status = "ENABLED" if user.totp_enabled else "DISABLED"
                color = Colors.GREEN if user.totp_enabled else Colors.RED
                print(f"2FA Status for {args.username}: {color}{status}{Colors.END}")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to manage 2FA: {e}")
            return 1
    
    def cmd_token_create(self, args):
        """Create API token"""
        if not self.authenticate_admin():
            return 1
        
        try:
            user = self.auth_engine.get_user_by_username(args.username)
            if not user:
                print_error(f"User '{args.username}' not found")
                return 1
            
            if not user.is_active:
                print_error(f"User '{args.username}' is not active")
                return 1
            
            token = self.auth_engine.create_api_token(
                user.id, args.name, args.expires
            )
            
            print_success(f"API token created for user {args.username}")
            print()
            print(f"{Colors.BOLD}Token Name:{Colors.END} {args.name}")
            print(f"{Colors.BOLD}Token:{Colors.END} {token}")
            print(f"{Colors.BOLD}Expires:{Colors.END} {args.expires} days")
            print()
            print_warning("Save this token securely - it will not be shown again!")
            
            return 0
            
        except TokenLimitExceededError as e:
            print_error(str(e))
            return 1
        except Exception as e:
            print_error(f"Failed to create token: {e}")
            return 1
    
    def cmd_token_list(self, args):
        """List API tokens"""
        try:
            user = self.auth_engine.get_user_by_username(args.username)
            if not user:
                print_error(f"User '{args.username}' not found")
                return 1
            
            tokens = self.auth_engine.list_user_tokens(user.id)
            
            if args.active_only:
                tokens = [t for t in tokens if t.is_active]
            
            if not tokens:
                print_info(f"No tokens found for user {args.username}")
                return 0
            
            print_header(f"API Tokens for {args.username} ({len(tokens)} found)")
            print()
            
            # Table header
            print(f"{'ID':<4} {'Name':<20} {'Status':<10} {'Created':<20} {'Last Used':<20} {'Expires':<20}")
            print("-" * 100)
            
            for token in tokens:
                status = format_status(token.is_active)
                created = format_datetime(token.created_at)
                last_used = format_datetime(token.last_used)
                expires = format_datetime(token.expires_at)
                
                print(f"{token.id:<4} {token.name:<20} {status:<18} {created:<20} {last_used:<20} {expires}")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to list tokens: {e}")
            return 1
    
    def cmd_token_revoke(self, args):
        """Revoke API token"""
        if not self.authenticate_admin():
            return 1
        
        try:
            user = self.auth_engine.get_user_by_username(args.username)
            if not user:
                print_error(f"User '{args.username}' not found")
                return 1
            
            if confirm_action(f"Revoke token ID {args.token_id} for user {args.username}?"):
                self.auth_engine.revoke_api_token(user.id, args.token_id)
                print_success(f"Token {args.token_id} revoked")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to revoke token: {e}")
            return 1
    
    def cmd_audit(self, args):
        """Show authentication audit log"""
        try:
            user_id = None
            if args.user:
                user = self.auth_engine.get_user_by_username(args.user)
                if not user:
                    print_error(f"User '{args.user}' not found")
                    return 1
                user_id = user.id
            
            events = self.auth_engine.get_auth_events(
                user_id=user_id, limit=args.limit, offset=args.offset
            )
            
            if not events:
                print_info("No authentication events found")
                return 0
            
            header = f"Authentication Events ({len(events)} found)"
            if args.user:
                header += f" for user {args.user}"
            print_header(header)
            print()
            
            for event in events:
                timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                status_color = Colors.GREEN if event.success else Colors.RED
                status = f"{status_color}{'SUCCESS' if event.success else 'FAILED'}{Colors.END}"
                
                print(f"{Colors.BOLD}{timestamp}{Colors.END} - {event.event_type} - {status}")
                
                if event.ip_address:
                    print(f"  IP: {event.ip_address}")
                
                if event.details:
                    for key, value in event.details.items():
                        print(f"  {key}: {value}")
                
                print()
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to get audit log: {e}")
            return 1
    
    def cmd_stats(self, args):
        """Show authentication statistics"""
        try:
            stats = self.auth_engine.get_dashboard_stats()
            
            print_header("LNMT Authentication Statistics")
            print()
            
            # User statistics
            print(f"{Colors.BOLD}Users:{Colors.END}")
            print(f"  Total: {stats['users']['total']}")
            print(f"  Active: {Colors.GREEN}{stats['users']['active']}{Colors.END}")
            print(f"  Locked: {Colors.RED}{stats['users']['locked']}{Colors.END}")
            print(f"  With 2FA: {Colors.CYAN}{stats['users']['with_2fa']}{Colors.END}")
            print()
            
            # Token statistics
            print(f"{Colors.BOLD}API Tokens:{Colors.END}")
            print(f"  Active: {Colors.GREEN}{stats['tokens']['active']}{Colors.END}")
            print()
            
            # Recent activity
            print(f"{Colors.BOLD}Recent Activity (24h):{Colors.END}")
            print(f"  Successful logins: {Colors.GREEN}{stats['recent_activity']['successful_logins_24h']}{Colors.END}")
            print(f"  Failed logins: {Colors.RED}{stats['recent_activity']['failed_logins_24h']}{Colors.END}")
            print()
            
            # Role distribution
            print(f"{Colors.BOLD}Role Distribution:{Colors.END}")
            for role, count in stats['role_distribution'].items():
                print(f"  {role.upper()}: {count}")
            
            return 0
            
        except Exception as e:
            print_error(f"Failed to get statistics: {e}")
            return 1

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LNMT Authentication Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s user create alice alice@company.com --role operator
  %(prog)s user list --active-only
  %(prog)s user 2fa setup alice
  %(prog)s token create alice "API Access" --expires 90
  %(prog)s token list alice
  %(prog)s audit --user alice --limit 50
  %(prog)s stats
        """
    )
    
    parser.add_argument('--db', default='lnmt.db', help='Database path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # User management commands
    user_parser = subparsers.add_parser('user', help='User management')
    user_subparsers = user_parser.add_subparsers(dest='user_action', help='User actions')
    
    # User create
    user_create = user_subparsers.add_parser('create', help='Create user')
    user_create.add_argument('username', help='Username')
    user_create.add_argument('email', help='Email address')
    user_create.add_argument('--role', default='viewer', 
                           choices=[r.value for r in UserRole],
                           help='User role')
    user_create.add_argument('--password', help='Password (will prompt if not provided)')
    user_create.add_argument('--enable-2fa', action='store_true', 
                           help='Enable 2FA during creation')
    
    # User list
    user_list = user_subparsers.add_parser('list', help='List users')
    user_list.add_argument('--active-only', action='store_true', 
                         help='Show only active users')
    user_list.add_argument('--limit', type=int, default=100, help='Limit results')
    user_list.add_argument('--offset', type=int, default=0, help='Offset results')
    
    # User update
    user_update = user_subparsers.add_parser('update', help='Update user')
    user_update.add_argument('user_id', type=int, help='User ID')
    user_update.add_argument('--role', choices=[r.value for r in UserRole],
                           help='New role')
    user_update.add_argument('--activate', action='store_true', help='Activate user')
    user_update.add_argument('--deactivate', action='store_true', help='Deactivate user')
    
    # User 2FA
    user_2fa = user_subparsers.add_parser('2fa', help='Manage 2FA')
    user_2fa.add_argument('action', choices=['setup', 'disable', 'status'],
                         help='2FA action')
    user_2fa.add_argument('username', help='Username')
    
    # Token management commands
    token_parser = subparsers.add_parser('token', help='Token management')
    token_subparsers = token_parser.add_subparsers(dest='token_action', help='Token actions')
    
    # Token create
    token_create = token_subparsers.add_parser('create', help='Create token')
    token_create.add_argument('username', help='Username')
    token_create.add_argument('name', help='Token name')
    token_create.add_argument('--expires', type=int, default=30,
                            help='Expiration in days')
    
    # Token list
    token_list = token_subparsers.add_parser('list', help='List tokens')
    token_list.add_argument('username', help='Username')
    token_list.add_argument('--active-only', action='store_true',
                          help='Show only active tokens')
    
    # Token revoke
    token_revoke = token_subparsers.add_parser('revoke', help='Revoke token')
    token_revoke.add_argument('username', help='Username')
    token_revoke.add_argument('token_id', type=int, help='Token ID')
    
    # Audit commands
    audit_parser = subparsers.add_parser('audit', help='Authentication audit log')
    audit_parser.add_argument('--user', help='Filter by username')
    audit_parser.add_argument('--limit', type=int, default=50, help='Limit results')
    audit_parser.add_argument('--offset', type=int, default=0, help='Offset results')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Authentication statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    cli = AuthCLI(args.db)
    
    try:
        # Route commands
        if args.command == 'user':
            if args.user_action == 'create':
                return cli.cmd_user_create(args)
            elif args.user_action == 'list':
                return cli.cmd_user_list(args)
            elif args.user_action == 'update':
                return cli.cmd_user_update(args)
            elif args.user_action == '2fa':
                return cli.cmd_user_2fa(args)
            else:
                user_parser.print_help()
                return 1
        
        elif args.command == 'token':
            if args.token_action == 'create':
                return cli.cmd_token_create(args)
            elif args.token_action == 'list':
                return cli.cmd_token_list(args)
            elif args.token_action == 'revoke':
                return cli.cmd_token_revoke(args)
            else:
                token_parser.print_help()
                return 1
        
        elif args.command == 'audit':
            return cli.cmd_audit(args)
        
        elif args.command == 'stats':
            return cli.cmd_stats(args)
        
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print_info("\nOperation cancelled")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())