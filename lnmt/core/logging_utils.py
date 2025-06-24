import datetime
import os
from .database import get_db

DEFAULT_LOG_FILE = os.environ.get("LNMT_LOG_FILE") or None

def log_event(username, action, status, extra=None, log_to_file=DEFAULT_LOG_FILE):
    # Log to database
    db = get_db()
    db.execute(
        "INSERT INTO logs (username, action, status) VALUES (?, ?, ?)",
        (username, action, status)
    )
    db.commit()
    db.close()
    # Optionally also log to file
    if log_to_file:
        timestamp = datetime.datetime.now().isoformat()
        with open(log_to_file, "a") as f:
            f.write(f"{timestamp} | {username} | {action} | {status} | {extra or ''}\n")

def fetch_logs(limit=100):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cur.fetchall()
    db.close()
    return logs
