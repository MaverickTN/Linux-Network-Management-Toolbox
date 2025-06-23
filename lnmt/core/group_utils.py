import grp
import pwd

REQUIRED_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "view": "lnmtv"
}

def get_user_groups(username):
    groups = []
    try:
        user_pw = pwd.getpwnam(username)
        for g in grp.getgrall():
            if username in g.gr_mem or g.gr_gid == user_pw.pw_gid:
                groups.append(g.gr_name)
    except Exception:
        pass
    return groups

def user_in_required_group(username):
    """Return which (if any) required group user is in, or None."""
    user_groups = get_user_groups(username)
    for role, group in REQUIRED_GROUPS.items():
        if group in user_groups:
            return role
    return None
