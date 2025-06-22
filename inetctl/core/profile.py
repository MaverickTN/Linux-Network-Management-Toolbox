import json
import os
from pathlib import Path
import pwd
import grp

PROFILE_DIR = Path("/etc/inetctl/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "viewer": "lnmtv"
}

DEFAULT_PROFILE = {
    "email": "",
    "theme": "dark",
    "notify_events": [],
    "role": "viewer"
}

def get_user_role(username):
    # Determine role by group membership
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        for role, group in GROUPS.items():
            if group in user_groups or group in [g.gr_name for g in grp.getgrall() if g.gr_gid == pwd.getpwnam(username).pw_gid]:
                return role
        return "none"
    except Exception:
        return "none"

def profile_path(username):
    return PROFILE_DIR / f"{username}.json"

def get_user_profile(username):
    p = profile_path(username)
    if p.exists():
        with p.open() as f:
            data = json.load(f)
            # auto-upgrade profile with new fields
            for k, v in DEFAULT_PROFILE.items():
                if k not in data:
                    data[k] = v
            return data
    return None

def update_user_profile(username, updates: dict):
    profile = get_user_profile(username) or DEFAULT_PROFILE.copy()
    profile.update(updates)
    with profile_path(username).open("w") as f:
        json.dump(profile, f, indent=2)

def auto_create_profile(username):
    p = profile_path(username)
    if not p.exists():
        # Only create if user exists on host and is in proper group
        try:
            pwd.getpwnam(username)
            role = get_user_role(username)
            if role == "none":
                return None
            data = DEFAULT_PROFILE.copy()
            data["role"] = role
            with p.open("w") as f:
                json.dump(data, f, indent=2)
            return data
        except KeyError:
            # User not found on host
            return None
    return get_user_profile(username)

def list_all_profiles():
    profiles = []
    for file in PROFILE_DIR.glob("*.json"):
        with file.open() as f:
            profiles.append(json.load(f))
    return profiles

def prevent_host_user_conflict(new_username):
    # No web-only user may match a host user
    try:
        pwd.getpwnam(new_username)
        return False
    except KeyError:
        return True
