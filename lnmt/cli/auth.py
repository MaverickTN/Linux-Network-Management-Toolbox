import os
import getpass
import sys

from lnmt.core.user import (
    pam_authenticate,
    get_access_level,
    cli_theme_for_user,
    auto_create_profile_for_host_user,
)

def check_user_allowed(username=None):
    """Check if the user is allowed to use CLI (must be lnmtadm, lnmt, lnmtv)."""
    if username is None:
        username = getpass.getuser()
    level = get_access_level(username)
    if level == "none":
        color = "\033[91m"  # Red
        print(f"{color}ERROR: User '{username}' is not authorized for CLI use. Access denied.{cli_theme_for_user('dark')['reset']}")
        sys.exit(2)
    return level

def require_admin(username=None):
    """Exit if not lnmtadm."""
    if username is None:
        username = getpass.getuser()
    if get_access_level(username) != "admin":
        color = cli_theme_for_user(username)["danger"]
        print(f"{color}ERROR: Admin privileges required for this operation.{cli_theme_for_user(username)['reset']}")
        sys.exit(2)

def require_operator_or_admin(username=None):
    """Exit if not lnmtadm or lnmt."""
    if username is None:
        username = getpass.getuser()
    access = get_access_level(username)
    if access not in ("admin", "operator"):
        color = cli_theme_for_user(username)["danger"]
        print(f"{color}ERROR: Operator or Admin privileges required for this operation.{cli_theme_for_user(username)['reset']}")
        sys.exit(2)

def login_cli():
    """Authenticate CLI user at startup using PAM and auto-create profile if needed."""
    username = getpass.getuser()
    # Only allow host users in the correct group(s)
    level = check_user_allowed(username)
    auto_create_profile_for_host_user(username)
    # Prompt for password (unless running as root)
    if os.geteuid() != 0:
        password = getpass.getpass("Authenticate with your system password: ")
        if not pam_authenticate(username, password):
            print("\033[91mERROR: PAM authentication failed. Exiting.\033[0m")
            sys.exit(2)
    color = cli_theme_for_user(username)["success"]
    print(f"{color}Authentication succeeded! Access level: {level}{cli_theme_for_user(username)['reset']}")
    return username, level
