import sqlite3
import time
import json
import subprocess
from pathlib import Path

DB_FILE = Path("./inetctl_stats.db")
POLL_INTERVAL_SECONDS = 5

def get_db_connection():
    try: return sqlite3.connect(DB_FILE, timeout=10)
    except sqlite3.Error as e: print(f"[{time.strftime('%H:%M:%S')}] FATAL: Could not connect to database at {DB_FILE}: {e}"); return None

def find_and_run_next_job():
    job_id, job_type, job_payload_str, requesting_user = None, None, None, None
    conn = get_db_connection()
    if not conn: return
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, job_type, job_payload, requesting_user FROM job_queue WHERE status = 'queued' ORDER BY timestamp_added ASC LIMIT 1")
            job_row = cursor.fetchone()
            if job_row:
                job_id, job_type, job_payload_str, requesting_user = job_row
                cursor.execute("UPDATE job_queue SET status = 'running', timestamp_started = ? WHERE id = ?", (int(time.time()), job_id))
                print(f"[{time.strftime('%H:%M:%S')}] Picked up job {job_id}: Type='{job_type}', User='{requesting_user}'")
            else: return
    except sqlite3.Error as e: print(f"DB error during job selection: {e}"); return
    finally:
        if conn: conn.close()

    if not job_id: return

    try:
        payload = json.loads(job_payload_str)
        command = ["./inetctl-runner.py"] 
        if job_type == "shorewall:sync" or job_type == "api:vlan_toggle_access": command.extend(["shorewall", "sync"])
        elif job_type == "netplan:apply": command.extend(["network", "apply"])
        elif job_type == "netplan:add_vlan":
            p = payload
            if not all(k in p for k in ['id', 'name', 'link', 'address']): raise ValueError("Missing required payload fields for add_vlan")
            command.extend(["network", "add", "vlan", f"vlan{p['id']}", "--link", p['link'], "--address", p['address'], "--name", p['name']])
        else: raise ValueError(f"Unknown or non-executable job type: {job_type}")
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        final_status, output_message, result_code = ('completed' if result.returncode == 0 else 'failed'), (result.stdout.strip() or result.stderr.strip() or "(No output)"), result.returncode
    except Exception as e:
        final_status, output_message, result_code = 'failed', f"Job runner failed: {str(e)}", -1
        print(f"CRITICAL: Error executing job {job_id}: {e}")

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE job_queue SET status = ?, timestamp_completed = ?, result_code = ?, result_message = ? WHERE id = ?", (final_status, int(time.time()), result_code, output_message, job_id))
            conn.commit()
            print(f"[{time.strftime('%H:%M:%S')}] Finished job {job_id} with status '{final_status}'")
        except sqlite3.Error as e: print(f"FATAL: DB error updating job {job_id}: {e}")
        finally: conn.close()

def main_loop():
    print("--- Starting inetctl Job Queue Service ---"); print(f"--- Polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to exit. ---")
    while True:
        try: find_and_run_next_job(); time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt: print("\nShutting down gracefully."); break
        except Exception as e: print(f"Unexpected error in main loop: {e}"); time.sleep(30)
if __name__ == "__main__": main_loop()