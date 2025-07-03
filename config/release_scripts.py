#!/usr/bin/env python3
"""
LNMT Release and Packaging Scripts
Handles version management, changelog generation, and release packaging
"""

import os
import sys
import json
import subprocess
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import semver
import git

class LNMTReleaseManager:
    """Manages LNMT releases, versioning, and packaging"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.repo = git.Repo(repo_path)
        self.version_file = self.repo_path / "VERSION"
        self.changelog_file = self.repo_path / "CHANGELOG.md"
        
    def get_current_version(self) -> str:
        """Get current version from VERSION file or git tags"""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        
        # Fallback to git tags
        try:
            tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
            if tags:
                return str(tags[0]).lstrip('v')
            return "0.1.0"
        except:
            return "0.1.0"
    
    def bump_version(self, bump_type: str = "patch") -> str:
        """Bump version based on type (major, minor, patch)"""
        current = self.get_current_version()
        
        if bump_type == "major":
            new_version = semver.bump_major(current)
        elif bump_type == "minor":
            new_version = semver.bump_minor(current)
        elif bump_type == "patch":
            new_version = semver.bump_patch(current)
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
        
        self.version_file.write_text(new_version + "\n")
        return new_version
    
    def generate_version_from_commits(self) -> str:
        """Generate version based on commit messages since last tag"""
        try:
            last_tag = list(self.repo.tags)[-1] if self.repo.tags else None
            
            if last_tag:
                commits = list(self.repo.iter_commits(f"{last_tag}..HEAD"))
            else:
                commits = list(self.repo.iter_commits())
            
            has_breaking = any("BREAKING CHANGE" in c.message or "!" in c.message.split(":")[0] 
                             for c in commits)
            has_feat = any(c.message.startswith("feat") for c in commits)
            
            current = self.get_current_version()
            
            if has_breaking:
                return semver.bump_major(current)
            elif has_feat:
                return semver.bump_minor(current)
            else:
                return semver.bump_patch(current)
                
        except Exception:
            return self.bump_version("patch")
    
    def update_version_in_files(self, version: str):
        """Update version in all relevant files"""
        files_to_update = [
            ("setup.py", r'version\s*=\s*["\'][^"\']*["\']', f'version="{version}"'),
            ("pyproject.toml", r'version\s*=\s*["\'][^"\']*["\']', f'version = "{version}"'),
            ("web/lnmt_web_app.py", r'__version__\s*=\s*["\'][^"\']*["\']', f'__version__ = "{version}"'),
            ("services/__init__.py", r'__version__\s*=\s*["\'][^"\']*["\']', f'__version__ = "{version}"'),
        ]
        
        for file_path, pattern, replacement in files_to_update:
            full_path = self.repo_path / file_path
            if full_path.exists():
                content = full_path.read_text()
                updated_content = re.sub(pattern, replacement, content)
                full_path.write_text(updated_content)
                print(f"Updated version in {file_path}")
    
    def generate_changelog(self, version: str = None) -> str:
        """Generate changelog from git commits"""
        if not version:
            version = self.get_current_version()
        
        try:
            last_tag = list(self.repo.tags)[-1] if self.repo.tags else None
            
            if last_tag:
                commits = list(self.repo.iter_commits(f"{last_tag}..HEAD"))
                since_text = f"since {last_tag}"
            else:
                commits = list(self.repo.iter_commits())
                since_text = "initial release"
            
            # Categorize commits
            features = []
            fixes = []
            breaking = []
            other = []
            
            for commit in commits:
                msg = commit.message.strip()
                short_msg = msg.split('\n')[0]
                
                if "BREAKING CHANGE" in msg or "!" in short_msg.split(":")[0]:
                    breaking.append(f"- {short_msg}")
                elif short_msg.startswith("feat"):
                    features.append(f"- {short_msg[5:]}")  # Remove "feat:"
                elif short_msg.startswith("fix"):
                    fixes.append(f"- {short_msg[4:]}")   # Remove "fix:"
                elif not short_msg.startswith(("docs", "test", "chore", "style", "refactor")):
                    other.append(f"- {short_msg}")
            
            # Build changelog
            changelog_sections = []
            
            if breaking:
                changelog_sections.append("### 💥 Breaking Changes\n" + "\n".join(breaking))
            
            if features:
                changelog_sections.append("### ✨ New Features\n" + "\n".join(features))
            
            if fixes:
                changelog_sections.append("### 🐛 Bug Fixes\n" + "\n".join(fixes))
            
            if other:
                changelog_sections.append("### 📝 Other Changes\n" + "\n".join(other))
            
            changelog = f"""## [{version}] - {datetime.now().strftime('%Y-%m-%d')}

{chr(10).join(changelog_sections) if changelog_sections else "- Initial release"}

