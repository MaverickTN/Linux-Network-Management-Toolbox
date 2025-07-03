#!/bin/bash
# LNMT CI/CD Supporting Scripts Collection

# =============================================================================
# scripts/generate_version.py
# =============================================================================
cat > scripts/generate_version.py << 'EOF'
#!/usr/bin/env python3
"""Generate version based on git history and conventional commits"""

import subprocess
import sys
import re
from datetime import datetime

def get_git_output(cmd):
    """Get git command output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def get_last_tag():
    """Get the last git tag"""
    return get_git_output("git describe --tags --abbrev=0 2>/dev/null")

def get_commits_since_tag(tag):
    """Get commits since last tag"""
    if tag:
        return get_git_output(f"git log {tag}..HEAD --oneline")
    else:
        return get_git_output("git log --oneline")

def parse_version(version_str):
    """Parse semantic version string"""
    if not version_str or not version_str.startswith('v'):
        return [0, 1, 0]
    
    version_str = version_str[1:]  # Remove 'v' prefix
    parts = version_str.split('.')
    return [int(parts[i]) if i < len(parts) else 0 for i in range(3)]

def increment_version(version, bump_type):
    """Increment version based on bump type"""
    major, minor, patch = version
    
    if bump_type == "major":
        return [major + 1, 0, 0]
    elif bump_type == "minor":
        return [major, minor + 1, 0]
    else:  # patch
        return [major, minor, patch + 1]

def determine_bump_type(commits):
    """Determine version bump type from commit messages"""
    has_breaking = False
    has_feat = False
    
    for commit in commits.split('\n'):
        if not commit.strip():
            continue
            
        # Check for breaking changes
        if 'BREAKING CHANGE' in commit or '!' in commit.split(':')[0]:
            has_breaking = True
        
        # Check for features
        if commit.strip().startswith(('feat:', 'feature:')):
            has_feat = True
    
    if has_breaking:
        return "major"
    elif has_feat:
        return "minor"
    else:
        return "patch"

def main():
    """Generate version string"""
    last_tag = get_last_tag()
    current_version = parse_version(last_tag)
    
    commits = get_commits_since_tag(last_tag)
    
    if not commits.strip():
        # No new commits, use current version or default
        if last_tag:
            print(last_tag[1:])  # Remove 'v' prefix
        else:
            print("0.1.0")
        return
    
    bump_type = determine_bump_type(commits)
    new_version = increment_version(current_version, bump_type)
    
    version_string = f"{new_version[0]}.{new_version[1]}.{new_version[2]}"
    print(version_string)

if __name__ == "__main__":
    main()
EOF

# =============================================================================
# scripts/update_version.py
# =============================================================================
cat > scripts/update_version.py << 'EOF'
#!/usr/bin/env python3
"""Update version in all project files"""

import sys
import re
from pathlib import Path

def update_file_version(file_path, version):
    """Update version in a specific file"""
    if not file_path.exists():
        return False
    
    content = file_path.read_text()
    updated = False
    
    # Common version patterns
    patterns = [
        (r'version\s*=\s*["\'][^"\']*["\']', f'version="{version}"'),
        (r'__version__\s*=\s*["\'][^"\']*["\']', f'__version__ = "{version}"'),
        (r'"version":\s*"[^"]*"', f'"version": "{version}"'),
        (r'Version:\s*[^\s]*', f'Version: {version}'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            updated = True
    
    if updated:
        file_path.write_text(content)
        print(f"Updated version in {file_path}")
        return True
    
    return False

def main():
    if len(sys.argv) != 2:
        print("Usage: update_version.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Files to update
    files_to_check = [
        "setup.py",
        "pyproject.toml",
        "package.json",
        "web/lnmt_web_app.py",
        "services/__init__.py",
        "cli/__init__.py",
        "VERSION",
    ]
    
    updated_count = 0
    
    # Update VERSION file
    version_file = Path("VERSION")
    version_file.write_text(version + "\n")
    print(f"Updated {version_file}")
    updated_count += 1
    
    # Update other files
    for file_path_str in files_to_check:
        file_path = Path(file_path_str)
        if update_file_version(file_path, version):
            updated_count += 1
    
    print(f"Updated version to {version} in {updated_count} files")

if __name__ == "__main__":
    main()
EOF

# =============================================================================
# scripts/generate_changelog.py
# =============================================================================
cat > scripts/generate_changelog.py << 'EOF'
#!/usr/bin/env python3
"""Generate changelog from git commits"""

import subprocess
import sys
import re
from datetime import datetime
from collections import defaultdict

def get_git_output(cmd):
    """Get git command output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def get_commits_since_tag(tag):
    """Get detailed commits since last tag"""
    if tag:
        cmd = f"git log {tag}..HEAD --pretty=format:'%H|%s|%b|%an|%ad' --date=short"
    else:
        cmd = "git log --pretty=format='%H|%s|%b|%an|%ad' --date=short"
    
    return get_git_output(cmd)

