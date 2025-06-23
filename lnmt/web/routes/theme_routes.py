# lnmt/web/routes/theme_routes.py

from flask import Blueprint, session, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from lnmt.core.theme_manager import THEMES
from lnmt.core.user_profile import update_user_profile

theme_bp = Blueprint("theme", __name__)

@theme_bp.route("/theme/<theme_key>", methods=["POST"])
@login_required
def set_theme(theme_key):
    if theme_key not in THEMES:
        return jsonify({"error": "Invalid theme"}), 400
    # Save to user profile (if possible)
    update_user_profile(current_user.username, theme=theme_key)
    session["theme"] = theme_key
    return jsonify({"status": "ok", "theme": theme_key})

@theme_bp.route("/theme/list")
@login_required
def list_themes():
    return jsonify({k: v["name"] for k, v in THEMES.items()})
