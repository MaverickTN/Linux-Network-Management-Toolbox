# lnmt/core/auth.py

import pam
from lnmt.core.user_manager import auto_create_profile, user_in_allowed_group

def authenticate_user(username, password):
    pam_auth = pam.pam()
    if pam_auth.authenticate(username, password):
        # Only allow users in the permitted groups
        if user_in_allowed_group(username):
            auto_create_profile(username)
            return True
    return False
