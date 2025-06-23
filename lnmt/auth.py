# lnmt/auth.py

import os
import pwd
import grp
import pam
from functools import wraps
from flask import session, redirect, url_for, flash, g

from lnmt.theme import get_cli_theme_for_group

LNMT_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "view": "lnmtv",
}

def user_in_group(user, group):
    try:
        groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
        # Also check primary group
        user_entry = pwd.getpwnam(user)
        groups.append(grp.getgrgid(user_entry.pw_gid).gr_name)
        return group in groups
    except KeyError:
        return False

def get_user_groups(user):
    try:
        groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
        user_entry = pwd.getpwnam(user)
        groups.append(grp.getgrgid(user_entry.pw_gid).gr_name)
        return set(groups)
    except KeyError:
        return set()

def pam_authenticate(username, password):
    """Authenticate user via PAM (Pluggable Authentication Modules)."""
    pam_auth = pam.pam()
    return pam_auth.authenticate(username, password)

def auto_create_profile(username):
    """Create a profile if the username matches a host user in a valid group."""
    try:
        pwd.getpwnam(username)
    except KeyError:
        # Not a real system user
        return False
    groups = get_user_groups(username)
    for group in LNMT_GROUPS.values():
        if group in groups:
            # Create a profile if not exists (simplified logic, e.g. in db or file)
            # Here, just use session for example
            session['user'] = {
                "username": username,
                "groups": list(groups),
                "theme": get_cli_theme_for_group(groups),
            }
            return True
    return False

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            flash("Login required.", "danger")
            return redirect(url_for('login'))
        g.user = session["user"]
        return view(*args, **kwargs)
    return wrapped_view

def cli_user_allowed():
    """Return (is_allowed, user, group_set, theme) for CLI context."""
    try:
        user = pwd.getpwuid(os.getuid()).pw_name
        groups = get_user_groups(user)
        # Must be in an allowed group
        allowed = any(g in groups for g in LNMT_GROUPS.values())
        theme = get_cli_theme_for_group(groups)
        return allowed, user, groups, theme
    except Exception:
        return False, None, set(), "dark"

def prevent_web_creation_of_host_users(username):
    """Prevent creation of new web users that match system usernames."""
    try:
        pwd.getpwnam(username)
        return False  # User exists on host, prevent creation
    except KeyError:
        return True

# Optionally, more utility functions for SSO, MFA, etc. can be added here.
