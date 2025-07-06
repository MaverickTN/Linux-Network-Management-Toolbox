# Dockerfile.test - Specialized container for running tests in CI/CD
FROM python:3.11-slim

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG BUILD_DATE
ARG VCS_REF

# Add metadata
LABEL maintainer="LNMT Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0" \
      org.label-schema.name="lnmt-test" \
      org.label-schema.description="LNMT Testing Container"

# Install system dependencies for testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    postgresql-client \
    redis-tools \
    netcat-openbsd \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r lnmt && useradd -r -g lnmt -d /app -s /bin/bash lnmt

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY config/requirements.txt ./config/
COPY tests/requirements-test.txt ./tests/ 2>/dev/null || echo "# No test requirements" > ./tests/requirements-test.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r config/requirements.txt && \
    pip install --no-cache-dir \
        pytest>=7.0.0 \
        pytest-cov>=4.0.0 \
        pytest-html>=3.1.0 \
        pytest-xdist>=3.0.0 \
        pytest-asyncio>=0.21.0 \
        pytest-mock>=3.10.0 \
        pytest-timeout>=2.1.0 \
        coverage>=7.0.0 \
        bandit>=1.7.0 \
        safety>=2.3.0 \
        black>=23.0.0 \
        isort>=5.12.0 \
        flake8>=6.0.0 \
        mypy>=1.0.0 \
        pre-commit>=3.0.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/test-results /app/logs /app/coverage

# Set permissions
RUN chown -R lnmt:lnmt /app

# Switch to non-root user
USER lnmt

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTEST_ADDOPTS="--strict-markers --strict-config" \
    COVERAGE_CORE=sysmon

# Health check for testing container
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command runs comprehensive test suite
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short", \
     "--junitxml=test-results/junit.xml", \
     "--html=test-results/report.html", \
     "--cov=services", "--cov=cli", "--cov=web", \
     "--cov-report=xml:test-results/coverage.xml", \
     "--cov-report=html:test-results/htmlcov", \
     "--cov-fail-under=70"]

# Alternative entrypoint for specific test types
# Usage: docker run --rm -e TEST_TYPE=unit lnmt-test
COPY <<'EOF' /app/entrypoint-test.sh
#!/bin/bash
set -e

# Wait for dependencies if needed
if [ "$WAIT_FOR_DEPS" = "true" ]; then
    echo "Waiting for database..."
    until pg_isready -h ${DATABASE_HOST:-postgres} -p ${DATABASE_PORT:-5432} -U ${DATABASE_USER:-lnmt}; do
        echo "Postgres is unavailable - sleeping"
        sleep 1
    done
    echo "Database is ready!"
    
    echo "Waiting for Redis..."
    until redis-cli -h ${REDIS_HOST:-redis} -p ${REDIS_PORT:-6379} ping; do
        echo "Redis is unavailable - sleeping"
        sleep 1
    done
    echo "Redis is ready!"
fi

# Run tests based on TEST_TYPE environment variable
case "${TEST_TYPE:-all}" in
    "unit")
        echo "Running unit tests..."
        exec python -m pytest tests/unit/ -v --tb=short \
            --junitxml=test-results/unit-junit.xml \
            --cov=services --cov=cli --cov=web \
            --cov-report=xml:test-results/unit-coverage.xml
        ;;
    "integration")
        echo "Running integration tests..."
        exec python -m pytest tests/integration/ -v --tb=short \
            --junitxml=test-results/integration-junit.xml
        ;;
    "security")
        echo "Running security tests..."
        bandit -r services/ cli/ web/ -f json -o test-results/bandit.json
        safety check --json --output test-results/safety.json
        echo "Security tests completed"
        ;;
    "performance")
        echo "Running performance tests..."
        exec python -m pytest tests/performance/ -v --tb=short \
            --junitxml=test-results/performance-junit.xml
        ;;
    "lint")
        echo "Running code quality checks..."
        echo "Checking formatting with Black..."
        black --check --diff .
        echo "Checking imports with isort..."
        isort --check-only --diff .
        echo "Linting with flake8..."
        flake8 services/ cli/ web/ --count --statistics
        echo "Type checking with mypy..."
        mypy services/ cli/ web/ --ignore-missing-imports
        echo "All linting checks passed"
        ;;
    "smoke")
        echo "Running smoke tests..."
        exec python -m pytest tests/smoke/ -v --tb=short \
            --junitxml=test-results/smoke-junit.xml
        ;;
    "all"|*)
        echo "Running full test suite..."
        exec "$@"
        ;;
esac
EOF

# Make entrypoint executable
RUN chmod +x /app/entrypoint-test.sh

# Set custom entrypoint
ENTRYPOINT ["/app/entrypoint-test.sh"]