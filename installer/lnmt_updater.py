#!/usr/bin/env python3
"""
LNMT Self-Updater - Linux Network Management Toolbox
Production-ready self-updater with rollback capabilities
Version: 1.0.0
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error
import hashlib
import tarfile
import zipfile

# Configuration
LNMT_HOME = Path("/opt/lnmt")
LNMT_CONFIG_DIR = Path("/etc/lnmt")
LNMT_DATA_DIR = Path("/var/lib/lnmt")
LNMT_LOG_DIR = Path("/var/log/lnmt")
BACKUP_DIR = LNMT_DATA_DIR / "backups"
VERSION_FILE = LNMT_HOME / "VERSION"
UPDATE_LOG = LNMT_LOG_DIR / "update.log"

# Update sources configuration
UPDATE_SOURCES = {
    "github": {
        "url": "https://api.github.com/repos/your-org/lnmt/releases/latest",
        "download_url_pattern": "https://github.com/your-org/lnmt/archive/refs/tags/{version}.tar.gz"
    },
    "pip": {
        "package": "lnmt",
        "index_url": "https://pypi.org/simple/"
    },
    "custom": {
        "url": "https://updates.your-domain.com/lnmt/latest.json"
    }
}

class LNMTUpdater:
    """LNMT Self-Updater with safe rollback capabilities"""
    
    def __init__(self, source: str = "github", dry_run: bool = False):
        self.source = source
        self.dry_run = dry_run
        self.current_version = self._get_current_version()
        self.backup_path: Optional[Path] = None
        self.temp_dir: Optional[Path] = None
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging for the updater"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(UPDATE_LOG),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _get_current_version(self) -> str:
        """Get currently installed LNMT version"""
        try:
            if VERSION_FILE.exists():
                return VERSION_FILE.read_text().strip()
            else:
                # Try to get version from Python package
                try:
                    import lnmt
                    return getattr(lnmt, '__version__', '0.0.0')
                except ImportError:
                    return '0.0.0'
        except Exception as e:
            self.logger.warning(f"Could not determine current version: {e}")
            return '0.0.0'
    
    def check_for_updates(self) -> Optional[Dict]:
        """Check for available updates from configured source"""
        self.logger.info(f"Checking for updates from {self.source}...")
        
        try:
            if self.source == "github":
                return self._check_github_updates()
            elif self.source == "pip":
                return self._check_pip_updates()
            elif self.source == "custom":
                return self._check_custom_updates()
            else:
                raise ValueError(f"Unknown update source: {self.source}")
                
        except Exception as e:
            self.logger.error(f"Failed to check for updates: {e}")
            return None
    
    def _check_github_updates(self) -> Optional[Dict]:
        """Check GitHub releases for updates"""
        url = UPDATE_SOURCES["github"]["url"]
        
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                
            latest_version = data["tag_name"].lstrip('v')
            
            if self._version_compare(latest_version, self.current_version) > 0:
                return {
                    "version": latest_version,
                    "download_url": UPDATE_SOURCES["github"]["download_url_pattern"].format(version=data["tag_name"]),
                    "changelog": data.get("body", ""),
                    "published_at": data["published_at"],
                    "prerelease": data["prerelease"]
                }
            return None
            
        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP error checking GitHub: {e}")
            return None
    
    def _check_pip_updates(self) -> Optional[Dict]:
        """Check PyPI for package updates"""
        package = UPDATE_SOURCES["pip"]["package"]
        
        try:
            # Use pip to check for updates
            result = subprocess.run([
                sys.executable, "-m", "pip", "list", "--outdated", "--format=json"
            ], capture_output=True, text=True, check=True)
            
            outdated_packages = json.loads(result.stdout)
            
            for pkg in outdated_packages:
                if pkg["name"].lower() == package.lower():
                    return {
                        "version": pkg["latest_version"],
                        "current": pkg["version"],
                        "type": "pip"
                    }
            return None
            
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.logger.error(f"Error checking pip updates: {e}")
            return None
    
    def _check_custom_updates(self) -> Optional[Dict]:
        """Check custom update server"""
        url = UPDATE_SOURCES["custom"]["url"]
        
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
            
            latest_version = data["version"]
            
            if self._version_compare(latest_version, self.current_version) > 0:
                return data
            return None
            
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            self.logger.error(f"Error checking custom updates: {e}")
            return None
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        def normalize(v):
            return [int(x) for x in v.replace('-', '.').split('.') if x.isdigit()]
        
        v1_parts = normalize(version1)
        v2_parts = normalize(version2)
        
        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        return 0
    
    def create_backup(self) -> bool:
        """Create a backup of the current installation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = BACKUP_DIR / f"lnmt_backup_{timestamp}"
        
        try:
            self.logger.info(f"Creating backup at {self.backup_path}")
            
            if self.dry_run:
                self.logger.info("[DRY RUN] Would create backup")
                return True
            
            # Ensure backup directory exists
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            self.backup_path.mkdir(parents=True, exist_ok=True)
            
            # Stop services before backup
            self._stop_services()
            
            # Backup directories
            backup_items = [
                (LNMT_HOME, "lnmt_home"),
                (LNMT_CONFIG_DIR, "config"),
                (LNMT_DATA_DIR / "db", "database"),
            ]
            
            for source, dest_name in backup_items:
                if source.exists():
                    dest = self.backup_path / dest_name
                    if source.is_dir():
                        shutil.copytree(source, dest, symlinks=True)
                    else:
                        shutil.copy2(source, dest)
                    self.logger.info(f"Backed up {source} to {dest}")
            
            # Create backup manifest
            manifest = {
                "timestamp": timestamp,
                "version": self.current_version,
                "source": self.source,
                "items": [item[1] for item in backup_items if item[0].exists()]
            }
            
            with open(self.backup_path / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info("Backup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
        finally:
            # Restart services
            self._start_services()
    
    def download_update(self, update_info: Dict) -> Optional[Path]:
        """Download the update package"""
        self.logger.info(f"Downloading update to version {update_info['version']}")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would download update")
            return Path("/tmp/fake_update.tar.gz")
        
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="lnmt_update_"))
            
            if self.source == "github":
                return self._download_github_update(update_info)
            elif self.source == "pip":
                return self._download_pip_update(update_info)
            elif self.source == "custom":
                return self._download_custom_update(update_info)
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            return None
    
    def _download_github_update(self, update_info: Dict) -> Path:
        """Download from GitHub release"""
        url = update_info["download_url"]
        filename = f"lnmt-{update_info['version']}.tar.gz"
        download_path = self.temp_dir / filename
        
        self.logger.info(f"Downloading from {url}")
        
        with urllib.request.urlopen(url) as response:
            with open(download_path, "wb") as f:
                shutil.copyfileobj(response, f)
        
        # Verify download (if checksum available)
        if "checksum" in update_info:
            if not self._verify_checksum(download_path, update_info["checksum"]):
                raise ValueError("Checksum verification failed")
        
        return download_path
    
    def _download_pip_update(self, update_info: Dict) -> Path:
        """Download using pip"""
        package = UPDATE_SOURCES["pip"]["package"]
        version = update_info["version"]
        
        # Use pip download to get the package
        download_path = self.temp_dir / f"{package}-{version}.whl"
        
        subprocess.run([
            sys.executable, "-m", "pip", "download",
            f"{package}=={version}",
            "--dest", str(self.temp_dir),
            "--no-deps"
        ], check=True)
        
        # Find the downloaded file
        downloaded_files = list(self.temp_dir.glob(f"{package}-{version}*"))
        if not downloaded_files:
            raise FileNotFoundError("Downloaded package not found")
        
        return downloaded_files[0]
    
    def _download_custom_update(self, update_info: Dict) -> Path:
        """Download from custom server"""
        url = update_info["download_url"]
        filename = update_info.get("filename", f"lnmt-{update_info['version']}.tar.gz")
        download_path = self.temp_dir / filename
        
        with urllib.request.urlopen(url) as response:
            with open(download_path, "wb") as f:
                shutil.copyfileobj(response, f)
        
        return download_path
    
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        actual_checksum = sha256_hash.hexdigest()
        return actual_checksum == expected_checksum
    
    def install_update(self, package_path: Path, update_info: Dict) -> bool:
        """Install the downloaded update"""
        self.logger.info(f"Installing update from {package_path}")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would install update")
            return True
        
        try:
            # Stop services
            self._stop_services()
            
            # Extract and install based on source type
            if self.source == "github" or self.source == "custom":
                return self._install_archive_update(package_path, update_info)
            elif self.source == "pip":
                return self._install_pip_update(package_path, update_info)
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            return False
        finally:
            # Start services
            self._start_services()
    
    def _install_archive_update(self, package_path: Path, update_info: Dict) -> bool:
        """Install from tar.gz or zip archive"""
        extract_dir = self.temp_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        # Extract archive
        if package_path.suffix == ".gz":
            with tarfile.open(package_path, "r:gz") as tar:
                tar.extractall(extract_dir)
        elif package_path.suffix == ".zip":
            with zipfile.ZipFile(package_path, "r") as zip_file:
                zip_file.extractall(extract_dir)
        
        # Find the source directory (usually the first subdirectory)
        source_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not source_dirs:
            raise ValueError("No source directory found in archive")
        
        source_dir = source_dirs[0]
        
        # Copy files to LNMT_HOME
        self._copy_update_files(source_dir, LNMT_HOME)
        
        # Run post-install scripts if they exist
        post_install_script = source_dir / "scripts" / "post_install.sh"
        if post_install_script.exists():
            subprocess.run([str(post_install_script)], check=True, cwd=str(source_dir))
        
        # Update version file
        VERSION_FILE.write_text(update_info["version"])
        
        return True
    
    def _install_pip_update(self, package_path: Path, update_info: Dict) -> bool:
        """Install using pip"""
        # Use pip to install the downloaded package
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            str(package_path),
            "--upgrade",
            "--force-reinstall"
        ], check=True)
        
        # Update version file
        VERSION_FILE.write_text(update_info["version"])
        
        return True
    
    def _copy_update_files(self, source_dir: Path, dest_dir: Path):
        """Copy update files with proper handling of existing files"""
        skip_patterns = {".git", "__pycache__", "*.pyc", "*.log", "backups"}
        
        for item in source_dir.rglob("*"):
            if any(pattern in str(item) for pattern in skip_patterns):
                continue
            
            rel_path = item.relative_to(source_dir)
            dest_path = dest_dir / rel_path
            
            if item.is_file():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)
                self.logger.debug(f"Copied {rel_path}")
            elif item.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
    
    def run_migrations(self, update_info: Dict) -> bool:
        """Run database and configuration migrations"""
        self.logger.info("Running migrations...")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run migrations")
            return True
        
        try:
            # Database migrations
            db_migration_script = LNMT_HOME / "scripts" / "migrate_db.py"
            if db_migration_script.exists():
                subprocess.run([
                    sys.executable, str(db_migration_script),
                    "--from-version", self.current_version,
                    "--to-version", update_info["version"]
                ], check=True)
            
            # Configuration migrations
            config_migration_script = LNMT_HOME / "scripts" / "migrate_config.py"
            if config_migration_script.exists():
                subprocess.run([
                    sys.executable, str(config_migration_script),
                    "--config-dir", str(LNMT_CONFIG_DIR)
                ], check=True)
            
            self.logger.info("Migrations completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Migration failed: {e}")
            return False
    
    def rollback(self) -> bool:
        """Rollback to the previous version using backup"""
        if not self.backup_path or not self.backup_path.exists():
            self.logger.error("No backup available for rollback")
            return False
        
        self.logger.info(f"Rolling back using backup from {self.backup_path}")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would rollback")
            return True
        
        try:
            # Stop services
            self._stop_services()
            
            # Load backup manifest
            manifest_file = self.backup_path / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file) as f:
                    manifest = json.load(f)
            else:
                manifest = {"items": ["lnmt_home", "config", "database"]}
            
            # Restore from backup
            restore_items = [
                ("lnmt_home", LNMT_HOME),
                ("config", LNMT_CONFIG_DIR),
                ("database", LNMT_DATA_DIR / "db"),
            ]
            
            for backup_name, restore_path in restore_items:
                if backup_name in manifest["items"]:
                    backup_item = self.backup_path / backup_name
                    if backup_item.exists():
                        if restore_path.exists():
                            if restore_path.is_dir():
                                shutil.rmtree(restore_path)
                            else:
                                restore_path.unlink()
                        
                        if backup_item.is_dir():
                            shutil.copytree(backup_item, restore_path, symlinks=True)
                        else:
                            restore_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup_item, restore_path)
                        
                        self.logger.info(f"Restored {backup_name}")
            
            self.logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
        finally:
            # Start services
            self._start_services()
    
    def _stop_services(self):
        """Stop LNMT services"""
        services = ["lnmt-scheduler", "lnmt-web", "lnmt"]
        
        for service in services:
            try:
                subprocess.run(["systemctl", "stop", service], 
                             check=False, capture_output=True)
                self.logger.info(f"Stopped {service}")
            except Exception as e:
                self.logger.warning(f"Could not stop {service}: {e}")
    
    def _start_services(self):
        """Start LNMT services"""
        services = ["lnmt", "lnmt-web", "lnmt-scheduler"]
        
        for service in services:
            try:
                subprocess.run(["systemctl", "start", service], 
                             check=False, capture_output=True)
                self.logger.info(f"Started {service}")
            except Exception as e:
                self.logger.warning(f"Could not start {service}: {e}")
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.logger.info("Cleaned up temporary files")
    
    def update(self, force: bool = False) -> bool:
        """Main update process"""
        try:
            # Check for updates
            update_info = self.check_for_updates()
            if not update_info:
                self.logger.info("No updates available")
                return True
            
            self.logger.info(f"Update available: {update_info['version']}")
            
            if not force:
                response = input(f"Update to version {update_info['version']}? [y/N]: ")
                if response.lower() not in ['y', 'yes']:
                    self.logger.info("Update cancelled by user")
                    return True
            
            # Create backup
            if not self.create_backup():
                self.logger.error("Backup failed, aborting update")
                return False
            
            # Download update
            package_path = self.download_update(update_info)
            if not package_path:
                self.logger.error("Download failed, aborting update")
                return False
            
            # Install update
            if not self.install_update(package_path, update_info):
                self.logger.error("Installation failed, attempting rollback")
                self.rollback()
                return False
            
            # Run migrations
            if not self.run_migrations(update_info):
                self.logger.error("Migrations failed, attempting rollback")
                self.rollback()
                return False
            
            self.logger.info(f"Successfully updated to version {update_info['version']}")
            
            # Display changelog if available
            if "changelog" in update_info and update_info["changelog"]:
                print("\n" + "="*50)
                print("CHANGELOG:")
                print("="*50)
                print(update_info["changelog"])
                print("="*50 + "\n")
            
            return True
            
        except KeyboardInterrupt:
            self.logger.info("Update interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LNMT Self-Updater")
    parser.add_argument("--source", choices=["github", "pip", "custom"], 
                       default="github", help="Update source")
    parser.add_argument("--check-only", action="store_true", 
                       help="Only check for updates, don't install")
    parser.add_argument("--force", action="store_true", 
                       help="Force update without confirmation")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without actually doing it")
    parser.add_argument("--rollback", action="store_true", 
                       help="Rollback to previous version")
    parser.add_argument("--list-backups", action="store_true", 
                       help="List available backups")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root")
        sys.exit(1)
    
    updater = LNMTUpdater(source=args.source, dry_run=args.dry_run)
    
    try:
        if args.list_backups:
            # List available backups
            if BACKUP_DIR.exists():
                backups = sorted(BACKUP_DIR.glob("lnmt_backup_*"), reverse=True)
                if backups:
                    print("Available backups:")
                    for backup in backups:
                        manifest_file = backup / "manifest.json"
                        if manifest_file.exists():
                            with open(manifest_file) as f:
                                manifest = json.load(f)
                            print(f"  {backup.name} - Version: {manifest.get('version', 'unknown')} - {manifest['timestamp']}")
                        else:
                            print(f"  {backup.name}")
                else:
                    print("No backups found")
            else:
                print("No backup directory found")
            return
        
        if args.rollback:
            # Find latest backup
            if BACKUP_DIR.exists():
                backups = sorted(BACKUP_DIR.glob("lnmt_backup_*"), reverse=True)
                if backups:
                    updater.backup_path = backups[0]
                    success = updater.rollback()
                    sys.exit(0 if success else 1)
                else:
                    print("No backups found for rollback")
                    sys.exit(1)
            else:
                print("No backup directory found")
                sys.exit(1)
        
        if args.check_only:
            # Only check for updates
            update_info = updater.check_for_updates()
            if update_info:
                print(f"Update available: {update_info['version']}")
                if "changelog" in update_info:
                    print(f"Changelog: {update_info['changelog'][:200]}...")
            else:
                print("No updates available")
            return
        
        # Run full update process
        success = updater.update(force=args.force)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logging.error(f"Updater failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    