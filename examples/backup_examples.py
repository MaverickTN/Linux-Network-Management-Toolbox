#!/usr/bin/env python3
"""
LNMT Backup System Examples and Tests

This file demonstrates usage of the LNMT backup and restore system
and provides test scenarios for validation.

Examples include:
- Basic backup operations
- Scheduled backup automation
- Disaster recovery procedures
- Integration with monitoring systems
- Custom backup configurations

Sample CLI Session:
    # Create a full system backup
    $ sudo backupctl.py --create --description "Pre-maintenance backup"
    Creating full backup...
    Description: Pre-maintenance backup
    ✓ Backup created successfully: lnmt_backup_20240701_143052
      Size: 145.2 MB
      Files: 1,247
      Type: full

    # List all backups
    $ backupctl.py --list
    Available backups (3):
    --------------------------------------------------------------------------------
    ID: lnmt_backup_20240701_143052
      Date: 2024-07-01 14:30:52
      Size: 145.2 MB (1247 files)
      Type: full
      Description: Pre-maintenance backup
      Status: ✓ Valid

    ID: lnmt_backup_20240630_090000
      Date: 2024-06-30 09:00:00
      Size: 142.8 MB (1203 files)
      Type: full
      Description: Daily automated backup
      Status: ✓ Valid

    # Restore with dry run first
    $ sudo backupctl.py --restore lnmt_backup_20240701_143052 --dry-run
    
    Restoring backup: lnmt_backup_20240701_143052
    Created: 2024-07-01 14:30:52
    Description: Pre-maintenance backup
    Type: full
    Files to restore: 1247

    --- DRY RUN MODE ---
    No changes will be made to the system

    Starting restore operation...
    Would restore: /etc/lnmt/config.yaml -> /etc/lnmt/config.yaml
    Would restore: /etc/lnmt/services.conf -> /etc/lnmt/services.conf
    [... more files ...]
    ✓ Dry run completed successfully

    # Actual restore
    $ sudo backupctl.py --restore lnmt_backup_20240701_143052
    
    Restoring backup: lnmt_backup_20240701_143052
    [... backup info ...]

    A safety backup will be created before restore.

    Proceed with restore? [y/N]: y

    Creating safety backup before restore...
    ✓ Backup created successfully: lnmt_backup_20240701_144523
    Starting restore operation...
    ✓ Restore completed successfully

    IMPORTANT: You may need to restart LNMT services:
      sudo systemctl restart lnmt
      sudo systemctl restart nginx
      sudo systemctl restart mysql
"""

import os
import sys
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backup_restore import BackupRestoreService, BackupMetadata


