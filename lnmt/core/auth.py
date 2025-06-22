# inetctl/core/auth.py

import pam
import pwd
import grp
import getpass

# Groups for access control
ADMIN_GROUP = "lnmtadm"
OPERATOR_GROUP = "lnmt"
VIEW_GROUP = "lnmtv"
ALLOWED_GROUPS = {ADMIN_GROUP, OPERATOR_GROUP, VIEW_GROUP}

def pam_authenticate(username, password):
    """Authenticate a user against system PAM."""
    p = pam.pam()
    return p.authenticate(username, password)

def user_exists(username):
    """Check if a username exists on the host system."""
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_user_groups(username):
    """Return a set of group names the user belongs to."""
    try:
        groups = {g.gr_name for g in grp.getgrall() if username in g.gr_mem}
        # Add primary group
        primary_gid = pwd.getpwnam(username).pw_gid
        groups.add(grp.getgrgid(primary_gid).gr_name)
        return groups
    except Exception:
        return set()

def is_authorized_user(username):
    """Return True if user is a member of an allowed group."""
    return not ALLOWED_GROUPS.isdisjoint(get_user_groups(username))

def require_cli_access():
    """CLI guard for group membership (use early in CLI scripts)."""
    username = getpass.getuser()
    if not is_authorized_user(username):
        raise PermissionError(f"User '{username}' lacks membership in {ALLOWED_GROUPS}. Access denied.")

# Example: Call require_cli_access() at the top of CLI scripts to enforce group policy.
