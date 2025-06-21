# inetctl/core/user_profile.py

import os
import json
import pwd
import grp
from pathlib import Path
from inetctl.theme import THEMES

USER_PROFILE_DIR = Path("/etc/inetctl/users")
USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

LNMT_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]

def get_system_users():
    """Return a set of all local system usernames."""
    return set(p.pw_name for p in pwd.getpwall())

def get_system_group_members(group):
    try:
        return set(grp.getgrnam(group).gr_mem)
    except KeyError:
        return set()

def ensure_profile_dir():
    if not USER_PROFILE_DIR.exists():
        USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _profile_path(username):
    return USER_PROFILE_DIR / f"{username}.json"

def valid_theme(theme):
    return theme in THEMES

def _default_profile(username):
    # Pick theme by group: admin gets 'dark', operator 'oceanic', view 'light'
    sys_groups = user_groups(username)
    if "lnmtadm" in sys_groups:
        theme = "dark"
    elif "lnmt" in sys_groups:
        theme = "oceanic"
    else:
        theme = "light"
    return {
        "username": username,
        "email": "",
        "theme": theme,
        "notification_settings": {
            "job_complete": True,
            "job_failed": True,
            "login": False,
            "config_change": True,
        }
    }

def user_groups(username):
    """Return all group names for a system user."""
    try:
        groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        user_gid = pwd.getpwnam(username).pw_gid
        groups.append(grp.getgrgid(user_gid).gr_name)
        return set(groups)
    except Exception:
        return set()

def get_user_profile(username, create_if_missing=True):
    ensure_profile_dir()
    path = _profile_path(username)
    if path.exists():
        try:
            with path.open("r") as f:
                data = json.load(f)
            # Validate
            if not valid_theme(data.get("theme", "")):
                data["theme"] = "dark"
            if "notification_settings" not in data:
                data["notification_settings"] = _default_profile(username)["notification_settings"]
            return data
        except Exception:
            # Corrupted, try repair
            path.rename(str(path) + ".corrupt")
            data = _default_profile(username)
            with path.open("w") as f:
                json.dump(data, f, indent=2)
            return data
    elif create_if_missing:
        data = _default_profile(username)
        with path.open("w") as f:
            json.dump(data, f, indent=2)
        return data
    else:
        return None

def update_user_profile(username, updates):
    path = _profile_path(username)
    data = get_user_profile(username, create_if_missing=False)
    if not data:
        return {"success": False, "message": "Profile does not exist."}
    # Password update? Not stored here—should be routed to system/PAM.
    if "new_password" in updates:
        from inetctl.core.auth import update_system_password
        result = update_system_password(username, updates["new_password"])
        return {"success": result["success"], "message": result.get("message", "")}
    # General profile update
    data.update({k: v for k, v in updates.items() if k in data or k in ["theme", "email", "notification_settings"]})
    with path.open("w") as f:
        json.dump(data, f, indent=2)
    return {"success": True}

def get_theme_names():
    return {k: v["name"] for k, v in THEMES.items()}

def auto_create_profiles_for_group_users():
    sys_users = get_system_users()
    created = []
    for group in LNMT_GROUPS:
        for user in get_system_group_members(group):
            # Do not create profile for users who already have one.
            if _profile_path(user).exists():
                continue
            if user in sys_users:
                get_user_profile(user, create_if_missing=True)
                created.append(user)
    return created

def validate_all_profiles():
    """Scan all user profiles for corruption and attempt repair."""
    for file in USER_PROFILE_DIR.glob("*.json"):
        username = file.stem
        get_user_profile(username, create_if_missing=True)

def delete_user_profile(username):
    path = _profile_path(username)
    if path.exists():
        path.unlink()
        return True
    return False
