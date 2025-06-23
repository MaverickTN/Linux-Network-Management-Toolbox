# lnmt/core/user_manager.py

import os
import pwd
import grp
import json
from pathlib import Path

LNMT_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]
PROFILE_DIR = Path("/etc/lnmt/user_profiles")

def user_exists_on_host(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def user_group_memberships(username):
    # Returns a set of all UNIX groups for the user
    groups = set()
    try:
        pw = pwd.getpwnam(username)
        # primary group
        groups.add(grp.getgrgid(pw.pw_gid).gr_name)
        # supplementary groups
        for g in grp.getgrall():
            if username in g.gr_mem:
                groups.add(g.gr_name)
    except Exception:
        pass
    return groups

def user_can_access_cli(username):
    # Must be in one of the LNMT groups
    groups = user_group_memberships(username)
    return any(g in groups for g in LNMT_GROUPS)

def user_access_level(username):
    # Returns 'admin', 'operator', or 'viewer', or None if not permitted
    groups = user_group_memberships(username)
    if "lnmtadm" in groups:
        return "admin"
    elif "lnmt" in groups:
        return "operator"
    elif "lnmtv" in groups:
        return "viewer"
    else:
        return None

def get_profile_path(username):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILE_DIR / f"{username}.json"

def get_user_profile(username):
    p = get_profile_path(username)
    if p.exists():
        try:
            with open(p, "r") as f:
                return json.load(f)
        except Exception:
            # Corrupted profile, backup and create default
            p.rename(str(p) + ".corrupt")
    # Create a default profile if not found or corrupt
    default = default_profile(username)
    save_user_profile(username, default)
    return default

def save_user_profile(username, profile):
    p = get_profile_path(username)
    with open(p, "w") as f:
        json.dump(profile, f, indent=2)

def check_or_create_auto_profile(username):
    """Creates a default profile for a valid system user if not present."""
    p = get_profile_path(username)
    if not p.exists():
        profile = default_profile(username)
        save_user_profile(username, profile)

def default_profile(username):
    return {
        "username": username,
        "email": "",
        "access": user_access_level(username),
        "theme": "dark",
        "notify": {
            "on_login": True,
            "on_schedule": True,
            "on_job_event": True,
        },
        "custom_theme": {},
        "contact_methods": []
    }

def can_create_web_user(username):
    # Prevent creating web users that shadow UNIX users
    return not user_exists_on_host(username)
