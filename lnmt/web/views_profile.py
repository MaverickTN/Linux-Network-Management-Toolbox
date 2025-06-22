from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from inetctl.profile import update_profile, get_profile, list_theme_names
from inetctl.web.auth import require_auth

profile_bp = Blueprint("profile", __name__)

@profile_bp.route('/profile', methods=["GET"])
@require_auth
def profile_page():
    username = session.get("user")
    profile = get_profile(username)
    return render_template(
        "profile.html",
        profile=profile,
        list_theme_names=list_theme_names
    )

@profile_bp.route('/profile/update', methods=["POST"])
@require_auth
def update_profile_route():
    username = session.get("user")
    theme = request.form.get("theme", "dark")
    email = request.form.get("email", "")
    notify = request.form.get("notify", "")
    update_profile(username, theme=theme, email=email, notify=notify)
    session["theme"] = theme
    flash("Profile updated!", "success")
    return redirect(url_for("profile.profile_page"))
