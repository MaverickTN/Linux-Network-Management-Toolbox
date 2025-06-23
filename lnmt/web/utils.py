import os
import getpass
from flask import session

def get_logged_in_user():
    # If using SSO or custom login, session['user']
    return session.get('user') or getpass.getuser()

def get_user_theme(user=None):
    # Placeholder for fetching user's preferred theme
    # In production, pull from user profile db or config
    from lnmt.theme import get_theme
    if not user:
        user = get_logged_in_user()
    # For now, use 'dark' for root, else 'light'
    if user == "root":
        return get_theme("dark")
    return get_theme("light")
