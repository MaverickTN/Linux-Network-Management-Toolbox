#!/usr/bin/env python3

import sqlite3
import os
import pwd
from functools import wraps
from flask import session, redirect, url_for, flash

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def init_auth_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER,
            permission_id INTEGER,
            FOREIGN KEY (role_id) REFERENCES roles(id),
            FOREIGN KEY (permission_id) REFERENCES permissions(id),
            UNIQUE(role_id, permission_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS group_mappings (
            sys_group TEXT,
            role_id INTEGER,
            FOREIGN KEY (role_id) REFERENCES roles(id),
            UNIQUE(sys_group)
        )
    """)

    conn.commit()
    conn.close()

def get_user_roles(username):
    init_auth_schema()
    user_groups = [g.gr_name for g in os.getgrouplist(username, pwd.getpwnam(username).pw_gid)]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    placeholders = ','.join('?' for _ in user_groups)
    cur.execute(f"""
        SELECT roles.name
        FROM group_mappings
        JOIN roles ON roles.id = group_mappings.role_id
        WHERE group_mappings.sys_group IN ({placeholders})
    """, tuple(user_groups))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def role_has_permission(role, permission):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM role_permissions
        JOIN roles ON roles.id = role_permissions.role_id
        JOIN permissions ON permissions.id = role_permissions.permission_id
        WHERE roles.name = ? AND permissions.name = ?
    """, (role, permission))
    found = cur.fetchone()
    conn.close()
    return found is not None

def user_has_permission(username, permission):
    roles = get_user_roles(username)
    for role in roles:
        if role_has_permission(role, permission):
            return True
    return False

def require_web_permission(permission):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user" not in session:
                flash("Login required", "warning")
                return redirect(url_for("login"))
            username = session["user"]
            if not user_has_permission(username, permission):
                flash("Access denied", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return wrapped
    return decorator
