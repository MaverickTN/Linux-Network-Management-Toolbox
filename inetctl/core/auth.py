import grp
import pwd
import getpass
import os

LNMT_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv"
}

def is_system_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def username_conflicts_with_system(username):
    """Returns True if username exists on system."""
    return is_system_user(username)

def get_lnmt_role(username=None):
    """Returns the LNMT group role for the given user, or None if not allowed."""
    if username is None:
        username = getpass.getuser()
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        primary_gid = pwd.getpwnam(username).pw_gid
        user_groups.append(grp.getgrgid(primary_gid).gr_name)
    except Exception:
        return None
    if LNMT_GROUPS["admin"] in user_groups:
        return "admin"
    if LNMT_GROUPS["operator"] in user_groups:
        return "operator"
    if LNMT_GROUPS["viewer"] in user_groups:
        return "viewer"
    return None

def enforce_cli_permission(min_role="operator"):
    """Decorator to restrict CLI access by group role."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            username = getpass.getuser()
            role = get_lnmt_role(username)
            allowed = ["admin"]
            if min_role == "operator":
                allowed.append("operator")
            if min_role == "viewer":
                allowed.extend(["operator", "viewer"])
            if role not in allowed:
                print("Access denied. You do not have the required group membership.")
                exit(1)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def is_cli_allowed():
    username = getpass.getuser()
    return get_lnmt_role(username) is not None

def create_profile_for_lnmt_user(username):
    from inetctl.core.user_profiles import get_user_profile, save_user_profile
    if not is_system_user(username):
        return
    if not get_lnmt_role(username):
        return
    profile = get_user_profile(username)
    if not profile or not isinstance(profile, dict):
        save_user_profile(username, {
            "theme": "dark",
            "email": "",
            "notifications": []
        })
