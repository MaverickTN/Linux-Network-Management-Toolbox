import sqlite3
from datetime import datetime

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def log_admin_event(action, actor=None, target=None, success=True, details=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_eventlog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            actor TEXT,
            action TEXT NOT NULL,
            target TEXT,
            success INTEGER NOT NULL,
            details TEXT
        )
    """)
    cur.execute("""
        INSERT INTO admin_eventlog (timestamp, actor, action, target, success, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), actor, action, target, int(success), details))
    conn.commit()
    conn.close()
