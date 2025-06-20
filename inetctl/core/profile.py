import json
from pathlib import Path
import pwd
import grp

PROFILE_DIR = Path("/etc/lnmt/profiles")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _profile_path(username):
    return PROFILE_DIR / f"{username}.json"

def list_user_profiles():
    return [p.stem for p in PROFILE_DIR.glob("*.json")]

def user_profile_exists(username):
    return _profile_path(username).exists()

def get_user_profile(username):
    path = _profile_path(username)
    if not path.exists():
        raise FileNotFoundError(f"No profile for user {username}")
    with open(path) as f:
        return json.load(f)

def create_user_profile(username, access_level="viewer", email="", display_name="", theme="dark"):
    profile = {
        "username": username,
        "display_name": display_name or username,
        "email": email,
        "theme": theme,
        "access_level": access_level,
        "notifications": {
            "network_events": True,
            "config_changes": True,
            "security_alerts": True,
            "schedule_reminders": True,
        }
    }
    save_user_profile(username, profile)

def save_user_profile(username, data):
    path = _profile_path(username)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def update_user_profile(username, updates: dict):
    profile = get_user_profile(username)
    profile.update(updates)
    save_user_profile(username, profile)

def remove_user_profile(username):
    path = _profile_path(username)
    if path.exists():
        path.unlink()

def ensure_host_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def get_access_level(username):
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    try:
        primary_gid = pwd.getpwnam(username).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        if primary_group not in groups:
            groups.append(primary_group)
    except Exception:
        pass
    for level, group in (("admin", "lnmtadm"), ("operator", "lnmt"), ("viewer", "lnmtv")):
        if group in groups:
            return level
    return None

def auto_generate_profiles():
    created = 0
    for group, level in [("lnmtadm", "admin"), ("lnmt", "operator"), ("lnmtv", "viewer")]:
        try:
            members = grp.getgrnam(group).gr_mem
            for u in members:
                if not user_profile_exists(u):
                    create_user_profile(u, access_level=level)
                    created += 1
        except KeyError:
            continue
    return created
