import os
import pwd
import grp
import pam  # Requires python-pam package
from lnmt.core.user_profiles import load_profile, save_profile, DEFAULT_PROFILE

# Define group names for access levels
ADMIN_GROUP = "lnmtadm"
OPERATOR_GROUP = "lnmt"
VIEW_GROUP = "lnmtv"
ALLOWED_GROUPS = [ADMIN_GROUP, OPERATOR_GROUP, VIEW_GROUP]

def system_user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_user_groups(username):
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        user_gid = pwd.getpwnam(username).pw_gid
        user_groups.append(grp.getgrgid(user_gid).gr_name)
        return set(user_groups)
    except Exception:
        return set()

def get_access_level(username):
    """Returns admin/operator/view if member, else None."""
    groups = get_user_groups(username)
    if ADMIN_GROUP in groups:
        return "admin"
    elif OPERATOR_GROUP in groups:
        return "operator"
    elif VIEW_GROUP in groups:
        return "view"
    return None

def pam_authenticate(username, password):
    p = pam.pam()
    return p.authenticate(username, password)

def can_access_cli(username):
    return get_access_level(username) is not None

def create_profile_if_needed(username):
    """Creates a profile for system user if allowed, prevents duplicates."""
    if not system_user_exists(username):
        return False
    if get_access_level(username) is None:
        return False
    # Prevent web users from colliding with system users
    profile = load_profile(username)
    if not profile.get("display_name"):
        profile["display_name"] = username
        save_profile(username, profile)
    return True

def prevent_web_conflicts(username):
    """Block new web user creation if a system user of that name exists."""
    return not system_user_exists(username)

def cli_login(username, password):
    """Authenticates and creates profile if needed. Returns access level or None."""
    if pam_authenticate(username, password) and can_access_cli(username):
        create_profile_if_needed(username)
        return get_access_level(username)
    return None

def web_login(username, password):
    """For web login. Returns access level if valid; otherwise None."""
    if pam_authenticate(username, password):
        if not prevent_web_conflicts(username):
            # Prevent web user creation for system users
            return None
        # Here, handle non-system users via DB (omitted for brevity)
        return "web_user"
    return None
