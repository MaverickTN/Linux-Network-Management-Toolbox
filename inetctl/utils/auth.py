import grp
import getpass
import os
import pwd

# Required groups
ADMIN_GROUP = "lnmtadm"
OPERATOR_GROUP = "lnmt"
VIEWER_GROUP = "lnmtv"
ALLOWED_GROUPS = [ADMIN_GROUP, OPERATOR_GROUP, VIEWER_GROUP]

def get_user_groups(user=None):
    """Return all UNIX groups a user belongs to."""
    if user is None:
        user = getpass.getuser()
    groups = []
    user_pw = pwd.getpwnam(user)
    groups.append(grp.getgrgid(user_pw.pw_gid).gr_name)  # Primary group
    for g in grp.getgrall():
        if user in g.gr_mem and g.gr_name not in groups:
            groups.append(g.gr_name)
    return groups

def allowed_cli_access(user=None):
    """Check if a user can access the CLI (is in required group)."""
    groups = get_user_groups(user)
    return any(g in ALLOWED_GROUPS for g in groups)

def get_cli_role(user=None):
    """Get CLI role (admin/operator/viewer) based on group membership."""
    groups = get_user_groups(user)
    if ADMIN_GROUP in groups:
        return "admin"
    elif OPERATOR_GROUP in groups:
        return "operator"
    elif VIEWER_GROUP in groups:
        return "viewer"
    return None

def is_system_user(user):
    """Check if a user exists on the host system."""
    try:
        pwd.getpwnam(user)
        return True
    except KeyError:
        return False
