# inetctl/web/routes/user_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from inetctl.theme import THEMES
from inetctl.core.user_db import (
    get_current_user,
    update_user_profile,
    change_user_password,
    set_user_theme,
    set_notification_prefs
)

bp_user = Blueprint('user', __name__, url_prefix='/user')

@bp_user.route("/", methods=["GET"])
def user_profile():
    user = get_current_user(session)
    return render_template(
        "user_profile.html",
        user=user,
        themes=THEMES,
        title="User Profile"
    )

@bp_user.route("/update", methods=["POST"])
def update_profile():
    user = get_current_user(session)
    # You may want to add input validation here
    updated = update_user_profile(
        user_id=user["id"],
        email=request.form.get("email"),
        notification_prefs=request.form.getlist("notifications")
    )
    if updated:
        flash("Profile updated!", "success")
    else:
        flash("Failed to update profile.", "danger")
    return redirect(url_for("user.user_profile"))

@bp_user.route("/change_password", methods=["POST"])
def change_password():
    user = get_current_user(session)
    old = request.form.get("old_password")
    new = request.form.get("new_password")
    confirm = request.form.get("confirm_password")
    if new != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("user.user_profile"))
    if change_user_password(user["id"], old, new):
        flash("Password updated successfully.", "success")
    else:
        flash("Current password is incorrect.", "danger")
    return redirect(url_for("user.user_profile"))

@bp_user.route("/theme", methods=["POST"])
def change_theme():
    user = get_current_user(session)
    theme = request.form.get("theme")
    if theme in THEMES:
        set_user_theme(user["id"], theme)
        flash("Theme updated. Changes may require a reload.", "success")
    else:
        flash("Invalid theme selection.", "danger")
    return redirect(url_for("user.user_profile"))

@bp_user.route("/notifications", methods=["POST"])
def update_notifications():
    user = get_current_user(session)
    prefs = request.form.getlist("notifications")
    set_notification_prefs(user["id"], prefs)
    flash("Notification preferences updated.", "success")
    return redirect(url_for("user.user_profile"))

@bp_user.route("/get_theme_vars", methods=["GET"])
def get_theme_vars():
    user = get_current_user(session)
    theme = user.get("theme", "dark")
    return jsonify(THEMES.get(theme, THEMES["dark"]))
