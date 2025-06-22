# inetctl/web/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from inetctl.core.auth import pam_authenticate, is_system_user, get_user_role
from inetctl.core.user_profiles import load_user_profile, save_user_profile, get_all_user_profiles

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Only allow logins for host system users in lnmt groups
        if not is_system_user(username):
            flash("Access denied: not a valid system user.", "danger")
            return render_template("login.html")
        role = get_user_role(username)
        if not role:
            flash("Access denied: you are not a member of lnmtadm, lnmt, or lnmtv.", "danger")
            return render_template("login.html")

        if pam_authenticate(username, password):
            # Load/create profile
            profile = load_user_profile(username)
            if not profile:
                # First login, create a new profile with default theme, etc.
                profile = {
                    "username": username,
                    "role": role,
                    "theme": "dark",  # default
                    "email": "",
                    "notification_prefs": [],
                    # ...any other default fields
                }
                save_user_profile(username, profile)
            session["user"] = username
            session["role"] = role
            session["theme"] = profile.get("theme", "dark")
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for("home.dashboard"))
        else:
            flash("Login failed: incorrect password.", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    username = session["user"]
    profile = load_user_profile(username)
    if not profile:
        flash("Profile not found!", "danger")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        # Handle theme/notification/email updates, etc.
        new_theme = request.form.get("theme")
        email = request.form.get("email")
        notification_prefs = request.form.getlist("notification_prefs")
        if new_theme:
            profile["theme"] = new_theme
            session["theme"] = new_theme
        if email is not None:
            profile["email"] = email
        profile["notification_prefs"] = notification_prefs
        save_user_profile(username, profile)
        flash("Profile updated.", "success")
    return render_template("profile.html", profile=profile)
