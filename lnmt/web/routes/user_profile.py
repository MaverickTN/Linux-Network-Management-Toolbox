import os
import pwd
import grp
import json
from pathlib import Path
from typing import Dict, Any

USER_PROFILES_PATH = Path("/etc/lnmt/user_profiles.json")
REQUIRED_GROUPS = {"lnmtadm", "lnmt", "lnmtv"}
DEFAULT_THEME = "dark"
DEFAULT_NOTIFICATIONS = ["critical", "warning", "status"]

def _load_profiles() -> Dict[str, Any]:
    if USER_PROFILES_PATH.exists():
        try:
            with open(USER_PROFILES_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_profiles(profiles: Dict[str, Any]):
    USER_PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)

def get_system_users() -> set:
    return {u.pw_name for u in pwd.getpwall()}

def get_user_groups(user: str) -> set:
    """Return all group names for the user, including primary and supplementary."""
    try:
        user_pw = pwd.getpwnam(user)
        groups = {grp.getgrgid(user_pw.pw_gid).gr_name}
        groups.update(g.gr_name for g in grp.getgrall() if user in g.gr_mem)
        return groups
    except Exception:
        return set()

def is_cli_allowed(user: str) -> bool:
    """Check if user is a member of one of the required groups."""
    return bool(get_user_groups(user) & REQUIRED_GROUPS)

def profile_exists(user: str) -> bool:
    profiles = _load_profiles()
    return user in profiles

def create_profile_for_system_user(user: str):
    """Auto-create profile for a new system user in required group if not present."""
    profiles = _load_profiles()
    if user not in profiles and user in get_system_users() and is_cli_allowed(user):
        profiles[user] = {
            "theme": DEFAULT_THEME,
            "notifications": DEFAULT_NOTIFICATIONS.copy(),
            "email": "",
            "created_from_system": True
        }
        _save_profiles(profiles)

def get_profile(user: str) -> Dict[str, Any]:
    """Return the user profile or create if system user in required group."""
    profiles = _load_profiles()
    if user not in profiles and user in get_system_users() and is_cli_allowed(user):
        create_profile_for_system_user(user)
        profiles = _load_profiles()
    return profiles.get(user)

def set_profile(user: str, data: dict):
    """Update user profile (but cannot create new for system users in a way that shadows them)."""
    profiles = _load_profiles()
    if user in get_system_users() and not profiles.get(user, {}).get("created_from_system"):
        raise Exception("Cannot create web-only user matching a system user.")
    profiles[user] = data
    _save_profiles(profiles)

def all_profiles() -> Dict[str, Any]:
    return _load_profiles()

def get_user_theme(user: str) -> str:
    profile = get_profile(user)
    return (profile or {}).get("theme", DEFAULT_THEME)

def get_user_notifications(user: str) -> list:
    profile = get_profile(user)
    return (profile or {}).get("notifications", DEFAULT_NOTIFICATIONS.copy())

def can_create_web_user(username: str) -> bool:
    """Don't allow creating web users that match system users."""
    return username not in get_system_users()

def get_email(user: str) -> str:
    profile = get_profile(user)
    return (profile or {}).get("email", "")

# Example for CLI scripts:
def get_cli_theme_for_user(user: str) -> str:
    # If not allowed, always return default
    return get_user_theme(user) if is_cli_allowed(user) else DEFAULT_THEME

def ensure_all_system_users_have_profiles():
    """Idempotent: ensures all current system users in proper groups have profiles."""
    sys_users = get_system_users()
    for user in sys_users:
        if is_cli_allowed(user):
            create_profile_for_system_user(user)
