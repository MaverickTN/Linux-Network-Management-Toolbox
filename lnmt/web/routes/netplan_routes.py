# inetctl/web/routes/netplan_routes.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from inetctl.core.netplan import (
    get_all_netplan_interfaces,
    get_netplan_config,
    update_netplan_config,
    apply_netplan,
    validate_netplan_config
)
from inetctl.Job_queue_service import JobQueueService

bp_netplan = Blueprint('netplan', __name__, url_prefix='/netplan')

@bp_netplan.route("/", methods=["GET"])
def netplan_overview():
    interfaces = get_all_netplan_interfaces()
    config = get_netplan_config()
    return render_template(
        "netplan_form.html",
        interfaces=interfaces,
        netplan_config=config,
        title="Netplan Configuration"
    )

@bp_netplan.route("/edit", methods=["POST"])
def netplan_edit():
    data = request.form.to_dict(flat=False)
    # Here you would extract and validate the netplan YAML structure from form data
    new_config = request.form.get("yaml_config", "")
    valid, error = validate_netplan_config(new_config)
    if not valid:
        flash(f"Netplan validation failed: {error}", "danger")
        return redirect(url_for("netplan.netplan_overview"))
    # Queue update + apply as job (ensures single source of change)
    JobQueueService.enqueue(
        description="Update and apply Netplan configuration",
        steps=[
            lambda: update_netplan_config(new_config),
            lambda: apply_netplan()
        ],
        notify_users=True
    )
    flash("Netplan configuration update queued.", "info")
    return redirect(url_for("netplan.netplan_overview"))

@bp_netplan.route("/apply", methods=["POST"])
def netplan_apply():
    # Queue apply as job
    JobQueueService.enqueue(
        description="Apply Netplan configuration",
        steps=[apply_netplan],
        notify_users=True
    )
    flash("Netplan apply queued.", "info")
    return redirect(url_for("netplan.netplan_overview"))

@bp_netplan.route("/validate", methods=["POST"])
def netplan_validate():
    new_config = request.form.get("yaml_config", "")
    valid, error = validate_netplan_config(new_config)
    return jsonify({"valid": valid, "error": error})