def parse_commits(commits_output):
    """Parse git log output into structured data"""
    commits = []
    
    for line in commits_output.split('\n'):
        if not line.strip():
            continue
        
        parts = line.split('|')
        if len(parts) >= 5:
            commits.append({
                'hash': parts[0][:7],
                'subject': parts[1],
                'body': parts[2],
                'author': parts[3],
                'date': parts[4]
            })
    
    return commits

def categorize_commits(commits):
    """Categorize commits by type"""
    categories = {
        'breaking': [],
        'features': [],
        'fixes': [],
        'docs': [],
        'style': [],
        'refactor': [],
        'perf': [],
        'test': [],
        'chore': [],
        'other': []
    }
    
    for commit in commits:
        subject = commit['subject'].lower()
        
        # Check for breaking changes
        if 'breaking change' in commit['body'].lower() or '!' in subject.split(':')[0]:
            categories['breaking'].append(commit)
        elif subject.startswith('feat'):
            categories['features'].append(commit)
        elif subject.startswith('fix'):
            categories['fixes'].append(commit)
        elif subject.startswith('docs'):
            categories['docs'].append(commit)
        elif subject.startswith('style'):
            categories['style'].append(commit)
        elif subject.startswith('refactor'):
            categories['refactor'].append(commit)
        elif subject.startswith('perf'):
            categories['perf'].append(commit)
        elif subject.startswith('test'):
            categories['test'].append(commit)
        elif subject.startswith('chore'):
            categories['chore'].append(commit)
        else:
            categories['other'].append(commit)
    
    return categories

def format_commit(commit):
    """Format a commit for changelog"""
    subject = commit['subject']
    
    # Remove conventional commit prefix
    if ':' in subject:
        subject = subject.split(':', 1)[1].strip()
    
    return f"- {subject} ([{commit['hash']}])"

def generate_changelog(version, commits):
    """Generate changelog content"""
    categories = categorize_commits(commits)
    
    sections = []
    
    # Breaking changes
    if categories['breaking']:
        sections.append("### 💥 Breaking Changes")
        for commit in categories['breaking']:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Features
    if categories['features']:
        sections.append("### ✨ New Features")
        for commit in categories['features']:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Bug fixes
    if categories['fixes']:
        sections.append("### 🐛 Bug Fixes")
        for commit in categories['fixes']:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Performance improvements
    if categories['perf']:
        sections.append("### ⚡ Performance Improvements")
        for commit in categories['perf']:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Documentation
    if categories['docs']:
        sections.append("### 📚 Documentation")
        for commit in categories['docs']:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Other changes
    other_commits = categories['refactor'] + categories['style'] + categories['other']
    if other_commits:
        sections.append("### 📝 Other Changes")
        for commit in other_commits:
            sections.append(format_commit(commit))
        sections.append("")
    
    # Build header
    date = datetime.now().strftime('%Y-%m-%d')
    header = f"## [{version}] - {date}"
    
    if not sections:
        sections = ["- Initial release"]
    
    changelog = header + "\n\n" + "\n".join(sections)
    
    return changelog.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: generate_changelog.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Get last tag
    last_tag = get_git_output("git describe --tags --abbrev=0 2>/dev/null")
    
    # Get commits
    commits_output = get_commits_since_tag(last_tag)
    
    if not commits_output.strip():
        print(f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}")
        print()
        print("- Initial release")
        return
    
    commits = parse_commits(commits_output)
    changelog = generate_changelog(version, commits)
    
    print(changelog)

if __name__ == "__main__":
    main()
EOF

# =============================================================================
# scripts/pre_release_qa.sh
# =============================================================================
cat > scripts/pre_release_qa.sh << 'EOF'
#!/bin/bash
# Pre-release Quality Assurance Script

set -e

