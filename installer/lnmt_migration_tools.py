#!/usr/bin/env python3
"""
LNMT Migration and Configuration Tools
Utilities for migrating from legacy tools and managing configurations
Version: 1.0.0
"""

import os
import sys
import json
import yaml
import shutil
import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
from datetime import datetime

# Configuration paths
LNMT_CONFIG_DIR = Path("/etc/lnmt")
LNMT_DATA_DIR = Path("/var/lib/lnmt")
LNMT_LOG_DIR = Path("/var/log/lnmt")
MIGRATION_LOG = LNMT_LOG_DIR / "migration.log"

class ConfigurationMigrator:
    """Base class for configuration migration"""
    
    def _migrate_blocklists(self, config: Dict):
        """Migrate Pi-hole blocklists to LNMT format"""
        blocklists = config['dns']['blocking']['blocklists']
        
        # Convert to LNMT blocklist format
        lnmt_blocklists = []
        for url in blocklists:
            lnmt_blocklists.append({
                'name': self._extract_list_name(url),
                'url': url,
                'enabled': True,
                'update_frequency': 'daily'
            })
        
        config['dns']['blocking']['lists'] = lnmt_blocklists
        del config['dns']['blocking']['blocklists']
    
    def _extract_list_name(self, url: str) -> str:
        """Extract a friendly name from blocklist URL"""
        if 'easylist' in url.lower():
            return 'EasyList'
        elif 'malware' in url.lower():
            return 'Malware Domains'
        elif 'ads' in url.lower():
            return 'Ad Servers'
        else:
            # Extract domain name
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or 'Custom List'
    
    def _convert_to_lnmt_dns(self, pihole_config: Dict) -> Dict:
        """Convert Pi-hole config to LNMT DNS configuration"""
        dns_config = pihole_config['dns']
        
        lnmt_config = {
            'dns': {
                'enabled': True,
                'service': {
                    'port': 53,
                    'interfaces': dns_config['interfaces']
                },
                'upstream': {
                    'servers': dns_config['upstream_servers'] or ['8.8.8.8', '8.8.4.4']
                },
                'filtering': {
                    'enabled': dns_config['blocking']['enabled'],
                    'blocklists': dns_config['blocking'].get('lists', []),
                    'whitelist': dns_config['blocking']['whitelist'],
                    'blacklist': dns_config['blocking']['blacklist']
                },
                'migration': {
                    'source': 'pihole',
                    'date': datetime.now().isoformat()
                }
            }
        }
        
        return lnmt_config
    
    def _write_lnmt_config(self, config: Dict) -> bool:
        """Write LNMT DNS configuration with Pi-hole features"""
        output_file = LNMT_CONFIG_DIR / "dns.yml"
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write DNS config to {output_file}")
            return True
        
        try:
            LNMT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"DNS configuration written to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write DNS configuration: {e}")
            return False

