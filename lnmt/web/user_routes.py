from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
import pam
from inetctl.core import user_profiles
from inetctl.theme import THEMES, list_theme_names

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user.get_id()
    profile = user_profiles.load_profile(user)
    themes = list_theme_names()

    if request.method == "POST":
        email = request.form.get("email", "")
        notification_events = request.form.getlist("notifications")
        selected_theme = request.form.get("theme", "dark")
        profile["email"] = email
        profile["notification_events"] = notification_events
        profile["theme"] = selected_theme
        user_profiles.save_profile(profile, user)
        flash("Profile updated successfully.", "success")
        session["theme"] = selected_theme  # persist
        return redirect(url_for("user.profile"))

    return render_template(
        "user_profile.html",
        profile=profile,
        themes=themes,
        all_themes=THEMES,
        notification_options=["login", "important", "network", "scheduled"],
        title="User Profile"
    )

@user_bp.route("/theme", methods=["POST"])
@login_required
def set_theme():
    user = current_user.get_id()
    theme = request.form.get("theme")
    if theme and theme in THEMES:
        user_profiles.set_theme(user, theme)
        session["theme"] = theme
        return jsonify({"success": True, "theme": theme})
    return jsonify({"success": False, "error": "Invalid theme"}), 400

@user_bp.route("/notifications", methods=["POST"])
@login_required
def set_notifications():
    user = current_user.get_id()
    events = request.json.get("events")
    if isinstance(events, list):
        user_profiles.set_notifications(user, events)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid events"}), 400

@user_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    user = current_user.get_id()
    old_pw = request.form.get("old_password")
    new_pw = request.form.get("new_password")
    confirm = request.form.get("confirm_password")
    if not old_pw or not new_pw or new_pw != confirm:
        return jsonify({"success": False, "error": "Password validation failed."}), 400
    # Use PAM to change password for system user
    p = pam.pam()
    if not p.authenticate(user, old_pw):
        return jsonify({"success": False, "error": "Current password is incorrect."}), 400
    try:
        import subprocess
        proc = subprocess.Popen(["passwd", user], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Write the new password twice for confirmation
        pw_input = f"{new_pw}\n{new_pw}\n".encode()
        stdout, stderr = proc.communicate(input=pw_input, timeout=10)
        if proc.returncode == 0:
            return jsonify({"success": True, "message": "Password changed successfully."})
        else:
            return jsonify({"success": False, "error": stderr.decode() or "Password change failed."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/logout")
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))

# API endpoint for getting user profile info (for web frontend)
@user_bp.route("/api/info")
@login_required
def api_user_info():
    user = current_user.get_id()
    profile = user_profiles.load_profile(user)
    return jsonify({
        "username": user,
        "display_name": profile.get("display_name", user),
        "theme": profile.get("theme", "dark"),
        "notification_events": profile.get("notification_events", []),
        "email": profile.get("email", ""),
        "groups": profile.get("groups", [])
    })
