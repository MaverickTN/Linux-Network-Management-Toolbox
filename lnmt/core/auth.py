# lnmt/core/auth.py

import pam
from .user_manager import user_exists, auto_create_profile, user_has_cli_access

def authenticate(username, password):
    p = pam.pam()
    if not user_exists(username):
        return False
    success = p.authenticate(username, password)
    if success:
        auto_create_profile(username)
        return True
    return False

def authorize(username, required_role="operator"):
    # Returns True if user is in the required role or higher
    from .user_manager import user_role
    roles = ["viewer", "operator", "admin"]
    user_r = user_role(username)
    return roles.index(user_r) >= roles.index(required_role)

def cli_access(username):
    return user_has_cli_access(username)
