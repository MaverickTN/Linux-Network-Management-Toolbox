import os
import pwd
import grp
import getpass
import pam
from pathlib import Path
import json

PROFILE_DIR = Path("/etc/lnmt/profiles/")
REQUIRED_GROUPS = {
    'admin': 'lnmtadm',
    'operator': 'lnmt',
    'viewer': 'lnmtv'
}

DEFAULT_PROFILE = {
    "username": "",
    "email": "",
    "theme": "dark",
    "access_level": "viewer",  # admin, operator, viewer
    "contact_methods": [],
    "notify": {
        "on_login": True,
        "on_schedule": True,
        "on_job_event": True
    }
}

def is_system_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_access_level(username):
    """Return one of admin, operator, viewer, or None if no access."""
    for level, group in REQUIRED_GROUPS.items():
        try:
            if username in grp.getgrnam(group).gr_mem or pwd.getpwnam(username).pw_gid == grp.getgrnam(group).gr_gid:
                return level
        except KeyError:
            continue
    return None

def load_profile(username):
    profile_path = PROFILE_DIR / f"{username}.json"
    if not profile_path.exists():
        return None
    try:
        with profile_path.open("r") as f:
            return json.load(f)
    except Exception:
        return None

def save_profile(profile):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    username = profile["username"]
    with (PROFILE_DIR / f"{username}.json").open("w") as f:
        json.dump(profile, f, indent=2)

def auto_provision_profile(username):
    """Auto-create a profile for system users in required groups, skip otherwise."""
    if not is_system_user(username):
        return None
    access_level = get_access_level(username)
    if not access_level:
        return None
    prof = DEFAULT_PROFILE.copy()
    prof["username"] = username
    prof["access_level"] = access_level
    prof["theme"] = "dark"
    prof["email"] = ""
    prof["contact_methods"] = []
    prof["notify"] = DEFAULT_PROFILE["notify"].copy()
    save_profile(prof)
    return prof

def pam_authenticate(username, password):
    p = pam.pam()
    return p.authenticate(username, password)

def user_exists_on_host(username):
    return is_system_user(username)

def prevent_duplicate_profile_creation(username):
    """Do not allow creating a profile if user exists on host but is not in allowed group."""
    if is_system_user(username) and not get_access_level(username):
        return False
    return True

def get_user_theme(username):
    prof = load_profile(username)
    return prof.get("theme", "dark") if prof else "dark"

def get_all_profiles():
    if not PROFILE_DIR.exists():
        return []
    profiles = []
    for f in PROFILE_DIR.glob("*.json"):
        try:
            with f.open("r") as file:
                profiles.append(json.load(file))
        except Exception:
            continue
    return profiles

def update_profile(username, updates):
    prof = load_profile(username)
    if not prof:
        return None
    prof.update(updates)
    save_profile(prof)
    return prof

def is_cli_allowed():
    """Allow CLI only for lnmtadm, lnmt, lnmtv group members."""
    username = getpass.getuser()
    return get_access_level(username) is not None

def get_cli_theme():
    username = getpass.getuser()
    return get_user_theme(username)

def ensure_profile_for_system_users():
    """Auto-provision profiles for all system users in allowed groups."""
    for group in REQUIRED_GROUPS.values():
        try:
            for user in grp.getgrnam(group).gr_mem:
                if not load_profile(user):
                    auto_provision_profile(user)
        except KeyError:
            continue

# Call this at app startup to pre-create missing profiles:
ensure_profile_for_system_users()