VERSION=${1:-"latest"}
echo "🔍 Running pre-release QA for LNMT v$VERSION"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Dependency checks
echo "📦 Checking dependencies..."
run_test "Python 3.9+" "python3 -c 'import sys; assert sys.version_info >= (3, 9)'"
run_test "pip installation" "python3 -m pip --version"
run_test "git availability" "git --version"

# Code quality checks
echo "🔍 Running code quality checks..."
if [ -d "services" ]; then
    run_test "Python syntax (services)" "python3 -m py_compile services/*.py"
fi

if [ -d "cli" ]; then
    run_test "Python syntax (cli)" "python3 -m py_compile cli/*.py"
fi

if [ -d "web" ]; then
    run_test "Python syntax (web)" "python3 -m py_compile web/*.py"
fi

# Configuration validation
echo "⚙️ Validating configurations..."
run_test "requirements.txt exists" "[ -f config/requirements.txt ]"
run_test "requirements.txt readable" "cat config/requirements.txt >/dev/null"

if [ -f "config/requirements.txt" ]; then
    run_test "requirements installable" "python3 -m pip install --dry-run -r config/requirements.txt"
fi

# Installer checks
echo "📦 Checking installer..."
run_test "installer script exists" "[ -f installer/lnmt_installer.sh ]"
run_test "installer script executable" "[ -x installer/lnmt_installer.sh ]"

# Documentation checks
echo "📚 Checking documentation..."
run_test "main README exists" "[ -f README.md ]"
run_test "documentation directory" "[ -d docs ]"

# Test suite
echo "🧪 Running test suite..."
if [ -d "tests" ]; then
    if command -v pytest &> /dev/null; then
        run_test "unit tests" "python3 -m pytest tests/ -x --tb=short"
    else
        run_test "unit tests (basic)" "python3 -m unittest discover tests/ -v"
    fi
fi

# Security checks
echo "🔒 Security checks..."
if command -v bandit &> /dev/null; then
    run_test "security scan" "bandit -r services/ cli/ web/ -f json"
fi

# Build verification
echo "🏗️ Build verification..."
if [ -f "setup.py" ]; then
    run_test "package build" "python3 setup.py check"
fi

# Service validation
echo "🚀 Service validation..."
if [ -f "services/health_monitor.py" ]; then
    run_test "health monitor imports" "python3 -c 'import sys; sys.path.insert(0, \"services\"); import health_monitor'"
fi

if [ -f "services/dns_manager_service.py" ]; then
    run_test "DNS manager imports" "python3 -c 'import sys; sys.path.insert(0, \"services\"); import dns_manager_service'"
fi

# Web interface checks
echo "🌐 Web interface checks..."
if [ -f "web/lnmt_web_app.py" ]; then
    run_test "web app imports" "python3 -c 'import sys; sys.path.insert(0, \"web\"); import lnmt_web_app'"
fi

