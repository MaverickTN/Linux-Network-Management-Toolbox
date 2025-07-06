# LNMT CI/CD & Release Automation Guide

## 🚀 Overview

This guide covers the complete CI/CD and release automation system for LNMT, including GitHub Actions workflows, GitLab CI/CD pipelines, Docker containerization, and automated release management.

## 📁 File Structure

```
.github/
├── workflows/
│   └── ci-cd.yml              # Main GitHub Actions pipeline
scripts/
├── generate_version.py        # Semantic version generation
├── update_version.py          # Version file updates
├── generate_changelog.py      # Automated changelog
├── pre_release_qa.sh          # Pre-release quality checks
├── post_release_qa.sh         # Post-release smoke tests
└── release_manager.py         # Release packaging system
docker-compose.yml             # Development/testing environment
docker-compose.ci.yml          # CI-specific overrides
.gitlab-ci.yml                 # GitLab CI/CD pipeline
Dockerfile.test               # Testing container
```

## 🔄 CI/CD Pipeline Stages

### 1. **Validation & Linting**
- **Code Quality**: Black formatting, isort imports, flake8 linting
- **Type Checking**: MyPy static analysis
- **Syntax Validation**: Python compilation checks
- **Security Scanning**: Bandit SAST, Safety dependency checks

### 2. **Testing**
- **Unit Tests**: pytest with coverage reporting (target: 80%+)
- **Integration Tests**: Database and Redis integration
- **Performance Tests**: k6 load testing
- **Smoke Tests**: Basic functionality verification

### 3. **Security**
- **SAST**: Static Application Security Testing
- **Dependency Scanning**: Known vulnerability detection
- **Container Scanning**: Trivy security scans
- **Secret Detection**: TruffleHog secret scanning

### 4. **Build & Package**
- **Python Packages**: Wheel and source distributions
- **Docker Images**: Multi-architecture containers
- **Installer Bundles**: Self-contained installation packages
- **Documentation**: Auto-generated API docs

### 5. **Release & Deploy**
- **Semantic Versioning**: Automated version bumping
- **Changelog Generation**: Git commit analysis
- **GitHub/GitLab Releases**: Automated release creation
- **Artifact Publishing**: PyPI, Docker Hub, GitHub Packages

## 🛠️ Setup Instructions

### GitHub Actions Setup

1. **Enable GitHub Actions** in your repository settings
2. **Set up secrets** in repository settings:
   ```
   DOCKER_USERNAME         # Docker Hub username
   DOCKER_PASSWORD         # Docker Hub password
   PYPI_API_TOKEN         # PyPI publishing token
   SLACK_WEBHOOK          # Slack notifications (optional)
   ```
3. **Copy workflow file**:
   ```bash
   mkdir -p .github/workflows
   cp ci-cd.yml .github/workflows/
   ```

### GitLab CI/CD Setup

1. **Enable GitLab CI/CD** in project settings
2. **Set up variables** in CI/CD settings:
   ```
   STAGING_DEPLOY_WEBHOOK  # Staging deployment endpoint
   PRODUCTION_DEPLOY_WEBHOOK # Production deployment endpoint
   DEPLOY_TOKEN           # Deployment authentication
   SLACK_WEBHOOK_URL      # Slack notifications (optional)
   GITLAB_TOKEN          # GitLab API token for releases
   ```
3. **Copy pipeline file**:
   ```bash
   cp .gitlab-ci.yml ./
   ```

### Local Development Environment

1. **Set up Docker environment**:
   ```bash
   # Development environment
   docker-compose up -d
   
   # CI testing environment
   docker-compose -f docker-compose.yml -f docker-compose.ci.yml up
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r config/requirements.txt
   pip install pytest pytest-cov black isort flake8 mypy bandit safety
   ```

## 📋 Release Process

### Automated Release (Recommended)

