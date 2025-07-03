# 🛠️ LNMT Developer Guide

Welcome to the LNMT developer community! This guide will help you contribute to LNMT, whether you're fixing bugs, adding features, or improving documentation.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Contributing Workflow](#contributing-workflow)
- [Release Process](#release-process)
- [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

Before you start developing for LNMT, ensure you have:

- **Python 3.8+** (we recommend using pyenv for version management)
- **Git** for version control
- **Docker** for containerized development (optional but recommended)
- **CUDA-capable GPU** for testing GPU functionality (optional)

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/your-org/lnmt.git
cd lnmt

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest tests/
```

---

## Development Setup

### Detailed Environment Setup

1. **Python Environment**:
```bash
# Using pyenv (recommended)
pyenv install 3.9.16
pyenv local 3.9.16

# Or using conda
conda create -n lnmt-dev python=3.9
conda activate lnmt-dev
```

2. **Install Dependencies**:
```bash
# Install all development dependencies
pip install -e ".[dev,test,docs]"

# Or install specific dependency groups
pip install -e ".[dev]"     # Core development tools
pip install -e ".[test]"    # Testing dependencies
pip install -e ".[docs]"    # Documentation tools
pip install -e ".[gpu]"     # GPU support
```

3. **Development Tools**:
```bash
# Install additional tools
pip install pre-commit black isort flake8 mypy pytest-cov

# Setup pre-commit hooks
pre-commit install
pre-commit run --all-files  # Run on all files initially
```

### IDE Configuration

#### Visual Studio Code

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

Create `.vscode/launch.json` for debugging:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${workspaceFolder}/tests/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

#### PyCharm

1. Set interpreter to your virtual environment
2. Enable Black as the code formatter
3. Configure isort for import sorting
4. Enable type checking with mypy

### Docker Development Environment

```dockerfile
# Dockerfile.dev
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Install LNMT in development mode
COPY setup.py setup.cfg pyproject.toml ./
COPY lnmt/ ./lnmt/
RUN pip install -e ".[dev]"

CMD ["bash"]
```

```bash
# Build and run development container
docker build -f Dockerfile.dev -t lnmt-dev .
docker run -it -v $(pwd):/app lnmt-dev
```

---

## Project Structure

```
lnmt/
├── lnmt/                   # Main package
│   ├── __init__.py
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   ├── models.py      # Model classes
│   │   ├── training.py    # Training logic
│   │   └── inference.py   # Inference engine
│   ├── data/              # Data processing
│   │   ├── __init__.py
│   │   ├── datasets.py    # Dataset classes
│   │   ├── loaders.py     # Data loaders
│   │   └── processors.py  # Data processors
│   ├── optimization/      # Training optimization
│   │   ├── __init__.py
│   │   ├── optimizers.py  # Custom optimizers
│   │   ├── schedulers.py  # Learning rate schedulers
│   │   └── loss.py        # Loss functions
│   ├── deployment/        # Deployment utilities
│   │   ├── __init__.py
│   │   ├── serving.py     # Model serving
│   │   ├── kubernetes.py  # K8s deployment
│   │   └── docker.py      # Docker utilities
│   ├── utils/             # Utility functions
│   │   ├── __init__.py
│   │   ├── logging.py     # Logging utilities
│   │   ├── metrics.py     # Evaluation metrics
│   │   └── gpu.py         # GPU utilities
│   └── cli/               # Command-line interface
│       ├── __init__.py
│       ├── main.py        # Main CLI entry
│       ├── train.py       # Training commands
│       └── deploy.py      # Deployment commands
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── performance/       # Performance tests
│   └── fixtures/          # Test fixtures
├── docs/                  # Documentation
│   ├── source/            # Sphinx documentation
│   ├── examples/          # Example notebooks
│   └── api/               # API documentation
├── examples/              # Example scripts
├── scripts/               # Development scripts
├── docker/                # Docker configurations
├── kubernetes/            # Kubernetes manifests
├── .github/               # GitHub workflows
├── setup.py               # Package setup
├── setup.cfg              # Configuration
├── pyproject.toml         # Modern Python project config
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── README.md
```

### Module Organization

#### Core Modules

- **`lnmt.core`**: Core functionality including models, training, and inference
- **`lnmt.data`**: Data handling, loading, and preprocessing
- **`lnmt.optimization`**: Training optimization components
- **`lnmt.deployment`**: Model deployment and serving
- **`lnmt.utils`**: Utility functions and helpers

#### Design Patterns

1. **Factory Pattern**: Used for creating models and optimizers
2. **Strategy Pattern**: Used for different training strategies
3. **Observer Pattern**: Used for training callbacks and monitoring
4. **Builder Pattern**: Used for complex configuration building

---

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310']
include = '\.pyi?$'
extend-exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["lnmt"]
known_third_party = ["torch", "transformers", "numpy"]

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
per-file-ignores = [
    "__init__.py:F401",
    "tests/*:S101"
]
```

### Code Formatting

```bash
# Format code with Black
black lnmt/ tests/

# Sort imports with isort
isort lnmt/ tests/

# Check with flake8
flake8 lnmt/ tests/

# Type checking with mypy
mypy lnmt/
```

### Type Hints