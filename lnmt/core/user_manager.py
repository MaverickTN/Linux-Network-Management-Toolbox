# lnmt/core/user_manager.py

import os
import json
import pwd
from pathlib import Path

USER_DB_PATH = Path.home() / ".config" / "lnmt" / "users.json"
GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv"
}

def get_system_users():
    return [p.pw_name for p in pwd.getpwall() if int(p.pw_uid) >= 1000 and "nologin" not in p.pw_shell]

def get_user_groups(username):
    import grp
    return [g.gr_name for g in grp.getgrall() if username in g.gr_mem]

def user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def load_users():
    if USER_DB_PATH.exists():
        with open(USER_DB_PATH) as f:
            return json.load(f)
    return {}

def save_users(users):
    USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_DB_PATH, "w") as f:
        json.dump(users, f, indent=2)

def create_or_update_user(username, profile):
    users = load_users()
    users[username] = profile
    save_users(users)

def auto_create_profile(username):
    if not user_exists(username):
        raise ValueError(f"System user {username} does not exist.")
    users = load_users()
    if username in users:
        return
    groups = get_user_groups(username)
    for group_name, group_val in GROUPS.items():
        if group_val in groups:
            users[username] = {
                "role": group_name,
                "theme": "dark"
            }
            break
    save_users(users)

def user_has_cli_access(username):
    groups = get_user_groups(username)
    return any(g in groups for g in GROUPS.values())

def user_role(username):
    users = load_users()
    return users.get(username, {}).get("role", "viewer")
