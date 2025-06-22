import getpass
import grp
import os
import pwd

REQUIRED_GROUPS = {
    "lnmtadm": "admin",
    "lnmt": "operator",
    "lnmtv": "view"
}

def get_user_role(username=None):
    if not username:
        username = getpass.getuser()
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        # Also check primary group
        user_gid = pwd.getpwnam(username).pw_gid
        user_groups.append(grp.getgrgid(user_gid).gr_name)
        for group, role in REQUIRED_GROUPS.items():
            if group in user_groups:
                return role
        return None
    except Exception:
        return None

def user_is_allowed_cli(username=None):
    return get_user_role(username) is not None

def get_user_cli_theme(username=None):
    # Example: Look for ~/.inetctl_theme or fallback to dark
    username = username or getpass.getuser()
    home = os.path.expanduser(f"~{username}")
    theme_file = os.path.join(home, ".inetctl_theme")
    if os.path.exists(theme_file):
        with open(theme_file, "r") as f:
            theme = f.read().strip()
            return theme
    return "dark"

def ensure_cli_access():
    username = getpass.getuser()
    if not user_is_allowed_cli(username):
        print("Access denied: You must be a member of lnmtadm, lnmt, or lnmtv to use the CLI.")
        exit(2)

def get_all_system_users():
    return [u.pw_name for u in pwd.getpwall() if u.pw_uid >= 1000 and "nologin" not in u.pw_shell]
