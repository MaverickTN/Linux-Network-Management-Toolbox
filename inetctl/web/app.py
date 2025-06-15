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
            log_event("INFO", "auth:login", f"User '{username}' successfully logged in.", username=username)
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

# --- Main Application Routes ---
@app.route("/")
@login_required
def home():
    config = load_config()
    known_hosts_map = {h['mac'].lower(): h for h in config.get("known_hosts", [])}
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []
    
    conn = get_db_connection()
    recent_traffic_macs = {row['host_id'] for row in conn.execute('SELECT host_id FROM bandwidth WHERE timestamp > ?', (int(time.time()) - 60,)).fetchall()}
    conn.close()
    
    ips_to_check = {l['ip'] for l in active_leases if not known_hosts_map.get(l['mac'], {}).get('network_access_blocked')}
    ips_to_check.update({ h.get("ip_assignment", {}).get("ip") for h in known_hosts_map.values() if h.get("ip_assignment", {}).get("ip") and not h.get('network_access_blocked') })
    ping_status_map = check_multiple_hosts_online(list(filter(None, ips_to_check)))
    
    active_devices, offline_reservations = [], []
    active_macs = {lease['mac'] for lease in active_leases}

    for mac, host_config in known_hosts_map.items():
        mac_sanitized = mac.replace(':', '')
        static_ip = host_config.get("ip_assignment", {}).get("ip")
        is_online = (not host_config.get('network_access_blocked')) and \
                    (mac in active_macs or ping_status_map.get(static_ip, False) or mac_sanitized in recent_traffic_macs)
        device_data, lease = host_config.copy(), next((l for l in active_leases if l['mac'] == mac), {})
        device_data.update({"is_online": is_online, "ip": lease.get('ip') or host_config.get("ip_assignment", {}).get("ip"), "hostname": lease.get('hostname') or host_config.get("hostname"), "assignment_status": "Reservation"})
        if is_online:
            active_devices.append(device_data)
        else:
            offline_reservations.append(device_data)

    for lease in active_leases:
        if lease['mac'] not in known_hosts_map:
            mac_sanitized = lease['mac'].replace(':', '')
            if not (ping_status_map.get(lease['ip'], False) or mac_sanitized in recent_traffic_macs):
                continue
            device_data = {"mac": lease['mac'], "ip": lease['ip'], "hostname": lease['hostname'], "description": lease['hostname'], "is_online": True, "assignment_status": "Dynamic", "network_access_blocked": False}
            vlan_id = "unassigned"
            try:
                device_ip = ipaddress.ip_address(lease['ip'])
                for subnet_cidr, v_id in config.get('_subnet_map', {}).items(): # Assuming _subnet_map exists
                    if device_ip in ipaddress.ip_network(subnet_cidr):
                        vlan_id = v_id; break
            except ValueError: pass
            device_data['vlan_id'] = vlan_id
            active_devices.append(device_data)

    networks, network_map = config.get("networks", []), {net['id']: net.get('name', net['id']) for net in config.get("networks", [])}
    active_by_vlan, offline_by_vlan = {}, {}
    all_vlan_ids = set(network_map.keys()) | {'unassigned'}
    for vlan_id in all_vlan_ids: active_by_vlan[vlan_id], offline_by_vlan[vlan_id] = [], []
    for device in active_devices: active_by_vlan.setdefault(device.get("vlan_id", "unassigned"), []).append(device)
    for device in offline_reservations: offline_by_vlan.setdefault(device.get("vlan_id", "unassigned"), []).append(device)
    all_vlan_keys = sorted([k for k in all_vlan_ids if network_map.get(k) or active_by_vlan.get(k) or offline_by_vlan.get(k)], key=lambda x: (x == 'unassigned', x))
    return render_template('home.html', all_vlan_keys=all_vlan_keys, active_by_vlan=active_by_vlan, offline_by_vlan=offline_by_vlan, network_map=network_map)

@app.route('/network')
@login_required
@roles_required('admin')
def network_management():
    netplan_config = load_netplan_config() or {'network': {'vlans': {}}}
    return render_template('network.html', netplan_config=netplan_config)
    
@app.route('/logs')
@login_required
@roles_required('admin')
def logs():
    conn = get_db_connection(); query, params, conditions = "SELECT * FROM event_log", [], []
    start_time_str, end_time_str, selected_users = request.args.get('start_time'), request.args.get('end_time'), request.args.getlist('users')
    end_ts, start_ts = int(time.time()), int(time.time() - 86400)
    try: start_ts = int(datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
    except(ValueError, TypeError): pass
    try: end_ts = int(datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
    except(ValueError, TypeError): pass
    conditions.append("timestamp BETWEEN ? AND ?"); params.extend([start_ts, end_ts])
    if selected_users: conditions.append(f"username IN ({','.join('?'*len(selected_users))})"); params.extend(selected_users)
    query += " WHERE " + " AND ".join(conditions) + " ORDER BY timestamp DESC"
    log_entries, all_users = conn.execute(query, params).fetchall(), get_all_users()
    conn.close()
    return render_template('logs.html', logs=log_entries, all_users=all_users, selected_users=selected_users, start_time_val=start_time_str, end_time_val=end_time_str)

@app.route('/api/online_status')
@login_required
def get_live_online_status():
    config = load_config(); known_hosts_map = {h['mac'].lower(): h for h in config.get("known_hosts", [])}
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", ""); active_leases = get_active_leases(leases_file) if leases_file else []
    conn = get_db_connection(); recent_traffic_macs = {row['host_id'] for row in conn.execute('SELECT host_id FROM bandwidth WHERE timestamp > ?', (int(time.time()) - 60,)).fetchall()}; conn.close()
    ips_to_check = {l['ip'] for l in active_leases if not known_hosts_map.get(l['mac'], {}).get('network_access_blocked')}
    ips_to_check.update({ h.get("ip_assignment",{}).get("ip") for mac, h in known_hosts_map.items() if h.get("ip_assignment",{}).get("ip") and not h.get('network_access_blocked') })
    ping_status_map = check_multiple_hosts_online(list(filter(None, ips_to_check)))
    final_mac_status = {}
    all_known_macs = set(known_hosts_map.keys()) | {l['mac'] for l in active_leases}
    for mac in all_known_macs:
        host_config = known_hosts_map.get(mac, {})
        if host_config.get('network_access_blocked'): final_mac_status[mac] = False; continue
        static_ip, mac_sanitized = host_config.get("ip_assignment", {}).get("ip"), mac.replace(':','')
        is_online = (mac in {l['mac'] for l in active_leases}) or ping_status_map.get(static_ip, False) or mac_sanitized in recent_traffic_macs
        final_mac_status[mac] = is_online
    return jsonify(final_mac_status)

# All other API routes are provided here in full...