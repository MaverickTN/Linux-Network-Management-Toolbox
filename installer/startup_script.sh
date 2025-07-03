#!/bin/bash
# web/start_lnmt_web.sh

# LNMT Web Dashboard Startup Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR="venv"
APP_DIR="web"
HOST="${LNMT_HOST:-0.0.0.0}"
PORT="${LNMT_PORT:-8000}"
WORKERS="${LNMT_WORKERS:-1}"
ENVIRONMENT="${LNMT_ENV:-development}"

echo -e "${BLUE}🚀 Starting LNMT Web Dashboard${NC}"
echo "=================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source $VENV_DIR/bin/activate

# Upgrade pip
pip install --upgrade pip > /dev/null 2>&1

# Install/upgrade dependencies
if [ -f "$APP_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}📋 Installing dependencies...${NC}"
    pip install -r $APP_DIR/requirements.txt
else
    echo -e "${YELLOW}📋 Installing core dependencies...${NC}"
    pip install fastapi uvicorn sqlalchemy python-jose jinja2 aiofiles
fi

# Check if app.py exists
if [ ! -f "$APP_DIR/app.py" ]; then
    echo -e "${RED}❌ app.py not found in $APP_DIR directory${NC}"
    echo "Please ensure the LNMT web application files are in place."
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}📁 Setting up directory structure...${NC}"
mkdir -p $APP_DIR/templates
mkdir -p $APP_DIR/static/{css,js}

# Set environment variables
export PYTHONPATH="$PWD/$APP_DIR:$PYTHONPATH"

# Display startup information
echo ""
echo -e "${BLUE}📊 Configuration:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  Environment: $ENVIRONMENT"
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down LNMT Web Dashboard...${NC}"
    # Kill any background processes if needed
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start the application based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${GREEN}🏭 Starting in production mode with Gunicorn...${NC}"
    
    # Check if gunicorn is installed
    if ! pip show gunicorn > /dev/null 2>&1; then
        echo -e "${YELLOW}📦 Installing Gunicorn for production...${NC}"
        pip install gunicorn
    fi
    
    cd $APP_DIR
    exec gunicorn app:app \
        -w $WORKERS \
        -k uvicorn.workers.UvicornWorker \
        --bind $HOST:$PORT \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    echo -e "${GREEN}🔧 Starting in development mode...${NC}"
    echo -e "${BLUE}📱 Access the dashboard at: http://localhost:$PORT${NC}"
    echo -e "${BLUE}📚 API documentation at: http://localhost:$PORT/api/docs${NC}"
    echo ""
    echo -e "${YELLOW}Default login credentials:${NC}"
    echo "  Admin: admin / admin123"
    echo "  User:  user / user123"
    echo ""
    echo -e "${GREEN}✨ LNMT Web Dashboard is starting...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""
    
    cd $APP_DIR
    exec uvicorn app:app \
        --host $HOST \
        --port $PORT \
        --reload \
        --reload-dir . \
        --log-level info
fi