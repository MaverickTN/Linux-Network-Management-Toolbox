import os
import sys
from functools import wraps

from lnmt.core.group_check import is_authorized_user, get_lnmt_role
from lnmt.core.user_profiles import get_user_profile
from lnmt.theme import cli_color

def require_lnmt_cli_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        username = os.environ.get("SUDO_USER") or os.environ.get("USER")
        if not username or not is_authorized_user(username):
            print(cli_color("Access denied: You must be a member of an LNMT group to use this CLI.", "danger"))
            sys.exit(1)
        # Get user profile and set CLI theme if exists
        profile = get_user_profile(username)
        if profile and profile[3]:  # profile[3] = theme
            os.environ["LNMT_THEME"] = profile[3]
        else:
            os.environ["LNMT_THEME"] = "dark"
        return func(*args, **kwargs)
    return wrapper
