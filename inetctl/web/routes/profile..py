from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from inetctl.core.user_profiles import (
    get_user_profile, update_user_profile, THEMES, list_theme_names
)
import os

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    username = current_user.username
    profile = get_user_profile(username)
    theme_names = list_theme_names()

    if request.method == "POST":
        # Collect form data, only update allowed fields
        display_name = request.form.get("display_name", username)
        email = request.form.get("email", "")
        theme = request.form.get("theme", profile.get("theme", "dark"))
        # Notifications can be toggled as checkboxes
        notifications = {
            "job_events": bool(request.form.get("notify_job_events")),
            "timer_events": bool(request.form.get("notify_timer_events")),
            "login_events": bool(request.form.get("notify_login_events")),
            "critical": bool(request.form.get("notify_critical")),
            "info": bool(request.form.get("notify_info"))
        }
        update_user_profile(
            username,
            display_name=display_name,
            email=email,
            theme=theme,
            notifications=notifications
        )
        flash("Profile updated!", "success")
        return redirect(url_for("profile.profile"))
    return render_template(
        "profile.html",
        user=current_user,
        profile=profile,
        theme_names=theme_names
    )
