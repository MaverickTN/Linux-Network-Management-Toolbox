# inetctl/auth.py

import os
import pwd
import grp
import getpass
import pam
import logging

LNMT_GROUPS = {
    "lnmtadm": "admin",
    "lnmt": "operator",
    "lnmtv": "view"
}

def user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def user_group(username):
    """Return lnmt group role for this user, or None if not in a valid group."""
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    try:
        primary = grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name
        if primary not in groups:
            groups.append(primary)
    except Exception:
        pass
    for group in LNMT_GROUPS:
        if group in groups:
            return LNMT_GROUPS[group]
    return None

def pam_authenticate(username, password):
    p = pam.pam()
    return p.authenticate(username, password)

def cli_authenticate(required_level="view", as_user=None):
    """
    Check the effective user/group.
    If as_user is given, only allow if current user is root.
    Returns (user, role) if allowed, else exits.
    """
    real_user = getpass.getuser()
    target_user = as_user or real_user

    if as_user and real_user != "root":
        print("ERROR: Only root can use --as-user override.")
        exit(1)

    if not user_exists(target_user):
        print(f"Access denied: user '{target_user}' does not exist.")
        exit(1)
    role = user_group(target_user)
    if not role:
        print(f"Access denied: '{target_user}' is not in lnmtadm, lnmt, or lnmtv group.")
        exit(1)
    allowed = {
        "admin": ["admin", "operator", "view"],
        "operator": ["operator", "view"],
        "view": ["view"]
    }
    # Map permission requirements
    perm_map = {
        "admin": 0,
        "operator": 1,
        "view": 2
    }
    if perm_map[role] > perm_map[required_level]:
        print(f"Access denied: '{target_user}' does not have required permission '{required_level}'.")
        exit(1)
    # Optional: log all root user-impersonation
    if as_user:
        logging.info(f"Root is running as {as_user} ({role}) for this CLI session.")
    return target_user, role
