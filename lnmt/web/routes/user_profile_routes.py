# lnmt/web/routes/user_profile_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from lnmt.core.user_profile import get_user_profile, update_user_profile, validate_and_update_password
from lnmt.core.theme_manager import THEMES

user_profile_bp = Blueprint("user_profile", __name__)

@user_profile_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    profile = get_user_profile(current_user.username)
    return render_template(
        "user_profile.html",
        user=current_user,
        profile=profile,
        themes=THEMES,
        current_theme=session.get("theme", "dark")
    )

@user_profile_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    updates = {}
    if "email" in request.form:
        updates["email"] = request.form["email"]
    if "notification_settings" in request.form:
        updates["notification_settings"] = request.form["notification_settings"]
    if "theme" in request.form and request.form["theme"] in THEMES:
        updates["theme"] = request.form["theme"]
        session["theme"] = request.form["theme"]
    update_user_profile(current_user.username, **updates)
    flash("Profile updated.", "success")
    return redirect(url_for("user_profile.profile"))

@user_profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    old = request.form.get("current_password")
    new = request.form.get("new_password")
    result, msg = validate_and_update_password(current_user.username, old, new)
    flash(msg, "success" if result else "danger")
    return redirect(url_for("user_profile.profile"))
