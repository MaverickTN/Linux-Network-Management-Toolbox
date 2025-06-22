# inetctl/web/routes/dhcp_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from inetctl.core.dnsmasq import (
    get_active_leases,
    get_reservations,
    add_reservation,
    remove_reservation,
    reload_dnsmasq
)
from inetctl.core.netplan import get_vlan_for_ip
from inetctl.Job_queue_service import JobQueueService

bp_dhcp = Blueprint('dhcp', __name__, url_prefix='/dhcp')

@bp_dhcp.route("/", methods=["GET"])
def dhcp_overview():
    leases = get_active_leases()
    reservations = get_reservations()
    # Enrich lease data with VLANs (if needed)
    for lease in leases:
        lease["vlan"] = get_vlan_for_ip(lease.get("ip"))
    return render_template(
        "dhcp.html",
        leases=leases,
        reservations=reservations,
        title="DHCP Assignments"
    )

@bp_dhcp.route("/reserve", methods=["POST"])
def dhcp_reserve():
    mac = request.form.get("mac")
    ip = request.form.get("ip")
    hostname = request.form.get("hostname")
    vlan = request.form.get("vlan")
    # Queue the reservation for safety
    def do_reservation():
        add_reservation(mac, ip, hostname, vlan)
        reload_dnsmasq()
    JobQueueService.enqueue(
        description=f"Create DHCP Reservation for {hostname or mac}",
        steps=[do_reservation],
        notify_users=True
    )
    flash("Reservation queued for creation.", "info")
    return redirect(url_for("dhcp.dhcp_overview"))

@bp_dhcp.route("/remove_reservation/<mac>", methods=["POST"])
def dhcp_remove_reservation(mac):
    def do_remove():
        remove_reservation(mac)
        reload_dnsmasq()
    JobQueueService.enqueue(
        description=f"Remove DHCP Reservation for {mac}",
        steps=[do_remove],
        notify_users=True
    )
    flash("Reservation queued for removal.", "info")
    return redirect(url_for("dhcp.dhcp_overview"))

@bp_dhcp.route("/leases", methods=["GET"])
def dhcp_leases_json():
    # API endpoint for dynamic tables/ajax
    leases = get_active_leases()
    for lease in leases:
        lease["vlan"] = get_vlan_for_ip(lease.get("ip"))
    return jsonify(leases)
