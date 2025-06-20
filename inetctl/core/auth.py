import pam
import getpass
import os
from functools import wraps
from inetctl.core.user_profile import (
    load_user_profile,
    get_access_level,
    user_exists_on_host,
    block_creation_of_existing_host_user,
    save_user_profile,
    update_user_profile,
    list_profiles,
)

# Required system groups
GROUPS = {
    "admin": "lnmtadm",
    "operator": "lnmt",
    "view": "lnmtv"
}

def pam_authenticate(username, password):
    """Authenticate a system user via PAM."""
    p = pam.pam()
    if p.authenticate(username, password):
        return True
    return False

def get_logged_in_user():
    """Get the username of the currently logged-in user for CLI."""
    try:
        return os.getlogin()
    except Exception:
        return getpass.getuser()

def login_and_profile(username=None, password=None):
    """Authenticate via PAM and load or create the user profile."""
    if username is None:
        username = input("Username: ")
    if password is None:
        password = getpass.getpass("Password: ")
    if not user_exists_on_host(username):
        print("User does not exist on this system.")
        return None
    if not pam_authenticate(username, password):
        print("Invalid credentials.")
        return None
    # Load or create profile (auto-assigned by group)
    try:
        profile = load_user_profile(username)
    except PermissionError:
        print("Access denied. Not a member of any allowed group.")
        return None
    return profile

def check_access(username, required="view"):
    """
    Check if user has at least the required access level.
    required: "view" < "operator" < "admin"
    """
    order = ["none", "view", "operator", "admin"]
    actual = get_access_level(username)
    return order.index(actual) >= order.index(required)

def require_access(required="view"):
    """Decorator for CLI or web functions to enforce access control."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = get_logged_in_user()
            if not check_access(username, required):
                print(f"Access denied. '{required}' access required.")
                return
            return func(*args, **kwargs)
        return wrapper
    return decorator

# --- For web: use with Flask or Starlette authentication middleware ---

def web_user_loader(session):
    """Get user from session (Flask or Starlette-style)."""
    username = session.get("user")
    if not username:
        return None
    try:
        profile = load_user_profile(username)
        return profile
    except Exception:
        return None

def web_login(username, password, session):
    if not user_exists_on_host(username):
        return False, "User does not exist on this system."
    if not pam_authenticate(username, password):
        return False, "Invalid credentials."
    try:
        profile = load_user_profile(username)
        session["user"] = username
        session["theme"] = profile.get("theme", "dark")
        session["access_level"] = profile.get("access_level", "view")
        return True, "Login successful"
    except PermissionError:
        return False, "Access denied. Not a member of allowed group."

def web_logout(session):
    session.clear()
    return True

# -- CLI helper for enforcing group membership (used at command entry) --
def cli_enforce_access(required="view"):
    username = get_logged_in_user()
    if not check_access(username, required):
        print(f"Access denied: You must be in group '{GROUPS[required]}' or higher to use this command.")
        exit(1)

# --- Extendable: MFA, password update, registration stubs (not yet implemented) ---

def change_password(username, old_password, new_password):
    """
    Change the system user's password (requires root or proper PAM config).
    Not enabled by default. Needs further PAM or shadow integration.
    """
    # Not implemented for security; OS password changes are better done by 'passwd'
    raise NotImplementedError("Password change not supported via this method.")

def enable_mfa(username):
    """
    Stub for future MFA integration.
    """
    # Not yet implemented
    return False

# -- For completeness, web registration stub (blocks if user exists) --
def web_register(username, password):
    if block_creation_of_existing_host_user(username):
        return False, "Cannot create user: System user already exists."
    # Would add new user to system here; not implemented for security
    return False, "Registration for new system users is not enabled."

