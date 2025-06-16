import sqlite3
import time
import os
import json
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

# --- Role-based Access Decorator ---
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

# --- Authentication Routes ---
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
    known_hosts_map = {h['mac'].lower(): h for h in config.get("known_hosts", [])}
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []
    networks = config.get("networks", [])
    network_map = {net['id']: net.get('name', net['id']) for net in networks}
    subnet_map = {ipaddress.ip_network(net['cidr']): net['id'] for net in networks if net.get('cidr')}

    ips_to_check = {l['ip'] for l in active_leases} | {h.get("ip_assignment", {}).get("ip") for h in known_hosts_map.values() if h.get("ip_assignment", {}).get("ip")}
    online_status_map = check_multiple_hosts_online(list(filter(None, ips_to_check)))

    devices = []
    processed_macs = set()
    for mac, host_config in known_hosts_map.items():
        processed_macs.add(mac)
        lease = next((l for l in active_leases if l['mac'] == mac), None)
        static_ip = host_config.get("ip_assignment", {}).get("ip")
        is_online = mac in {l['mac'] for l in active_leases} or (static_ip and online_status_map.get(static_ip, False))

        device = host_config.copy()
        device.update({
            "is_online": is_online,
            "assignment_status": "Reservation",  # Reserved static assignment
            "ip": (lease['ip'] if lease else static_ip),
            "hostname": (lease.get('hostname') if lease and lease.get('hostname') != '(unknown)' else host_config.get('hostname')),
            "vlan_id": host_config.get('vlan_id', 'unassigned'),
            "network_access_blocked": host_config.get("network_access_blocked", False),
        })
        device["is_active"] = bool(lease)  # True if lease is active for reservation
        devices.append(device)

    for lease in active_leases:
        if lease['mac'] not in processed_macs:
            vlan_id = next((vid for net, vid in subnet_map.items() if ipaddress.ip_address(lease['ip']) in net), "unassigned")
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

    active_by_vlan = {}
    offline_by_vlan = {}
    unassigned_by_vlan = {}

    if 'unassigned' not in network_map:
        network_map['unassigned'] = 'Unassigned'

    all_vlan_ids = set(network_map.keys())
    for vlan_id in all_vlan_ids:
        active_by_vlan[vlan_id] = []
        offline_by_vlan[vlan_id] = []
        unassigned_by_vlan[vlan_id] = []

    for d in devices:
        vlan_id = d.get('vlan_id', 'unassigned')
        if d.get('assignment_status') == "Reservation":
            if d.get("is_active"):
                active_by_vlan[vlan_id].append(d)  # Reserved and assigned
            else:
                unassigned_by_vlan[vlan_id].append(d)  # Reserved but not assigned
        else:
            active_by_vlan[vlan_id].append(d)

    return render_template(
        "home.html",
        vlan_ids=list(all_vlan_ids),
        active_by_vlan=active_by_vlan,
        unassigned_by_vlan=unassigned_by_vlan,
        network_map=network_map,
        offline_by_vlan=offline_by_vlan,
        current_user=current_user,
    )

# (Other routes can follow below...)
