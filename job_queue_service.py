import sqlite3
import time
import json
import subprocess
from pathlib import Path

DB_FILE = Path("./inetctl_stats.db")
POLL_INTERVAL_SECONDS = 5 # How often to check for new jobs

def get_db_connection():
    """Gets a fresh, writable database connection."""
    return sqlite3.connect(DB_FILE, timeout=10)

def find_and_run_next_job():
    """
    Finds the oldest queued job, runs it, and updates its status.
    This function uses a transaction to ensure jobs are processed one at a time.
    """
    job_id = None
    job_type = None
    job_payload_str = None
    
    # Transactionally find and lock a job
    conn = get_db_connection()
    try:
        with conn: # 'with' starts a transaction
            cursor = conn.cursor()
            # Find the oldest queued job
            cursor.execute("SELECT id, job_type, job_payload FROM job_queue WHERE status = 'queued' ORDER BY timestamp_added ASC LIMIT 1")
            job_row = cursor.fetchone()

            if job_row:
                job_id, job_type, job_payload_str = job_row
                # Immediately mark it as 'running' so no other process picks it up
                cursor.execute(
                    "UPDATE job_queue SET status = 'running', timestamp_started = ? WHERE id = ?",
                    (int(time.time()), job_id)
                )
                print(f"[{time.strftime('%H:%M:%S')}] Picked up job {job_id}: {job_type}")
            else:
                return # No jobs to run
    except sqlite3.Error as e:
        print(f"Database error during job selection: {e}")
        if conn: conn.close()
        return
    finally:
        if conn: conn.close()

    # If we successfully locked a job, run it now (outside the transaction)
    if not job_id:
        return

    try:
        payload = json.loads(job_payload_str)
        
        # --- Job Execution Logic ---
        command = ["./inetctl-runner.py"] # Base command
        
        if job_type == "shorewall:sync":
            command.extend(["shorewall", "sync"])
        elif job_type == "access:block":
            command.extend(["access", "block", payload["ip"]])
        elif job_type == "access:unblock":
            command.extend(["access", "unblock", payload["ip"]])
        # Add more job types here in the future
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        result = subprocess.run(command, capture_output=True, text=True, timeout=60)

        # Update job with completion status
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE job_queue 
            SET status = ?, timestamp_completed = ?, result_code = ?, result_message = ?
            WHERE id = ?
            """,
            (
                'completed' if result.returncode == 0 else 'failed',
                int(time.time()),
                result.returncode,
                result.stdout.strip() or result.stderr.strip(),
                job_id
            )
        )
        conn.commit()
        conn.close()
        print(f"[{time.strftime('%H:%M:%S')}] Finished job {job_id} with code {result.returncode}")

    except Exception as e:
        # Handle exceptions during job execution (e.g., bad payload, command error)
        print(f"Critical error executing job {job_id}: {e}")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE job_queue SET status = 'failed', timestamp_completed = ?, result_message = ?
            WHERE id = ?
            """,
            (int(time.time()), str(e), job_id)
        )
        conn.commit()
        conn.close()

def main_loop():
    print("--- Starting inetctl Job Queue Service ---")
    while True:
        try:
            find_and_run_next_job()
            time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\nShutting down job queue service.")
            break
        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            time.sleep(30) # Wait a bit longer after an unexpected error

if __name__ == "__main__":
    main_loop()