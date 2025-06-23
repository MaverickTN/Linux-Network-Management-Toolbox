# lnmt/core/user_manager.py

import os
import pwd
import grp

REQUIRED_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "view": "lnmtv"
}

def get_system_groups(username):
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    try:
        primary_group = grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name
        if primary_group not in groups:
            groups.append(primary_group)
    except Exception:
        pass
    return groups

def is_system_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_user_role(username):
    groups = get_system_groups(username)
    if REQUIRED_GROUPS["admin"] in groups:
        return "admin"
    elif REQUIRED_GROUPS["operator"] in groups:
        return "operator"
    elif REQUIRED_GROUPS["view"] in groups:
        return "view"
    else:
        return None

def can_user_access_cli(username):
    role = get_user_role(username)
    return role in ("admin", "operator", "view")

def auto_create_profile(username, user_db):
    """
    Auto-creates a profile in the database for a new system user if not present.
    Skips creation for root, and disables creation if username already exists in user_db.
    """
    if username == "root":
        return
    if not is_system_user(username):
        return
    if user_db.get(username):
        return
    user_db[username] = {
        "username": username,
        "role": get_user_role(username),
        "theme": "dark",
        "notifications": {
            "toast": True,
            "email": False
        }
    }
    return user_db[username]
