import sqlite3
import os
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get("LNMT_DB_PATH") or str(Path.home() / ".config" / "lnmt" / "lnmt.db")

def get_db(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db(db_path)
    cur = conn.cursor()
    # Create tables if not exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        group TEXT,
        theme TEXT DEFAULT 'dark',
        notification_settings TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Add more tables as needed (e.g., scheduled_tasks, blocks, etc.)
    conn.commit()
    conn.close()
