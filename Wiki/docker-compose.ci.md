version: '3.8'

services:
  # LNMT Application
  lnmt:
    build:
      context: .
      dockerfile: docs/dockerfile.txt
      args:
        VERSION: ${LNMT_VERSION:-latest}
    container_name: lnmt-app
    ports:
      - "8080:8080"
      - "8443:8443"
    environment:
      - DATABASE_URL=postgresql://lnmt:lnmt_password@postgres:5432/lnmt
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=testing
      - LOG_LEVEL=DEBUG
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - lnmt-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: lnmt-postgres
    environment:
      POSTGRES_USER: lnmt
      POSTGRES_PASSWORD: lnmt_password
      POSTGRES_DB: lnmt
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./tests/sql:/docker-entrypoint-initdb.d
    networks:
      - lnmt-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lnmt -d lnmt"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: lnmt-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    networks:
      - lnmt-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  # Test Runner
  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.test
    container_name: lnmt-test-runner
    environment:
      - DATABASE_URL=postgresql://lnmt:lnmt_password@postgres:5432/lnmt_test
      - REDIS_URL=redis://redis:6379
      - PYTHONPATH=/app
    volumes:
      - .:/app
      - ./test-results:/app/test-results
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - lnmt-network
    command: >
      sh -c "
        echo 'Setting up test database...' &&
        createdb -h postgres -U lnmt lnmt_test &&
        echo 'Running tests...' &&
        python -m pytest tests/ -v --junitxml=test-results/junit.xml --html=test-results/report.html --cov=services --cov=cli --cov=web --cov-report=html:test-results/htmlcov &&
        echo 'Tests completed.'
      "

  # Nginx Load Balancer (for testing)
  nginx:
    image: nginx:alpine
    container_name: lnmt-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
      - ./config/ssl:/etc/nginx/ssl
    depends_on:
      - lnmt
    networks:
      - lnmt-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring Stack
  prometheus:
    image: prom/prometheus:latest
    container_name: lnmt-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - lnmt-network

  grafana:
    image: grafana/grafana:latest
    container_name: lnmt-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - lnmt-network

  # Log Aggregation
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    container_name: lnmt-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - lnmt-network

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    container_name: lnmt-kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - lnmt-network

  # Security Scanner
  security-scanner:
    image: aquasec/trivy:latest
    container_name: lnmt-security-scanner
    volumes:
      - .:/app
      - ./security-reports:/reports
    working_dir: /app
    networks:
      - lnmt-network
    command: >
      sh -c "
        echo 'Running security scans...' &&
        trivy fs --format json --output /reports/filesystem-scan.json . &&
        trivy image --format json --output /reports/image-scan.json lnmt:latest &&
        echo 'Security scans completed.'
      "

  # Performance Testing
  k6:
    image: grafana/k6:latest
    container_name: lnmt-k6
    volumes:
      - ./tests/performance:/scripts
      - ./performance-results:/results
    environment:
      - K6_OUT=json=/results/k6-results.json
    networks:
      - lnmt-network
    command: run --vus 10 --duration 30s /scripts/load-test.js
    depends_on:
      - lnmt

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  elasticsearch_data:
    driver: local

networks:
  lnmt-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# Additional configurations for CI/CD
x-common-variables: &common-variables
  DATABASE_URL: postgresql://lnmt:lnmt_password@postgres:5432/lnmt
  REDIS_URL: redis://redis:6379
  PYTHONPATH: /app
  LOG_LEVEL: DEBUG

# Override for different environments
# Usage: docker-compose -f docker-compose.yml -f docker-compose.ci.yml up
---
# docker-compose.ci.yml - CI/CD specific overrides
version: '3.8'

services:
  lnmt:
    environment:
      <<: *common-variables
      ENVIRONMENT: ci
    ports:
      - "8080"  # Random port assignment
    command: >
      sh -c "
        echo 'Waiting for dependencies...' &&
        sleep 10 &&
        python -m pytest tests/integration/ --tb=short &&
        python web/lnmt_web_app.py
      "

  postgres:
    environment:
      POSTGRES_DB: lnmt_ci
    tmpfs:
      - /var/lib/postgresql/data  # Use tmpfs for faster CI

  redis:
    tmpfs:
      - /data  # Use tmpfs for faster CI

  test-runner:
    environment:
      <<: *common-variables
      DATABASE_URL: postgresql://lnmt:lnmt_password@postgres:5432/lnmt_ci
    command: >
      sh -c "
        echo 'Setting up CI test environment...' &&
        pip install pytest-xdist pytest-cov pytest-html bandit safety &&
        createdb -h postgres -U lnmt lnmt_test || true &&
        echo 'Running comprehensive test suite...' &&
        python -m pytest tests/ -v -x --tb=short --maxfail=5 \
          --junitxml=test-results/junit.xml \
          --html=test-results/report.html \
          --cov=services --cov=cli --cov=web --cov=integration \
          --cov-report=html:test-results/htmlcov \
          --cov-report=xml:test-results/coverage.xml \
          --cov-fail-under=80 &&
        echo 'Running security scans...' &&
        bandit -r services/ cli/ web/ -f json -o test-results/bandit.json &&
        safety check --json --output test-results/safety.json &&
        echo 'All CI tests completed successfully.'
      "