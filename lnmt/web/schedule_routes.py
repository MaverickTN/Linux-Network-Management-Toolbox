from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from lnmt.core.schedule import (
    get_host_schedules,
    add_schedule_block,
    remove_schedule_block,
    validate_new_block
)

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")

@schedule_bp.route("/<host>", methods=["GET"])
@login_required
def api_get_schedule(host):
    blocks = get_host_schedules(host)
    return jsonify({"blocks": blocks})

@schedule_bp.route("/<host>/add", methods=["POST"])
@login_required
def api_add_block(host):
    data = request.json
    start, end = data.get("start"), data.get("end")
    if not start or not end:
        return jsonify({"success": False, "message": "Start and end required"}), 400
    ok, msg = validate_new_block(host, {"start": start, "end": end})
    if not ok:
        return jsonify({"success": False, "message": msg}), 409
    add_schedule_block(host, {"start": start, "end": end})
    return jsonify({"success": True})

@schedule_bp.route("/<host>/remove/<int:idx>", methods=["POST"])
@login_required
def api_remove_block(host, idx):
    success = remove_schedule_block(host, idx)
    return jsonify({"success": success})

# For convenience, add a route for all schedules
@schedule_bp.route("/all", methods=["GET"])
@login_required
def api_all_schedules():
    from lnmt.core.schedule import full_schedule_for_all_hosts
    return jsonify(full_schedule_for_all_hosts())
