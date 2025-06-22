# inetctl/core/theme_manager.py

from inetctl.theme import THEMES, get_theme
from flask import session

def get_user_theme_key(username):
    # This should use the user profile DB or config
    from inetctl.core.user_profile import get_or_create_user_profile
    profile, _ = get_or_create_user_profile(username)
    return profile.get("theme", "dark")

def get_active_theme():
    # For Flask (web): checks session, falls back to dark
    return session.get("theme", "dark")

def set_active_theme(theme_key):
    if theme_key in THEMES:
        session["theme"] = theme_key
    else:
        session["theme"] = "dark"

def apply_theme_to_cli(username, text, style="primary"):
    theme_key = get_user_theme_key(username)
    color = THEMES.get(theme_key, THEMES["dark"])["cli"].get(style, "")
    reset = THEMES.get(theme_key, THEMES["dark"])["cli"]["reset"]
    return f"{color}{text}{reset}"

def list_themes():
    return {k: v["name"] for k, v in THEMES.items()}

def validate_theme_key(theme_key):
    return theme_key in THEMES
