import os
import json
import pwd
import grp
from pathlib import Path

USER_PROFILE_DIR = Path("/etc/lnmt_user_profiles")
USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# Allowed groups for CLI/web access
ADMIN_GROUP = "lnmtadm"
OPERATOR_GROUP = "lnmt"
VIEW_GROUP = "lnmtv"
ALLOWED_GROUPS = [ADMIN_GROUP, OPERATOR_GROUP, VIEW_GROUP]

DEFAULT_THEME = "dark"
DEFAULT_NOTIFICATION = {
    "job_status": True,
    "timer_events": True,
    "admin": False
}
DEFAULT_PROFILE = {
    "theme": DEFAULT_THEME,
    "notifications": DEFAULT_NOTIFICATION,
    "email": "",
    "access_level": "view",
    "custom_theme": {},
}

def get_host_users():
    """Return a set of all usernames on the host."""
    return {u.pw_name for u in pwd.getpwall()}

def get_user_groups(username):
    """Return all groups a user belongs to."""
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        primary_group = grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name
        if primary_group not in user_groups:
            user_groups.append(primary_group)
        return set(user_groups)
    except Exception:
        return set()

def get_access_level(groups):
    """Determine LNMT access level from Unix groups."""
    if ADMIN_GROUP in groups:
        return "admin"
    if OPERATOR_GROUP in groups:
        return "operator"
    if VIEW_GROUP in groups:
        return "view"
    return None

def profile_path(username):
    return USER_PROFILE_DIR / f"{username}.json"

def load_user_profile(username):
    """Load profile, or auto-create if host user in group."""
    path = profile_path(username)
    # If file exists, load it
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    # If host user & in an allowed group, auto-create
    host_users = get_host_users()
    if username in host_users:
        groups = get_user_groups(username)
        access = get_access_level(groups)
        if access:
            profile = DEFAULT_PROFILE.copy()
            profile["access_level"] = access
            profile["theme"] = DEFAULT_THEME
            save_user_profile(username, profile)
            return profile
    raise FileNotFoundError(f"Profile for {username} not found.")

def save_user_profile(username, profile):
    """Save or update user profile (only if host user, or already exists)."""
    host_users = get_host_users()
    if username in host_users:
        # Only allow if user in allowed group
        access = get_access_level(get_user_groups(username))
        if not access:
            raise PermissionError("User not in allowed group.")
    path = profile_path(username)
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    return True

def is_manual_user_creation_allowed(username):
    """Prevent manual creation of user that matches a host user."""
    host_users = get_host_users()
    return username not in host_users

def list_profiles():
    return [f.stem for f in USER_PROFILE_DIR.glob("*.json")]

def validate_profile(profile):
    """Basic schema check, can be extended."""
    if "theme" not in profile:
        profile["theme"] = DEFAULT_THEME
    if "notifications" not in profile:
        profile["notifications"] = DEFAULT_NOTIFICATION
    if "access_level" not in profile:
        profile["access_level"] = "view"
    return profile

# --- Flask/PAM integration: Example utility (use with caution!) ---
def pam_authenticate(username, password):
    """Try to authenticate using PAM if available."""
    try:
        import pam
        return pam.pam().authenticate(username, password)
    except Exception:
        return False
