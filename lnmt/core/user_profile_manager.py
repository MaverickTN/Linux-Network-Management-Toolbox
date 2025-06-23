import json
import os
from pathlib import Path
import pwd
import grp

PROFILE_DIR = "/var/lib/lnmt/user_profiles"
REQUIRED_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]

def ensure_profile_dir():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

def get_profile(username):
    ensure_profile_dir()
    profile_path = Path(PROFILE_DIR) / f"{username}.json"
    if profile_path.exists():
        with open(profile_path, "r") as f:
            return json.load(f)
    return None

def save_profile(username, data):
    ensure_profile_dir()
    profile_path = Path(PROFILE_DIR) / f"{username}.json"
    with open(profile_path, "w") as f:
        json.dump(data, f, indent=2)

def get_all_profiles():
    ensure_profile_dir()
    profiles = []
    for profile_file in Path(PROFILE_DIR).glob("*.json"):
        with open(profile_file, "r") as f:
            try:
                profiles.append(json.load(f))
            except Exception:
                continue
    return profiles

def is_valid_system_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_user_groups(username):
    """Return a list of group names for this user."""
    user_groups = []
    try:
        user = pwd.getpwnam(username)
        groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        primary_group = grp.getgrgid(user.pw_gid).gr_name
        user_groups.append(primary_group)
        user_groups.extend(groups)
    except Exception:
        pass
    return list(set(user_groups))

def is_authorized_cli_user(username):
    """Check if user is in one of the required groups for CLI use."""
    user_groups = get_user_groups(username)
    return any(g in user_groups for g in REQUIRED_GROUPS)

def auto_create_profile_for_system_user(username):
    if not is_valid_system_user(username):
        return None
    profile = get_profile(username)
    if profile:
        return profile
    # Default profile template
    new_profile = {
        "username": username,
        "theme": "dark",
        "email": "",
        "notification_settings": {
            "toast": True,
            "email": False,
            "notify_events": ["job_complete", "job_failed", "schedule_triggered"]
        },
        "groups": get_user_groups(username),
        "created_from_system": True
    }
    save_profile(username, new_profile)
    return new_profile

def prevent_conflicting_user_creation(new_username):
    """Prevent creation of a new user if system user of same name exists."""
    return not is_valid_system_user(new_username)
