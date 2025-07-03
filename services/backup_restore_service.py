#!/usr/bin/env python3
"""
LNMT Backup and Restore Service

A comprehensive backup and restore system for LNMT configuration and database files.
Supports timestamped snapshots with validation and safe recovery operations.

Features:
- Creates timestamped backup archives
- Validates backup integrity before restore
- Supports selective file restoration
- Maintains backup metadata and logs
- Safe operations with rollback capabilities

Usage Example:
    from services.backup_restore import BackupRestoreService
    
    service = BackupRestoreService()
    
    # Create a backup
    backup_id = service.create_backup("manual_backup")
    
    # List available backups
    backups = service.list_backups()
    
    # Restore from backup
    service.restore_backup(backup_id, dry_run=True)  # Preview first
    service.restore_backup(backup_id)  # Actual restore
"""

import os
import sys
import json
import shutil
import tarfile
import hashlib
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import tempfile


@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    timestamp: str
    description: str
    size_bytes: int
    file_count: int
    checksum: str
    created_by: str
    lnmt_version: str
    backup_type: str  # 'full', 'config', 'database'
    files_included: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        return cls(**data)


class BackupRestoreService:
    """Service for backing up and restoring LNMT system files"""
    
    def __init__(self, backup_dir: str = "/var/backups/lnmt"):
        """
        Initialize the backup service
        
        Args:
            backup_dir: Directory to store backups (default: /var/backups/lnmt)
        """
        self.backup_dir = Path(backup_dir)
        self.metadata_file = self.backup_dir / "metadata.json"
        
        # Default paths to backup
        self.default_paths = {
            'config_dir': Path('/etc/lnmt'),
            'database_dir': Path('/var/lib/lnmt'),
            'log_dir': Path('/var/log/lnmt'),
            'service_files': [
                Path('/etc/systemd/system/lnmt.service'),
                Path('/etc/systemd/system/lnmt-worker.service'),
            ],
            'additional_configs': [
                Path('/etc/nginx/sites-available/lnmt'),
                Path('/etc/mysql/conf.d/lnmt.cnf'),
            ]
        }
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Ensure backup directory exists
        self._initialize_backup_dir()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for backup operations"""
        logger = logging.getLogger('lnmt_backup')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # File handler
            log_file = self.backup_dir / 'backup.log'
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        return logger
    
    def _initialize_backup_dir(self) -> None:
        """Initialize backup directory and metadata file"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions
            os.chmod(self.backup_dir, 0o700)
            
            # Initialize metadata file if it doesn't exist
            if not self.metadata_file.exists():
                with open(self.metadata_file, 'w') as f:
                    json.dump({"backups": {}}, f, indent=2)
                os.chmod(self.metadata_file, 0o600)
                
        except Exception as e:
            self.logger.error(f"Failed to initialize backup directory: {e}")
            raise
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _get_lnmt_version(self) -> str:
        """Get LNMT version from system"""
        try:
            # Try to get version from package info or version file
            version_file = Path('/etc/lnmt/version')
            if version_file.exists():
                return version_file.read_text().strip()
            return "unknown"
        except Exception:
            return "unknown"
    
    def _validate_paths(self, paths: List[Path]) -> List[Path]:
        """Validate that paths exist and are accessible"""
        valid_paths = []
        for path in paths:
            if path.exists():
                if path.is_file() and os.access(path, os.R_OK):
                    valid_paths.append(path)
                elif path.is_dir() and os.access(path, os.R_OK | os.X_OK):
                    valid_paths.append(path)
                else:
                    self.logger.warning(f"Path not accessible: {path}")
            else:
                self.logger.warning(f"Path does not exist: {path}")
        return valid_paths
    
    def _create_archive(self, backup_id: str, paths: List[Path]) -> Tuple[Path, int]:
        """Create compressed archive of specified paths"""
        archive_path = self.backup_dir / f"{backup_id}.tar.gz"
        file_count = 0
        
        with tarfile.open(archive_path, "w:gz") as tar:
            for path in paths:
                try:
                    if path.is_file():
                        tar.add(path, arcname=str(path))
                        file_count += 1
                    elif path.is_dir():
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = Path(root) / file
                                if file_path.exists() and os.access(file_path, os.R_OK):
                                    tar.add(file_path, arcname=str(file_path))
                                    file_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to add {path} to archive: {e}")
        
        return archive_path, file_count
    
    def _backup_database(self, backup_dir: Path) -> List[Path]:
        """Create database backups"""
        db_backups = []
        db_dir = Path('/var/lib/lnmt')
        
        if not db_dir.exists():
            return db_backups
        
        # SQLite databases
        for db_file in db_dir.glob("*.db"):
            if db_file.exists():
                backup_path = backup_dir / f"{db_file.name}.backup"
                try:
                    # Use SQLite backup API for consistency
                    source_conn = sqlite3.connect(str(db_file))
                    backup_conn = sqlite3.connect(str(backup_path))
                    source_conn.backup(backup_conn)
                    source_conn.close()
                    backup_conn.close()
                    db_backups.append(backup_path)
                    self.logger.info(f"Backed up database: {db_file}")
                except Exception as e:
                    self.logger.error(f"Failed to backup database {db_file}: {e}")
        
        return db_backups
    
    def create_backup(self, description: str = "", backup_type: str = "full", 
                     custom_paths: Optional[List[Path]] = None) -> str:
        """
        Create a new backup
        
        Args:
            description: Description for the backup
            backup_type: Type of backup ('full', 'config', 'database')
            custom_paths: Custom paths to backup (overrides defaults)
            
        Returns:
            backup_id: Unique identifier for the backup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"lnmt_backup_{timestamp}"
        
        self.logger.info(f"Starting backup creation: {backup_id}")
        
        try:
            # Determine paths to backup
            if custom_paths:
                paths_to_backup = custom_paths
            else:
                paths_to_backup = []
                
                if backup_type in ['full', 'config']:
                    paths_to_backup.extend([
                        self.default_paths['config_dir'],
                        *self.default_paths['service_files'],
                        *self.default_paths['additional_configs']
                    ])
                
                if backup_type in ['full', 'database']:
                    paths_to_backup.extend([
                        self.default_paths['database_dir']
                    ])
                
                if backup_type == 'full':
                    paths_to_backup.append(self.default_paths['log_dir'])
            
            # Validate paths
            valid_paths = self._validate_paths(paths_to_backup)
            
            if not valid_paths:
                raise ValueError("No valid paths found to backup")
            
            # Create temporary directory for database backups
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Backup databases separately for consistency
                db_backups = self._backup_database(temp_path)
                valid_paths.extend(db_backups)
                
                # Create archive
                archive_path, file_count = self._create_archive(backup_id, valid_paths)
            
            # Calculate checksum
            checksum = self._calculate_checksum(archive_path)
            size_bytes = archive_path.stat().st_size
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=timestamp,
                description=description or f"Automatic {backup_type} backup",
                size_bytes=size_bytes,
                file_count=file_count,
                checksum=checksum,
                created_by=os.getenv('USER', 'root'),
                lnmt_version=self._get_lnmt_version(),
                backup_type=backup_type,
                files_included=[str(p) for p in valid_paths]
            )
            
            # Save metadata
            self._save_metadata(metadata)
            
            self.logger.info(f"Backup created successfully: {backup_id}")
            self.logger.info(f"Archive size: {size_bytes / 1024 / 1024:.2f} MB")
            self.logger.info(f"Files backed up: {file_count}")
            
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            # Cleanup on failure
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            if archive_path.exists():
                archive_path.unlink()
            raise
    
    def _save_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to metadata file"""
        try:
            # Load existing metadata
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            # Add new backup metadata
            data["backups"][metadata.backup_id] = metadata.to_dict()
            
            # Save updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            raise
    
    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups"""
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            backups = []
            for backup_id, backup_data in data.get("backups", {}).items():
                try:
                    metadata = BackupMetadata.from_dict(backup_data)
                    backups.append(metadata)
                except Exception as e:
                    self.logger.warning(f"Invalid metadata for backup {backup_id}: {e}")
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.timestamp, reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []
    
    def validate_backup(self, backup_id: str) -> bool:
        """Validate backup integrity"""
        try:
            # Get metadata
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                return False
            
            # Check if archive exists
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            if not archive_path.exists():
                self.logger.error(f"Archive file missing: {archive_path}")
                return False
            
            # Verify checksum
            current_checksum = self._calculate_checksum(archive_path)
            if current_checksum != metadata.checksum:
                self.logger.error(f"Checksum mismatch for {backup_id}")
                return False
            
            # Verify archive can be opened
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.getnames()  # Try to read archive contents
            except Exception as e:
                self.logger.error(f"Archive corrupted: {e}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup validation failed: {e}")
            return False
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get metadata for a specific backup"""
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            backup_data = data.get("backups", {}).get(backup_id)
            if backup_data:
                return BackupMetadata.from_dict(backup_data)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {backup_id}: {e}")
            return None
    
    def restore_backup(self, backup_id: str, target_dir: Optional[str] = None, 
                      dry_run: bool = False, create_safety_backup: bool = True) -> bool:
        """
        Restore from a backup
        
        Args:
            backup_id: ID of backup to restore
            target_dir: Target directory (defaults to original locations)
            dry_run: Preview operation without making changes
            create_safety_backup: Create safety backup before restore
            
        Returns:
            bool: Success status
        """
        self.logger.info(f"Starting restore operation: {backup_id}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No changes will be made")
        
        try:
            # Validate backup
            if not self.validate_backup(backup_id):
                raise ValueError(f"Backup validation failed: {backup_id}")
            
            metadata = self._get_backup_metadata(backup_id)
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            
            # Create safety backup if requested
            safety_backup_id = None
            if create_safety_backup and not dry_run:
                self.logger.info("Creating safety backup before restore...")
                safety_backup_id = self.create_backup(
                    description=f"Safety backup before restore of {backup_id}",
                    backup_type="full"
                )
            
            # Extract and restore files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract archive
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(temp_path)
                
                # Restore files
                restored_files = []
                for file_path_str in metadata.files_included:
                    original_path = Path(file_path_str)
                    extracted_path = temp_path / file_path_str.lstrip('/')
                    
                    if not extracted_path.exists():
                        continue
                    
                    target_path = Path(target_dir) / file_path_str.lstrip('/') if target_dir else original_path
                    
                    if dry_run:
                        self.logger.info(f"Would restore: {original_path} -> {target_path}")
                        restored_files.append(str(target_path))
                    else:
                        try:
                            # Create parent directories
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Copy file
                            if extracted_path.is_file():
                                shutil.copy2(extracted_path, target_path)
                            elif extracted_path.is_dir():
                                if target_path.exists():
                                    shutil.rmtree(target_path)
                                shutil.copytree(extracted_path, target_path)
                            
                            restored_files.append(str(target_path))
                            self.logger.debug(f"Restored: {target_path}")
                            
                        except Exception as e:
                            self.logger.error(f"Failed to restore {original_path}: {e}")
                            
                            # Rollback on critical failure
                            if safety_backup_id:
                                self.logger.info("Rolling back due to restore failure...")
                                self.restore_backup(safety_backup_id, create_safety_backup=False)
                            raise
                
                if not dry_run:
                    self.logger.info(f"Restore completed: {len(restored_files)} files restored")
                else:
                    self.logger.info(f"Dry run completed: {len(restored_files)} files would be restored")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Restore operation failed: {e}")
            return False
    
    def delete_backup(self, backup_id: str, force: bool = False) -> bool:
        """Delete a backup"""
        try:
            if not force:
                # Safety check - don't delete if it's the only backup
                backups = self.list_backups()
                if len(backups) <= 1:
                    self.logger.warning("Cannot delete the only available backup")
                    return False
            
            # Remove archive file
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            if archive_path.exists():
                archive_path.unlink()
            
            # Remove from metadata
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            if backup_id in data.get("backups", {}):
                del data["backups"][backup_id]
                
                with open(self.metadata_file, 'w') as f:
                    json.dump(data, f, indent=2)
            
            self.logger.info(f"Backup deleted: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Clean up old backups, keeping only the most recent ones"""
        try:
            backups = self.list_backups()
            if len(backups) <= keep_count:
                return 0
            
            # Delete oldest backups
            deleted_count = 0
            for backup in backups[keep_count:]:
                if self.delete_backup(backup.backup_id, force=True):
                    deleted_count += 1
            
            self.logger.info(f"Cleaned up {deleted_count} old backups")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return 0


# Example usage and testing
if __name__ == "__main__":
    # Example usage (requires root privileges for system paths)
    import argparse
    
    parser = argparse.ArgumentParser(description="LNMT Backup Service Test")
    parser.add_argument("--test", action="store_true", help="Run test operations")
    parser.add_argument("--backup-dir", default="/tmp/lnmt_backup_test", 
                       help="Test backup directory")
    
    args = parser.parse_args()
    
    if args.test:
        # Test with a temporary directory
        service = BackupRestoreService(backup_dir=args.backup_dir)
        
        print("Testing backup creation...")
        backup_id = service.create_backup("Test backup", backup_type="config")
        
        print("Listing backups...")
        backups = service.list_backups()
        for backup in backups:
            print(f"  {backup.backup_id}: {backup.description} ({backup.size_bytes} bytes)")
        
        print("Validating backup...")
        is_valid = service.validate_backup(backup_id)
        print(f"  Backup valid: {is_valid}")
        
        print("Testing dry run restore...")
        service.restore_backup(backup_id, dry_run=True)
        
        print("Test completed!")
    else:
        print("Use --test flag to run test operations")