1. **Create commits** following [Conventional Commits](https://conventionalcommits.org/):
   ```bash
   git commit -m "feat: add new DNS management feature"
   git commit -m "fix: resolve authentication timeout issue"
   git commit -m "feat!: redesign API endpoints" # Breaking change
   ```

2. **Push to main branch**:
   ```bash
   git push origin main
   ```

3. **Create release** (triggers full pipeline):
   ```bash
   # GitHub
   gh release create v1.2.0 --generate-notes
   
   # GitLab
   git tag v1.2.0
   git push origin v1.2.0
   ```

### Manual Release

1. **Generate version**:
   ```bash
   python scripts/generate_version.py
   ```

2. **Update version files**:
   ```bash
   python scripts/update_version.py 1.2.0
   ```

3. **Generate changelog**:
   ```bash
   python scripts/generate_changelog.py 1.2.0
   ```

4. **Create packages**:
   ```bash
   python scripts/release_manager.py release --version 1.2.0
   ```

## 🧪 Quality Assurance

### Pre-Release Checks
```bash
# Run complete QA suite
./scripts/pre_release_qa.sh 1.2.0

# Individual checks
python -m pytest tests/ --cov=services --cov-fail-under=80
python -m bandit -r services/ cli/ web/
python -m safety check
python -m mypy services/ cli/ web/
```

### Post-Release Verification
```bash
# Smoke tests
./scripts/post_release_qa.sh 1.2.0

# Manual verification
curl -f https://api.github.com/repos/lnmt/lnmt/releases/tags/v1.2.0
docker pull lnmt/lnmt:1.2.0
pip install lnmt==1.2.0
```

## 🐳 Container Management

### Development
```bash
# Build development image
docker build -t lnmt:dev -f docs/dockerfile.txt .

# Run with dependencies
docker-compose up -d

# View logs
docker-compose logs -f lnmt
```

### Production
```bash
# Multi-architecture build
docker buildx build --platform linux/amd64,linux/arm64 -t lnmt/lnmt:latest .

# Health check
docker run --rm lnmt/lnmt:latest python -c "import services; print('OK')"
```

## 📊 Monitoring & Metrics

### Pipeline Metrics
- **Test Coverage**: Target 80%+ code coverage
- **Build Time**: Monitor pipeline duration
- **Failure Rate**: Track failed builds/deployments
- **Security Scan Results**: Zero high/critical vulnerabilities

### Performance Benchmarks
- **Application Startup**: < 30 seconds
- **API Response Time**: < 500ms (95th percentile)
- **Memory Usage**: < 512MB baseline
- **CPU Usage**: < 50% under normal load

## 🔧 Troubleshooting

### Common Issues

**Tests failing in CI but passing locally:**
```bash
# Check Python version consistency
python --version

# Verify dependencies
pip list | grep -E "(pytest|coverage)"

# Run tests with same environment
docker-compose -f docker-compose.ci.yml run test-runner
```

**Docker build failures:**
```bash
# Check Docker buildx setup
docker buildx ls

# Verify base image availability
docker pull python:3.11-slim

# Build with debug output
docker build --progress=plain -t lnmt:debug .
```

**Version conflicts:**
```bash
# Check current version
cat VERSION

# Verify git tags
git tag -l | sort -V | tail -5

# Reset version if needed
python scripts/update_version.py $(python scripts/generate_version.py)
```

### Pipeline Debugging

**GitHub Actions:**
```bash
# Download artifact logs
gh run download <run-id>

# View specific job logs
gh run view <run-id> --job <job-id>
```

**GitLab CI/CD:**
```bash
# View pipeline status
gitlab-ci-ls -p <project-id>

# Download job artifacts
gitlab-ci-artifacts -p <project-id> -j <job-id>
```

## 🔐 Security Best Practices

### Secret Management
- Use repository secrets for sensitive data
- Rotate tokens regularly (quarterly)
- Limit token permissions to minimum required
- Use environment-specific secrets

### Container Security
- Regular base image updates
- Non-root user execution
- Minimal attack surface
- Security scanning in pipeline

### Code Security
- SAST scanning on every commit
- Dependency vulnerability monitoring
- Secret detection in commits
- Code signing for releases

## 📈 Optimization Tips

### Pipeline Performance
- Use caching for dependencies
- Parallel job execution
- Conditional builds (only on changes)
- Artifact optimization

### Resource Management
- Use tmpfs for CI databases
- Optimize Docker layer caching
- Minimize artifact size
- Clean up old artifacts

### Developer Experience
- Fast feedback loops
- Clear error messages
- Comprehensive documentation
- Local development parity

## 🔄 Continuous Improvement

### Metrics to Track
- Pipeline success rate
- Average build time
- Test coverage trends
- Security vulnerability trends
- Release frequency

### Regular Reviews
- Monthly pipeline performance review
- Quarterly security assessment
- Annual tool evaluation
- Regular dependency updates

### Automation Enhancements
- Auto-dependency updates (Dependabot/Renovate)
- Intelligent test selection
- Progressive deployment strategies
- Automated rollback capabilities

---

## 📞 Support

For CI/CD issues:
1. Check pipeline logs first
2. Review this documentation
3. Search existing issues
4. Create detailed bug report with logs

For questions or improvements:
- Open GitHub/GitLab issue
- Join development discussions
- Contribute pipeline improvements