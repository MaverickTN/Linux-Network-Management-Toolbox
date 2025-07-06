#!/bin/bash
# LNMT Standalone Runner
# Run LNMT without any external web server

set -e

# Default values
HOST="${LNMT_HOST:-0.0.0.0}"
PORT="${LNMT_PORT:-8080}"
WORKERS="${LNMT_WORKERS:-4}"
CONFIG_FILE="${LNMT_CONFIG:-/etc/lnmt/config.yml}"

# Simple start function
start_standalone() {
    echo "Starting LNMT in standalone mode..."
    echo "Host: $HOST"
    echo "Port: $PORT"
    echo "Workers: $WORKERS"

    exec gunicorn \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind ${HOST}:${PORT} \
        --timeout 30 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        lnmt.web.lnmt_web_app:app
}

# Run
start_standalone
