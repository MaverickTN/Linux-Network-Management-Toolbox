from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from inetctl.core.profile import (
    get_user_profile, save_user_profile, auto_generate_profiles,
    get_access_level, ensure_host_user, list_user_profiles
)
from inetctl.theme import THEMES, list_theme_names
import os

bp = Blueprint('profile', __name__, url_prefix='/profile')

def get_current_user():
    return session.get('username') or os.environ.get("USER")

@bp.route("/", methods=["GET"])
def profile_page():
    username = get_current_user()
    if not username:
        flash("Please log in to view your profile.", "danger")
        return redirect(url_for("auth.login"))
    try:
        profile = get_user_profile(username)
    except Exception:
        flash("No profile found.", "danger")
        return redirect(url_for("home"))
    access_level = get_access_level(username)
    theme_names = list_theme_names()
    return render_template(
        "profile.html",
        profile=profile,
        access_level=access_level,
        themes=theme_names,
    )

@bp.route("/api", methods=["GET", "POST"])
def profile_api():
    username = get_current_user()
    if not username:
        return jsonify({"error": "not authenticated"}), 401
    if request.method == "GET":
        try:
            profile = get_user_profile(username)
            return jsonify(profile)
        except Exception as e:
            return jsonify({"error": str(e)}), 404
    elif request.method == "POST":
        updates = request.json
        try:
            profile = get_user_profile(username)
            # Security: Only allow certain fields to be updated by user
            allowed = ["display_name", "email", "theme", "notifications"]
            for k in updates:
                if k in allowed:
                    profile[k] = updates[k]
            save_user_profile(username, profile)
            return jsonify({"success": True, "profile": profile})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@bp.route("/list", methods=["GET"])
def list_profiles():
    username = get_current_user()
    if get_access_level(username) != "admin":
        return jsonify({"error": "Not authorized"}), 403
    return jsonify(list_user_profiles())

@bp.route("/init", methods=["POST"])
def init_profiles():
    username = get_current_user()
    if get_access_level(username) != "admin":
        return jsonify({"error": "Not authorized"}), 403
    created = auto_generate_profiles()
    return jsonify({"created": created})
