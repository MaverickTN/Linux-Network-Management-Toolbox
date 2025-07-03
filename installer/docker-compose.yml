# docker-compose.yml for LNMT Web Dashboard

version: '3.8'

services:
  lnmt-web:
    build: .
    container_name: lnmt-web-dashboard
    ports:
      - "8000:8000"
    environment:
      - LNMT_ENV=production
      - DATABASE_URL=postgresql://lnmt:lnmt_password@postgres:5432/lnmt_db
      - SECRET_KEY=your-super-secret-key-change-in-production
      - CORS_ORIGINS=http://localhost:3000,http://localhost:8080
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - lnmt-network

  postgres:
    image: postgres:15-alpine
    container_name: lnmt-postgres
    environment:
      - POSTGRES_DB=lnmt_db
      - POSTGRES_USER=lnmt
      - POSTGRES_PASSWORD=lnmt_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - lnmt-network

  redis:
    image: redis:7-alpine
    container_name: lnmt-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - lnmt-network

  nginx:
    image: nginx:alpine
    container_name: lnmt-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./web/static:/usr/share/nginx/html/static:ro
    depends_on:
      - lnmt-web
    restart: unless-stopped
    networks:
      - lnmt-network

volumes:
  postgres_data:
  redis_data:

networks:
  lnmt-network:
    driver: bridge

# Development override file (docker-compose.override.yml)
---
# docker-compose.override.yml (for development)
version: '3.8'

services:
  lnmt-web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    environment:
      - LNMT_ENV=development
      - DATABASE_URL=sqlite:///./lnmt.db
    volumes:
      - ./web:/app
      - ./data:/app/data
    command: ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    ports:
      - "8000:8000"

  # Disable production services for development
  postgres:
    profiles: ["production"]
  
  redis:
    profiles: ["production"]
    
  nginx:
    profiles: ["production"]