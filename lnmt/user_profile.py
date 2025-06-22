# inetctl/user_profile.py

import json
import os
from pathlib import Path

USER_PROFILE_DIR = Path.home() / ".lnmt_profiles"
USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def get_profile_path(username):
    return USER_PROFILE_DIR / f"{username}.json"

def load_user_profile(username):
    path = get_profile_path(username)
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_user_profile(username, profile):
    path = get_profile_path(username)
    try:
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
        return True
    except Exception:
        return False

def create_or_update_profile(username, group_list, email=None, theme="dark"):
    """Auto-creates or updates a user profile. Theme defaults to group-sensible theme."""
    profile = load_user_profile(username) or {}
    profile["username"] = username
    profile["groups"] = group_list
    if email:
        profile["email"] = email
    profile["theme"] = theme
    # Default notification preferences (can be extended)
    if "notifications" not in profile:
        profile["notifications"] = {
            "job_queue": True,
            "schedule": True,
            "system": True,
        }
    save_user_profile(username, profile)
    return profile

def get_notification_prefs(username):
    profile = load_user_profile(username)
    if profile:
        return profile.get("notifications", {})
    return {}

def set_notification_prefs(username, prefs):
    profile = load_user_profile(username) or {}
    profile["notifications"] = prefs
    save_user_profile(username, profile)

def update_theme(username, theme):
    profile = load_user_profile(username) or {}
    profile["theme"] = theme
    save_user_profile(username, profile)

def get_theme(username):
    profile = load_user_profile(username)
    if profile:
        return profile.get("theme", "dark")
    return "dark"
