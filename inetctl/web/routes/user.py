from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from inetctl.core import user_profile
from inetctl.theme import THEMES, list_theme_names

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.before_request
def require_login():
    if "username" not in session:
        return redirect(url_for("auth.login"))

@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    username = session["username"]
    profile = user_profile.load_user_profile(username)
    themes = list_theme_names()
    if request.method == "POST":
        # User submitted profile update
        updates = {}
        email = request.form.get("email", "")
        theme = request.form.get("theme", "dark")
        # Notification options (checkboxes)
        notification_options = {
            "system": bool(request.form.get("notif_system")),
            "jobs": bool(request.form.get("notif_jobs")),
            "warnings": bool(request.form.get("notif_warnings")),
            "critical": bool(request.form.get("notif_critical"))
        }
        updates["email"] = email
        updates["theme"] = theme
        updates["notification_options"] = notification_options
        user_profile.update_user_profile(username, updates)
        flash("Profile updated!", "success")
        return redirect(url_for("user.profile"))
    return render_template("user_profile.html",
                           profile=profile,
                           themes=themes)

@user_bp.route("/theme", methods=["POST"])
def change_theme():
    # For AJAX theme change
    username = session["username"]
    theme = request.json.get("theme")
    if theme and theme in THEMES:
        user_profile.update_user_profile(username, {"theme": theme})
        return jsonify({"success": True, "theme": theme})
    return jsonify({"success": False, "error": "Invalid theme"})

@user_bp.route("/api/list", methods=["GET"])
def list_profiles_api():
    # Admin only: List all profiles
    username = session["username"]
    if user_profile.get_user_access_level(username) != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"profiles": user_profile.list_profiles()})

