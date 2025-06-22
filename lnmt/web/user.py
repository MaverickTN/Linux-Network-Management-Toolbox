from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from inetctl.core.auth import get_lnmt_role, username_conflicts_with_system
from inetctl.theme import list_theme_names
from inetctl.core.user_profiles import (
    get_user_profile, save_user_profile, current_user, user_profiles
)

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if not user:
        flash("You must be logged in.", "danger")
        return redirect(url_for("auth.login"))
    profile = get_user_profile(user)
    theme_names = list_theme_names()
    if request.method == "POST":
        email = request.form.get("email")
        theme = request.form.get("theme")
        notifications = request.form.getlist("notifications")
        if username_conflicts_with_system(user):
            flash("Cannot modify a system user's profile via web.", "danger")
            return redirect(url_for("user.profile"))
        profile["email"] = email
        profile["theme"] = theme
        profile["notifications"] = notifications
        save_user_profile(user, profile)
        flash("Profile updated.", "success")
        return redirect(url_for("user.profile"))
    return render_template(
        "profile.html",
        user=user,
        profile=profile,
        theme_names=theme_names
    )

@user_bp.route("/change-password", methods=["POST"])
def change_password():
    # Placeholder: integrate with PAM if needed.
    flash("Password changes must be performed using your system credentials.", "info")
    return redirect(url_for("user.profile"))