class BackupExamples:
    """Examples and test scenarios for LNMT backup system"""
    
    def __init__(self, test_dir: str = "/tmp/lnmt_backup_examples"):
        """Initialize with test environment"""
        self.test_dir = Path(test_dir)
        self.backup_dir = self.test_dir / "backups"
        self.mock_lnmt_dir = self.test_dir / "mock_lnmt"
        
        self._setup_test_environment()
        self.service = BackupRestoreService(backup_dir=str(self.backup_dir))
    
    def _setup_test_environment(self):
        """Create mock LNMT directory structure for testing"""
        # Clean up and recreate test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        
        self.test_dir.mkdir(parents=True)
        
        # Create mock LNMT structure
        mock_paths = {
            'config': self.mock_lnmt_dir / 'etc' / 'lnmt',
            'database': self.mock_lnmt_dir / 'var' / 'lib' / 'lnmt',
            'logs': self.mock_lnmt_dir / 'var' / 'log' / 'lnmt',
            'systemd': self.mock_lnmt_dir / 'etc' / 'systemd' / 'system'
        }
        
        for path in mock_paths.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # Create mock configuration files
        config_files = {
            mock_paths['config'] / 'config.yaml': """
# LNMT Configuration
server:
  host: 0.0.0.0
  port: 8080
  debug: false

database:
  type: sqlite
  path: /var/lib/lnmt/lnmt.db
  
logging:
  level: INFO
  file: /var/log/lnmt/lnmt.log
""",
            mock_paths['config'] / 'services.conf': """
# Service Configuration
nginx:
  enabled: true
  config_path: /etc/nginx/nginx.conf

mysql:
  enabled: true
  socket: /var/run/mysqld/mysqld.sock

php:
  version: "8.1"
  modules: [curl, json, mysql]
""",
            mock_paths['config'] / 'version': "1.2.3",
            
            mock_paths['systemd'] / 'lnmt.service': """
[Unit]
Description=LNMT Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/lnmt-server
Restart=always

[Install]
WantedBy=multi-user.target
""",
            
            mock_paths['logs'] / 'lnmt.log': """
2024-07-01 10:00:00 INFO Starting LNMT service
2024-07-01 10:00:01 INFO Database connection established
2024-07-01 10:00:02 INFO Web server listening on port 8080
""",
            
            mock_paths['logs'] / 'error.log': """
2024-07-01 09:59:58 ERROR Failed to connect to database (retry 1/3)
2024-07-01 09:59:59 ERROR Failed to connect to database (retry 2/3)
2024-07-01 10:00:00 INFO Database connection established
"""
        }
        
        for file_path, content in config_files.items():
            file_path.write_text(content.strip())
        
        # Create mock SQLite database
        db_path = mock_paths['database'] / 'lnmt.db'
        import sqlite3
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create sample tables
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE services (
                id INTEGER PRIMARY KEY,
                name TEXT,
                status TEXT,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert sample data
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                      ("admin", "admin@lnmt.local"))
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                      ("user1", "user1@lnmt.local"))
        
        cursor.execute("INSERT INTO services (name, status) VALUES (?, ?)", 
                      ("nginx", "running"))
        cursor.execute("INSERT INTO services (name, status) VALUES (?, ?)", 
                      ("mysql", "running"))
        cursor.execute("INSERT INTO services (name, status) VALUES (?, ?)", 
                      ("php-fpm", "running"))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Test environment created at: {self.mock_lnmt_dir}")
    
    def example_basic_operations(self):
        """Example: Basic backup and restore operations"""
        print("\n" + "="*60)
        print("EXAMPLE 1: Basic Backup Operations")
        print("="*60)
        
        # Override default paths to use our mock structure
        self.service.default_paths = {
            'config_dir': self.mock_lnmt_dir / 'etc' / 'lnmt',
            'database_dir': self.mock_lnmt_dir / 'var' / 'lib' / 'lnmt',
            'log_dir': self.mock_lnmt_dir / 'var' / 'log' / 'lnmt',
            'service_files': [
                self.mock_lnmt_dir / 'etc' / 'systemd' / 'system' / 'lnmt.service',
            ],
            'additional_configs': []
        }
        
        # 1. Create different types of backups
        print("\n1. Creating different backup types...")
        
        config_backup = self.service.create_backup(
            "Configuration only backup", 
            backup_type="config"
        )
        print(f"✓ Config backup: {config_backup}")
        
        time.sleep(1)  # Ensure different timestamps
        
        full_backup = self.service.create_backup(
            "Complete system backup", 
            backup_type="full"
        )
        print(f"✓ Full backup: {full_backup}")
        
        # 2. List backups
        print("\n2. Listing all backups...")
        backups = self.service.list_backups()
        for backup in backups:
            print(f"  {backup.backup_id}: {backup.description} "
                  f"({backup.backup_type}, {backup.file_count} files)")
        
        # 3. Validate backups
        print("\n3. Validating backup integrity...")
        for backup in backups:
            is_valid = self.service.validate_backup(backup.backup_id)
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"  {backup.backup_id}: {status}")
        
        # 4. Demonstrate restore with dry run
        print("\n4. Testing restore (dry run)...")
        success = self.service.restore_backup(
            full_backup, 
            target_dir=str(self.test_dir / "restore_test"),
            dry_run=True
        )
        print(f"  Dry run result: {'✓ Success' if success else '✗ Failed'}")
        
        return backups
    
    def example_disaster_recovery(self):
        """Example: Disaster recovery scenario"""
        print("\n" + "="*60)
        print("EXAMPLE 2: Disaster Recovery Scenario")
        print("="*60)
        
        # Create a baseline backup
        print("\n1. Creating baseline backup...")
        baseline_backup = self.service.create_backup(
            "Baseline before disaster simulation",
            backup_type="full"
        )
        
        # Simulate disaster - corrupt/delete files
        print("\n2. Simulating disaster (corrupting files)...")
        config_file = self.mock_lnmt_dir / 'etc' / 'lnmt' / 'config.yaml'
        original_content = config_file.read_text()
        
        # Corrupt the config file
        config_file.write_text("CORRUPTED DATA - DISASTER SIMULATION")
        
        # Delete a service file
        service_file = self.mock_lnmt_dir / 'etc' / 'systemd' / 'system' / 'lnmt.service'
        service_file.unlink()
        
        print("  ✗ Configuration file corrupted")
        print("  ✗ Service file deleted")
        print("  System is now in a broken state!")
        
        # Recovery process
        print("\n3. Disaster recovery process...")
        
        # Step 1: Validate available backups
        print("   Step 1: Validating available backups...")
        backups = self.service.list_backups()
        valid_backups = []
        for backup in backups:
            if self.service.validate_backup(backup.backup_id):
                valid_backups.append(backup)
                print(f"     ✓ {backup.backup_id} is valid")
            else:
                print(f"     ✗ {backup.backup_id} is corrupted")
        
        if not valid_backups:
            print("   CRITICAL: No valid backups available!")
            return False
        
        # Step 2: Create emergency backup of current state
        print("   Step 2: Creating emergency backup of current state...")
        emergency_backup = self.service.create_backup(
            "Emergency backup before recovery",
            backup_type="full"
        )
        
        # Step 3: Restore from most recent valid backup
        print("   Step 3: Restoring from most recent valid backup...")
        latest_backup = valid_backups[0]  # List is sorted by timestamp desc
        
        recovery_success = self.service.restore_backup(
            latest_backup.backup_id,
            create_safety_backup=False  # We already have emergency backup
        )
        
        if recovery_success:
            print("   ✓ System recovery completed successfully!")
            
            # Verify recovery
            if config_file.exists() and "server:" in config_file.read_text():
                print("   ✓ Configuration file restored")
            if service_file.exists():
                print("   ✓ Service file restored")
                
            print("\n   Recovery Summary:")
            print(f"     - Restored from: {latest_backup.backup_id}")
            print(f"     - Backup date: {latest_backup.timestamp}")
            print(f"     - Emergency backup: {emergency_backup}")
            
        else:
            print("   ✗ System recovery failed!")
            return False
        
        return True
    
    def example_automated_backup_schedule(self):
        """Example: Automated backup scheduling simulation"""
        print("\n" + "="*60)
        print("EXAMPLE 3: Automated Backup Schedule Simulation")
        print("="*60)
        
        print("\nSimulating automated backup schedule:")
        print("- Daily full backups at 2 AM")
        print("- Hourly config backups during business hours")
        print("- Weekly cleanup (keep last 30 days)")
        
        # Simulate multiple backups over time
        backup_schedule = [
            ("Daily backup - Week 1", "full", 7),
            ("Hourly config backups", "config", 8),
            ("Daily backup - Week 2", "full", 7),
            ("Daily backup - Week 3", "full", 7),
            ("Daily backup - Week 4", "full", 7),
        ]
        
        all_backups = []
        
        for description, backup_type, count in backup_schedule:
            print(f"\n  Creating {description}...")
            for i in range(count):
                backup_id = self.service.create_backup(
                    f"{description} - Day {i+1}",
                    backup_type=backup_type
                )
                all_backups.append(backup_id)
                time.sleep(0.1)  # Small delay for different timestamps
        
        # Show current backup status
        print(f"\n  Total backups created: {len(all_backups)}")
        
        current_backups = self.service.list_backups()
        total_size = sum(backup.size_bytes for backup in current_backups)
        
        print(f"  Total storage used: {total_size / 1024 / 1024:.1f} MB")
        
        # Simulate cleanup policy
        print("\n  Applying retention policy (keep last 10 backups)...")
        deleted_count = self.service.cleanup_old_backups(keep_count=10)
        
        remaining_backups = self.service.list_backups()
        remaining_size = sum(backup.size_bytes for backup in remaining_backups)
        
        print(f"  Deleted {deleted_count} old backups")
        print(f"  Remaining backups: {len(remaining_backups)}")
        print(f"  Storage after cleanup: {remaining_size / 1024 / 1024:.1f} MB")
        print(f"  Space saved: {(total_size - remaining_size) / 1024 / 1024:.1f} MB")
        
        return remaining_backups
    
    def example_custom_backup_paths(self):
        """Example: Custom backup with specific paths"""
        print("\n" + "="*60)
        print("EXAMPLE 4: Custom Backup Paths")
        print("="*60)
        
        # Create additional test files
        custom_dir = self.test_dir / "custom_app"
        custom_dir.mkdir(exist_ok=True)
        
        (custom_dir / "app.conf").write_text("custom_app_config=true")
        (custom_dir / "data.json").write_text('{"users": [], "settings": {}}')
        
        print(f"\n  Created custom application files in: {custom_dir}")
        
        # Create backup with custom paths
        custom_paths = [
            self.mock_lnmt_dir / 'etc' / 'lnmt' / 'config.yaml',  # Specific file
            custom_dir,  # Entire directory
        ]
        
        print(f"  Backing up custom paths:")
        for path in custom_paths:
            print(f"    - {path}")
        
        custom_backup = self.service.create_backup(
            "Custom application backup",
            backup_type="config",
            custom_paths=custom_paths
        )
        
        print(f"  ✓ Custom backup created: {custom_backup}")
        
        # Verify custom backup contents
        metadata = self.service._get_backup_metadata(custom_backup)
        print(f"  Files included: {metadata.file_count}")
        print(f"  Backup size: {metadata.size_bytes / 1024:.1f} KB")
        
        # Test restore to different location
        restore_target = self.test_dir / "custom_restore"
        
        print(f"\n  Testing restore to custom location: {restore_target}")
        success = self.service.restore_backup(
            custom_backup,
            target_dir=str(restore_target),
            create_safety_backup=False
        )
        
        if success:
            print("  ✓ Custom restore completed")
            
            # Verify restored files
            restored_config = restore_target / str(custom_paths[0]).lstrip('/')
            restored_app = restore_target / str(custom_paths[1]).lstrip('/')
            
            if restored_config.exists():
                print(f"    ✓ Config file restored: {restored_config}")
            if restored_app.exists():
                print(f"    ✓ App directory restored: {restored_app}")
        
        return custom_backup
    
    def example_monitoring_integration(self):
        """Example: Integration with monitoring systems"""
        print("\n" + "="*60)
        print("EXAMPLE 5: Monitoring Integration")
        print("="*60)
        
        # Simulate monitoring checks
        print("\n  Monitoring backup system health...")
        
        # Check 1: Backup directory accessibility
        backup_accessible = self.backup_dir.exists() and os.access(self.backup_dir, os.W_OK)
        print(f"  Backup directory accessible: {'✓' if backup_accessible else '✗'}")
        
        # Check 2: Recent backup availability
        backups = self.service.list_backups()
        if backups:
            latest_backup = backups[0]
            backup_age = datetime.now() - datetime.strptime(latest_backup.timestamp, "%Y%m%d_%H%M%S")
            recent_backup = backup_age.total_seconds() < 86400  # Less than 24 hours
            print(f"  Recent backup available: {'✓' if recent_backup else '✗'}")
            print(f"    Latest backup: {latest_backup.backup_id}")
            print(f"    Age: {backup_age}")
        else:
            print("  Recent backup available: ✗ (No backups found)")
            recent_backup = False
        
        # Check 3: Backup integrity
        valid_backups = 0
        total_backups = len(backups)
        
        for backup in backups:
            if self.service.validate_backup(backup.backup_id):
                valid_backups += 1
        
        integrity_ok = valid_backups == total_backups if total_backups > 0 else False
        print(f"  Backup integrity: {'✓' if integrity_ok else '✗'}")
        print(f"    Valid backups: {valid_backups}/{total_backups}")
        
        # Check 4: Storage space
        if self.backup_dir.exists():
            total_size = sum(backup.size_bytes for backup in backups)
            available_space = shutil.disk_usage(self.backup_dir)[2]  # Free space
            space_ok = available_space > total_size * 2  # At least 2x current usage
            
            print(f"  Storage space: {'✓' if space_ok else '✗'}")
            print(f"    Used: {total_size / 1024 / 1024:.1f} MB")
            print(f"    Available: {available_space / 1024 / 1024 / 1024:.1f} GB")
        else:
            space_ok = False
            print("  Storage space: ✗ (Backup directory not found)")
        
        # Overall health score
        checks = [backup_accessible, recent_backup, integrity_ok, space_ok]
        health_score = sum(checks) / len(checks) * 100
        
        print(f"\n  Overall backup system health: {health_score:.0f}%")
        
        if health_score == 100:
            print("  Status: ✓ All systems operational")
        elif health_score >= 75:
            print("  Status: ⚠ Minor issues detected")
        else:
            print("  Status: ✗ Critical issues require attention")
        
        # Generate monitoring report
        report = {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "checks": {
                "backup_directory_accessible": backup_accessible,
                "recent_backup_available": recent_backup,
                "backup_integrity_ok": integrity_ok,
                "storage_space_ok": space_ok
            },
            "backup_count": total_backups,
            "valid_backup_count": valid_backups,
            "total_storage_mb": total_size / 1024 / 1024 if backups else 0
        }
        
        # Save monitoring report
        report_file = self.test_dir / "backup_monitoring_report.json"
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"  📊 Monitoring report saved: {report_file}")
        
        return report
    
    def example_backup_verification(self):
        """Example: Comprehensive backup verification"""
        print("\n" + "="*60)
        print("EXAMPLE 6: Backup Verification & Testing")
        print("="*60)
        
        # Get latest backup for testing
        backups = self.service.list_backups()
        if not backups:
            print("  No backups available for verification")
            return False
        
        test_backup = backups[0]
        print(f"\n  Testing backup: {test_backup.backup_id}")
        
        # Test 1: Checksum verification
        print("\n  Test 1: Checksum Verification")
        is_valid = self.service.validate_backup(test_backup.backup_id)
        print(f"    Result: {'✓ PASS' if is_valid else '✗ FAIL'}")
        
        # Test 2: Archive extraction test
        print("\n  Test 2: Archive Extraction Test")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                import tarfile
                archive_path = self.backup_dir / f"{test_backup.backup_id}.tar.gz"
                
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(temp_dir)
                    extracted_files = list(Path(temp_dir).rglob("*"))
                
                print(f"    Result: ✓ PASS - Extracted {len(extracted_files)} files")
        except Exception as e:
            print(f"    Result: ✗ FAIL - {e}")
        
        # Test 3: Database integrity check (if database backup exists)
        print("\n  Test 3: Database Integrity Check")
        db_files = [f for f in test_backup.files_included if f.endswith('.db')]
        
        if db_files:
            try:
                # Extract and test database
                with tempfile.TemporaryDirectory() as temp_dir:
                    import tarfile
                    import sqlite3
                    
                    archive_path = self.backup_dir / f"{test_backup.backup_id}.tar.gz"
                    with tarfile.open(archive_path, "r:gz") as tar:
                        tar.extractall(temp_dir)
                    
                    # Find extracted database file
                    db_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('.db'):
                                db_path = Path(root) / file
                                break
                        if db_path:
                            break
                    
                    if db_path and db_path.exists():
                        # Test database connection and integrity
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        
                        # Run integrity check
                        cursor.execute("PRAGMA integrity_check")
                        result = cursor.fetchone()[0]
                        
                        # Count tables and records
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        
                        conn.close()
                        
                        if result == "ok":
                            print(f"    Result: ✓ PASS - Database integrity OK ({len(tables)} tables)")
                        else:
                            print(f"    Result: ✗ FAIL - Database integrity issues: {result}")
                    else:
                        print("    Result: ⚠ SKIP - No database file found in backup")
                        
            except Exception as e:
                print(f"    Result: ✗ FAIL - Database test error: {e}")
        else:
            print("    Result: ⚠ SKIP - No database files in backup")
        
        # Test 4: File count verification
        print("\n  Test 4: File Count Verification")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                import tarfile
                archive_path = self.backup_dir / f"{test_backup.backup_id}.tar.gz"
                
                with tarfile.open(archive_path, "r:gz") as tar:
                    members = tar.getmembers()
                    actual_files = len([m for m in members if m.isfile()])
                
                expected_files = test_backup.file_count
                
                if actual_files == expected_files:
                    print(f"    Result: ✓ PASS - File count matches ({actual_files} files)")
                else:
                    print(f"    Result: ✗ FAIL - File count mismatch (expected: {expected_files}, actual: {actual_files})")
                    
        except Exception as e:
            print(f"    Result: ✗ FAIL - File count test error: {e}")
        
        # Test 5: Restore simulation
        print("\n  Test 5: Restore Simulation (Dry Run)")
        try:
            restore_success = self.service.restore_backup(
                test_backup.backup_id,
                target_dir=str(self.test_dir / "verification_restore"),
                dry_run=True,
                create_safety_backup=False
            )
            
            print(f"    Result: {'✓ PASS' if restore_success else '✗ FAIL'} - Restore simulation")
            
        except Exception as e:
            print(f"    Result: ✗ FAIL - Restore simulation error: {e}")
        
        print(f"\n  Verification completed for backup: {test_backup.backup_id}")
        return True
    
    def run_all_examples(self):
        """Run all examples in sequence"""
        print("LNMT Backup System - Comprehensive Examples")
        print("=" * 80)
        
        try:
            # Run all examples
            self.example_basic_operations()
            self.example_disaster_recovery()
            self.example_automated_backup_schedule()
            self.example_custom_backup_paths()
            self.example_monitoring_integration()
            self.example_backup_verification()
            
            # Final summary
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            
            final_backups = self.service.list_backups()
            total_size = sum(backup.size_bytes for backup in final_backups)
            
            print(f"Total backups created: {len(final_backups)}")
            print(f"Total storage used: {total_size / 1024 / 1024:.1f} MB")
            print(f"Test environment: {self.test_dir}")
            
            print("\nAll examples completed successfully! 🎉")
            print("\nTo clean up test environment:")
            print(f"  rm -rf {self.test_dir}")
            
        except Exception as e:
            print(f"\nExample execution failed: {e}")
            raise


def main():
    """Main function to run examples"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LNMT Backup System Examples")
    parser.add_argument('--test-dir', default='/tmp/lnmt_backup_examples',
                       help='Directory for test environment')
    parser.add_argument('--example', choices=['basic', 'disaster', 'schedule', 
                       'custom', 'monitoring', 'verification', 'all'],
                       default='all', help='Which example to run')
    
    args = parser.parse_args()
    
    # Initialize examples
    examples = BackupExamples(test_dir=args.test_dir)
    
    try:
        if args.example == 'all':
            examples.run_all_examples()
        elif args.example == 'basic':
            examples.example_basic_operations()
        elif args.example == 'disaster':
            examples.example_disaster_recovery()
        elif args.example == 'schedule':
            examples.example_automated_backup_schedule()
        elif args.example == 'custom':
            examples.example_custom_backup_paths()
        elif args.example == 'monitoring':
            examples.example_monitoring_integration()
        elif args.example == 'verification':
            examples.example_backup_verification()
            
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nExample failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()