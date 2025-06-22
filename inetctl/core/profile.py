import json
import os
from pathlib import Path

PROFILE_DIR = Path("/etc/lnmt_profiles")  # Can be customized/configurable

def _profile_path(username):
    return PROFILE_DIR / f"{username}.json"

def get_user_profile(username):
    try:
        path = _profile_path(username)
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

def update_user_profile(username, updates):
    PROFILE_DIR.mkdir(exist_ok=True)
    path = _profile_path(username)
    profile = get_user_profile(username) or {"username": username}
    profile.update(updates)
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)

def auto_create_profile(username, default_theme="dark"):
    # Should be called at first login (if not present)
    if get_user_profile(username) is None:
        profile = {
            "username": username,
            "theme": default_theme,
            "email": "",
            "notify_events": [],
        }
        update_user_profile(username, profile)
        return True
    return False

def list_all_profiles():
    profiles = []
    if not PROFILE_DIR.exists():
        return profiles
    for file in PROFILE_DIR.glob("*.json"):
        try:
            with open(file) as f:
                profiles.append(json.load(f))
        except Exception:
            continue
    return profiles
