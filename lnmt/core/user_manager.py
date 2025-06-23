# lnmt/core/user_manager.py

import os
import pwd
import grp
import json
from pathlib import Path
from lnmt.core.theme_manager import get_theme

DB_PATH = Path.home() / ".lnmt" / "lnmt_users.json"
REQUIRED_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv"
}

def _get_system_users():
    return {u.pw_name for u in pwd.getpwall()}

def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        with open(DB_PATH, "w") as f:
            json.dump({}, f)

def _load_users():
    _ensure_db()
    with open(DB_PATH, "r") as f:
        return json.load(f)

def _save_users(users):
    with open(DB_PATH, "w") as f:
        json.dump(users, f, indent=2)

def create_user(username, email=None, group=None, theme="dark"):
    system_users = _get_system_users()
    if username not in system_users:
        raise ValueError(f"User {username} does not exist on this system.")
    users = _load_users()
    if username in users:
        raise ValueError(f"User profile for {username} already exists.")
    group = group or get_user_group(username)
    users[username] = {
        "email": email or "",
        "group": group,
        "theme": theme
    }
    _save_users(users)
    return users[username]

def get_user_group(username):
    for role, group in REQUIRED_GROUPS.items():
        try:
            members = grp.getgrnam(group).gr_mem
            if username in members:
                return role
        except KeyError:
            continue
    return None

def user_has_cli_access(username):
    return get_user_group(username) in ("admin", "operator", "viewer")

def get_user(username):
    users = _load_users()
    return users.get(username)

def auto_create_user_profile(username):
    system_users = _get_system_users()
    if username not in system_users:
        return None
    users = _load_users()
    if username not in users:
        group = get_user_group(username)
        theme = "dark"
        users[username] = {"email": "", "group": group, "theme": theme}
        _save_users(users)
    return users[username]

def set_user_theme(username, theme_key):
    users = _load_users()
    if username not in users:
        raise ValueError("User profile does not exist.")
    if theme_key not in get_theme():
        raise ValueError("Invalid theme selected.")
    users[username]["theme"] = theme_key
    _save_users(users)

def list_all_users():
    return _load_users()
