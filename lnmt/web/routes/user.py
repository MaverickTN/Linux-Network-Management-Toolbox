from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import getpass
from lnmt.core.user import (
    load_profile,
    save_profile,
    get_access_level,
    prevent_duplicate_profile_creation,
    pam_authenticate,
    update_profile,
    get_all_profiles,
    auto_provision_profile,
    PROFILE_DIR,
    REQUIRED_GROUPS
)
from lnmt.theme import THEMES

bp = Blueprint("user", __name__, url_prefix="/user")

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper

@bp.route("/profile", methods=["GET", "POST"])
@require_login
def profile():
    username = session["username"]
    prof = load_profile(username) or auto_provision_profile(username)
    if not prof:
        flash("User profile not found or not authorized", "danger")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        updates = {}
        if "theme" in request.form and request.form["theme"] in THEMES:
            updates["theme"] = request.form["theme"]
        if "email" in request.form:
            updates["email"] = request.form["email"]
        if "notify_on_login" in request.form:
            updates.setdefault("notify", {})["on_login"] = bool(request.form.get("notify_on_login"))
        if "notify_on_schedule" in request.form:
            updates.setdefault("notify", {})["on_schedule"] = bool(request.form.get("notify_on_schedule"))
        if "notify_on_job_event" in request.form:
            updates.setdefault("notify", {})["on_job_event"] = bool(request.form.get("notify_on_job_event"))
        # Only update access_level if user is admin
        if session.get("access_level") == "admin" and "access_level" in request.form:
            updates["access_level"] = request.form["access_level"]
        update_profile(username, updates)
        flash("Profile updated.", "success")
        return redirect(url_for("user.profile"))
    return render_template(
        "user_profile.html",
        profile=prof,
        themes=THEMES,
        access_level=get_access_level(username),
        group_names=REQUIRED_GROUPS
    )

@bp.route("/all")
@require_login
def all_profiles():
    # Only admins can see all
    if session.get("access_level") != "admin":
        flash("Not authorized", "danger")
        return redirect(url_for("user.profile"))
    profiles = get_all_profiles()
    return render_template("user_list.html", profiles=profiles)

@bp.route("/set_theme", methods=["POST"])
@require_login
def set_theme():
    theme = request.form.get("theme")
    username = session["username"]
    if theme in THEMES:
        update_profile(username, {"theme": theme})
        flash("Theme updated!", "success")
    else:
        flash("Invalid theme.", "danger")
    return redirect(url_for("user.profile"))

@bp.route("/contact", methods=["POST"])
@require_login
def update_contact():
    username = session["username"]
    methods = request.form.getlist("contact_methods")
    update_profile(username, {"contact_methods": methods})
    flash("Contact methods updated.", "success")
    return redirect(url_for("user.profile"))
