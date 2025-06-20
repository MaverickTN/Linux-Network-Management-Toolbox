# inetctl/web/user.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import pam
import pwd
import grp
import os
from inetctl.core.config_loader import load_config, save_config
from inetctl.theme import THEMES
from inetctl.core.logging import log_event

user_bp = Blueprint('user', __name__, url_prefix='/user')

# Utility: Check system group membership for CLI/Web permissions
def check_user_group(username, group):
    try:
        return username in grp.getgrnam(group).gr_mem
    except KeyError:
        return False

def system_user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

# --- PAM Authentication ---
def pam_authenticate(username, password):
    pam_service = pam.pam()
    return pam_service.authenticate(username, password)

# --- User profile logic ---
def get_user_profiles():
    config = load_config()
    return config.get("user_profiles", {})

def save_user_profiles(profiles):
    config = load_config()
    config["user_profiles"] = profiles
    save_config(config)

def ensure_user_profile(username):
    profiles = get_user_profiles()
    if username not in profiles:
        # Only create for actual system users
        if system_user_exists(username):
            # Default to 'dark' theme and empty details
            profiles[username] = {
                "theme": "dark",
                "email": "",
                "notify_events": ["critical", "job", "login"],
                "contact": {},
            }
            save_user_profiles(profiles)
            log_event("user", f"Profile auto-created for system user {username}")
            return True
        else:
            return False
    return True

def can_create_profile(username):
    # Prevent creating a user that matches a system account via web form
    return not system_user_exists(username)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        # Only allow login for host system users
        if not system_user_exists(username):
            flash("No such system user.", "danger")
            return redirect(url_for('user.login'))
        if pam_authenticate(username, password):
            # Ensure profile exists
            ensure_user_profile(username)
            session['username'] = username
            # Load user's preferred theme
            theme = get_user_profiles().get(username, {}).get("theme", "dark")
            session['theme'] = theme
            log_event("user", f"{username} logged in")
            return redirect(url_for('home.index'))
        else:
            flash("Authentication failed.", "danger")
            return redirect(url_for('user.login'))
    return render_template("login.html", themes=THEMES)

@user_bp.route('/logout')
def logout():
    if 'username' in session:
        log_event("user", f"{session['username']} logged out")
        session.pop('username', None)
        session.pop('theme', None)
    flash("Logged out.", "success")
    return redirect(url_for('user.login'))

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('user.login'))
    username = session['username']
    profiles = get_user_profiles()
    profile = profiles.get(username, {})
    if request.method == 'POST':
        profile['email'] = request.form.get('email', "")
        profile['notify_events'] = request.form.getlist('notify_events')
        profile['theme'] = request.form.get('theme', 'dark')
        profiles[username] = profile
        save_user_profiles(profiles)
        session['theme'] = profile['theme']
        log_event("user", f"Profile updated for {username}")
        flash("Profile updated.", "success")
        return redirect(url_for('user.profile'))
    return render_template("profile.html", profile=profile, themes=THEMES)

@user_bp.route('/theme', methods=['POST'])
def update_theme():
    if 'username' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    theme = request.form.get('theme', 'dark')
    username = session['username']
    profiles = get_user_profiles()
    if username in profiles:
        profiles[username]['theme'] = theme
        save_user_profiles(profiles)
        session['theme'] = theme
        log_event("user", f"{username} theme changed to {theme}")
    return jsonify({"success": True, "theme": theme})

# --- Admin: Create or delete user profiles (not system accounts) ---
@user_bp.route('/admin/create', methods=['POST'])
def admin_create_profile():
    username = request.form['username'].strip()
    if not can_create_profile(username):
        return jsonify({"error": "Cannot create profile matching system user"}), 400
    profiles = get_user_profiles()
    if username in profiles:
        return jsonify({"error": "User profile already exists"}), 409
    profiles[username] = {
        "theme": "dark",
        "email": request.form.get('email', ""),
        "notify_events": [],
        "contact": {}
    }
    save_user_profiles(profiles)
    log_event("user", f"Admin created user profile for {username}")
    return jsonify({"success": True})

@user_bp.route('/admin/delete', methods=['POST'])
def admin_delete_profile():
    username = request.form['username'].strip()
    if system_user_exists(username):
        return jsonify({"error": "Cannot delete system user profile"}), 400
    profiles = get_user_profiles()
    if username not in profiles:
        return jsonify({"error": "User profile not found"}), 404
    profiles.pop(username)
    save_user_profiles(profiles)
    log_event("user", f"Admin deleted user profile for {username}")
    return jsonify({"success": True})

# Example route for fetching user's theme in CLI context
@user_bp.route('/api/cli-theme/<username>')
def api_cli_theme(username):
    profiles = get_user_profiles()
    theme = profiles.get(username, {}).get('theme', 'dark')
    return jsonify({"theme": theme})

# More API endpoints for notifications and settings can be added as needed

