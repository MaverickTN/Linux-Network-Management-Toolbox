import sqlite3
import time
import os
import ipaddress
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pathlib import Path
from datetime import datetime
from functools import wraps

from inetctl.core.auth import User, get_user_by_id, get_user_by_name, verify_password, get_all_users
from inetctl.core.config_loader import load_config, save_config
from inetctl.core.utils import get_host_by_mac, check_multiple_hosts_online, get_active_leases
from inetctl.core.logger import log_event
from inetctl.core.job_queue import add_job, get_job_status
from inetctl.core.netplan import load_netplan_config

DB_FILE = Path("./inetctl_stats.db")
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message, login_manager.login_message_category = "You must be logged in.", "error"

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated: return login_manager.unauthorized()
            if current_user.role not in roles: return jsonify({"status": "error", "message": "Permission denied"}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.template_filter("format_datetime")
def format_datetime_filter(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        username, password = request.form["username"], request.form["password"]
        user_obj, password_hash = get_user_by_name(username)
        if user_obj and verify_password(password, password_hash):
            login_user(user_obj)
            log_event("INFO", "auth:login", f"User '{username}' logged in.", username=username)
            return redirect(url_for("home"))
        flash("Invalid username or password.", "error")
        log_event("WARNING", "auth:login", f"Failed login for '{username}'.", username="anonymous")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    log_event("INFO", "auth:logout", f"User '{current_user.username}' logged out.", username=current_user.username)
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    config = load_config()
    netplan = load_netplan_config()

    # Add base interface as VLAN 1
    networks = []
    base_iface = netplan.get('base_interface', 'eth0')
    base_name = netplan.get('base_name', 'Base')
    networks.append({'id': '1', 'interface': base_iface, 'name': base_name, 'cidr': config.get('base_cidr', '192.168.1.0/24')})
    for vlan_name, vlan_def in netplan['network'].get('vlans', {}).items():
        networks.append({
            'id': str(vlan_def['id']),
            'interface': vlan_name,
            'name': vlan_name,
            'cidr': vlan_def.get('cidr', '192.168.100.0/24')
        })

    vlan_ids = sorted([net['id'] for net in networks], key=int)
    network_map = {net['id']: net['name'] for net in networks}
    subnet_map = {ipaddress.ip_network(net['cidr']): net['id'] for net in networks if net.get('cidr')}

    known_hosts_map = {h['mac'].lower(): h for h in config.get("known_hosts", [])}
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []

    ips_to_check = {l['ip'] for l in active_leases} | {h.get("ip_assignment", {}).get("ip") for h in known_hosts_map.values() if h.get("ip_assignment", {}).get("ip")}
    online_status_map = check_multiple_hosts_online(list(filter(None, ips_to_check)))

    devices = []
    processed_macs = set()
    for mac, host_config in known_hosts_map.items():
        processed_macs.add(mac)
        lease = next((l for l in active_leases if l['mac'] == mac), None)
        static_ip = host_config.get("ip_assignment", {}).get("ip")
        is_online = mac in {l['mac'] for l in active_leases} or (static_ip and online_status_map.get(static_ip, False))
        device_vlan_id = str(host_config.get('vlan_id', '1'))  # default to '1'

        device = host_config.copy()
        device.update({
            "is_online": is_online,
            "assignment_status": "Reservation",
            "ip": (lease['ip'] if lease else static_ip),
            "hostname": (lease.get('hostname') if lease and lease.get('hostname') != '(unknown)' else host_config.get('hostname')),
            "vlan_id": device_vlan_id,
            "network_access_blocked": host_config.get("network_access_blocked", False),
        })
        device["is_active"] = bool(lease)
        devices.append(device)

    for lease in active_leases:
        if lease['mac'] not in processed_macs:
            vlan_id = None
            for net, vid in subnet_map.items():
                try:
                    if ipaddress.ip_address(lease['ip']) in net:
                        vlan_id = vid
                        break
                except Exception:
                    continue
            if vlan_id is None:
                vlan_id = '1'
            devices.append({
                "mac": lease['mac'],
                "ip": lease['ip'],
                "hostname": lease['hostname'],
                "description": lease['hostname'],
                "is_online": True,
                "assignment_status": "Dynamic",
                "vlan_id": vlan_id,
                "network_access_blocked": False,
                "is_active": True,
            })

    active_by_vlan = {vlan_id: [] for vlan_id in vlan_ids}
    offline_by_vlan = {vlan_id: [] for vlan_id in vlan_ids}
    unassigned_by_vlan = {vlan_id: [] for vlan_id in vlan_ids}

    for d in devices:
        vlan_id = d.get('vlan_id', '1')
        if d.get('assignment_status') == "Reservation":
            if d.get("is_active"):
                active_by_vlan[vlan_id].append(d)
            else:
                unassigned_by_vlan[vlan_id].append(d)
        else:
            active_by_vlan[vlan_id].append(d)

    return render_template(
        "home.html",
        vlan_ids=vlan_ids,
        active_by_vlan=active_by_vlan,
        unassigned_by_vlan=unassigned_by_vlan,
        network_map=network_map,
        offline_by_vlan=offline_by_vlan,
        current_user=current_user,
    )

@app.route("/toggle_access", methods=["POST"])
@login_required
def toggle_access():
    data = request.get_json()
    mac = data.get("mac", "").lower()
    config = load_config()
    hosts = config.get("known_hosts", [])
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []

    host = next((h for h in hosts if h.get("mac", "").lower() == mac), None)
    if not host:
        return jsonify(success=False, message="Host not found"), 404
    lease = next((l for l in active_leases if l['mac'].lower() == mac), None)
    ip = lease['ip'] if lease else host.get("ip_assignment", {}).get("ip")
    if not ip:
        return jsonify(success=False, message="Could not determine IP for host"), 400

    blocked = host.get("network_access_blocked", False)
    job_type = "block_access" if not blocked else "allow_access"
    job_payload = {
        "mac": mac,
        "ip": ip,
        "username": current_user.username
    }
    job_id = add_job(job_type, job_payload)
    return jsonify(success=True, queued=True, job_id=job_id,
                   message=f"{'Block' if not blocked else 'Allow'} request queued for {ip}.")

@app.route("/job_status/<job_id>")
@login_required
def job_status(job_id):
    status = get_job_status(job_id)
    return jsonify(status)

@app.route("/api/transfer/<mac>")
@login_required
def transfer_api(mac):
    hours = int(request.args.get("hours", 1))
    end_time = int(time.time())
    start_time = end_time - (hours * 3600)
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT timestamp, rx, tx FROM transfers WHERE mac = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
        (mac.lower(), start_time, end_time)
    ).fetchall()
    conn.close()
    return jsonify([
        {"timestamp": row["timestamp"], "rx": row["rx"], "tx": row["tx"]} for row in rows
    ])

@app.route("/api/host/<mac>", methods=["GET", "POST"])
@login_required
def api_host(mac):
    config = load_config()
    hosts = config.get("known_hosts", [])
    host = next((h for h in hosts if h.get("mac", "").lower() == mac.lower()), None)
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []
    lease = next((l for l in active_leases if l['mac'].lower() == mac.lower()), None)
    vlan_id = str(host.get('vlan_id', '1')) if host else "1"
    netplan = load_netplan_config()
    vlan_cfg = None
    if vlan_id == "1":
        vlan_cfg = {"cidr": config.get('base_cidr', '192.168.1.0/24')}
    else:
        vlan_cfg = next((v for v in netplan['network'].get('vlans', {}).values() if str(v['id']) == vlan_id), None)
    subnet = vlan_cfg['cidr'] if vlan_cfg and 'cidr' in vlan_cfg else "255.255.255.0"
    if request.method == "GET":
        return jsonify({
            "mac": mac,
            "description": host.get('description', '') if host else '',
            "ip": lease['ip'] if lease else (host.get('ip_assignment', {}).get('ip', '') if host else ''),
            "subnet": subnet,
            "qos_profile": host.get('qos_profile', 'Default') if host else "Default",
            "qos_dl": host.get('qos_dl', '') if host else '',
            "qos_ul": host.get('qos_ul', '') if host else '',
            "schedule": host.get('schedule', '') if host else ''
        })
    if request.method == "POST":
        data = request.get_json()
        if not host:
            return jsonify(success=False, message="Host not found"), 404
        host['description'] = data.get('description', '')
        if 'ip_assignment' not in host:
            host['ip_assignment'] = {}
        host['ip_assignment']['ip'] = data.get('ip', '')
        host['qos_profile'] = data.get('qos_profile', 'Default')
        host['qos_dl'] = data.get('qos_dl', '')
        host['qos_ul'] = data.get('qos_ul', '')
        host['schedule'] = data.get('schedule', '')
        save_config(config)
        return jsonify(success=True)
