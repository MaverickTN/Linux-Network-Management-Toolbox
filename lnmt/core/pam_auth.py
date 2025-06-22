import pam
import pwd
from inetctl.core.cli_auth import LNMT_GROUPS

def pam_authenticate(username, password):
    p = pam.pam()
    if not p.authenticate(username, password):
        return False
    # Make sure the username exists on the system and is in a valid group.
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    # Check group membership
    from inetctl.core.cli_auth import get_user_role
    if get_user_role(username) is None:
        return False
    return True

def is_system_user(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def can_create_profile(username):
    # Forbid creation if this matches a system account (security)
    return not is_system_user(username)
