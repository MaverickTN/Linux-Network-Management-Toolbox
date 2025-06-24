from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from lnmt.core.pam_auth import pam_authenticate
from lnmt.core.user_manager import get_user, set_user_theme, update_user_profile
from lnmt.core.theme_manager import get_all_themes

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if pam_authenticate(username, password):
            session["user"] = username
            flash("Welcome, {}".format(username), "success")
            return redirect(url_for("home.index"))
        else:
            flash("Login failed", "danger")
    return render_template("login.html", themes=get_all_themes())

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile", methods=["GET", "POST"])
def profile():
    username = session.get("user")
    if not username:
        return redirect(url_for("auth.login"))
    user = get_user(username)
    if request.method == "POST":
        email = request.form.get("email")
        theme = request.form.get("theme")
        notif = request.form.get("notification_settings")
        update_user_profile(username, email=email, theme=theme, notification_settings=notif)
        set_user_theme(username, theme)
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("profile.html", user=user, themes=get_all_themes())
