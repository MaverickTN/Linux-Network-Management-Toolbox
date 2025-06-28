import os
import shutil
from datetime import datetime
from lnmt.db import db
from lnmt.core import logger, notifier

BACKUP_DIR = "/var/backups/lnmt"

def run_backup(backup_type, target=None):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{backup_type}_backup_{ts}.zip"
    filepath = os.path.join(BACKUP_DIR, filename)
    # Stub: just create an empty file for demo
    open(filepath, 'w').close()
    db.execute("INSERT INTO backup_history (timestamp, type, target, status, filename, size, run_by) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)",
               (backup_type, target or 'local', 'OK', filename, 0, 'system'))
    logger.log("backup", f"Backup {filename} created.")
    print(f"Backup {filename} created.")

def list_backups():
    rows = db.query("SELECT id, timestamp, type, target, status, filename, size FROM backup_history ORDER BY timestamp DESC")
    for r in rows:
        print(f"{r['id']}: {r['timestamp']} [{r['type']}] {r['filename']} {r['status']}")

def restore_backup(backup_id):
    row = db.query_one("SELECT filename FROM backup_history WHERE id = ?", (backup_id,))
    if not row:
        print("Backup not found.")
        return
    filename = row['filename']
    # Stub: just print action
    print(f"Would restore from {filename} (not actually implemented).")

def export_backup(backup_id):
    row = db.query_one("SELECT filename FROM backup_history WHERE id = ?", (backup_id,))
    if not row:
        print("Backup not found.")
        return
    filename = row['filename']
    print(f"Would export {filename} for download (stub).")

def set_policy(value):
    print(f"Would set retention policy to {value} (stub).")

def get_policy():
    print("Current retention policy: keep last 7 backups (stub).")
