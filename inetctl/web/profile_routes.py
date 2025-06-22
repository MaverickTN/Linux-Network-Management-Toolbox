from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from inetctl.core.profile import (
    get_user_profile,
    update_user_profile,
    auto_create_profile,
    list_all_profiles,
    get_user_role,
)
from inetctl.theme import THEMES

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def my_profile():
    username = current_user.username
    profile = auto_create_profile(username)
    if request.method == "POST":
        # Update fields from the form
        email = request.form.get("email", "")
        theme = request.form.get("theme", "dark")
        notify_events = request.form.getlist("notify_events")
        data = {
            "email": email,
            "theme": theme,
            "notify_events": notify_events,
        }
        update_user_profile(username, data)
        flash("Profile updated.", "success")
        return redirect(url_for("profile.my_profile"))
    return render_template(
        "profile.html",
        profile=profile,
        themes=THEMES,
        theme_names=[(k, v["name"]) for k, v in THEMES.items()]
    )

@profile_bp.route("/admin")
@login_required
def admin_profiles():
    if get_user_role(current_user.username) != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("profile.my_profile"))
    profiles = list_all_profiles()
    return render_template("profiles_admin.html", profiles=profiles)
