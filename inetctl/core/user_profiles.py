import json
from pathlib import Path

PROFILE_PATH = Path.home() / ".lnmt_profiles.json"
DEFAULT_PROFILE = {
    "theme": "dark",
    "email": "",
    "notifications": []
}

def _load_all_profiles():
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_all_profiles(data):
    try:
        with open(PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def get_user_profile(username):
    profiles = _load_all_profiles()
    return profiles.get(username, DEFAULT_PROFILE.copy())

def save_user_profile(username, profile):
    profiles = _load_all_profiles()
    profiles[username] = profile
    _save_all_profiles(profiles)

def user_profiles():
    return _load_all_profiles()

def current_user():
    import getpass
    return getpass.getuser()
