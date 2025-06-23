# lnmt/web/routes/netplan.py

from flask import Blueprint, request, jsonify, render_template
from lnmt.auth import require_login, require_admin
from lnmt.core import netplan
from lnmt.job_queue_service import enqueue_job
from lnmt.theme import get_theme

bp = Blueprint('netplan', __name__, url_prefix='/netplan')

@bp.route('/')
@require_admin
def netplan_page():
    """Netplan main UI: show VLANs, interfaces, config form."""
    interfaces = netplan.get_all_netplan_interfaces()
    vlans = netplan.get_vlan_subnets()
    theme = get_theme()
    return render_template('netplan_form.html', interfaces=interfaces, vlans=vlans, theme=theme)

@bp.route('/api/interfaces', methods=['GET'])
@require_admin
def api_interfaces():
    return jsonify(netplan.get_all_netplan_interfaces())

@bp.route('/api/vlans', methods=['GET'])
@require_admin
def api_vlans():
    return jsonify(netplan.get_vlan_subnets())

@bp.route('/api/reload', methods=['POST'])
@require_admin
def api_reload_netplan():
    """Apply Netplan changes (queue for safety)."""
    enqueue_job("apply_netplan", {})
    return jsonify({"queued": True, "message": "Netplan apply scheduled."})

@bp.route('/api/update', methods=['POST'])
@require_admin
def api_update_netplan():
    """Update Netplan config with posted YAML or dict (queued, logged)."""
    new_config = request.json.get('netplan_yaml')
    enqueue_job("update_netplan", {"netplan_yaml": new_config})
    return jsonify({"queued": True, "message": "Netplan update scheduled."})

@bp.route('/api/validate', methods=['POST'])
@require_admin
def api_validate_netplan():
    """Validate posted netplan YAML before applying (returns result)."""
    netplan_yaml = request.json.get('netplan_yaml')
    try:
        ok, errors = netplan.validate_netplan_yaml(netplan_yaml)
        if ok:
            return jsonify({"valid": True})
        else:
            return jsonify({"valid": False, "errors": errors}), 400
    except Exception as e:
        return jsonify({"valid": False, "errors": str(e)}), 500

@bp.route('/api/get', methods=['GET'])
@require_admin
def api_get_netplan():
    """Get current netplan YAML."""
    return jsonify(netplan.get_netplan_yaml())

@bp.route('/api/vlan/<vlan_id>', methods=['POST'])
@require_admin
def api_edit_vlan(vlan_id):
    """Edit a VLAN (update subnet, description, etc, via Netplan)."""
    params = request.json
    enqueue_job("edit_vlan", {"vlan_id": vlan_id, **params})
    return jsonify({"queued": True, "message": f"Edit VLAN {vlan_id} scheduled."})

@bp.route('/api/vlan/<vlan_id>', methods=['DELETE'])
@require_admin
def api_delete_vlan(vlan_id):
    """Remove a VLAN (remove from netplan config, queued)."""
    enqueue_job("delete_vlan", {"vlan_id": vlan_id})
    return jsonify({"queued": True, "message": f"Delete VLAN {vlan_id} scheduled."})
