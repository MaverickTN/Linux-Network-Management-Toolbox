import pam
import getpass

def pam_authenticate(username, password):
    p = pam.pam()
    return p.authenticate(username, password)

def get_current_user():
    """Get the currently logged-in UNIX username."""
    try:
        return getpass.getuser()
    except Exception:
        return None
