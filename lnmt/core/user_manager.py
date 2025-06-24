import os
import pwd
import grp
import hashlib
from .database import get_db

LNMT_GROUPS = {
    "lnmtadm": "admin",
    "lnmt": "operator",
    "lnmtv": "view"
}

def get_host_users():
    return [u.pw_name for u in pwd.getpwall() if u.pw_uid >= 1000 and 'nologin' not in u.pw_shell]

def user_group(username):
    for group in LNMT_GROUPS.keys():
        try:
            if username in grp.getgrnam(group).gr_mem:
                return LNMT_GROUPS[group]
        except KeyError:
            continue
    return None

def create_profile_if_group_member(username, email=None):
    if user_group(username):
        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO users (username, email, group) VALUES (?, ?, ?)",
                (username, email, user_group(username))
            )
            db.commit()
        db.close()
        return True
    return False

def get_user(username):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    db.close()
    return user

def set_user_theme(username, theme):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username))
    db.commit()
    db.close()

def list_users():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    db.close()
    return users

def set_password(username, new_password):
    # This example hashes password for local profile, not PAM!
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, username))
    db.commit()
    db.close()

def verify_password(username, password):
    # Only for local fallback, prefer PAM!
    hashed = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    c = db.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    db.close()
    return row and row["password_hash"] == hashed

def update_user_profile(username, email=None, theme=None, notification_settings=None):
    db = get_db()
    c = db.cursor()
    if email:
        c.execute("UPDATE users SET email = ? WHERE username = ?", (email, username))
    if theme:
        c.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username))
    if notification_settings is not None:
        c.execute("UPDATE users SET notification_settings = ? WHERE username = ?", (notification_settings, username))
    db.commit()
    db.close()
