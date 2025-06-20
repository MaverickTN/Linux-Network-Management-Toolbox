import json
import os
import grp
import pwd

USER_PROFILE_DIR = "/etc/lnmt/user_profiles"

REQUIRED_GROUPS = ["lnmtadm", "lnmt", "lnmtv"]  # Set in one place

DEFAULT_PROFILE = {
    "theme": "dark",
    "email": "",
    "notify": [],
    "contact": "",
    "profile_created": True,
    "cli_style": "default"
}

def get_required_groups():
    return REQUIRED_GROUPS

def get_profile_path(username):
    return os.path.join(USER_PROFILE_DIR, f"{username}.json")

def load_profile(username):
    path = get_profile_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def save_profile(profile, username):
    os.makedirs(USER_PROFILE_DIR, exist_ok=True)
    with open(get_profile_path(username), "w") as f:
        json.dump(profile, f, indent=2)

def user_in_required_group(username):
    for group in REQUIRED_GROUPS:
        try:
            if username in grp.getgrnam(group).gr_mem:
                return True
        except KeyError:
            continue
    return False

def create_default_profile(username):
    # Set theme by group, e.g. admin gets "dark", view-only gets "light"
    try:
        groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        if "lnmtadm" in groups:
            DEFAULT_PROFILE["theme"] = "dark"
            DEFAULT_PROFILE["cli_style"] = "admin"
        elif "lnmt" in groups:
            DEFAULT_PROFILE["theme"] = "nord"
            DEFAULT_PROFILE["cli_style"] = "operator"
        elif "lnmtv" in groups:
            DEFAULT_PROFILE["theme"] = "light"
            DEFAULT_PROFILE["cli_style"] = "viewer"
    except Exception:
        pass
    save_profile(DEFAULT_PROFILE, username)
    return DEFAULT_PROFILE

def list_profiles():
    if not os.path.exists(USER_PROFILE_DIR):
        return []
    return [f[:-5] for f in os.listdir(USER_PROFILE_DIR) if f.endswith(".json")]

def get_system_users():
    return [u.pw_name for u in pwd.getpwall()]

def user_exists_on_system(username):
    return username in get_system_users()

def is_profile_editable_by(username, editor):
    # Only self or admin can edit
    return username == editor or user_in_required_group(editor)

def prevent_local_duplicate(username):
    """Prevent registering a web user if system user exists."""
    return not user_exists_on_system(username)
