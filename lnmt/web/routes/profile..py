# lnmt/web/routes/profile.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from lnmt.core.user_profile import (
    get_or_create_user_profile, update_profile, get_user_theme
)
from lnmt.theme import THEMES

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    username = current_user.username
    profile, _ = get_or_create_user_profile(username)
    theme_keys = list(THEMES.keys())

    if request.method == "POST":
        # Theme selection
        theme = request.form.get("theme")
        if theme not in theme_keys:
            theme = "dark"

        # Email and notifications
        email = request.form.get("email", "")
        notification_prefs = request.form.getlist("notifications")
        contact_methods = request.form.get("contact_methods", "").split(',')

        update_profile(
            username,
            theme=theme,
            email=email,
            notification_prefs=notification_prefs,
            contact_methods=contact_methods,
        )
        flash("Profile updated.", "success")
        return redirect(url_for("profile.profile"))

    # Populate form fields
    return render_template(
        "profile.html",
        profile=profile,
        themes=THEMES,
        theme_keys=theme_keys
    )
