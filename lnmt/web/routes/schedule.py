from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from lnmt.core.config_loader import load_config, save_config
from lnmt.core.user import require_web_group
from lnmt.core.logging import log_event
from lnmt.web.utils import toast_notify

bp = Blueprint("schedule", __name__, url_prefix="/schedule")

def _get_host(mac):
    config = load_config()
    for host in config.get("known_hosts", []):
        if host.get("mac") == mac:
            return host, config
    return None, config

def _overlaps(blocks, start, end, skip_idx=None):
    s = int(start[:2])*60 + int(start[3:])
    e = int(end[:2])*60 + int(end[3:])
    for idx, blk in enumerate(blocks):
        if skip_idx is not None and idx == skip_idx:
            continue
        bs = int(blk["start"][:2])*60 + int(blk["start"][3:])
        be = int(blk["end"][:2])*60 + int(blk["end"][3:])
        if not (e <= bs or s >= be):
            return True
    return False

@bp.route("/<mac>")
@login_required
@require_web_group(['lnmtadm', 'lnmt', 'lnmtv'])
def manage(mac):
    host, _ = _get_host(mac)
    if not host:
        toast_notify("Host not found.", "danger")
        return render_template("not_found.html")
    return render_template("schedule_manage.html", host=host)

@bp.route("/api/list", methods=["POST"])
@login_required
@require_web_group(['lnmtadm', 'lnmt', 'lnmtv'])
def list_blocks():
    mac = request.json.get("mac")
    host, _ = _get_host(mac)
    if not host:
        return jsonify({"error": "Host not found."}), 404
    blocks = host.setdefault("schedules", [])
    return jsonify({"blocks": blocks})

@bp.route("/api/add", methods=["POST"])
@login_required
@require_web_group(['lnmtadm', 'lnmt'])
def add_block():
    data = request.json
    mac, start, end = data["mac"], data["start"], data["end"]
    host, config = _get_host(mac)
    if not host:
        return jsonify({"error": "Host not found."}), 404
    blocks = host.setdefault("schedules", [])
    if start >= end:
        return jsonify({"error": "Start must be before end."}), 400
    if _overlaps(blocks, start, end):
        return jsonify({"error": "Block overlaps."}), 409
    blocks.append({"start": start, "end": end})
    save_config(config)
    log_event(current_user.username, f"Web: Added schedule {start}-{end} to {mac}")
    return jsonify({"success": True})

@bp.route("/api/update", methods=["POST"])
@login_required
@require_web_group(['lnmtadm', 'lnmt'])
def update_block():
    data = request.json
    mac, idx, start, end = data["mac"], int(data["idx"]), data["start"], data["end"]
    host, config = _get_host(mac)
    if not host:
        return jsonify({"error": "Host not found."}), 404
    blocks = host.setdefault("schedules", [])
    if not (0 <= idx < len(blocks)):
        return jsonify({"error": "Invalid block index."}), 400
    if start >= end:
        return jsonify({"error": "Start must be before end."}), 400
    if _overlaps(blocks, start, end, skip_idx=idx):
        return jsonify({"error": "Block overlaps."}), 409
    blocks[idx] = {"start": start, "end": end}
    save_config(config)
    log_event(current_user.username, f"Web: Updated schedule {start}-{end} for {mac}")
    return jsonify({"success": True})

@bp.route("/api/remove", methods=["POST"])
@login_required
@require_web_group(['lnmtadm', 'lnmt'])
def remove_block():
    data = request.json
    mac, idx = data["mac"], int(data["idx"])
    host, config = _get_host(mac)
    if not host:
        return jsonify({"error": "Host not found."}), 404
    blocks = host.setdefault("schedules", [])
    if not (0 <= idx < len(blocks)):
        return jsonify({"error": "Invalid block index."}), 400
    removed = blocks.pop(idx)
    save_config(config)
    log_event(current_user.username, f"Web: Removed schedule {removed['start']}-{removed['end']} from {mac}")
    return jsonify({"success": True})
