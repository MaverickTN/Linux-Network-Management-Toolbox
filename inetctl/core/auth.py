import os
import pwd
import grp

REQUIRED_GROUPS = {
    "lnmtadm": "admin",
    "lnmt": "operator",
    "lnmtv": "view"
}

def get_system_user(username):
    try:
        return pwd.getpwnam(username)
    except KeyError:
        return None

def get_user_groups(username):
    """Returns a set of group names the user belongs to."""
    user = get_system_user(username)
    if not user:
        return set()
    groups = {g.gr_name for g in grp.getgrall() if username in g.gr_mem}
    # Always add the primary group
    try:
        primary_group = grp.getgrgid(user.pw_gid).gr_name
        groups.add(primary_group)
    except Exception:
        pass
    return groups

def get_lnmt_role(username):
    """Returns admin/operator/view/None based on group membership."""
    user_groups = get_user_groups(username)
    for group, role in REQUIRED_GROUPS.items():
        if group in user_groups:
            return role
    return None

def can_run_cli(username):
    """Return True if user is allowed to run CLI commands (any role)."""
    return get_lnmt_role(username) in ("admin", "operator", "view")

def can_run_admin(username):
    """Return True if user is an admin."""
    return get_lnmt_role(username) == "admin"

def authenticate_with_pam(username, password):
    """PAM authentication using python-pam if available."""
    try:
        import pam
        p = pam.pam()
        return p.authenticate(username, password)
    except ImportError:
        # Fallback: always fail
        return False

def pam_available():
    try:
        import pam
        return True
    except ImportError:
        return False

def username_conflicts_with_system(username):
    """Prevents creation of web users that match a system user."""
    return get_system_user(username) is not None
