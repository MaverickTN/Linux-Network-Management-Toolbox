from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from lnmt.core.user_profiles import get_user_profile, upsert_user_profile
from lnmt.theme import list_theme_names

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.route("/", methods=["GET", "POST"])
@login_required
def user_profile():
    username = current_user.username
    profile = get_user_profile(username)
    themes = list_theme_names()
    if request.method == "POST":
        theme = request.form.get("theme")
        email = request.form.get("email")
        notify_mask = request.form.get("notify_mask")
        upsert_user_profile(username, email=email, notify_mask=notify_mask, theme=theme)
        flash("Profile updated.", "success")
        return redirect(url_for("profile.user_profile"))
    return render_template(
        "profile.html",
        profile=profile,
        themes=themes,
    )
