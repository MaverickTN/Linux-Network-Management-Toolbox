import sqlite3
import time
import os
import json
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

DB_FILE = Path("./inetctl_stats.db")
app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message, login_manager.login_message_category = "You must be logged in to access this page.", "error"

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                return jsonify({"status": "error", "message": "Permission denied"}), 403
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
    known_hosts_map = {h['mac'].lower(): h for h in config.get("known_hosts", [])}
    leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []
    ips_to_check = {l['ip'] for l in active_leases}
    ips_to_check.update({h.get("ip_assignment", {}).get("ip") for h in known_hosts_map.values() if h.get("ip_assignment", {}).get("ip")})
    online_status_map = check_multiple_hosts_online(list(filter(None, ips_to_check)))
    active_devices, offline_reservations = [], []
    active_macs = {lease['mac'] for lease in active_leases}
    for mac, host_config in known_hosts_map.items():
        is_online = mac in active_macs or online_status_map.get(host_config.get("ip_assignment", {}).get("ip"), False)
        device_data, lease = host_config.copy(), next((l for l in active_leases if l['mac'] == mac), {})
        device_data.update({"is_online": is_online, "ip": lease.get('ip') or host_config.get("ip_assignment", {}).get("ip"), "hostname": lease.get('hostname') or host_config.get("hostname"), "assignment_status": "Reserved"})
        if is_online:
            active_devices.append(device_data)
        else:
            offline_reservations.append(device_data)
    for lease in active_leases:
        if lease['mac'] not in known_hosts_map:
            active_devices.append({"mac": lease['mac'], "ip": lease['ip'], "hostname": lease['hostname'], "description": f"Dynamic ({lease['hostname']})", "is_online": True, "assignment_status": "Dynamic", "network_access_blocked": False})
    networks, network_map = config.get("networks", []), {net['id']: net.get('name', net['id']) for net in config.get("networks", [])}
    active_by_vlan, offline_by_vlan = {}, {}
    all_vlan_ids = set(network_map.keys()) | {'unassigned'}
    for vlan_id in all_vlan_ids: active_by_vlan[vlan_id], offline_by_vlan[vlan_id] = [], []
    for device in active_devices: active_by_vlan.setdefault(device.get("vlan_id", "unassigned"), []).append(device)
    for device in offline_reservations: offline_by_vlan.setdefault(device.get("vlan_id", "unassigned"), []).append(device)
    all_vlan_keys = sorted([k for k in all_vlan_ids if k in network_map or active_by_vlan[k] or offline_by_vlan[k]], key=lambda x: (x == 'unassigned', x))
    return render_template('home.html', all_vlan_keys=all_vlan_keys, active_by_vlan=active_by_vlan, offline_by_vlan=offline_by_vlan, network_map=network_map)
#... All other API routes follow and are included ...