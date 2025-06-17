import os
from flask import Flask, render_template, jsonify, request, redirect, url_for
from inetctl.core import netplan
from inetctl.core import dnsmasq
from inetctl.core import config_loader
from inetctl.job_queue_service import JobQueueService
from datetime import datetime

# Set your site title in one place
APP_TITLE = "Linux Network Management Toolbox"

app = Flask(__name__)
queue = JobQueueService()

# Utility: get VLANs and mapping from netplan
def get_vlan_list_and_map():
    interfaces = netplan.get_all_netplan_interfaces()
    vlan_map = {}
    vlan_list = []
    for iface in interfaces:
        vlan_id = iface.get('vlan_id', '1') if iface['type'] == 'vlan' else '1'
        vlan_list.append({'id': vlan_id, 'name': iface['name']})
        vlan_map[vlan_id] = iface['subnet']
    return vlan_list, vlan_map

@app.route("/")
def home():
    vlan_list, vlan_map = get_vlan_list_and_map()
    hosts_by_vlan = {vlan['id']: [] for vlan in vlan_list}

    # DHCP assignments (example using your dnsmasq parser)
    all_assignments = dnsmasq.get_active_assignments()
    for host in all_assignments:
        ip = host.get("ip")
        # Find VLAN by subnet match
        vlan_id = "1"
        for vid, subnet in vlan_map.items():
            if ip and dnsmasq.ip_in_subnet(ip, subnet):
                vlan_id = vid
                break
        host['assignment_type'] = 'Reservation' if host.get('reservation') else 'Dynamic'
        host['blocked'] = host.get('blocked', False)
        host['status'] = "blocked" if host['blocked'] else "online"
        hosts_by_vlan.setdefault(vlan_id, []).append(host)

    # Compose per-vlan lists for template
    vlan_hosts = []
    for vlan in vlan_list:
        hosts = hosts_by_vlan.get(vlan['id'], [])
        active_hosts = [h for h in hosts if h.get("active", True)]
        unassigned_reservations = [h for h in hosts if not h.get("active", True) and h.get('reservation')]
        vlan_hosts.append({
            "id": vlan['id'],
            "active_hosts": active_hosts,
            "unassigned_reservations": unassigned_reservations
        })

    return render_template(
        "home.html",
        app_title=APP_TITLE,
        vlan_list=vlan_hosts,
        selected_vlan=vlan_hosts[0]["id"] if vlan_hosts else "1"
    )

@app.route("/toggle_access", methods=["POST"])
def toggle_access():
    data = request.get_json()
    mac = data.get('mac')
    job_id = queue.add_job("toggle_access", mac=mac)
    return jsonify({"queued": True, "message": "Access change queued.", "job_id": job_id})

@app.route("/job_status/<job_id>")
def job_status(job_id):
    status, message = queue.get_status(job_id)
    return jsonify({"status": status, "message": message})

@app.route("/api/transfer/<mac>")
def api_transfer(mac):
    hours = int(request.args.get("hours", 1))
    # Implement actual traffic query for this MAC; dummy data here:
    now = int(datetime.now().timestamp())
    data = [
        {"timestamp": now - 3600 + i * 60, "rx": 200000 + i*1000, "tx": 50000 + i*500}
        for i in range(60)
    ]
    return jsonify(data)

@app.route("/api/host/<mac>", methods=["GET", "POST"])
def api_host(mac):
    if request.method == "GET":
        # Query from db, or dummy
        host = dnsmasq.get_host_info(mac)
        return jsonify({
            "mac": mac,
            "description": host.get('description', ''),
            "ip": host.get('ip', '10.0.0.1'),
            "subnet": host.get('subnet', '255.255.255.0'),
            "qos_profile": host.get('qos_profile', 'Default'),
            "qos_dl": host.get('qos_dl', ''),
            "qos_ul": host.get('qos_ul', ''),
            "schedule": host.get('schedule', '')
        })
    else:
        data = request.get_json()
        # Schedule update via job queue
        job_id = queue.add_job("update_host", **data)
        return jsonify({"success": True, "job_id": job_id})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
