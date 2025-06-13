import sqlite3
import time
import json
from pathlib import Path

DB_FILE = Path("./inetctl_stats.db")

def setup_job_queue_table():
    """Ensures the job_queue table exists in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_added INTEGER NOT NULL,
            timestamp_started INTEGER,
            timestamp_completed INTEGER,
            job_type TEXT NOT NULL,
            job_payload TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'completed', 'failed')),
            result_code INTEGER,
            result_message TEXT,
            requesting_user TEXT NOT NULL
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"CRITICAL [job_queue.setup]: Could not set up job_queue table: {e}")
    finally:
        if conn: conn.close()

def add_job(job_type: str, payload: dict, username: str) -> int:
    """Adds a new job to the queue and returns the job ID."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO job_queue 
        (timestamp_added, job_type, job_payload, status, requesting_user)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(time.time()), job_type, json.dumps(payload), 'queued', username)
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def get_job_status(job_id: int):
    """Retrieves the full status of a job by its ID."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    job = conn.execute("SELECT * FROM job_queue WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return job

# Ensure the table exists on first import
setup_job_queue_table()