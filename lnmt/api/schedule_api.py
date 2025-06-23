from flask import Blueprint, request, jsonify
from lnmt.core.schedule import (
    get_schedules_for_host,
    add_schedule_block,
    update_schedule_block,
    remove_schedule_block,
)
from lnmt.core.logging_service import log_event
from flask_login import login_required, current_user

bp = Blueprint('schedule_api', __name__, url_prefix='/api/schedule')

@bp.route('/<mac>', methods=['GET'])
@login_required
def api_get_schedules(mac):
    schedules = get_schedules_for_host(mac)
    return jsonify({"blocks": schedules})

@bp.route('/<mac>/add', methods=['POST'])
@login_required
def api_add_block(mac):
    data = request.json
    result, msg = add_schedule_block(mac, data, user=current_user.username)
    if result:
        log_event(f"Schedule block added for {mac} by {current_user.username}: {data}")
        return jsonify({"success": True, "desc": "Block added."})
    else:
        return jsonify({"success": False, "desc": msg}), 400

@bp.route('/<mac>/<int:block_idx>', methods=['PATCH'])
@login_required
def api_edit_block(mac, block_idx):
    data = request.json
    result, msg = update_schedule_block(mac, block_idx, data, user=current_user.username)
    if result:
        log_event(f"Schedule block {block_idx} updated for {mac} by {current_user.username}: {data}")
        return jsonify({"success": True, "desc": "Block updated."})
    else:
        return jsonify({"success": False, "desc": msg}), 400

@bp.route('/<mac>/<int:block_idx>', methods=['DELETE'])
@login_required
def api_delete_block(mac, block_idx):
    result, msg = remove_schedule_block(mac, block_idx, user=current_user.username)
    if result:
        log_event(f"Schedule block {block_idx} deleted for {mac} by {current_user.username}")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "desc": msg}), 400
