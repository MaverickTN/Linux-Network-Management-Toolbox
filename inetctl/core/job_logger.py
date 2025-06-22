import json
import os
from datetime import datetime
from pathlib import Path

JOB_LOG_FILE = "/var/lib/inetctl/job_log.jsonl"

def ensure_job_log_file():
    Path(JOB_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    if not Path(JOB_LOG_FILE).exists():
        with open(JOB_LOG_FILE, "w") as f:
            pass

def log_job_event(job_id, user, action, status, step=None, message=None, details=None):
    ensure_job_log_file()
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "job_id": job_id,
        "user": user,
        "action": action,
        "status": status,
        "step": step,
        "message": message,
        "details": details or {}
    }
    with open(JOB_LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

def get_recent_job_events(limit=50, job_id=None, user=None):
    if not os.path.exists(JOB_LOG_FILE):
        return []
    events = []
    with open(JOB_LOG_FILE, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                if job_id and event.get("job_id") != job_id:
                    continue
                if user and event.get("user") != user:
                    continue
                events.append(event)
            except Exception:
                continue
    return events[-limit:]
