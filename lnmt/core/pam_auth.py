import pam
import grp
import pwd

# Define LNMT groups
ADMIN_GROUP = "lnmtadm"
OPERATOR_GROUP = "lnmt"
VIEW_GROUP = "lnmtv"

def pam_authenticate(username, password):
    """Authenticate user against system using PAM."""
    p = pam.pam()
    return p.authenticate(username, password)

def is_lnmt_user(username):
    """Check if user is a member of any LNMT access group."""
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        # Primary group
        primary_gid = pwd.getpwnam(username).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        user_groups.append(primary_group)
        return any(g in [ADMIN_GROUP, OPERATOR_GROUP, VIEW_GROUP] for g in user_groups)
    except Exception:
        return False

def get_user_role(username):
    """Return LNMT access level: admin, operator, or view, or None."""
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        primary_gid = pwd.getpwnam(username).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        user_groups.append(primary_group)
        if ADMIN_GROUP in user_groups:
            return "admin"
        elif OPERATOR_GROUP in user_groups:
            return "operator"
        elif VIEW_GROUP in user_groups:
            return "view"
        else:
            return None
    except Exception:
        return None
