from flask import Blueprint, request, jsonify
from flask_login import login_required
from inetctl.core.netplan import (
    list_interfaces,
    get_netplan_config,
    set_netplan_config,
    get_vlan_subnets,
    validate_netplan_config,
)
from inetctl.Job_queue_service import queue_job

bp = Blueprint("network", __name__, url_prefix="/api/network")

@bp.route("/interfaces", methods=["GET"])
@login_required
def interfaces():
    return jsonify({"interfaces": list_interfaces()})

@bp.route("/vlan_subnets", methods=["GET"])
@login_required
def vlan_subnets():
    return jsonify({"vlans": get_vlan_subnets()})

@bp.route("/config", methods=["GET"])
@login_required
def netplan_config():
    # Returns current netplan YAML (raw)
    cfg = get_netplan_config()
    return jsonify({"config": cfg})

@bp.route("/config/validate", methods=["POST"])
@login_required
def validate_netplan():
    config = request.json.get("config")
    is_valid, errors = validate_netplan_config(config)
    return jsonify({"valid": is_valid, "errors": errors})

@bp.route("/config", methods=["POST"])
@login_required
def update_netplan_config():
    # Queue network config update to avoid race
    config = request.json.get("config")
    user = getattr(request, 'user', None) or getattr(request, 'remote_user', None)
    job_id = queue_job(
        "apply_netplan_config",
        {"config": config, "user": user},
        notify_users=True,
        description="Update Netplan configuration"
    )
    return jsonify({"success": True, "queued": True, "job_id": job_id})

@bp.route("/config/apply", methods=["POST"])
@login_required
def apply_netplan_config():
    user = getattr(request, 'user', None) or getattr(request, 'remote_user', None)
    job_id = queue_job(
        "apply_netplan_changes",
        {"user": user},
        notify_users=True,
        description="Apply Netplan changes (netplan apply)"
    )
    return jsonify({"success": True, "queued": True, "job_id": job_id})
