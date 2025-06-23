import grp
import getpass
import os

LNMT_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]

def user_in_group(user=None, group=None):
    user = user or getpass.getuser()
    group_info = grp.getgrnam(group)
    return user in group_info.gr_mem

def get_cli_user_role():
    user = getpass.getuser()
    if user == "root":
        return "lnmtadm"
    for group in LNMT_GROUPS:
        if user_in_group(user, group):
            return group
    return None

def require_cli_access():
    role = get_cli_user_role()
    if not role:
        print("Access denied: You must be a member of lnmtadm, lnmt, or lnmtv group.")
        exit(1)
    return role
