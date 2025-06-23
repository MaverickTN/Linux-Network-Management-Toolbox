# lnmt/core/group_access.py

import grp
import os

REQUIRED_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv"
}

def get_user_groups(username=None):
    if not username:
        username = os.getlogin()
    user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    # Also check the user's primary group
    try:
        import pwd
        primary_gid = pwd.getpwnam(username).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        if primary_group not in user_groups:
            user_groups.append(primary_group)
    except Exception:
        pass
    return user_groups

def user_access_level(username=None):
    groups = get_user_groups(username)
    if REQUIRED_GROUPS["admin"] in groups:
        return "admin"
    elif REQUIRED_GROUPS["operator"] in groups:
        return "operator"
    elif REQUIRED_GROUPS["viewer"] in groups:
        return "viewer"
    else:
        return None

def can_use_cli(username=None):
    return user_access_level(username) is not None

def is_admin(username=None):
    return user_access_level(username) == "admin"