class ShorewallMigrator(ConfigurationMigrator):
    """Migrate from Shorewall firewall configuration"""
    
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.shorewall_dir = Path("/etc/shorewall")
        
    def migrate(self) -> bool:
        """Main migration process for Shorewall"""
        self.logger.info("Starting Shorewall migration...")
        
        try:
            if not self._check_shorewall_installation():
                self.logger.warning("Shorewall not found, skipping migration")
                return True
            
            # Parse Shorewall configuration
            config = self._parse_shorewall_config()
            if not config:
                self.logger.error("Failed to parse Shorewall configuration")
                return False
            
            # Convert to LNMT format
            lnmt_config = self._convert_to_lnmt_firewall(config)
            
            # Write LNMT configuration
            if not self._write_lnmt_config(lnmt_config):
                return False
            
            self.logger.info("Shorewall migration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Shorewall migration failed: {e}")
            return False
    
    def _check_shorewall_installation(self) -> bool:
        """Check if Shorewall is installed"""
        return (self.shorewall_dir / "shorewall.conf").exists()
    
    def _parse_shorewall_config(self) -> Dict:
        """Parse Shorewall configuration files"""
        config = {
            'firewall': {
                'enabled': True,
                'zones': {},
                'interfaces': {},
                'policies': [],
                'rules': [],
                'masq': []
            }
        }
        
        # Backup Shorewall directory
        if self.shorewall_dir.exists():
            self.create_backup(self.shorewall_dir, "shorewall")
        
        # Parse configuration files
        config_files = {
            'zones': self.shorewall_dir / "zones",
            'interfaces': self.shorewall_dir / "interfaces",
            'policy': self.shorewall_dir / "policy",
            'rules': self.shorewall_dir / "rules",
            'masq': self.shorewall_dir / "masq"
        }
        
        for config_type, file_path in config_files.items():
            if file_path.exists():
                self._parse_shorewall_file(config_type, file_path, config)
        
        return config
    
    def _parse_shorewall_file(self, config_type: str, file_path: Path, config: Dict):
        """Parse individual Shorewall configuration file"""
        self.logger.info(f"Parsing {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#') or line.startswith('?'):
                        continue
                    
                    # Remove inline comments
                    if '#' in line:
                        line = line[:line.index('#')].strip()
                    
                    self._parse_shorewall_line(config_type, line, config, file_path, line_num)
                    
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
    
    def _parse_shorewall_line(self, config_type: str, line: str, config: Dict, file_path: Path, line_num: int):
        """Parse individual Shorewall configuration line"""
        try:
            fields = line.split()
            if not fields:
                return
            
            if config_type == 'zones':
                # zones file: zone_name zone_type
                if len(fields) >= 2:
                    zone_name, zone_type = fields[0], fields[1]
                    config['firewall']['zones'][zone_name] = {
                        'type': zone_type,
                        'interfaces': []
                    }
            
            elif config_type == 'interfaces':
                # interfaces file: zone interface options
                if len(fields) >= 2:
                    zone, interface = fields[0], fields[1]
                    options = fields[2:] if len(fields) > 2 else []
                    
                    if zone in config['firewall']['zones']:
                        config['firewall']['zones'][zone]['interfaces'].append(interface)
                    
                    config['firewall']['interfaces'][interface] = {
                        'zone': zone,
                        'options': options
                    }
            
            elif config_type == 'policy':
                # policy file: source dest policy log_level
                if len(fields) >= 3:
                    source, dest, policy = fields[0], fields[1], fields[2]
                    log_level = fields[3] if len(fields) > 3 else None
                    
                    config['firewall']['policies'].append({
                        'source': source,
                        'destination': dest,
                        'action': policy,
                        'log_level': log_level
                    })
            
            elif config_type == 'rules':
                # rules file: action source dest proto dport sport
                if len(fields) >= 3:
                    action, source, dest = fields[0], fields[1], fields[2]
                    proto = fields[3] if len(fields) > 3 else 'all'
                    dport = fields[4] if len(fields) > 4 else 'any'
                    sport = fields[5] if len(fields) > 5 else 'any'
                    
                    config['firewall']['rules'].append({
                        'action': action,
                        'source': source,
                        'destination': dest,
                        'protocol': proto,
                        'dest_port': dport,
                        'source_port': sport
                    })
            
            elif config_type == 'masq':
                # masq file: interface source address
                if len(fields) >= 2:
                    interface, source = fields[0], fields[1]
                    address = fields[2] if len(fields) > 2 else None
                    
                    config['firewall']['masq'].append({
                        'interface': interface,
                        'source': source,
                        'address': address
                    })
                    
        except Exception as e:
            self.logger.warning(f"Failed to parse line {line_num} in {file_path}: {line} - {e}")
    
    def _convert_to_lnmt_firewall(self, shorewall_config: Dict) -> Dict:
        """Convert Shorewall config to LNMT firewall configuration"""
        fw_config = shorewall_config['firewall']
        
        lnmt_config = {
            'firewall': {
                'enabled': True,
                'default_policy': 'DROP',
                'zones': self._convert_zones(fw_config['zones']),
                'policies': self._convert_policies(fw_config['policies']),
                'rules': self._convert_rules(fw_config['rules']),
                'nat': {
                    'masquerade': self._convert_masq(fw_config['masq'])
                },
                'migration': {
                    'source': 'shorewall',
                    'date': datetime.now().isoformat(),
                    'original_interfaces': fw_config['interfaces']
                }
            }
        }
        
        return lnmt_config
    
    def _convert_zones(self, zones: Dict) -> Dict:
        """Convert Shorewall zones to LNMT format"""
        lnmt_zones = {}
        
        for zone_name, zone_config in zones.items():
            lnmt_zones[zone_name] = {
                'description': f"Migrated from Shorewall {zone_config['type']} zone",
                'interfaces': zone_config['interfaces'],
                'type': zone_config['type']
            }
        
        return lnmt_zones
    
    def _convert_policies(self, policies: List) -> List:
        """Convert Shorewall policies to LNMT format"""
        lnmt_policies = []
        
        for policy in policies:
            lnmt_policies.append({
                'source_zone': policy['source'],
                'dest_zone': policy['destination'],
                'action': policy['action'].upper(),
                'log': bool(policy.get('log_level'))
            })
        
        return lnmt_policies
    
    def _convert_rules(self, rules: List) -> List:
        """Convert Shorewall rules to LNMT format"""
        lnmt_rules = []
        
        for rule in rules:
            lnmt_rules.append({
                'name': f"Migrated rule {len(lnmt_rules) + 1}",
                'action': rule['action'].upper(),
                'source': rule['source'],
                'destination': rule['destination'],
                'protocol': rule['protocol'],
                'dest_port': rule['dest_port'] if rule['dest_port'] != 'any' else None,
                'source_port': rule['source_port'] if rule['source_port'] != 'any' else None,
                'enabled': True
            })
        
        return lnmt_rules
    
    def _convert_masq(self, masq_rules: List) -> List:
        """Convert Shorewall masquerading rules to LNMT format"""
        lnmt_masq = []
        
        for masq in masq_rules:
            lnmt_masq.append({
                'interface': masq['interface'],
                'source': masq['source'],
                'nat_address': masq.get('address'),
                'enabled': True
            })
        
        return lnmt_masq
    
    def _write_lnmt_config(self, config: Dict) -> bool:
        """Write LNMT firewall configuration"""
        output_file = LNMT_CONFIG_DIR / "firewall.yml"
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write firewall config to {output_file}")
            return True
        
        try:
            LNMT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Firewall configuration written to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write firewall configuration: {e}")
            return False

class ConfigValidator:
    """Validate LNMT configuration files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def validate_all(self) -> bool:
        """Validate all LNMT configuration files"""
        self.logger.info("Validating LNMT configuration...")
        
        config_files = {
            'main': LNMT_CONFIG_DIR / "lnmt.yml",
            'dns': LNMT_CONFIG_DIR / "dns.yml",
            'firewall': LNMT_CONFIG_DIR / "firewall.yml",
            'interfaces': LNMT_CONFIG_DIR / "interfaces.yml"
        }
        
        all_valid = True
        
        for config_type, config_file in config_files.items():
            if config_file.exists():
                if not self._validate_config_file(config_type, config_file):
                    all_valid = False
            else:
                self.logger.warning(f"Configuration file not found: {config_file}")
        
        return all_valid
    
    def _validate_config_file(self, config_type: str, config_file: Path) -> bool:
        """Validate individual configuration file"""
        self.logger.info(f"Validating {config_type} configuration: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            if config_type == 'main':
                return self._validate_main_config(config)
            elif config_type == 'dns':
                return self._validate_dns_config(config)
            elif config_type == 'firewall':
                return self._validate_firewall_config(config)
            elif config_type == 'interfaces':
                return self._validate_interfaces_config(config)
            
            return True
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML syntax error in {config_file}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating {config_file}: {e}")
            return False
    
    def _validate_main_config(self, config: Dict) -> bool:
        """Validate main LNMT configuration"""
        required_sections = ['core', 'database', 'web', 'network']
        
        for section in required_sections:
            if section not in config:
                self.logger.error(f"Missing required section: {section}")
                return False
        
        # Validate core settings
        core = config.get('core', {})
        if not core.get('data_dir') or not core.get('log_dir'):
            self.logger.error("Missing required core directory settings")
            return False
        
        return True
    
    def _validate_dns_config(self, config: Dict) -> bool:
        """Validate DNS configuration"""
        if 'dns' not in config:
            self.logger.error("Missing DNS configuration section")
            return False
        
        dns = config['dns']
        
        # Check required fields
        if not dns.get('enabled'):
            self.logger.warning("DNS service is disabled")
        
        # Validate upstream servers
        upstream = dns.get('upstream', {})
        servers = upstream.get('servers', [])
        if not servers:
            self.logger.warning("No upstream DNS servers configured")
        
        return True
    
    def _validate_firewall_config(self, config: Dict) -> bool:
        """Validate firewall configuration"""
        if 'firewall' not in config:
            self.logger.error("Missing firewall configuration section")
            return False
        
        firewall = config['firewall']
        
        # Check zones configuration
        zones = firewall.get('zones', {})
        if not zones:
            self.logger.warning("No firewall zones configured")
        
        return True
    
    def _validate_interfaces_config(self, config: Dict) -> bool:
        """Validate network interfaces configuration"""
        if 'interfaces' not in config:
            self.logger.error("Missing interfaces configuration section")
            return False
        
        interfaces = config['interfaces']
        if not interfaces:
            self.logger.warning("No network interfaces configured")
        
        return True

class ConfigBackupRestore:
    """Backup and restore LNMT configurations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backup_dir = LNMT_DATA_DIR / "backups"
        
    def create_backup(self, description: str = "") -> Optional[Path]:
        """Create a full configuration backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}"
        if description:
            backup_name += f"_{description}"
        
        backup_path = self.backup_dir / backup_name
        
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup configuration directory
            if LNMT_CONFIG_DIR.exists():
                shutil.copytree(LNMT_CONFIG_DIR, backup_path / "config")
            
            # Backup database
            db_path = LNMT_DATA_DIR / "db"
            if db_path.exists():
                shutil.copytree(db_path, backup_path / "db")
            
            # Create backup manifest
            manifest = {
                'timestamp': timestamp,
                'description': description,
                'lnmt_version': self._get_lnmt_version(),
                'system_info': {
                    'hostname': os.uname().nodename,
                    'platform': os.uname().sysname
                }
            }
            
            with open(backup_path / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Configuration backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    def list_backups(self) -> List[Dict]:
        """List available configuration backups"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_dir in sorted(self.backup_dir.glob("config_backup_*"), reverse=True):
            manifest_file = backup_dir / "manifest.json"
            
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    backups.append({
                        'path': backup_dir,
                        'name': backup_dir.name,
                        'timestamp': manifest.get('timestamp'),
                        'description': manifest.get('description', ''),
                        'lnmt_version': manifest.get('lnmt_version', 'unknown')
                    })
                except Exception as e:
                    self.logger.warning(f"Could not read manifest for {backup_dir}: {e}")
            else:
                # Backup without manifest
                backups.append({
                    'path': backup_dir,
                    'name': backup_dir.name,
                    'timestamp': backup_dir.name.split('_')[-1] if '_' in backup_dir.name else 'unknown',
                    'description': 'No manifest available',
                    'lnmt_version': 'unknown'
                })
        
        return backups
    
    def restore_backup(self, backup_path: Path, dry_run: bool = False) -> bool:
        """Restore configuration from backup"""
        if not backup_path.exists():
            self.logger.error(f"Backup not found: {backup_path}")
            return False
        
        self.logger.info(f"Restoring configuration from: {backup_path}")
        
        if dry_run:
            self.logger.info("[DRY RUN] Would restore configuration")
            return True
        
        try:
            # Create current backup before restore
            current_backup = self.create_backup("pre_restore")
            if current_backup:
                self.logger.info(f"Current config backed up to: {current_backup}")
            
            # Restore configuration
            config_backup = backup_path / "config"
            if config_backup.exists():
                if LNMT_CONFIG_DIR.exists():
                    shutil.rmtree(LNMT_CONFIG_DIR)
                shutil.copytree(config_backup, LNMT_CONFIG_DIR)
                self.logger.info("Configuration files restored")
            
            # Restore database
            db_backup = backup_path / "db"
            db_target = LNMT_DATA_DIR / "db"
            if db_backup.exists():
                if db_target.exists():
                    shutil.rmtree(db_target)
                shutil.copytree(db_backup, db_target)
                self.logger.info("Database restored")
            
            self.logger.info("Configuration restore completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore configuration: {e}")
            return False
    
    def _get_lnmt_version(self) -> str:
        """Get current LNMT version"""
        version_file = Path("/opt/lnmt/VERSION")
        if version_file.exists():
            return version_file.read_text().strip()
        return "unknown"

def main():
    """Main entry point for migration tools"""
    parser = argparse.ArgumentParser(description="LNMT Migration and Configuration Tools")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migration commands
    migrate_parser = subparsers.add_parser('migrate', help='Migrate from legacy tools')
    migrate_parser.add_argument('--source', choices=['dnsmasq', 'pihole', 'shorewall', 'all'],
                               required=True, help='Source to migrate from')
    migrate_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without making changes')
    
    # Validation commands
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--config', choices=['all', 'dns', 'firewall', 'interfaces'],
                                default='all', help='Configuration to validate')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Backup configuration')
    backup_parser.add_argument('--description', help='Backup description')
    
    # Restore commands
    restore_parser = subparsers.add_parser('restore', help='Restore configuration')
    restore_parser.add_argument('--backup', required=True, help='Backup name or path')
    restore_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without making changes')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List backups')
    
    # Convert commands
    convert_parser = subparsers.add_parser('convert', help='Convert configuration formats')
    convert_parser.add_argument('--input', required=True, help='Input file')
    convert_parser.add_argument('--output', required=True, help='Output file')
    convert_parser.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                               help='Output format')
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if running as root for most operations
    if args.command in ['migrate', 'restore'] and os.geteuid() != 0:
        print("Error: This command must be run as root")
        sys.exit(1)
    
    try:
        if args.command == 'migrate':
            success = True
            
            if args.source in ['dnsmasq', 'all']:
                migrator = DnsmasqMigrator(dry_run=args.dry_run)
                success &= migrator.migrate()
            
            if args.source in ['pihole', 'all']:
                migrator = PiHoleMigrator(dry_run=args.dry_run)
                success &= migrator.migrate()
            
            if args.source in ['shorewall', 'all']:
                migrator = ShorewallMigrator(dry_run=args.dry_run)
                success &= migrator.migrate()
            
            sys.exit(0 if success else 1)
        
        elif args.command == 'validate':
            validator = ConfigValidator()
            success = validator.validate_all()
            sys.exit(0 if success else 1)
        
        elif args.command == 'backup':
            backup_restore = ConfigBackupRestore()
            backup_path = backup_restore.create_backup(args.description or "")
            if backup_path:
                print(f"Backup created: {backup_path}")
                sys.exit(0)
            else:
                sys.exit(1)
        
        elif args.command == 'restore':
            backup_restore = ConfigBackupRestore()
            
            # Handle backup argument (name or path)
            backup_path = Path(args.backup)
            if not backup_path.is_absolute():
                # Assume it's a backup name
                backup_dir = LNMT_DATA_DIR / "backups"
                backup_path = backup_dir / args.backup
            
            success = backup_restore.restore_backup(backup_path, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
        
        elif args.command == 'list':
            backup_restore = ConfigBackupRestore()
            backups = backup_restore.list_backups()
            
            if backups:
                print("Available configuration backups:")
                print("-" * 80)
                for backup in backups:
                    print(f"Name: {backup['name']}")
                    print(f"  Date: {backup['timestamp']}")
                    print(f"  Description: {backup['description']}")
                    print(f"  LNMT Version: {backup['lnmt_version']}")
                    print(f"  Path: {backup['path']}")
                    print()
            else:
                print("No configuration backups found")
        
        elif args.command == 'convert':
            # Simple format conversion utility
            input_path = Path(args.input)
            output_path = Path(args.output)
            
            if not input_path.exists():
                print(f"Error: Input file not found: {input_path}")
                sys.exit(1)
            
            try:
                with open(input_path, 'r') as f:
                    if input_path.suffix in ['.yml', '.yaml']:
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                with open(output_path, 'w') as f:
                    if args.format == 'yaml':
                        yaml.dump(data, f, default_flow_style=False, indent=2)
                    else:
                        json.dump(data, f, indent=2)
                
                print(f"Converted {input_path} to {output_path} ({args.format} format)")
                
            except Exception as e:
                print(f"Error converting file: {e}")
                sys.exit(1)
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()_init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.logger = self._setup_logging()
        self.backup_dir = LNMT_DATA_DIR / "backups" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def _setup_logging(self):
        """Setup logging for migration"""
        MIGRATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(MIGRATION_LOG),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def create_backup(self, source_path: Path, description: str):
        """Create backup of source configuration"""
        if not source_path.exists():
            return None
            
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / f"{description}_{source_path.name}"
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would backup {source_path} to {backup_path}")
            return backup_path
        
        if source_path.is_dir():
            shutil.copytree(source_path, backup_path)
        else:
            shutil.copy2(source_path, backup_path)
        
        self.logger.info(f"Backed up {source_path} to {backup_path}")
        return backup_path

class DnsmasqMigrator(ConfigurationMigrator):
    """Migrate from dnsmasq configuration"""
    
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.dnsmasq_config = Path("/etc/dnsmasq.conf")
        self.dnsmasq_dir = Path("/etc/dnsmasq.d")
        
    def migrate(self) -> bool:
        """Main migration process for dnsmasq"""
        self.logger.info("Starting dnsmasq migration...")
        
        try:
            # Check if dnsmasq is installed
            if not self._check_dnsmasq_installation():
                self.logger.warning("dnsmasq not found, skipping migration")
                return True
            
            # Parse dnsmasq configuration
            config = self._parse_dnsmasq_config()
            if not config:
                self.logger.error("Failed to parse dnsmasq configuration")
                return False
            
            # Convert to LNMT format
            lnmt_config = self._convert_to_lnmt_dns(config)
            
            # Write LNMT configuration
            if not self._write_lnmt_config(lnmt_config):
                return False
            
            self.logger.info("dnsmasq migration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"dnsmasq migration failed: {e}")
            return False
    
    def _check_dnsmasq_installation(self) -> bool:
        """Check if dnsmasq is installed and configured"""
        if not self.dnsmasq_config.exists():
            return False
        
        # Check if dnsmasq service exists
        try:
            result = subprocess.run(["systemctl", "status", "dnsmasq"], 
                                  capture_output=True, text=True)
            return result.returncode in [0, 3]  # 0=running, 3=stopped
        except:
            return False
    
    def _parse_dnsmasq_config(self) -> Dict[str, Any]:
        """Parse dnsmasq configuration files"""
        config = {
            'dns': {
                'enabled': True,
                'port': 53,
                'interfaces': [],
                'upstream_servers': [],
                'local_domains': [],
                'static_hosts': {},
                'dhcp_ranges': [],
                'dhcp_hosts': {},
                'options': {}
            }
        }
        
        # Backup original config
        self.create_backup(self.dnsmasq_config, "dnsmasq_main")
        
        # Parse main config file
        if self.dnsmasq_config.exists():
            config = self._parse_dnsmasq_file(self.dnsmasq_config, config)
        
        # Parse additional config files in dnsmasq.d
        if self.dnsmasq_dir.exists():
            self.create_backup(self.dnsmasq_dir, "dnsmasq_includes")
            for conf_file in self.dnsmasq_dir.glob("*.conf"):
                config = self._parse_dnsmasq_file(conf_file, config)
        
        return config
    
    def _parse_dnsmasq_file(self, config_file: Path, config: Dict) -> Dict:
        """Parse individual dnsmasq configuration file"""
        self.logger.info(f"Parsing {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Remove inline comments
                    if '#' in line:
                        line = line[:line.index('#')].strip()
                    
                    self._parse_dnsmasq_directive(line, config, config_file, line_num)
                    
        except Exception as e:
            self.logger.error(f"Error parsing {config_file}: {e}")
        
        return config
    
    def _parse_dnsmasq_directive(self, line: str, config: Dict, file_path: Path, line_num: int):
        """Parse individual dnsmasq directive"""
        try:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
            else:
                key = line.strip()
                value = True
            
            # Map dnsmasq options to LNMT configuration
            if key == 'port':
                config['dns']['port'] = int(value) if value != '0' else 53
            elif key == 'interface':
                if value not in config['dns']['interfaces']:
                    config['dns']['interfaces'].append(value)
            elif key == 'server':
                if value and value not in config['dns']['upstream_servers']:
                    config['dns']['upstream_servers'].append(value)
            elif key == 'local':
                config['dns']['local_domains'].append(value.strip('/'))
            elif key == 'address':
                # Parse address=/domain/ip format
                if value.startswith('/') and value.count('/') >= 2:
                    parts = value.strip('/').split('/')
                    if len(parts) >= 2:
                        domain, ip = parts[0], parts[1]
                        config['dns']['static_hosts'][domain] = ip
            elif key == 'dhcp-range':
                config['dns']['dhcp_ranges'].append(value)
            elif key == 'dhcp-host':
                # Parse dhcp-host=mac,ip,hostname format
                parts = value.split(',')
                if len(parts) >= 2:
                    mac = parts[0]
                    host_config = {
                        'mac': mac,
                        'ip': parts[1] if len(parts) > 1 else None,
                        'hostname': parts[2] if len(parts) > 2 else None
                    }
                    config['dns']['dhcp_hosts'][mac] = host_config
            else:
                # Store other options for reference
                config['dns']['options'][key] = value
                
        except Exception as e:
            self.logger.warning(f"Failed to parse line {line_num} in {file_path}: {line} - {e}")
    
    def _convert_to_lnmt_dns(self, dnsmasq_config: Dict) -> Dict:
        """Convert dnsmasq config to LNMT DNS configuration"""
        dns_config = dnsmasq_config['dns']
        
        lnmt_config = {
            'dns': {
                'enabled': True,
                'service': {
                    'port': dns_config['port'],
                    'interfaces': dns_config['interfaces'],
                    'bind_interfaces': True
                },
                'upstream': {
                    'servers': dns_config['upstream_servers'] or ['8.8.8.8', '8.8.4.4']
                },
                'zones': {
                    'local': dns_config['local_domains']
                },
                'hosts': {
                    'static': dns_config['static_hosts']
                },
                'dhcp': {
                    'enabled': bool(dns_config['dhcp_ranges']),
                    'ranges': dns_config['dhcp_ranges'],
                    'reservations': dns_config['dhcp_hosts']
                },
                'migration': {
                    'source': 'dnsmasq',
                    'date': datetime.now().isoformat(),
                    'original_options': dns_config['options']
                }
            }
        }
        
        return lnmt_config
    
    def _write_lnmt_config(self, config: Dict) -> bool:
        """Write LNMT DNS configuration"""
        output_file = LNMT_CONFIG_DIR / "dns.yml"
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would write DNS config to {output_file}")
            self.logger.info(f"[DRY RUN] Config preview:\n{yaml.dump(config, default_flow_style=False)}")
            return True
        
        try:
            LNMT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"DNS configuration written to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write DNS configuration: {e}")
            return False

class PiHoleMigrator(ConfigurationMigrator):
    """Migrate from Pi-hole configuration"""
    
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.pihole_dir = Path("/etc/pihole")
        self.pihole_config = self.pihole_dir / "setupVars.conf"
        
    def migrate(self) -> bool:
        """Main migration process for Pi-hole"""
        self.logger.info("Starting Pi-hole migration...")
        
        try:
            if not self._check_pihole_installation():
                self.logger.warning("Pi-hole not found, skipping migration")
                return True
            
            # Parse Pi-hole configuration
            config = self._parse_pihole_config()
            if not config:
                self.logger.error("Failed to parse Pi-hole configuration")
                return False
            
            # Convert to LNMT format
            lnmt_config = self._convert_to_lnmt_dns(config)
            
            # Migrate blocklists
            self._migrate_blocklists(lnmt_config)
            
            # Write LNMT configuration
            if not self._write_lnmt_config(lnmt_config):
                return False
            
            self.logger.info("Pi-hole migration completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Pi-hole migration failed: {e}")
            return False
    
    def _check_pihole_installation(self) -> bool:
        """Check if Pi-hole is installed"""
        return self.pihole_config.exists() or (self.pihole_dir / "pihole-FTL.conf").exists()
    
    def _parse_pihole_config(self) -> Dict:
        """Parse Pi-hole configuration"""
        config = {
            'dns': {
                'enabled': True,
                'upstream_servers': [],
                'interfaces': [],
                'blocking': {
                    'enabled': True,
                    'blocklists': [],
                    'whitelist': [],
                    'blacklist': []
                }
            }
        }
        
        # Backup Pi-hole directory
        if self.pihole_dir.exists():
            self.create_backup(self.pihole_dir, "pihole")
        
        # Parse setupVars.conf
        if self.pihole_config.exists():
            config = self._parse_setup_vars(config)
        
        # Parse other Pi-hole files
        self._parse_pihole_lists(config)
        
        return config
    
    def _parse_setup_vars(self, config: Dict) -> Dict:
        """Parse Pi-hole setupVars.conf"""
        try:
            with open(self.pihole_config, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        
                        if key == 'PIHOLE_DNS_1':
                            config['dns']['upstream_servers'].append(value)
                        elif key == 'PIHOLE_DNS_2' and value:
                            config['dns']['upstream_servers'].append(value)
                        elif key == 'PIHOLE_INTERFACE':
                            config['dns']['interfaces'].append(value)
                        elif key == 'BLOCKING_ENABLED':
                            config['dns']['blocking']['enabled'] = value == '1'
                            
        except Exception as e:
            self.logger.error(f"Error parsing setupVars.conf: {e}")
        
        return config
    
    def _parse_pihole_lists(self, config: Dict):
        """Parse Pi-hole block/allow lists"""
        list_files = {
            'blocklists': self.pihole_dir / "adlists.list",
            'whitelist': self.pihole_dir / "whitelist.txt",
            'blacklist': self.pihole_dir / "blacklist.txt"
        }
        
        for list_type, file_path in list_files.items():
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        items = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        config['dns']['blocking'][list_type] = items
                except Exception as e:
                    self.logger.error(f"Error parsing {file_path}: {e}")
    
    def _