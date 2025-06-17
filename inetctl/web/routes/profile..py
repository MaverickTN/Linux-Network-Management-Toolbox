from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from inetctl.theme import get_theme, APP_TITLE

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    # Available theme names
    themes = {k: v["name"] for k, v in get_theme().items()}
    current_theme = session.get("theme", "dark")
    user = current_user

    if request.method == "POST":
        # Handle user info update
        if "theme" in request.form:
            session["theme"] = request.form["theme"]
        if "email" in request.form:
            user.email = request.form["email"]
        # ... handle notification prefs, password, etc.
        flash("Profile updated", "success")
        return redirect(url_for("profile.profile"))
    return render_template("profile.html",
                           user=user,
                           themes=themes,
                           current_theme=current_theme,
                           APP_TITLE=APP_TITLE)
