#!/usr/bin/env python3
"""
LNMT Backup Control CLI

Command-line interface for managing LNMT system backups and restores.
Provides intuitive commands for backup operations with safety features.

Usage Examples:
    # Create a full backup
    sudo backupctl.py --create --description "Before system update"
    
    # Create config-only backup
    sudo backupctl.py --create --type config --description "Config changes"
    
    # List all backups
    backupctl.py --list
    
    # Show detailed backup information
    backupctl.py --info lnmt_backup_20240101_120000
    
    # Restore from backup (with safety backup)
    sudo backupctl.py --restore lnmt_backup_20240101_120000
    
    # Dry run restore (preview only)
    sudo backupctl.py --restore lnmt_backup_20240101_120000 --dry-run
    
    # Validate backup integrity
    backupctl.py --validate lnmt_backup_20240101_120000
    
    # Clean up old backups (keep last 5)
    sudo backupctl.py --cleanup --keep 5
    
    # Delete specific backup
    sudo backupctl.py --delete lnmt_backup_20240101_120000 --force

Interactive mode:
    backupctl.py --interactive
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add the parent directory to the path to import the service
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from services.backup_restore import BackupRestoreService, BackupMetadata
except ImportError:
    print("Error: Cannot import BackupRestoreService. Make sure services/backup_restore.py exists.")
    sys.exit(1)


class BackupCLI:
    """Command-line interface for LNMT backup operations"""
    
    def __init__(self, backup_dir: str = "/var/backups/lnmt"):
        """Initialize the CLI with backup service"""
        self.service = BackupRestoreService(backup_dir)
        self.is_root = os.geteuid() == 0
    
    def _check_permissions(self, operation: str) -> bool:
        """Check if current user has required permissions"""
        write_operations = ['create', 'restore', 'delete', 'cleanup']
        
        if operation in write_operations and not self.is_root:
            print(f"Error: {operation} operation requires root privileges")
            print("Please run with sudo")
            return False
        return True
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display"""
        try:
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return timestamp
    
    def create_backup(self, description: str = "", backup_type: str = "full") -> bool:
        """Create a new backup"""
        if not self._check_permissions('create'):
            return False
        
        try:
            print(f"Creating {backup_type} backup...")
            if description:
                print(f"Description: {description}")
            
            backup_id = self.service.create_backup(description, backup_type)
            print(f"✓ Backup created successfully: {backup_id}")
            
            # Show backup details
            metadata = self.service._get_backup_metadata(backup_id)
            if metadata:
                print(f"  Size: {self._format_size(metadata.size_bytes)}")
                print(f"  Files: {metadata.file_count}")
                print(f"  Type: {metadata.backup_type}")
            
            return True
            
        except Exception as e:
            print(f"✗ Backup creation failed: {e}")
            return False
    
    def list_backups(self, show_details: bool = False) -> None:
        """List all available backups"""
        try:
            backups = self.service.list_backups()
            
            if not backups:
                print("No backups found.")
                return
            
            print(f"\nAvailable backups ({len(backups)}):")
            print("-" * 80)
            
            for backup in backups:
                timestamp_formatted = self._format_timestamp(backup.timestamp)
                size_formatted = self._format_size(backup.size_bytes)
                
                print(f"ID: {backup.backup_id}")
                print(f"  Date: {timestamp_formatted}")
                print(f"  Size: {size_formatted} ({backup.file_count} files)")
                print(f"  Type: {backup.backup_type}")
                print(f"  Description: {backup.description}")
                
                if show_details:
                    print(f"  Created by: {backup.created_by}")
                    print(f"  LNMT version: {backup.lnmt_version}")
                    print(f"  Checksum: {backup.checksum[:16]}...")
                
                # Validate backup integrity
                is_valid = self.service.validate_backup(backup.backup_id)
                status = "✓ Valid" if is_valid else "✗ Invalid"
                print(f"  Status: {status}")
                print()
                
        except Exception as e:
            print(f"Error listing backups: {e}")
    
    def show_backup_info(self, backup_id: str) -> None:
        """Show detailed information about a specific backup"""
        try:
            metadata = self.service._get_backup_metadata(backup_id)
            
            if not metadata:
                print(f"Backup not found: {backup_id}")
                return
            
            print(f"\nBackup Information: {backup_id}")
            print("=" * 60)
            print(f"Date Created: {self._format_timestamp(metadata.timestamp)}")
            print(f"Description: {metadata.description}")
            print(f"Size: {self._format_size(metadata.size_bytes)}")
            print(f"File Count: {metadata.file_count}")
            print(f"Type: {metadata.backup_type}")
            print(f"Created by: {metadata.created_by}")
            print(f"LNMT Version: {metadata.lnmt_version}")
            print(f"Checksum: {metadata.checksum}")
            
            # Validate backup
            print("\nValidating backup integrity...")
            is_valid = self.service.validate_backup(backup_id)
            status = "✓ Valid - backup is intact" if is_valid else "✗ Invalid - backup may be corrupted"
            print(f"Status: {status}")
            
            # Show included files
            print(f"\nIncluded Files ({len(metadata.files_included)}):")
            for file_path in sorted(metadata.files_included):
                print(f"  {file_path}")
                
        except Exception as e:
            print(f"Error getting backup info: {e}")
    
    def restore_backup(self, backup_id: str, dry_run: bool = False, 
                      target_dir: Optional[str] = None, no_safety_backup: bool = False) -> bool:
        """Restore from a backup"""
        if not dry_run and not self._check_permissions('restore'):
            return False
        
        try:
            # Get backup info
            metadata = self.service._get_backup_metadata(backup_id)
            if not metadata:
                print(f"Backup not found: {backup_id}")
                return False
            
            print(f"\nRestoring backup: {backup_id}")
            print(f"Created: {self._format_timestamp(metadata.timestamp)}")
            print(f"Description: {metadata.description}")
            print(f"Type: {metadata.backup_type}")
            print(f"Files to restore: {metadata.file_count}")
            
            if target_dir:
                print(f"Target directory: {target_dir}")
            
            if dry_run:
                print("\n--- DRY RUN MODE ---")
                print("No changes will be made to the system")
            else:
                # Confirm restore operation
                if not no_safety_backup:
                    print("\nA safety backup will be created before restore.")
                
                response = input("\nProceed with restore? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Restore cancelled.")
                    return False
            
            print("\nStarting restore operation...")
            success = self.service.restore_backup(
                backup_id=backup_id,
                target_dir=target_dir,
                dry_run=dry_run,
                create_safety_backup=not no_safety_backup
            )
            
            if success:
                if dry_run:
                    print("✓ Dry run completed successfully")
                else:
                    print("✓ Restore completed successfully")
                    print("\nIMPORTANT: You may need to restart LNMT services:")
                    print("  sudo systemctl restart lnmt")
                    print("  sudo systemctl restart nginx")
                    print("  sudo systemctl restart mysql")
            else:
                print("✗ Restore operation failed")
            
            return success
            
        except Exception as e:
            print(f"✗ Restore failed: {e}")
            return False
    
    def validate_backup(self, backup_id: str) -> bool:
        """Validate backup integrity"""
        try:
            print(f"Validating backup: {backup_id}")
            is_valid = self.service.validate_backup(backup_id)
            
            if is_valid:
                print("✓ Backup validation passed - backup is intact")
            else:
                print("✗ Backup validation failed - backup may be corrupted")
            
            return is_valid
            
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    def delete_backup(self, backup_id: str, force: bool = False) -> bool:
        """Delete a backup"""
        if not self._check_permissions('delete'):
            return False
        
        try:
            # Get backup info
            metadata = self.service._get_backup_metadata(backup_id)
            if not metadata:
                print(f"Backup not found: {backup_id}")
                return False
            
            print(f"\nDeleting backup: {backup_id}")
            print(f"Created: {self._format_timestamp(metadata.timestamp)}")
            print(f"Description: {metadata.description}")
            print(f"Size: {self._format_size(metadata.size_bytes)}")
            
            if not force:
                response = input("\nAre you sure you want to delete this backup? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Deletion cancelled.")
                    return False
            
            success = self.service.delete_backup(backup_id, force=force)
            
            if success:
                print("✓ Backup deleted successfully")
            else:
                print("✗ Failed to delete backup")
            
            return success
            
        except Exception as e:
            print(f"Deletion error: {e}")
            return False
    
    def cleanup_backups(self, keep_count: int = 10) -> bool:
        """Clean up old backups"""
        if not self._check_permissions('cleanup'):
            return False
        
        try:
            backups = self.service.list_backups()
            total_backups = len(backups)
            
            if total_backups <= keep_count:
                print(f"No cleanup needed. Current backups: {total_backups}, Keep: {keep_count}")
                return True
            
            to_delete = total_backups - keep_count
            print(f"\nCleanup operation:")
            print(f"Total backups: {total_backups}")
            print(f"Keep most recent: {keep_count}")
            print(f"Will delete: {to_delete} old backups")
            
            # Show backups that will be deleted
            print("\nBackups to be deleted:")
            for backup in backups[keep_count:]:
                print(f"  {backup.backup_id} - {self._format_timestamp(backup.timestamp)}")
            
            response = input(f"\nProceed with cleanup? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("Cleanup cancelled.")
                return False
            
            deleted_count = self.service.cleanup_old_backups(keep_count)
            print(f"✓ Cleanup completed. Deleted {deleted_count} backups.")
            
            return True
            
        except Exception as e:
            print(f"Cleanup error: {e}")
            return False
    
    def interactive_mode(self) -> None:
        """Interactive CLI mode"""
        print("\n" + "=" * 60)
        print("LNMT Backup Manager - Interactive Mode")
        print("=" * 60)
        
        while True:
            print("\nAvailable commands:")
            print("  1. List backups")
            print("  2. Create backup")
            print("  3. Restore backup")
            print("  4. Validate backup")
            print("  5. Show backup info")
            print("  6. Delete backup")
            print("  7. Cleanup old backups")
            print("  8. Exit")
            
            try:
                choice = input("\nEnter choice (1-8): ").strip()
                
                if choice == '1':
                    self.list_backups(show_details=True)
                
                elif choice == '2':
                    print("\nBackup types: full, config, database")
                    backup_type = input("Backup type [full]: ").strip() or "full"
                    description = input("Description (optional): ").strip()
                    self.create_backup(description, backup_type)
                
                elif choice == '3':
                    backups = self.service.list_backups()
                    if not backups:
                        print("No backups available.")
                        continue
                    
                    print("\nAvailable backups:")
                    for i, backup in enumerate(backups):
                        print(f"  {i+1}. {backup.backup_id} - {self._format_timestamp(backup.timestamp)}")
                    
                    try:
                        idx = int(input("Select backup number: ")) - 1
                        if 0 <= idx < len(backups):
                            backup_id = backups[idx].backup_id
                            dry_run = input("Dry run? [y/N]: ").strip().lower() in ['y', 'yes']
                            self.restore_backup(backup_id, dry_run=dry_run)
                        else:
                            print("Invalid selection.")
                    except ValueError:
                        print("Invalid input.")
                
                elif choice == '4':
                    backup_id = input("Enter backup ID: ").strip()
                    if backup_id:
                        self.validate_backup(backup_id)
                
                elif choice == '5':
                    backup_id = input("Enter backup ID: ").strip()
                    if backup_id:
                        self.show_backup_info(backup_id)
                
                elif choice == '6':
                    backup_id = input("Enter backup ID: ").strip()
                    if backup_id:
                        self.delete_backup(backup_id)
                
                elif choice == '7':
                    try:
                        keep_count = int(input("Number of backups to keep [10]: ") or "10")
                        self.cleanup_backups(keep_count)
                    except ValueError:
                        print("Invalid number.")
                
                elif choice == '8':
                    print("Goodbye!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-8.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                print("\n\nExiting...")
                break


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="LNMT Backup Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create backup:
    sudo %(prog)s --create --description "Before update"
    sudo %(prog)s --create --type config
  
  List and info:
    %(prog)s --list
    %(prog)s --list --details
    %(prog)s --info lnmt_backup_20240101_120000
  
  Restore:
    sudo %(prog)s --restore lnmt_backup_20240101_120000
    sudo %(prog)s --restore lnmt_backup_20240101_120000 --dry-run
  
  Validate and cleanup:
    %(prog)s --validate lnmt_backup_20240101_120000
    sudo %(prog)s --cleanup --keep 5
  
  Interactive mode:
    %(prog)s --interactive
        """
    )
    
    # Main operations (mutually exclusive)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument('--create', action='store_true',
                           help='Create a new backup')
    operations.add_argument('--restore', metavar='BACKUP_ID',
                           help='Restore from specified backup')
    operations.add_argument('--list', action='store_true',
                           help='List all available backups')
    operations.add_argument('--info', metavar='BACKUP_ID',
                           help='Show detailed information about a backup')
    operations.add_argument('--validate', metavar='BACKUP_ID',
                           help='Validate backup integrity')
    operations.add_argument('--delete', metavar='BACKUP_ID',
                           help='Delete a backup')
    operations.add_argument('--cleanup', action='store_true',
                           help='Clean up old backups')
    operations.add_argument('--interactive', action='store_true',
                           help='Start interactive mode')
    
    # Options for backup creation
    parser.add_argument('--type', choices=['full', 'config', 'database'], 
                       default='full', help='Type of backup to create')
    parser.add_argument('--description', help='Description for the backup')
    
    # Options for restore
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview restore without making changes')
    parser.add_argument('--target', help='Target directory for restore')
    parser.add_argument('--no-safety-backup', action='store_true',
                       help='Skip creating safety backup before restore')
    
    # Options for listing
    parser.add_argument('--details', action='store_true',
                       help='Show detailed information in list')
    
    # Options for cleanup
    parser.add_argument('--keep', type=int, default=10,
                       help='Number of recent backups to keep (default: 10)')
    
    # Options for delete
    parser.add_argument('--force', action='store_true',
                       help='Force operation without confirmation')
    
    # General options
    parser.add_argument('--backup-dir', default='/var/backups/lnmt',
                       help='Backup directory (default: /var/backups/lnmt)')
    parser.add_argument('--version', action='version', version='LNMT Backup CLI 1.0')
    
    args = parser.parse_args()
    
    # Initialize CLI
    try:
        cli = BackupCLI(backup_dir=args.backup_dir)
    except Exception as e:
        print(f"Error initializing backup service: {e}")
        return 1
    
    # Execute operations
    try:
        if args.create:
            success = cli.create_backup(
                description=args.description or "",
                backup_type=args.type
            )
            return 0 if success else 1
        
        elif args.restore:
            success = cli.restore_backup(
                backup_id=args.restore,
                dry_run=args.dry_run,
                target_dir=args.target,
                no_safety_backup=args.no_safety_backup
            )
            return 0 if success else 1
        
        elif args.list:
            cli.list_backups(show_details=args.details)
            return 0
        
        elif args.info:
            cli.show_backup_info(args.info)
            return 0
        
        elif args.validate:
            success = cli.validate_backup(args.validate)
            return 0 if success else 1
        
        elif args.delete:
            success = cli.delete_backup(args.delete, force=args.force)
            return 0 if success else 1
        
        elif args.cleanup:
            success = cli.cleanup_backups(keep_count=args.keep)
            return 0 if success else 1
        
        elif args.interactive:
            cli.interactive_mode()
            return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())