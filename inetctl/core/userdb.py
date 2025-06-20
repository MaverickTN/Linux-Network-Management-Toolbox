import os
import pwd
import grp
import json
from pathlib import Path
from inetctl.utils.auth import user_role, get_user_theme

USER_PROFILE_DIR = Path("/var/lib/inetctl/user_profiles")  # or your preferred directory

# Ensure profile dir exists
USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE = {
    "username": None,
    "full_name": "",
    "email": "",
    "groups": [],
    "role": "viewer",   # admin, operator, viewer
    "theme": "dark",
    "notification_prefs": {
        "toast": True,
        "email": False,
        "critical_only": False,
    }
}

def get_profile_path(username):
    return USER_PROFILE_DIR / f"{username}.json"

def host_user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_user_groups(username):
    user_groups = []
    all_groups = grp.getgrall()
    for g in all_groups:
        if username in g.gr_mem or (g.gr_gid == pwd.getpwnam(username).pw_gid):
            user_groups.append(g.gr_name)
    return user_groups

def auto_create_user_profile(username):
    """
    Create a profile for a host user who has not previously logged in.
    Assigns role based on group membership (lnmtadm/lnmt/lnmtv).
    """
    if not host_user_exists(username):
        raise ValueError(f"User {username} does not exist on the host system.")
    profile_path = get_profile_path(username)
    if profile_path.exists():
        return  # Already exists
    groups = get_user_groups(username)
    role = user_role(username)
    profile = DEFAULT_PROFILE.copy()
    profile.update({
        "username": username,
        "full_name": pwd.getpwnam(username).pw_gecos.split(",")[0],
        "groups": groups,
        "role": role or "viewer",
        "theme": get_user_theme(username),
    })
    with profile_path.open("w") as f:
        json.dump(profile, f, indent=2)
    return profile

def get_user_profile(username):
    """
    Loads a user profile if it exists; auto-creates if a host user in a required group logs in.
    """
    profile_path = get_profile_path(username)
    if not profile_path.exists():
        if host_user_exists(username) and user_role(username):
            return auto_create_user_profile(username)
        else:
            raise FileNotFoundError(f"Profile for {username} not found and not eligible for auto-creation.")
    with profile_path.open("r") as f:
        profile = json.load(f)
    return profile

def update_user_profile(username, updates: dict):
    profile = get_user_profile(username)
    profile.update(updates)
    with get_profile_path(username).open("w") as f:
        json.dump(profile, f, indent=2)
    return profile

def all_profiles():
    """ List all user profiles. """
    return [json.load(p.open()) for p in USER_PROFILE_DIR.glob("*.json")]
