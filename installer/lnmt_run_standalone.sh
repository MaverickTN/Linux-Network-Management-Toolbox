#!/bin/bash
# LNMT Standalone Runner
# Run LNMT without any external web server

set -e

# Default values
HOST="0.0.0.0"
PORT="8080"
WORKERS="4"
SSL_CERT=""
SSL_KEY=""
CONFIG_FILE="/etc/lnmt/config.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --ssl-cert)
            SSL_CERT="$2"
            shift 2
            ;;
        --ssl-key)
            SSL_KEY="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help)
            echo "LNMT Standalone Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --host HOST          Bind address (default: 0.0.0.0)"
            echo "  --port PORT          Port number (default: 8080)"
            echo "  --workers N          Number of workers (default: 4)"
            echo "  --ssl-cert FILE      SSL certificate file"
            echo "  --ssl-key FILE       SSL private key file"
            echo "  --config FILE        Config file path (default: /etc/lnmt/config.yml)"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Run with HTTP"
            echo "  $0"
            echo ""
            echo "  # Run with HTTPS"
            echo "  $0 --ssl-cert cert.pem --ssl-key key.pem --port 8443"
            echo ""
            echo "  # Run with custom settings"
            echo "  $0 --host 127.0.0.1 --port 8000 --workers 2"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then 
    echo "Warning: Running as root is not recommended!"
    echo "Consider running as the 'lnmt' user instead."
fi

# Export configuration
export LNMT_CONFIG="$CONFIG_FILE"

# Build the gunicorn command
CMD="gunicorn"
CMD="$CMD --workers $WORKERS"
CMD="$CMD --worker-class uvicorn.workers.UvicornWorker"
CMD="$CMD --bind ${HOST}:${PORT}"
CMD="$CMD --timeout 30"
CMD="$CMD --access-logfile -"
CMD="$CMD --error-logfile -"
CMD="$CMD --log-level info"

# Add SSL options if provided
if [ -n "$SSL_CERT" ] && [ -n "$SSL_KEY" ]; then
    if [ ! -f "$SSL_CERT" ]; then
        echo "Error: SSL certificate not found: $SSL_CERT"
        exit 1
    fi
    if [ ! -f "$SSL_KEY" ]; then
        echo "Error: SSL key not found: $SSL_KEY"
        exit 1
    fi
    
    CMD="$CMD --certfile=$SSL_CERT"
    CMD="$CMD --keyfile=$SSL_KEY"
    
    echo "Starting LNMT with HTTPS on ${HOST}:${PORT}"
else
    echo "Starting LNMT with HTTP on ${HOST}:${PORT}"
fi

echo "Workers: $WORKERS"
echo "Config: $CONFIG_FILE"
echo ""

# Add the application
CMD="$CMD lnmt.web.lnmt_web_app:app"

# Run the server
echo "Executing: $CMD"
exec $CMD