import json
import time
from datetime import datetime
from lnmt.db import db
from lnmt.core import notifier, logger
from lnmt.util.cron import is_due

def list_jobs():
    rows = db.query("SELECT id, name, schedule, action, enabled, last_run FROM scheduled_jobs")
    for r in rows:
        print(f"{r['id']}: {r['name']} [{r['schedule']}] -> {r['action']} enabled={r['enabled']}")

def run_job(job_id):
    job = db.query_one("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,))
    if not job:
        print("Job not found.")
        return

    try:
        logger.log("scheduler", f"Running job: {job['name']}")
        output = execute_action(job['action'], json.loads(job['params']))
        db.execute("INSERT INTO job_run_log (job_id, run_time, result, output) VALUES (?, datetime('now'), ?, ?)",
                   (job_id, "OK", output))
        db.execute("UPDATE scheduled_jobs SET last_run = datetime('now'), last_result = ? WHERE id = ?", ("OK", job_id))
    except Exception as e:
        err_msg = str(e)
        db.execute("INSERT INTO job_run_log (job_id, run_time, result, output) VALUES (?, datetime('now'), ?, ?)",
                   (job_id, "FAIL", err_msg))
        db.execute("UPDATE scheduled_jobs SET last_run = datetime('now'), last_result = ? WHERE id = ?", ("FAIL", job_id))
        notifier.notify_admin(f"Scheduled job '{job['name']}' failed: {err_msg}")

def show_job_log(job_id):
    logs = db.query("SELECT run_time, result, output FROM job_run_log WHERE job_id = ? ORDER BY run_time DESC LIMIT 10", (job_id,))
    for log in logs:
        print(f"{log['run_time']} - {log['result']}: {log['output']}")

def add_job(name, action, schedule, params):
    db.execute("INSERT INTO scheduled_jobs (name, action, schedule, params, enabled) VALUES (?, ?, ?, ?, 1)",
               (name, action, schedule, params))
    print("Job added.")

def edit_job(job_id, enable):
    db.execute("UPDATE scheduled_jobs SET enabled = ? WHERE id = ?", (1 if enable else 0, job_id))
    print("Job updated.")

def execute_action(action, params):
    if action == "backup":
        return "Backup completed"
    elif action == "report":
        return "Report generated"
    elif action == "purge_logs":
        return "Logs purged"
    elif action == "sync_dns":
        return "DNS synchronized"
    elif action == "custom":
        return "Custom action run"
    return "Unknown action"

def scheduler_loop():
    jobs = db.query("SELECT * FROM scheduled_jobs WHERE enabled = 1")
    now = datetime.now()
    for job in jobs:
        if is_due(job['schedule'], job['last_run'], now):
            run_job(job['id'])
