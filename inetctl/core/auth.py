import os
import sys
import getpass
import functools
import grp

from inetctl.theme import cli_color

# These are the valid groups for various access levels
REQUIRED_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv",
}

def get_current_user():
    return getpass.getuser()

def user_in_group(user, group):
    try:
        return user in grp.getgrnam(group).gr_mem or grp.getgrnam(group).gr_gid == os.getgid()
    except KeyError:
        return False

def check_group(user, allowed_groups):
    if user == "root":
        # Allow root to do everything, with a warning
        return True
    for g in allowed_groups:
        if user_in_group(user, g):
            return True
    return False

def require_group(groups):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not check_group(user, groups):
                msg = f"User '{user}' lacks required group(s): {groups}. Access denied."
                print(cli_color(msg, "danger"))
                sys.exit(1)
            return f(*args, **kwargs)
        return wrapper
    return decorator
