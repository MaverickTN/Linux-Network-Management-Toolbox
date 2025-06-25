import difflib
import sqlite3
import os
from datetime import datetime
from lnmt.core.admin_eventlog import log_admin_event

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def diff_and_log_config(filepath, actor="system"):
    backup_path = filepath + ".bak"
    if not os.path.exists(backup_path):
        return

    with open(backup_path, "r") as f1, open(filepath, "r") as f2:
        before = f1.readlines()
        after = f2.readlines()

    diff = ''.join(difflib.unified_diff(before, after, fromfile=backup_path, tofile=filepath))

    log_admin_event(
        action="config_diff",
        actor=actor,
        target=filepath,
        success=True,
        details=diff[:1000]  # truncate for DB storage
    )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS config_diff (id INTEGER PRIMARY KEY, filepath TEXT, timestamp TEXT, diff TEXT)")
    cur.execute("INSERT INTO config_diff (filepath, timestamp, diff) VALUES (?, ?, ?)",
                (filepath, datetime.utcnow().isoformat(), diff))
    conn.commit()
    conn.close()
