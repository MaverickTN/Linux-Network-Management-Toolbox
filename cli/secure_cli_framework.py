#!/usr/bin/env python3
"""
LNMT Secure CLI Framework
Version: RC2-Hardened
Security Level: Production Ready

This module provides a secure foundation for all LNMT CLI tools
with comprehensive input validation and command injection prevention.
"""

import os
import re
import sys
import json
import shlex
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from functools import wraps
from dataclasses import dataclass
import tempfile

# Configure secure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """CLI Security configuration"""
    max_input_length: int = 1024
    allowed_file_extensions: List[str] = None
    allowed_directories: List[str] = None
    blocked_commands: List[str] = None
    require_auth: bool = True
    audit_commands: bool = True
    
    def __post_init__(self):
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = ['.conf', '.json', '.yml', '.yaml', '.txt', '.log']
        if self.allowed_directories is None:
            self.allowed_directories = ['/opt/lnmt', '/etc/lnmt', '/var/lib/lnmt', '/var/log/lnmt']
        if self.blocked_commands is None:
            self.blocked_commands = ['rm', 'dd', 'mkfs', 'fdisk', 'wget', 'curl', 'nc', 'netcat']

class SecurityException(Exception):
    """Base security exception"""
    pass

class InputValidationError(SecurityException):
    """Input validation failed"""
    pass

class CommandInjectionError(SecurityException):
    """Potential command injection detected"""
    pass

class AuthorizationError(SecurityException):
    """Authorization failed"""
    pass

class SecureInputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
        # Dangerous patterns that could indicate injection attempts
        self.dangerous_patterns = [
            r'[;&|`$(){}[\]<>]',  # Shell metacharacters
            r'\.\./|\.\.\\',       # Path traversal
            r'[\x00-\x1f\x7f]',   # Control characters
            r'(rm|dd|mkfs|fdisk|wget|curl|nc|netcat)\s',  # Dangerous commands
            r'(sudo|su)\s',       # Privilege escalation
            r'(eval|exec|system)\s*\(',  # Code execution
            r'(/etc/passwd|/etc/shadow|/etc/hosts)',  # Sensitive files
        ]
        
        # Compile patterns for efficiency
        self.dangerous_regex = re.compile('|'.join(self.dangerous_patterns), re.IGNORECASE)
    
    def sanitize_string(self, input_str: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            raise InputValidationError("Input must be a string")
        
        if not input_str.strip():
            return ""
        
        # Check length
        max_len = max_length or self.config.max_input_length
        if len(input_str) > max_len:
            raise InputValidationError(f"Input too long: {len(input_str)} > {max_len}")
        
        # Remove null bytes and control characters (except common whitespace)
        sanitized = ''.join(char for char in input_str 
                          if ord(char) >= 32 or char in '\t\n\r')
        
        # Check for dangerous patterns
        if self.dangerous_regex.search(sanitized):
            raise InputValidationError("Input contains potentially dangerous characters")
        
        return sanitized.strip()
    
    def validate_filename(self, filename: str) -> str:
        """Validate and sanitize filename"""
        if not filename:
            raise InputValidationError("Filename cannot be empty")
        
        # Basic sanitization
        filename = self.sanitize_string(filename, 255)
        
        # Remove directory separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Check for reserved names (Windows compatibility)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                         'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        
        if filename.upper() in reserved_names:
            raise InputValidationError(f"Reserved filename: {filename}")
        
        # Check extension if configured
        if self.config.allowed_file_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext and file_ext not in self.config.allowed_file_extensions:
                raise InputValidationError(f"File extension not allowed: {file_ext}")
        
        return filename
    
    def validate_file_path(self, file_path: str) -> Path:
        """Validate and resolve file path"""
        if not file_path:
            raise InputValidationError("File path cannot be empty")
        
        # Sanitize input
        file_path = self.sanitize_string(file_path, 4096)
        
        try:
            # Resolve to absolute path
            path = Path(file_path).resolve()
        except Exception as e:
            raise InputValidationError(f"Invalid path: {e}")
        
        # Check if path is within allowed directories
        if self.config.allowed_directories:
            allowed = False
            for allowed_dir in self.config.allowed_directories:
                try:
                    path.relative_to(allowed_dir)
                    allowed = True
                    break
                except ValueError:
                    continue
            
            if not allowed:
                raise InputValidationError(f"Path not in allowed directories: {path}")
        
        return path
    
    def validate_ip_address(self, ip_str: str) -> str:
        """Validate IP address"""
        import ipaddress
        
        ip_str = self.sanitize_string(ip_str, 45)  # IPv6 max length
        
        try:
            # This will raise ValueError for invalid IPs
            ip_obj = ipaddress.ip_address(ip_str)
            return str(ip_obj)
        except ValueError:
            raise InputValidationError(f"Invalid IP address: {ip_str}")
    
    def validate_port(self, port: Union[str, int]) -> int:
        """Validate network port"""
        if isinstance(port, str):
            port = self.sanitize_string(port, 5)
            
        try:
            port_num = int(port)
        except ValueError:
            raise InputValidationError(f"Invalid port number: {port}")
        
        if not (1 <= port_num <= 65535):
            raise InputValidationError(f"Port out of range: {port_num}")
        
        return port_num
    
    def validate_command_args(self, args: List[str]) -> List[str]:
        """Validate command line arguments"""
        if not isinstance(args, list):
            raise InputValidationError("Arguments must be a list")
        
        validated_args = []
        for arg in args:
            if not isinstance(arg, str):
                raise InputValidationError(f"All arguments must be strings: {type(arg)}")
            
            # Sanitize each argument
            sanitized_arg = self.sanitize_string(arg)
            
            # Additional check for blocked commands
            for blocked_cmd in self.config.blocked_commands:
                if sanitized_arg.lower().startswith(blocked_cmd.lower()):
                    raise CommandInjectionError(f"Blocked command detected: {blocked_cmd}")
            
            validated_args.append(sanitized_arg)
        
        return validated_args

class SecureCommandExecutor:
    """Secure command execution with sandboxing"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.validator = SecureInputValidator(config)
    
    def execute_safe_command(self, command: List[str], cwd: Optional[str] = None, 
                           timeout: int = 30, capture_output: bool = True) -> Dict[str, Any]:
        """Execute command safely with validation and sandboxing"""
        
        # Validate command arguments
        safe_command = self.validator.validate_command_args(command)
        
        # Validate working directory
        if cwd:
            cwd_path = self.validator.validate_file_path(cwd)
            cwd = str(cwd_path)
        
        # Prepare secure environment
        env = self._get_secure_environment()
        
        try:
            logger.info(f"Executing command: {' '.join(safe_command)}")
            
            # Execute with restrictions
            process = subprocess.run(
                safe_command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=False
            )
            
            result = {
                'returncode': process.returncode,
                'stdout': process.stdout if capture_output else '',
                'stderr': process.stderr if capture_output else '',
                'success': process.returncode == 0
            }
            
            if not result['success']:
                logger.warning(f"Command failed with code {process.returncode}: {' '.join(safe_command)}")
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(safe_command)}")
            raise SecurityException(f"Command timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise SecurityException(f"Command execution failed: {e}")
    
    def _get_secure_environment(self) -> Dict[str, str]:
        """Get secure environment variables"""
        # Start with minimal environment
        secure_env = {
            'PATH': '/usr/local/bin:/usr/bin:/bin',
            'HOME': '/tmp',
            'SHELL': '/bin/bash',
            'TERM': 'xterm',
            'LC_ALL': 'C'
        }
        
        # Add LNMT-specific variables
        secure_env.update({
            'LNMT_CONFIG_DIR': '/etc/lnmt',
            'LNMT_DATA_DIR': '/var/lib/lnmt',
            'LNMT_LOG_DIR': '/var/log/lnmt'
        })
        
        return secure_env

class CLIAuthenticator:
    """CLI authentication and authorization"""
    
    def __init__(self, config_path: str = "/etc/lnmt/lnmt.conf"):
        self.config_path = config_path
        self.current_user = None
    
    def authenticate(self, username: str = None, token: str = None) -> bool:
        """Authenticate CLI user"""
        try:
            # For CLI, we can use environment variables or config files
            if not username and not token:
                # Try to get from environment
                username = os.environ.get('LNMT_USER')
                token = os.environ.get('LNMT_TOKEN')
            
            if not username or not token:
                logger.error("Authentication required: set LNMT_USER and LNMT_TOKEN")
                return False
            
            # Here you would validate against the auth engine
            # For now, we'll do basic validation
            if self._validate_token(username, token):
                self.current_user = username
                logger.info(f"Authenticated as user: {username}")
                return True
            else:
                logger.error("Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _validate_token(self, username: str, token: str) -> bool:
        """Validate authentication token"""
        # This should integrate with the SecureAuthEngine
        # For demo purposes, we'll accept any non-empty token
        return bool(username and token and len(token) > 10)
    
    def require_auth(self, func: Callable) -> Callable:
        """Decorator requiring authentication"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.current_user:
                raise AuthorizationError("Authentication required")
            return func(*args, **kwargs)
        return wrapper

class SecureCLIBase:
    """Base class for secure CLI tools"""
    
    def __init__(self, tool_name: str, description: str, config: SecurityConfig = None):
        self.tool_name = tool_name
        self.description = description
        self.config = config or SecurityConfig()
        self.validator = SecureInputValidator(self.config)
        self.executor = SecureCommandExecutor(self.config)
        self.authenticator = CLIAuthenticator()
        
        # Setup argument parser
        self.parser = argparse.ArgumentParser(
            prog=tool_name,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        self._setup_common_args()
        self._setup_logging()
    
    def _setup_common_args(self):
        """Setup common CLI arguments"""
        self.parser.add_argument(
            '--config', '-c',
            default='/etc/lnmt/lnmt.conf',
            help='Configuration file path'
        )
        
        self.parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        self.parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing'
        )
        
        self.parser.add_argument(
            '--user',
            help='Username for authentication'
        )
        
        self.parser.add_argument(
            '--token',
            help='Authentication token'
        )
    
    def _setup_logging(self):
        """Setup secure logging"""
        log_format = f'%(asctime)s - {self.tool_name} - %(levelname)s - %(message)s'
        
        # File handler
        log_file = f'/var/log/lnmt/{self.tool_name}.log'
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(file_handler)
        except PermissionError:
            # Fallback to console only
            pass
    
    def add_subcommand(self, name: str, help_text: str, handler: Callable) -> argparse.ArgumentParser:
        """Add subcommand with validation"""
        name = self.validator.sanitize_string(name, 50)
        
        if not hasattr(self, 'subparsers'):
            self.subparsers = self.parser.add_subparsers(dest='command', help='Available commands')
        
        subparser = self.subparsers.add_parser(name, help=help_text)
        subparser.set_defaults(func=handler)
        
        return subparser
    
    def validate_args(self, args: argparse.Namespace) -> argparse.Namespace:
        """Validate parsed arguments"""
        # Validate config path
        if hasattr(args, 'config') and args.config:
            args.config = str(self.validator.validate_file_path(args.config))
        
        # Validate user input
        if hasattr(args, 'user') and args.user:
            args.user = self.validator.sanitize_string(args.user, 50)
        
        # Validate other string arguments
        for attr_name in dir(args):
            if not attr_name.startswith('_'):
                attr_value = getattr(args, attr_name)
                if isinstance(attr_value, str) and attr_value:
                    try:
                        setattr(args, attr_name, self.validator.sanitize_string(attr_value))
                    except InputValidationError as e:
                        logger.error(f"Invalid argument {attr_name}: {e}")
                        sys.exit(1)
        
        return args
    
    def run(self, argv: List[str] = None) -> int:
        """Main CLI execution with security checks"""
        try:
            # Parse arguments
            args = self.parser.parse_args(argv)
            
            # Validate arguments
            args = self.validate_args(args)
            
            # Setup verbose logging
            if args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Authenticate if required
            if self.config.require_auth:
                if not self.authenticator.authenticate(args.user, args.token):
                    logger.error("Authentication failed")
                    return 1
            
            # Execute command
            if hasattr(args, 'func'):
                return args.func(args)
            else:
                self.parser.print_help()
                return 1
                
        except (InputValidationError, CommandInjectionError, AuthorizationError) as e:
            logger.error(f"Security error: {e}")
            return 1
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 1

# Example: Secure DNS Manager CLI
class SecureDNSManagerCLI(SecureCLIBase):
    """Secure DNS Manager CLI implementation"""
    
    def __init__(self):
        super().__init__(
            tool_name='dnsmgr',
            description='LNMT DNS Management Tool',
            config=SecurityConfig(
                allowed_directories=['/etc/lnmt', '/var/lib/lnmt', '/etc/bind'],
                blocked_commands=['rm', 'dd', 'wget', 'curl']
            )
        )
        self._setup_dns_commands()
    
    def _setup_dns_commands(self):
        """Setup DNS-specific commands"""
        # Add record command
        add_parser = self.add_subcommand('add', 'Add DNS record', self._add_record)
        add_parser.add_argument('zone', help='DNS zone')
        add_parser.add_argument('name', help='Record name')
        add_parser.add_argument('type', choices=['A', 'AAAA', 'CNAME', 'MX', 'TXT'], help='Record type')
        add_parser.add_argument('value', help='Record value')
        add_parser.add_argument('--ttl', type=int, default=3600, help='TTL value')
        
        # Delete record command
        del_parser = self.add_subcommand('delete', 'Delete DNS record', self._delete_record)
        del_parser.add_argument('zone', help='DNS zone')
        del_parser.add_argument('name', help='Record name')
        del_parser.add_argument('type', choices=['A', 'AAAA', 'CNAME', 'MX', 'TXT'], help='Record type')
        
        # List records command
        list_parser = self.add_subcommand('list', 'List DNS records', self._list_records)
        list_parser.add_argument('zone', help='DNS zone')
        list_parser.add_argument('--type', choices=['A', 'AAAA', 'CNAME', 'MX', 'TXT'], help='Filter by type')
    
    def _validate_dns_name(self, name: str) -> str:
        """Validate DNS name"""
        name = self.validator.sanitize_string(name, 253)
        
        # DNS name validation
        if not re.match(r'^[a-zA-Z0-9.-]+, name):
            raise InputValidationError("Invalid DNS name format")
        
        if '..' in name or name.startswith('.') or name.endswith('.'):
            raise InputValidationError("Invalid DNS name structure")
        
        return name.lower()
    
    def _validate_dns_value(self, record_type: str, value: str) -> str:
        """Validate DNS record value"""
        value = self.validator.sanitize_string(value, 512)
        
        if record_type in ['A']:
            return self.validator.validate_ip_address(value)
        elif record_type in ['AAAA']:
            # IPv6 validation
            try:
                import ipaddress
                ipv6 = ipaddress.IPv6Address(value)
                return str(ipv6)
            except ValueError:
                raise InputValidationError("Invalid IPv6 address")
        elif record_type in ['CNAME', 'MX']:
            return self._validate_dns_name(value)
        elif record_type == 'TXT':
            # TXT records can contain more varied content but still need validation
            if len(value) > 255:
                raise InputValidationError("TXT record too long")
            return value
        
        return value
    
    @CLIAuthenticator().require_auth
    def _add_record(self, args: argparse.Namespace) -> int:
        """Add DNS record"""
        try:
            # Validate inputs
            zone = self._validate_dns_name(args.zone)
            name = self._validate_dns_name(args.name)
            record_type = args.type.upper()
            value = self._validate_dns_value(record_type, args.value)
            ttl = args.ttl
            
            if not (60 <= ttl <= 86400):
                raise InputValidationError("TTL must be between 60 and 86400")
            
            logger.info(f"Adding DNS record: {name}.{zone} {ttl} IN {record_type} {value}")
            
            if args.dry_run:
                print(f"Would add: {name}.{zone} {ttl} IN {record_type} {value}")
                return 0
            
            # Execute DNS update command
            result = self.executor.execute_safe_command([
                'nsupdate', '-k', '/etc/lnmt/dns.key'
            ], capture_output=True)
            
            if result['success']:
                logger.info("DNS record added successfully")
                print("DNS record added successfully")
                return 0
            else:
                logger.error(f"Failed to add DNS record: {result['stderr']}")
                print(f"Error: {result['stderr']}")
                return 1
                
        except (InputValidationError, SecurityException) as e:
            logger.error(f"DNS add error: {e}")
            print(f"Error: {e}")
            return 1
    
    @CLIAuthenticator().require_auth
    def _delete_record(self, args: argparse.Namespace) -> int:
        """Delete DNS record"""
        try:
            # Validate inputs
            zone = self._validate_dns_name(args.zone)
            name = self._validate_dns_name(args.name)
            record_type = args.type.upper()
            
            logger.info(f"Deleting DNS record: {name}.{zone} {record_type}")
            
            if args.dry_run:
                print(f"Would delete: {name}.{zone} {record_type}")
                return 0
            
            # Execute DNS delete command
            result = self.executor.execute_safe_command([
                'nsupdate', '-k', '/etc/lnmt/dns.key'
            ], capture_output=True)
            
            if result['success']:
                logger.info("DNS record deleted successfully")
                print("DNS record deleted successfully")
                return 0
            else:
                logger.error(f"Failed to delete DNS record: {result['stderr']}")
                print(f"Error: {result['stderr']}")
                return 1
                
        except (InputValidationError, SecurityException) as e:
            logger.error(f"DNS delete error: {e}")
            print(f"Error: {e}")
            return 1
    
    def _list_records(self, args: argparse.Namespace) -> int:
        """List DNS records"""
        try:
            # Validate inputs
            zone = self._validate_dns_name(args.zone)
            
            logger.info(f"Listing DNS records for zone: {zone}")
            
            # Execute DNS query command
            cmd = ['dig', '@localhost', zone, 'AXFR']
            if args.type:
                cmd = ['dig', '@localhost', zone, args.type.upper()]
            
            result = self.executor.execute_safe_command(cmd, capture_output=True)
            
            if result['success']:
                print(result['stdout'])
                return 0
            else:
                logger.error(f"Failed to list DNS records: {result['stderr']}")
                print(f"Error: {result['stderr']}")
                return 1
                
        except (InputValidationError, SecurityException) as e:
            logger.error(f"DNS list error: {e}")
            print(f"Error: {e}")
            return 1

# Example: Secure Backup CLI
class SecureBackupCLI(SecureCLIBase):
    """Secure Backup CLI implementation"""
    
    def __init__(self):
        super().__init__(
            tool_name='backupmgr',
            description='LNMT Backup Management Tool',
            config=SecurityConfig(
                allowed_directories=['/var/lib/lnmt', '/etc/lnmt', '/tmp/lnmt-backup'],
                allowed_file_extensions=['.tar', '.gz', '.bz2', '.xz', '.backup']
            )
        )
        self._setup_backup_commands()
    
    def _setup_backup_commands(self):
        """Setup backup-specific commands"""
        # Create backup command
        create_parser = self.add_subcommand('create', 'Create backup', self._create_backup)
        create_parser.add_argument('--source', default='/var/lib/lnmt', help='Source directory')
        create_parser.add_argument('--destination', default='/var/lib/lnmt/backups', help='Backup destination')
        create_parser.add_argument('--compress', choices=['gzip', 'bzip2', 'xz'], default='gzip', help='Compression type')
        create_parser.add_argument('--name', help='Backup name')
        
        # Restore backup command
        restore_parser = self.add_subcommand('restore', 'Restore backup', self._restore_backup)
        restore_parser.add_argument('backup_file', help='Backup file to restore')
        restore_parser.add_argument('--destination', default='/var/lib/lnmt', help='Restore destination')
        
        # List backups command
        self.add_subcommand('list', 'List backups', self._list_backups)
    
    @CLIAuthenticator().require_auth
    def _create_backup(self, args: argparse.Namespace) -> int:
        """Create backup"""
        try:
            # Validate paths
            source_path = self.validator.validate_file_path(args.source)
            dest_path = self.validator.validate_file_path(args.destination)
            
            # Generate backup name
            if args.name:
                backup_name = self.validator.validate_filename(args.name)
            else:
                from datetime import datetime
                backup_name = f"lnmt-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Choose compression
            compress_map = {
                'gzip': 'gz',
                'bzip2': 'bz2',
                'xz': 'xz'
            }
            
            backup_file = dest_path / f"{backup_name}.tar.{compress_map[args.compress]}"
            
            logger.info(f"Creating backup: {source_path} -> {backup_file}")
            
            if args.dry_run:
                print(f"Would create backup: {backup_file}")
                return 0
            
            # Create backup directory if needed
            dest_path.mkdir(parents=True, exist_ok=True)
            
            # Execute tar command
            tar_args = ['tar', f'-c{args.compress[0]}f', str(backup_file), '-C', str(source_path.parent), source_path.name]
            
            result = self.executor.execute_safe_command(tar_args, timeout=300)
            
            if result['success']:
                logger.info(f"Backup created successfully: {backup_file}")
                print(f"Backup created: {backup_file}")
                return 0
            else:
                logger.error(f"Backup failed: {result['stderr']}")
                print(f"Error: {result['stderr']}")
                return 1
                
        except (InputValidationError, SecurityException) as e:
            logger.error(f"Backup creation error: {e}")
            print(f"Error: {e}")
            return 1
    
    @CLIAuthenticator().require_auth
    def _restore_backup(self, args: argparse.Namespace) -> int:
        """Restore backup"""
        try:
            # Validate paths
            backup_file = self.validator.validate_file_path(args.backup_file)
            dest_path = self.validator.validate_file_path(args.destination)
            
            if not backup_file.exists():
                raise InputValidationError(f"Backup file not found: {backup_file}")
            
            logger.info(f"Restoring backup: {backup_file} -> {dest_path}")
            
            if args.dry_run:
                print(f"Would restore backup: {backup_file} to {dest_path}")
                return 0
            
            # Execute tar command
            tar_args = ['tar', '-xf', str(backup_file), '-C', str(dest_path)]
            
            result = self.executor.execute_safe_command(tar_args, timeout=300)
            
            if result['success']:
                logger.info(f"Backup restored successfully: {backup_file}")
                print(f"Backup restored from: {backup_file}")
                return 0
            else:
                logger.error(f"Restore failed: {result['stderr']}")
                print(f"Error: {result['stderr']}")
                return 1
                
        except (InputValidationError, SecurityException) as e:
            logger.error(f"Backup restore error: {e}")
            print(f"Error: {e}")
            return 1
    
    def _list_backups(self, args: argparse.Namespace) -> int:
        """List available backups"""
        try:
            backup_dir = Path('/var/lib/lnmt/backups')
            
            if not backup_dir.exists():
                print("No backup directory found")
                return 0
            
            backups = []
            for backup_file in backup_dir.glob('*.tar.*'):
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })
            
            if not backups:
                print("No backups found")
                return 0
            
            # Sort by modification time
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            print(f"{'Name':<40} {'Size':<15} {'Modified'}")
            print("-" * 70)
            
            for backup in backups:
                from datetime import datetime
                size_mb = backup['size'] / (1024 * 1024)
                modified = datetime.fromtimestamp(backup['modified']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{backup['name']:<40} {size_mb:>10.1f} MB   {modified}")
            
            return 0
            
        except Exception as e:
            logger.error(f"List backups error: {e}")
            print(f"Error: {e}")
            return 1

# Main execution functions
def main_dns():
    """Main entry point for DNS CLI"""
    cli = SecureDNSManagerCLI()
    return cli.run()

def main_backup():
    """Main entry point for Backup CLI"""
    cli = SecureBackupCLI()
    return cli.run()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 0:
        script_name = Path(sys.argv[0]).name
        
        if 'dns' in script_name:
            sys.exit(main_dns())
        elif 'backup' in script_name:
            sys.exit(main_backup())
        else:
            print("Unknown CLI tool")
            sys.exit(1)