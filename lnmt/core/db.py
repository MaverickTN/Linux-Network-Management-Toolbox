import sqlite3
import os

DB_PATH = os.environ.get("LNMT_DB_PATH", "/etc/lnmt/lnmt.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_username(username):
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone()

def update_user_theme(username, theme):
    db = get_db()
    db.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username))
    db.commit()

def create_user_if_not_exists(username, default_theme="dark"):
    db = get_db()
    db.execute("""
        INSERT OR IGNORE INTO users (username, theme)
        VALUES (?, ?)
    """, (username, default_theme))
    db.commit()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            theme TEXT DEFAULT 'dark',
            email TEXT,
            notify_events TEXT
        );
    """)
    db.commit()
