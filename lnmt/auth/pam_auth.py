# lnmt/auth/pam_auth.py

import pam
import grp
import pwd

ALLOWED_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]

def authenticate(username, password):
    p = pam.pam()
    if not p.authenticate(username, password):
        return False, "Invalid username or password"
    if not user_in_groups(username, ALLOWED_GROUPS):
        return False, f"User '{username}' is not in an allowed group ({', '.join(ALLOWED_GROUPS)})"
    return True, ""

def user_in_groups(username, allowed_groups):
    try:
        user = pwd.getpwnam(username)
        groups = [g.gr_name for g in grp.getgrall() if user.pw_name in g.gr_mem]
        gid_group = grp.getgrgid(user.pw_gid).gr_name
        groups.append(gid_group)
        return any(g in allowed_groups for g in groups)
    except Exception:
        return False