**Full Changelog**: {f"{last_tag}...v{version}" if last_tag else f"Initial release v{version}"}
"""
            
            return changelog
            
        except Exception as e:
            return f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}\n\n- Release version {version}\n"
    
    def update_changelog_file(self, version: str):
        """Update CHANGELOG.md file with new version"""
        new_entry = self.generate_changelog(version)
        
        if self.changelog_file.exists():
            existing_content = self.changelog_file.read_text()
            # Insert new entry after the header
            lines = existing_content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('# ') or line.startswith('## '):
                    if 'changelog' in line.lower():
                        header_end = i + 1
                        break
                    elif line.startswith('## ['):
                        header_end = i
                        break
            
            lines.insert(header_end, new_entry)
            content = '\n'.join(lines)
        else:
            content = f"# LNMT Changelog\n\n{new_entry}"
        
        self.changelog_file.write_text(content)
        print(f"Updated {self.changelog_file}")
    
    def create_release_bundle(self, version: str) -> Path:
        """Create complete release bundle"""
        bundle_dir = self.repo_path / "dist" / f"lnmt-{version}"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all necessary files
        directories_to_copy = [
            "services", "cli", "web", "themes", "tests", 
            "docs", "installer", "integration", "config"
        ]
        
        files_to_copy = [
            "README.md", "LICENSE", "CHANGELOG.md", "VERSION"
        ]
        
        for directory in directories_to_copy:
            src_dir = self.repo_path / directory
            if src_dir.exists():
                subprocess.run(["cp", "-r", str(src_dir), str(bundle_dir)], check=True)
        
        for file in files_to_copy:
            src_file = self.repo_path / file
            if src_file.exists():
                subprocess.run(["cp", str(src_file), str(bundle_dir)], check=True)
        
        # Create tarball
        tarball_path = self.repo_path / "dist" / f"lnmt-{version}.tar.gz"
        subprocess.run([
            "tar", "-czf", str(tarball_path), 
            "-C", str(bundle_dir.parent), 
            bundle_dir.name
        ], check=True)
        
        print(f"Created release bundle: {tarball_path}")
        return tarball_path
    
    def create_installer_package(self, version: str) -> Path:
        """Create installer package with embedded dependencies"""
        installer_dir = self.repo_path / "dist" / f"lnmt-installer-{version}"
        installer_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy installer files
        subprocess.run(["cp", "-r", str(self.repo_path / "installer"), str(installer_dir)], check=True)
        
        # Copy application files
        app_dirs = ["services", "cli", "web", "themes", "config", "integration"]
        for directory in app_dirs:
            src_dir = self.repo_path / directory
            if src_dir.exists():
                subprocess.run(["cp", "-r", str(src_dir), str(installer_dir)], check=True)
        
        # Create install script
        install_script = installer_dir / "install.sh"
        install_script.write_text(f"""#!/bin/bash
# LNMT Installer v{version}
set -e

echo "Installing LNMT v{version}..."

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3, 9)" || {{
    echo "Error: Python 3.9+ required"
    exit 1
}}

# Install dependencies
python3 -m pip install --user -r config/requirements.txt

# Set up LNMT
mkdir -p ~/.lnmt
cp -r . ~/.lnmt/

# Create symlinks
mkdir -p ~/.local/bin
for cmd in cli/*.py; do
    cmd_name=$(basename "$cmd" .py)
    ln -sf ~/.lnmt/"$cmd" ~/.local/bin/"$cmd_name"
done

# Set up systemd services (if available)
if command -v systemctl >/dev/null 2>&1; then
    echo "Setting up systemd services..."
    sudo cp installer/*.service /etc/systemd/system/ || true
    sudo systemctl daemon-reload || true
fi

echo "LNMT v{version} installed successfully!"
echo "Run: export PATH=$HOME/.local/bin:$PATH"
""")
        install_script.chmod(0o755)
        
        # Create tarball
        tarball_path = self.repo_path / "dist" / f"lnmt-installer-{version}.tar.gz"
        subprocess.run([
            "tar", "-czf", str(tarball_path),
            "-C", str(installer_dir.parent),
            installer_dir.name
        ], check=True)
        
        print(f"Created installer package: {tarball_path}")
        return tarball_path

def main():
    parser = argparse.ArgumentParser(description="LNMT Release Manager")
    parser.add_argument("command", choices=[
        "version", "bump", "changelog", "bundle", "installer", "release"
    ])
    parser.add_argument("--type", choices=["major", "minor", "patch"], default="patch")
    parser.add_argument("--version", help="Specific version to use")
    parser.add_argument("--repo-path", default=".", help="Repository path")
    
    args = parser.parse_args()
    
    manager = LNMTReleaseManager(args.repo_path)
    
    if args.command == "version":
        print(manager.get_current_version())
    
    elif args.command == "bump":
        if args.version:
            version = args.version
            manager.version_file.write_text(version + "\n")
        else:
            version = manager.bump_version(args.type)
        
        manager.update_version_in_files(version)
        print(f"Bumped version to: {version}")
    
    elif args.command == "changelog":
        version = args.version or manager.get_current_version()
        changelog = manager.generate_changelog(version)
        print(changelog)
    
    elif args.command == "bundle":
        version = args.version or manager.get_current_version()
        bundle_path = manager.create_release_bundle(version)
        print(f"Bundle created: {bundle_path}")
    
    elif args.command == "installer":
        version = args.version or manager.get_current_version()
        installer_path = manager.create_installer_package(version)
        print(f"Installer created: {installer_path}")
    
    elif args.command == "release":
        # Full release process
        if not args.version:
            version = manager.generate_version_from_commits()
            manager.version_file.write_text(version + "\n")
        else:
            version = args.version
        
        print(f"Creating release {version}...")
        
        # Update version in files
        manager.update_version_in_files(version)
        
        # Update changelog
        manager.update_changelog_file(version)
        
        # Create packages
        bundle_path = manager.create_release_bundle(version)
        installer_path = manager.create_installer_package(version)
        
        print(f"Release {version} created successfully!")
        print(f"- Bundle: {bundle_path}")
        print(f"- Installer: {installer_path}")

if __name__ == "__main__":
    main()