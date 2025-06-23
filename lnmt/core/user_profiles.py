import sqlite3
import os

DB_PATH = os.environ.get("LNMT_PROFILE_DB") or "/etc/lnmt/lnmt_users.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_user_db():
    conn = get_db()
    with conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                notify_mask TEXT,
                theme TEXT DEFAULT 'dark'
            )"""
        )
    conn.close()

def get_user_profile(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row

def upsert_user_profile(username, email=None, notify_mask=None, theme=None):
    conn = get_db()
    with conn:
        existing = get_user_profile(username)
        if existing:
            conn.execute(
                "UPDATE user_profiles SET email = COALESCE(?, email), notify_mask = COALESCE(?, notify_mask), theme = COALESCE(?, theme) WHERE username = ?",
                (email, notify_mask, theme, username),
            )
        else:
            conn.execute(
                "INSERT INTO user_profiles (username, email, notify_mask, theme) VALUES (?, ?, ?, ?)",
                (username, email, notify_mask, theme or "dark"),
            )
    conn.close()

def all_user_profiles():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles")
    rows = cur.fetchall()
    conn.close()
    return rows

def auto_create_user(username):
    """Auto-create a profile for first-time LNMT group member."""
    if get_user_profile(username) is None:
        upsert_user_profile(username)
