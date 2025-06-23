# lnmt/web/auth.py

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from pam import pam
from lnmt.core.user_manager import (
    user_exists_on_host,
    user_can_access_cli,
    user_access_level,
    check_or_create_auto_profile,
    get_user_profile,
    save_user_profile,
)
from lnmt.theme import THEMES, get_theme

bp = Blueprint("auth", __name__, url_prefix="/auth")

def pam_authenticate(username, password):
    p = pam()
    return p.authenticate(username, password)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not user_exists_on_host(username):
            flash("Invalid username.", "danger")
            return render_template("login.html", title="Login", theme=get_theme("dark"))

        if pam_authenticate(username, password):
            if not user_can_access_cli(username):
                flash("Access denied: User not in permitted LNMT group.", "danger")
                return render_template("login.html", title="Login", theme=get_theme("dark"))

            # Create auto profile if not present
            check_or_create_auto_profile(username)
            session["username"] = username
            flash("Login successful.", "success")
            return redirect(url_for("home.index"))
        else:
            flash("Invalid credentials.", "danger")
            return render_template("login.html", title="Login", theme=get_theme("dark"))
    return render_template("login.html", title="Login", theme=get_theme("dark"))

@bp.route("/logout")
def logout():
    session.pop("username", None)
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))

def get_logged_in_user():
    return session.get("username", None)

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_logged_in_user():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper
