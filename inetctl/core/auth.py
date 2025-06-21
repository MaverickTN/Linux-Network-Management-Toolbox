# inetctl/core/auth.py

import pam
import getpass
from inetctl.core.user_manager import (
    user_can_access_cli,
    get_user_profile,
    create_user_profile,
    user_exists_on_host,
    check_or_create_auto_profile,
)

def pam_authenticate(username, password):
    """Authenticate using system PAM."""
    p = pam.pam()
    return p.authenticate(username, password)

def authenticate_cli():
    """
    Prompt the user for credentials and validate them via PAM and group.
    Returns username if successful, else None.
    """
    username = getpass.getuser()
    if not user_can_access_cli(username):
        print("Access denied: User is not in a permitted group.")
        return None
    try:
        password = getpass.getpass(prompt=f"Password for {username}: ")
    except Exception:
        print("Unable to read password input.")
        return None
    if pam_authenticate(username, password):
        # Ensure auto profile if not present
        check_or_create_auto_profile(username)
        return username
    else:
        print("Authentication failed.")
        return None

def web_authenticate(username, password):
    """Authenticate for web login."""
    if not user_exists_on_host(username):
        return False
    if not user_can_access_cli(username):
        return False
    if pam_authenticate(username, password):
        # Ensure auto profile if not present
        check_or_create_auto_profile(username)
        return True
    return False

def prevent_duplicate_profile_creation(new_username):
    """
    Prevent web from creating new users that conflict with system users.
    Returns True if safe to create, False if user is a real system user.
    """
    if user_exists_on_host(new_username):
        return False
    return True

# Optional: Admin override for root, for system maintenance.
def is_admin_user(username):
    return username == "root" or user_can_access_cli(username) == "admin"
