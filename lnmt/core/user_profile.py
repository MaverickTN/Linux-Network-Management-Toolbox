# lnmt/core/user_profile.py

import json
from pathlib import Path
import hashlib

USER_PROFILE_PATH = Path("/etc/lnmt/user_profiles.json")

def _load_profiles():
    if USER_PROFILE_PATH.exists():
        with USER_PROFILE_PATH.open("r") as f:
            return json.load(f)
    return {}

def _save_profiles(data):
    USER_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with USER_PROFILE_PATH.open("w") as f:
        json.dump(data, f, indent=2)

def get_user_profile(username):
    profiles = _load_profiles()
    return profiles.get(username, {})

def update_user_profile(username, **kwargs):
    profiles = _load_profiles()
    profile = profiles.get(username, {})
    for k, v in kwargs.items():
        profile[k] = v
    profiles[username] = profile
    _save_profiles(profiles)

def _hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def validate_and_update_password(username, old, new):
    profiles = _load_profiles()
    profile = profiles.get(username)
    if not profile:
        return False, "User not found."
    if profile.get("password") and _hash_password(old) != profile["password"]:
        return False, "Current password incorrect."
    profile["password"] = _hash_password(new)
    profiles[username] = profile
    _save_profiles(profiles)
    return True, "Password changed successfully."
