import os
import json
import pwd
from pathlib import Path
from lnmt.theme import THEMES

PROFILE_DIR = Path("/etc/lnmt/users")  # Adjust as needed for permissions

DEFAULT_PROFILE = {
    "email": "",
    "notify_events": [],
    "theme": "dark",
    "custom_theme": {},
    "contact": {},
}

def get_profile_path(username):
    return PROFILE_DIR / f"{username}.json"

def ensure_profile(username):
    path = get_profile_path(username)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # System users get a default profile with their preferred theme
        profile = DEFAULT_PROFILE.copy()
        # Try to read their preferred shell (for CLI) or assign dark theme
        profile["theme"] = "dark"
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
    return path

def get_profile(username):
    path = get_profile_path(username)
    if not path.exists():
        ensure_profile(username)
    with open(path, "r") as f:
        return json.load(f)

def update_profile(username, updates):
    path = get_profile_path(username)
    if not path.exists():
        ensure_profile(username)
    profile = get_profile(username)
    profile.update(updates)
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    return profile

def get_user_theme(username):
    try:
        profile = get_profile(username)
        theme_key = profile.get("theme", "dark")
        return THEMES.get(theme_key, THEMES["dark"])
    except Exception:
        return THEMES["dark"]

def list_all_profiles():
    if not PROFILE_DIR.exists():
        return []
    return [p.stem for p in PROFILE_DIR.glob("*.json")]
