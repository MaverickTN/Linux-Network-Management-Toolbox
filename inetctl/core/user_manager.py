import os
import json
import hashlib
from pathlib import Path
import crypt
import pwd
import grp

USER_DATA_DIR = Path("/etc/inetctl/users")  # Adjust as needed (ensure secure permissions)
USER_PROFILE_FILENAME = "profile.json"
ALLOWED_GROUPS = {"lnmtadm", "lnmt", "lnmtv"}

def get_user_profile_path(username):
    return USER_DATA_DIR / username / USER_PROFILE_FILENAME

def user_exists_on_system(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_system_groups(username):
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    try:
        gid = pwd.getpwnam(username).pw_gid
        groups.append(grp.getgrgid(gid).gr_name)
    except Exception:
        pass
    return set(groups)

def ensure_user_profile(username):
    profile_path = get_user_profile_path(username)
    if not profile_path.parent.exists():
        profile_path.parent.mkdir(parents=True, exist_ok=True)
    if not profile_path.exists():
        profile = {
            "username": username,
            "theme": "dark",
            "notifications": [],
            "email": "",
            "custom_theme": {},
            "groups": list(get_system_groups(username)),
        }
        with open(profile_path, "w") as f:
            json.dump(profile, f)
    return profile_path

def get_user_profile(username):
    profile_path = ensure_user_profile(username)
    try:
        with open(profile_path, "r") as f:
            return json.load(f)
    except Exception:
        # Auto repair: if corrupted, recreate
        profile_path.unlink(missing_ok=True)
        return get_user_profile(username)

def update_user_profile(username, updates: dict):
    profile = get_user_profile(username)
    profile.update(updates)
    profile["groups"] = list(get_system_groups(username))
    with open(get_user_profile_path(username), "w") as f:
        json.dump(profile, f)

def set_user_theme(username, theme_key):
    update_user_profile(username, {"theme": theme_key})

def set_custom_theme(username, custom_theme: dict):
    update_user_profile(username, {"custom_theme": custom_theme})

def set_user_notifications(username, notifications):
    update_user_profile(username, {"notifications": notifications})

def set_user_email(username, email):
    update_user_profile(username, {"email": email})

def set_user_password(username, old_password, new_password):
    # For host-based users, use PAM or system methods (not implemented here)
    # For internal users, update the profile file (hashed)
    # Here we provide a stub; recommend using PAM via python-pam for real use
    if user_exists_on_system(username):
        # Reject change, or use PAM for real
        return {"success": False, "message": "Password changes for system users must be handled by the OS admin."}
    # For internal users (not in /etc/passwd): (hash password)
    profile = get_user_profile(username)
    if "password" in profile:
        hashed = hashlib.sha256(old_password.encode()).hexdigest()
        if profile["password"] != hashed:
            return {"success": False, "message": "Old password incorrect."}
    profile["password"] = hashlib.sha256(new_password.encode()).hexdigest()
    with open(get_user_profile_path(username), "w") as f:
        json.dump(profile, f)
    return {"success": True}

def authenticate_user(username, password):
    # Prefer PAM or host authentication for host users
    if user_exists_on_system(username):
        try:
            import pam
            p = pam.pam()
            if p.authenticate(username, password):
                return True
            else:
                return False
        except ImportError:
            return False
    # Internal users (profile-based)
    profile = get_user_profile(username)
    if "password" in profile:
        return profile["password"] == hashlib.sha256(password.encode()).hexdigest()
    return False

def create_internal_user(username, password, email=""):
    if user_exists_on_system(username):
        raise ValueError("Cannot create internal user that matches a system account.")
    if not username.isalnum():
        raise ValueError("Invalid username.")
    profile_path = get_user_profile_path(username)
    if profile_path.exists():
        raise ValueError("User already exists.")
    profile = {
        "username": username,
        "theme": "dark",
        "notifications": [],
        "email": email,
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "custom_theme": {},
        "groups": []
    }
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with open(profile_path, "w") as f:
        json.dump(profile, f)
    return True

def auto_provision_system_user(username):
    # On first login, auto-create user profile for host user
    if not user_exists_on_system(username):
        return False
    ensure_user_profile(username)
    return True

def set_user_groups(username):
    update_user_profile(username, {"groups": list(get_system_groups(username))})

def is_authorized_for_cli(username):
    groups = get_system_groups(username)
    return bool(ALLOWED_GROUPS & groups)

def get_theme_for_user(username):
    profile = get_user_profile(username)
    theme = profile.get("theme", "dark")
    if theme == "custom" and "custom_theme" in profile:
        return profile["custom_theme"]
    return theme
