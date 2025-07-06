# LNMT Development Requirements
# Install with: pip install -r requirements-dev.txt

# Include base requirements
-r requirements.txt

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-timeout==2.2.0
pytest-xdist==3.5.0  # Parallel test execution
httpx-mock==0.24.0
faker==20.1.0
factory-boy==3.3.0
hypothesis==6.92.1

# Code Quality
black==23.12.0
isort==5.13.2
flake8==6.1.0
flake8-docstrings==1.7.0
flake8-bugbear==23.12.2
mypy==1.7.1
pylint==3.0.3
bandit==1.7.5
safety==3.0.1
pre-commit==3.6.0

# Type Stubs
types-redis==4.6.0.11
types-requests==2.31.0.10
types-PyYAML==6.0.12.12
types-python-dateutil==2.8.19.14
types-tabulate==0.9.0.3

# Documentation
mkdocs==1.5.3
mkdocs-material==9.5.2
mkdocstrings[python]==0.24.0
mkdocs-git-revision-date-localized-plugin==1.2.2
mkdocs-minify-plugin==0.7.2

# Performance Testing
locust==2.17.0
memory-profiler==0.61.0
py-spy==0.3.14

# Debugging
ipdb==0.13.13
pdbpp==0.10.3
icecream==2.1.3

# Development Tools
jupyter==1.0.0
notebook==7.0.6
ipykernel==6.27.1
bpython==0.24

# API Testing
tavern==2.9.1
schemathesis==3.23.0

# Database Tools
sqlalchemy-utils==0.41.1
alembic-autogenerate-enums==0.1.2

# Monitoring Development
flower==2.0.1  # Celery monitoring

# Security Testing
semgrep==1.51.0
pip-audit==2.6.2

# Build Tools
build==1.0.3
twine==4.0.2
wheel==0.42.0

# CI/CD Tools
tox==4.11.4
nox==2023.4.22

# Code Coverage
coverage[toml]==7.3.4
codecov==2.1.13

# Git Hooks
gitpython==3.1.40
commitizen==3.13.0