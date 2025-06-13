import sqlite3
import time
import json
import subprocess
from pathlib import Path

# --- Configuration ---
DB_FILE = Path("./inetctl_stats.db")
POLL_INTERVAL_SECONDS = 5  # How often to check for new jobs

def get_db_connection():
    """Gets a fresh, writable database connection."""
    try:
        # The timeout helps prevent database locked errors if the web UI and this service
        # try to access the database at the exact same moment.
        return sqlite3.connect(DB_FILE, timeout=10)
    except sqlite3.Error as e:
        print(f"[{time.strftime('%H:%M:%S')}] FATAL: Could not connect to database at {DB_FILE}: {e}")
        return None

def find_and_run_next_job():
    """
    Finds the oldest queued job, runs it, and updates its status.
    This function uses a transaction to ensure jobs are processed atomically.
    """
    job_id = None
    job_type = None
    job_payload_str = None
    requesting_user = None
    
    # --- Step 1: Find and "lock" a job in a transaction ---
    conn = get_db_connection()
    if not conn:
        return # Cannot proceed without a database connection
        
    try:
        # Using 'with conn' ensures the block is a transaction. It will either
        # all succeed, or all be rolled back.
        with conn:
            cursor = conn.cursor()
            # Find the oldest job that is still in the 'queued' state.
            cursor.execute("SELECT id, job_type, job_payload, requesting_user FROM job_queue WHERE status = 'queued' ORDER BY timestamp_added ASC LIMIT 1")
            job_row = cursor.fetchone()

            if job_row:
                job_id, job_type, job_payload_str, requesting_user = job_row
                # Immediately mark the job as 'running' so no other process picks it up.
                cursor.execute(
                    "UPDATE job_queue SET status = 'running', timestamp_started = ? WHERE id = ?",
                    (int(time.time()), job_id)
                )
                print(f"[{time.strftime('%H:%M:%S')}] Picked up job {job_id}: Type='{job_type}', User='{requesting_user}'")
            else:
                return  # No jobs to run, exit function silently.
    
    except sqlite3.Error as e:
        print(f"Database error during job selection: {e}")
        return
    finally:
        if conn:
            conn.close()

    # If we did not successfully get a job, stop here.
    if not job_id:
        return

    # --- Step 2: Execute the job (outside the transaction) ---
    try:
        payload = json.loads(job_payload_str)
        
        # Build the command to be executed based on the job type
        command = ["./inetctl-runner.py"] 
        
        if job_type == "shorewall:sync":
            command.extend(["shorewall", "sync"])
        elif job_type == "api:vlan_toggle_access":
            # This job type is just a config change and a sync.
            # For simplicity, we make it just run the sync job which reads the latest config.
            command.extend(["shorewall", "sync"])
        # Add more job types here in the future
        else:
            raise ValueError(f"Unknown or non-executable job type: {job_type}")

        # Execute the command as a subprocess
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        
        final_status = 'completed' if result.returncode == 0 else 'failed'
        output_message = result.stdout.strip() or result.stderr.strip() or "(No output)"
        result_code = result.returncode

    except Exception as e:
        # This catches errors in *this script*, e.g., bad payload, unknown job type, etc.
        final_status = 'failed'
        output_message = f"Job runner failed: {str(e)}"
        result_code = -1 # Use -1 for internal service errors
        print(f"CRITICAL: Error executing job {job_id}: {e}")

    # --- Step 3: Update the job with the final result ---
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_queue 
                SET status = ?, timestamp_completed = ?, result_code = ?, result_message = ?
                WHERE id = ?
                """,
                (final_status, int(time.time()), result_code, output_message, job_id)
            )
            conn.commit()
            print(f"[{time.strftime('%H:%M:%S')}] Finished job {job_id} with status '{final_status}'")
        except sqlite3.Error as e:
            print(f"FATAL: Database error updating job {job_id} status: {e}")
        finally:
            conn.close()


def main_loop():
    """The main infinite loop for the daemon process."""
    print("--- Starting inetctl Job Queue Service ---")
    print(f"--- Polling for new jobs every {POLL_INTERVAL_SECONDS} seconds. Press Ctrl+C to exit. ---")
    while True:
        try:
            find_and_run_next_job()
            time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\nShutting down job queue service gracefully.")
            break
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            print("Restarting loop after 30 seconds...")
            time.sleep(30) 

if __name__ == "__main__":
    main_loop()