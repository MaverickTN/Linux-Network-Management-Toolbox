import sqlite3
import os

DB_PATH = "/etc/lnmt/lnmt.db"

def get_setting(key, default=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM detection_settings WHERE key=?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default
    except Exception:
        return default

def set_setting(key, value):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO detection_settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
