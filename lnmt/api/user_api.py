from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from inetctl.core.user import (
    get_user_profile,
    update_user_profile,
    can_edit,
    get_user_theme,
    list_all_users,
    pam_authenticate,
    auto_provision_host_user,
)
from inetctl.core.logging_service import log_event

bp = Blueprint("user_api", __name__, url_prefix="/api/user")

@bp.route("/me", methods=["GET"])
@login_required
def get_me():
    user = get_user_profile(current_user.username)
    return jsonify(user)

@bp.route("/<username>", methods=["GET"])
@login_required
def get_profile(username):
    if not can_edit(current_user.username, username):
        return jsonify({"error": "Not allowed"}), 403
    user = get_user_profile(username)
    return jsonify(user)

@bp.route("/<username>", methods=["POST"])
@login_required
def update_profile(username):
    if not can_edit(current_user.username, username):
        return jsonify({"error": "Not allowed"}), 403
    data = request.json
    update_user_profile(username, data)
    log_event(f"User {current_user.username} updated profile of {username}")
    return jsonify({"success": True})

@bp.route("/theme/<theme>", methods=["POST"])
@login_required
def update_theme(theme):
    update_user_profile(current_user.username, {"theme": theme})
    log_event(f"User {current_user.username} changed theme to {theme}")
    return jsonify({"success": True})

@bp.route("/login", methods=["POST"])
def login_api():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    # Try PAM login (host users)
    ok, msg = pam_authenticate(username, password)
    if ok:
        auto_provision_host_user(username)
        # You would call flask_login's login_user() here in real logic
        log_event(f"User {username} authenticated via PAM")
        return jsonify({"success": True, "type": "host", "msg": msg})
    # Could fallback to local DB login if you wish
    return jsonify({"success": False, "msg": msg}), 401

@bp.route("/list", methods=["GET"])
@login_required
def api_list_users():
    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403
    return jsonify({"users": list_all_users()})
