# lnmt/core/user_manager.py

import sqlite3
import hashlib
import os
from lnmt.core.theme_manager import get_theme_list

USER_DB = os.environ.get('LNMT_USER_DB', '/etc/lnmt/lnmt.db')

def get_db():
    conn = sqlite3.connect(USER_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user_profile(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if not user:
        # Auto-create if host user, else None (should trigger on login only)
        return {
            "username": username,
            "email": "",
            "notify_options": [],
            "theme": "dark"
        }
    return dict(user)

def update_user_profile(username, email=None, notify_options=None):
    notify = ",".join(notify_options or [])
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET email=?, notify_options=? WHERE username=?",
        (email or '', notify, username)
    )
    conn.commit()
    conn.close()

def update_user_theme(username, theme):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET theme=? WHERE username=?",
        (theme, username)
    )
    conn.commit()
    conn.close()

def validate_and_update_password(username, old_password, new_password, confirm_password):
    if new_password != confirm_password:
        return False, "New password and confirmation do not match."
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if not row:
        return False, "User not found."
    stored_hash = row["password_hash"]
    if stored_hash and not check_password(old_password, stored_hash):
        return False, "Old password incorrect."
    # update password
    new_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, username))
    conn.commit()
    conn.close()
    return True, ""

def get_theme_list():
    return get_theme_list()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hash_value):
    return hashlib.sha256(password.encode()).hexdigest() == hash_value
