# inetctl/core/user.py

import os
import pwd
import grp
from pathlib import Path
from inetctl.theme import get_theme

LNMT_GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "view": "lnmtv"
}

USER_PROFILE_DIR = Path("/etc/lnmt_users")

def get_system_users():
    return [u.pw_name for u in pwd.getpwall() if u.pw_uid >= 1000 and "nologin" not in u.pw_shell]

def get_user_groups(username):
    """Return a list of groups the user is a member of."""
    groups = []
    for g in grp.getgrall():
        if username in g.gr_mem or (g.gr_gid == pwd.getpwnam(username).pw_gid):
            groups.append(g.gr_name)
    return groups

def has_cli_access(username):
    """Returns the highest privilege group the user is in, or None."""
    groups = set(get_user_groups(username))
    if LNMT_GROUPS["admin"] in groups:
        return "admin"
    if LNMT_GROUPS["operator"] in groups:
        return "operator"
    if LNMT_GROUPS["view"] in groups:
        return "view"
    return None

def ensure_profile(username):
    """
    Ensures a user profile file exists for the given username.
    If not, auto-create from template with the user's default theme.
    """
    profile_file = USER_PROFILE_DIR / f"{username}.json"
    if not profile_file.exists():
        USER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        theme_key = "dark"  # could be auto-chosen based on shell env or time of day
        profile_data = {
            "username": username,
            "theme": theme_key,
            "email": "",
            "notify_events": ["system", "security"],
            "cli_color": theme_key,
            "created_from_system": True
        }
        profile_file.write_text(json.dumps(profile_data, indent=2))
    return profile_file

def get_user_theme(username):
    """Returns the preferred theme key for a given user, fallback to dark."""
    profile_file = USER_PROFILE_DIR / f"{username}.json"
    if profile_file.exists():
        import json
        profile = json.loads(profile_file.read_text())
        return profile.get("theme", "dark")
    return "dark"

def can_create_profile(username):
    """Prevents creation of a profile if the user already exists on the host."""
    return username not in get_system_users()

def is_valid_user(username):
    """Checks if username exists on system and is in an LNMT group."""
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    return has_cli_access(username) is not None

def pam_authenticate(username, password):
    """
    Authenticate via PAM.
    (NOTE: Needs python-pam module and running as root or with sufficient privileges.)
    """
    try:
        import pam
        p = pam.pam()
        return p.authenticate(username, password)
    except ImportError:
        raise Exception("python-pam is not installed.")
    except Exception as e:
        return False

def get_user_profile(username):
    """Loads user profile JSON, creating if necessary."""
    ensure_profile(username)
    profile_file = USER_PROFILE_DIR / f"{username}.json"
    import json
    return json.loads(profile_file.read_text())

def update_user_profile(username, **kwargs):
    """Update user profile JSON with new fields."""
    profile = get_user_profile(username)
    profile.update(kwargs)
    profile_file = USER_PROFILE_DIR / f"{username}.json"
    import json
    profile_file.write_text(json.dumps(profile, indent=2))
    return profile

