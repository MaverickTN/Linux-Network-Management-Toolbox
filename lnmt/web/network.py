# lnmt/web/network.py

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from lnmt.core.netplan import get_all_netplan_interfaces, get_vlan_subnets, apply_netplan_changes
from lnmt.core.config_loader import load_config, save_config
from lnmt.core.logging import log_event
from lnmt.job_queue_service import JobQueueService

network_bp = Blueprint('network', __name__, url_prefix='/network')

@network_bp.route('/', methods=['GET'])
def network_overview():
    config = load_config()
    interfaces = get_all_netplan_interfaces()
    vlans = get_vlan_subnets()
    return render_template(
        "network.html",
        interfaces=interfaces,
        vlans=vlans,
        config=config
    )

@network_bp.route('/apply', methods=['POST'])
def apply_network_changes():
    # User submits Netplan changes
    data = request.form.to_dict()
    user = getattr(request, 'user', 'web')
    job = JobQueueService.queue_job(
        description=f"Apply Netplan changes by {user}",
        command=lambda: apply_netplan_changes(data)
    )
    log_event("network", "Queued Netplan apply", details=data)
    flash(f"Network changes queued as job #{job.id}", "info")
    return redirect(url_for('network.network_overview'))

@network_bp.route('/vlan/<vlan_id>/edit', methods=['POST'])
def edit_vlan(vlan_id):
    config = load_config()
    vlan_config = request.form.to_dict()
    # Edit the VLAN in config and netplan
    for net in config['networks']:
        if net['id'] == vlan_id:
            net.update(vlan_config)
    save_config(config)
    log_event("network", f"VLAN {vlan_id} updated", details=vlan_config)
    return jsonify({"success": True, "message": f"VLAN {vlan_id} updated."})

@network_bp.route('/api/vlans', methods=['GET'])
def api_get_vlans():
    return jsonify(get_vlan_subnets())

# Add more endpoints as needed (CRUD for interfaces/VLANs, etc)
