#!/bin/bash

# A script to launch all required lnmt services and manage their shutdown.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the directory of this script, so it can be run from anywhere.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define a cleanup function to be called on script exit.
cleanup() {
    echo "Shutting down lnmt services..."
    # The 'pkill -P $$' command is a robust way to kill all child processes of this script.
    # This ensures that when the script stops, sync.py and job_queue_service.py are also stopped.
    pkill -P $$
    echo "Shutdown complete."
}

# The 'trap' command registers the 'cleanup' function to run when the script
# receives a signal to terminate (SIGINT from Ctrl+C, or SIGTERM from systemd).
trap cleanup SIGINT SIGTERM

# Change to the script's directory to ensure all relative paths in our python files work.
cd "$DIR"

echo "Starting lnmt sync daemon..."
# Launch the sync daemon in the background.
/usr/bin/python3 sync.py &

echo "Starting lnmt job queue service..."
# Launch the job queue service in the background.
/usr/bin/python3 job_queue_service.py &

echo "Starting lnmt web server (foreground)..."
# Launch the web server in the foreground. This is crucial.
# The wrapper script will stay running as long as this command is running,
# allowing systemd to correctly monitor the service's state.
/usr/bin/python3 ./lnmt-runner.py web serve