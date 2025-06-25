#!/usr/bin/env python3

import sqlite3
from datetime import datetime
import os

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            role TEXT DEFAULT 'guest',
            theme TEXT DEFAULT 'default',
            created TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user_profile(username):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username, role, theme, created FROM user_profiles WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "role": row[1], "theme": row[2], "created": row[3]}
    return None

def update_user_profile(username, updates):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    profile = get_user_profile(username)
    if profile is None:
        cur.execute("""
            INSERT INTO user_profiles (username, role, theme, created)
            VALUES (?, ?, ?, ?)
        """, (
            username,
            updates.get("role", "guest"),
            updates.get("theme", "default"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
    else:
        if "role" in updates:
            cur.execute("UPDATE user_profiles SET role = ? WHERE username = ?", (updates["role"], username))
        if "theme" in updates:
            cur.execute("UPDATE user_profiles SET theme = ? WHERE username = ?", (updates["theme"], username))
    conn.commit()
    conn.close()

def get_user_role(username):
    profile = get_user_profile(username)
    if profile:
        return profile["role"]
    return None

def set_user_role(username, role):
    valid_roles = {"admin", "operator", "guest"}
    if role not in valid_roles:
        raise ValueError("Invalid role. Choose from: admin, operator, guest.")
    update_user_profile(username, {"role": role})

def get_user_theme(username):
    profile = get_user_profile(username)
    if profile:
        return profile.get("theme", "default")
    return "default"

def set_user_theme(username, theme):
    update_user_profile(username, {"theme": theme})
