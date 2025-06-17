# inetctl/web/routes/netplan.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from inetctl.core.netplan import get_all_netplan_interfaces, update_netplan_config, validate_netplan_config
from inetctl.theme import get_theme

netplan_bp = Blueprint('netplan', __name__)

@netplan_bp.route("/", methods=['GET'])
def show_netplan():
    interfaces = get_all_netplan_interfaces()
    theme = get_theme()
    return render_template("netplan_form.html", interfaces=interfaces, theme=theme)

@netplan_bp.route("/update", methods=['POST'])
def update_netplan():
    config_data = request.form.to_dict()
    result, message = update_netplan_config(config_data)
    if result:
        flash("Netplan configuration updated successfully.", "success")
    else:
        flash(f"Error updating netplan: {message}", "danger")
    return redirect(url_for('netplan.show_netplan'))

@netplan_bp.route("/validate", methods=['POST'])
def validate():
    result, message = validate_netplan_config()
    if result:
        flash("Netplan configuration is valid.", "success")
    else:
        flash(f"Validation failed: {message}", "danger")
    return redirect(url_for('netplan.show_netplan'))