# CLI validation
echo "💻 CLI validation..."
if [ -d "cli" ]; then
    for cli_script in cli/*.py; do
        if [ -f "$cli_script" ]; then
            script_name=$(basename "$cli_script" .py)
            run_test "$script_name CLI syntax" "python3 -m py_compile $cli_script"
        fi
    done
fi

# Final report
echo
echo "========================================="
echo "📊 Pre-release QA Results for v$VERSION"
echo "========================================="
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo "Total tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Ready for release.${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED test(s) failed. Please fix before release.${NC}"
    exit 1
fi
EOF

# =============================================================================
# scripts/post_release_qa.sh
# =============================================================================
cat > scripts/post_release_qa.sh << 'EOF'
#!/bin/bash
# Post-release Quality Assurance and Smoke Tests

set -e

VERSION=${1:-"latest"}
echo "🔥 Running post-release smoke tests for LNMT v$VERSION"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
SMOKE_TESTS_PASSED=0
SMOKE_TESTS_FAILED=0

smoke_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "🔥 $test_name... "
    
    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((SMOKE_TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((SMOKE_TESTS_FAILED++))
        return 1
    fi
}

# Download and installation tests
echo "📦 Testing release artifacts..."

# Test GitHub release
if command -v curl &> /dev/null; then
    smoke_test "GitHub release exists" "curl -s https://api.github.com/repos/lnmt/lnmt/releases/tags/v$VERSION | grep -q '\"tag_name\"'"
fi

# Test Docker image
if command -v docker &> /dev/null; then
    smoke_test "Docker image pullable" "docker pull ghcr.io/lnmt/lnmt:$VERSION || docker pull lnmt/lnmt:$VERSION"
    
    if docker images | grep -q lnmt; then
        smoke_test "Docker container starts" "timeout 30 docker run --rm -d --name lnmt-test lnmt/lnmt:$VERSION || timeout 30 docker run --rm -d --name lnmt-test ghcr.io/lnmt/lnmt:$VERSION"
        
        # Clean up
        docker stop lnmt-test 2>/dev/null || true
        docker rm lnmt-test 2>/dev/null || true
    fi
fi

# Test PyPI package (if applicable)
if command -v pip &> /dev/null; then
    smoke_test "PyPI package installable" "pip install --dry-run lnmt==$VERSION"
fi

# Test installer download
echo "🔽 Testing installer download..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

if command -v wget &> /dev/null; then
    smoke_test "Installer tarball download" "wget -q https://github.com/lnmt/lnmt/releases/download/v$VERSION/lnmt-installer-$VERSION.tar.gz"
    
    if [ -f "lnmt-installer-$VERSION.tar.gz" ]; then
        smoke_test "Installer tarball extraction" "tar -xzf lnmt-installer-$VERSION.tar.gz"
        
        if [ -d "lnmt-installer-$VERSION" ]; then
            cd "lnmt-installer-$VERSION"
            smoke_test "Installer script executable" "[ -x install.sh ]"
            smoke_test "Required directories present" "[ -d services ] && [ -d cli ] && [ -d web ]"
        fi
    fi
fi

cd - > /dev/null
rm -rf "$TEMP_DIR"

# Test documentation accessibility
echo "📚 Testing documentation..."
if command -v curl &> /dev/null; then
    smoke_test "Documentation accessible" "curl -s https://github.com/lnmt/lnmt/blob/v$VERSION/README.md | grep -q 'LNMT'"
fi

# Health check endpoints (if applicable)
echo "🏥 Testing health endpoints..."
# These would test actual deployed instances
# smoke_test "Health endpoint responds" "curl -f http://your-deployment/health"
# smoke_test "API version matches" "curl -s http://your-deployment/version | grep -q '$VERSION'"

# Integration smoke tests
echo "🔗 Testing integrations..."

# Test CLI availability (if installed)
for cli_tool in authctl healthctl schedctl vlanctl reportctl; do
    if command -v "$cli_tool" &> /dev/null; then
        smoke_test "$cli_tool version" "$cli_tool --version | grep -q '$VERSION'"
    fi
done

# Test service imports
echo "🐍 Testing Python imports..."
TEMP_VENV=$(mktemp -d)
python3 -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

if pip install "lnmt==$VERSION" &>/dev/null; then
    smoke_test "Core modules importable" "python3 -c 'import lnmt; print(lnmt.__version__)'"
fi

deactivate
rm -rf "$TEMP_VENV"

# Performance smoke tests
echo "⚡ Performance smoke tests..."
smoke_test "System resources check" "[ $(free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2 }' | cut -d. -f1) -lt 90 ]"

# Final report
echo
echo "========================================="
echo "🔥 Post-release Smoke Test Results"
echo "========================================="
echo "Version tested: v$VERSION"
echo -e "Smoke tests passed: ${GREEN}$SMOKE_TESTS_PASSED${NC}"
echo -e "Smoke tests failed: ${RED}$SMOKE_TESTS_FAILED${NC}"
echo "Total smoke tests: $((SMOKE_TESTS_PASSED + SMOKE_TESTS_FAILED))"

if [ $SMOKE_TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All smoke tests passed! Release v$VERSION is healthy.${NC}"
    
    # Send success notification (optional)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"✅ LNMT v$VERSION post-release smoke tests passed!\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    exit 0
else
    echo -e "${RED}❌ $SMOKE_TESTS_FAILED smoke test(s) failed! Please investigate release v$VERSION.${NC}"
    
    # Send failure notification (optional)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 LNMT v$VERSION post-release smoke tests failed! $SMOKE_TESTS_FAILED failures detected.\"}" \
            "$SLACK_WEBHOOK_URL" &>/dev/null || true
    fi
    
    exit 1
fi
EOF

# Make all scripts executable
chmod +x scripts/*.py scripts/*.sh

echo "✅ All CI/CD supporting scripts created successfully!"