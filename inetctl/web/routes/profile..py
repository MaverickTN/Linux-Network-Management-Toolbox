from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from inetctl.core.profile import get_user_profile, update_user_profile, list_all_profiles
from inetctl.theme import THEMES

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.route("/", methods=["GET", "POST"])
@login_required
def my_profile():
    username = current_user.get_id()
    profile = get_user_profile(username)
    if not profile:
        flash("Profile not found or access denied.", "danger")
        return redirect(url_for("home.index"))

    if request.method == "POST":
        email = request.form.get("email", "")
        notify_events = request.form.getlist("notify_events")
        theme = request.form.get("theme", "dark")
        # Update user profile
        update_user_profile(username, {
            "email": email,
            "notify_events": notify_events,
            "theme": theme
        })
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.my_profile"))

    theme_options = [(key, theme["name"]) for key, theme in THEMES.items()]
    return render_template(
        "profile.html",
        profile=profile,
        theme_options=theme_options,
        active_theme=profile.get("theme", "dark")
    )

@bp.route("/all")
@login_required
def all_profiles():
    # Admin-only, for future RBAC
    profiles = list_all_profiles()
    return render_template("profile_list.html", profiles=profiles)
