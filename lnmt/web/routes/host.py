# inetctl/web/routes/host.py

from flask import Blueprint, request, jsonify, abort, render_template
from inetctl.auth import require_login, require_admin
from inetctl.db import get_host_by_mac, update_host, delete_host, get_all_hosts
from inetctl.job_queue_service import enqueue_job
from inetctl.core.dnsmasq import refresh_dhcp
from inetctl.theme import get_theme

bp = Blueprint('host', __name__, url_prefix='/api/host')

@bp.route('/<mac>', methods=['GET'])
@require_login
def get_host(mac):
    """Return all editable data for this host (for modal editing, etc)"""
    host = get_host_by_mac(mac)
    if not host:
        abort(404)
    return jsonify(host)

@bp.route('/<mac>', methods=['POST'])
@require_admin
def save_host(mac):
    """Edit host: reservation, description, QoS, schedule."""
    data = request.json
    ok = update_host(mac, data)
    if not ok:
        return jsonify({"success": False, "error": "Failed to update host"}), 400
    # After update, restart DHCP or schedule relevant jobs if needed
    enqueue_job("refresh_dhcp", {"mac": mac})
    return jsonify({"success": True})

@bp.route('/<mac>', methods=['DELETE'])
@require_admin
def delete_host_api(mac):
    """Remove host from database (remove reservation, blocklists, etc)."""
    ok = delete_host(mac)
    if not ok:
        return jsonify({"success": False, "error": "Failed to remove host"}), 400
    enqueue_job("refresh_dhcp", {"mac": mac})
    return jsonify({"success": True})

@bp.route('/all', methods=['GET'])
@require_login
def all_hosts():
    """List all hosts (for table population)."""
    return jsonify(get_all_hosts())

@bp.route('/schedule/<mac>', methods=['POST'])
@require_admin
def add_schedule(mac):
    """Add or edit one or more schedule blocks for a host."""
    blocks = request.json.get("blocks", [])
    # Validate no overlap
    times = []
    for b in blocks:
        start, end = b.get("start"), b.get("end")
        times.append((start, end))
    for i in range(len(times)):
        for j in range(i + 1, len(times)):
            if max(times[i][0], times[j][0]) < min(times[i][1], times[j][1]):
                return jsonify({"success": False, "error": "Schedule blocks overlap"}), 400
    ok = update_host(mac, {"schedules": blocks})
    return jsonify({"success": ok})

@bp.route('/block/<mac>', methods=['POST'])
@require_admin
def block_host(mac):
    """Block host (add to black/denylist)."""
    enqueue_job("block_host", {"mac": mac})
    return jsonify({"queued": True, "message": f"Block scheduled for {mac}"})

@bp.route('/allow/<mac>', methods=['POST'])
@require_admin
def allow_host(mac):
    """Remove host from blocklist."""
    enqueue_job("allow_host", {"mac": mac})
    return jsonify({"queued": True, "message": f"Allow scheduled for {mac}"})

@bp.route('/qos_profiles', methods=['GET'])
@require_login
def qos_profiles():
    """Return list of QoS profiles (for editing)."""
    # Assume defined in config or database
    from inetctl.core.config_loader import load_config
    cfg = load_config()
    return jsonify(cfg.get("qos_policies", {}))
