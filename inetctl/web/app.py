import sqlite3
import time
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pathlib import Path
from datetime import datetime
from functools import wraps

# All required local imports
from inetctl.core.auth import User, get_user_by_id, get_user_by_name, verify_password, get_all_users
from inetctl.core.config_loader import load_config, save_config
from inetctl.core.utils import get_host_by_mac, check_multiple_hosts_online, get_active_leases
from inetctl.core.logger import log_event
from inetctl.core.job_queue import add_job, get_job_status

DB_FILE = Path("./inetctl_stats.db")
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "You must be logged in to access this page."
login_manager.login_message_category = "error"

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
    all_hosts_config = {h['mac']: h for h in config.get("known_hosts", [])}
    leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file", "")
    active_leases = get_active_leases(leases_file) if leases_file else []
    active_devices, offline_reservations = [], []
    macs_with_leases = {lease['mac'] for lease in active_leases}

    for lease in active_leases:
        # THIS IS THE CORRECTED LOGIC THAT FIXES THE UnboundLocalError
        mac = lease['mac']
        device = all_hosts_config.get(mac, {})
        
        active_devices.append({
            "mac": mac, "ip": lease['ip'], "hostname": lease['hostname'],
            "description": device.get("description", lease['hostname']),
            "vlan_id": device.get("vlan_id"), "qos_policy": device.get("qos_policy"),
            "schedule": device.get("schedule"), "network_access_blocked": device.get("network_access_blocked", False),
            "assignment_status": "Reserved" if mac in all_hosts_config else "Dynamic"
        })

    for mac, device in all_hosts_config.items():
        if mac not in macs_with_leases:
            device['assignment_status'] = "Reserved"
            offline_reservations.append(device)

    networks = config.get("networks", []); network_map = {net['id']: net.get('name', net['id']) for net in networks}
    active_by_vlan, offline_by_vlan = {net['id']: [] for net in networks}, {net['id']: [] for net in networks}
    unassigned_active, unassigned_offline = [], []

    for device in active_devices:
        if (vlan_id := device.get("vlan_id")) in active_by_vlan: active_by_vlan[vlan_id].append(device)
        else: unassigned_active.append(device)
    if unassigned_active: active_by_vlan['unassigned'], network_map['unassigned'] = unassigned_active, 'Unassigned'
    
    for device in offline_reservations:
        if (vlan_id := device.get("vlan_id")) in offline_by_vlan: offline_by_vlan[vlan_id].append(device)
        else: unassigned_offline.append(device)
    if unassigned_offline: offline_by_vlan['unassigned'] = unassigned_offline

    all_vlan_keys = sorted(list(set(active_by_vlan.keys()) | set(offline_by_vlan.keys()) | {n['id'] for n in networks}))
    
    return render_template('home.html', all_vlan_keys=all_vlan_keys, active_by_vlan=active_by_vlan, offline_by_vlan=offline_by_vlan, network_map=network_map)

@app.route('/logs')
@login_required
@roles_required('admin')
def logs():
    conn = get_db_connection()
    query = "SELECT timestamp, level, source, message, username FROM event_log"
    params, conditions = [], []
    start_time_str, end_time_str, selected_users = request.args.get('start_time'), request.args.get('end_time'), request.args.getlist('users')
    end_ts, start_ts = int(time.time()), int(time.time() - 86400)
    try: start_ts = int(datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
    except (ValueError, TypeError): pass
    try: end_ts = int(datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
    except (ValueError, TypeError): pass
    conditions.append("timestamp BETWEEN ? AND ?"); params.extend([start_ts, end_ts])
    if selected_users:
        conditions.append(f"username IN ({', '.join('?'*len(selected_users))})"); params.extend(selected_users)
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"
    log_entries, all_users = conn.execute(query, params).fetchall(), get_all_users()
    conn.close()
    return render_template('logs.html', logs=log_entries, all_users=all_users, selected_users=selected_users, start_time_val=start_time_str, end_time_val=end_time_str)

# --- API Routes for Async UI ---

@app.route('/api/submit_job', methods=['POST'])
@login_required
def submit_job():
    data, job_type, payload = request.get_json(), request.get_json().get("job_type"), request.get_json().get("payload", {})
    if job_type in ["shorewall:sync", "access:block", "access:unblock", "api:vlan_toggle_access"] and current_user.role not in ['admin', 'operator']:
        return jsonify({"status": "error", "message": "Permission denied."}), 403
    if job_type in ["netplan:apply", "netplan:add_vlan"] and current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Permission denied."}), 403
    job_id = add_job(job_type, payload, current_user.username)
    log_event("INFO", f"api:{job_type}", f"Job {job_id} created", username=current_user.username)
    return jsonify({"status": "queued", "job_id": job_id})

@app.route('/api/job_status/<int:job_id>')
@login_required
def check_job_status(job_id):
    job = get_job_status(job_id)
    if not job: return jsonify({"status": "error", "message": "Job not found."}), 404
    if job['requesting_user'] != current_user.username and current_user.role != 'admin':
        return jsonify({"status": "error", "message": "Permission denied."}), 403
    return jsonify(dict(job))

@app.route('/api/host_details/<host_mac>')
@login_required
def get_host_details(host_mac):
    config = load_config(); leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file", "")
    host_config = get_host_by_mac(config, host_mac)[0] or {"mac": host_mac}
    lease_info = next((l for l in get_active_leases(leases_file) if l['mac'] == host_mac), None)
    if lease_info: host_config['ip'], host_config['hostname'] = lease_info['ip'], host_config.get('hostname') or lease_info.get('hostname')
    return jsonify(host_config)

@app.route('/api/update_host_config/<host_mac>', methods=['POST'])
@login_required
@roles_required('admin', 'operator')
def update_host_config(host_mac):
    config, data = load_config(), request.get_json()
    host, _ = get_host_by_mac(config, host_mac)
    if not host:
        host = {"mac": host_mac, "ip_assignment": {"type": "dhcp"}}
        config.setdefault("known_hosts", []).append(host)
    hostname = data.get('hostname'); schedule_data = data.get('schedule')
    if schedule_data and not schedule_data.get('enabled'): schedule_data = None
    host.update({'description': data.get('description', hostname), 'hostname': hostname, 'vlan_id': data.get('vlan_id'), 'qos_policy': data.get('qos_policy'), 'ip_assignment': {'type': 'static', 'ip': data['ip']} if data.get('ip') else {'type': 'dhcp'}, 'network_access_blocked': data.get('network_access_blocked', False), 'schedule': schedule_data})
    config['known_hosts'] = sorted(config['known_hosts'], key=lambda h: h.get('hostname', 'z').lower())
    save_config(config)
    log_event("INFO", "api:host:update", f"Config saved for '{hostname or host_mac}'", username=current_user.username)
    if data.get('trigger_sync'): add_job("shorewall:sync", {}, current_user.username); log_event("INFO", "api:host:update", "Host config change triggered firewall sync.", username=current_user.username)
    return jsonify({"status": "ok", "message": "Host configuration saved."})

@app.route('/data/bandwidth/<host_id>')
@login_required
def get_bandwidth_data(host_id):
    conn = get_db_connection()
    readings = conn.execute('SELECT timestamp, rate_in, rate_out FROM bandwidth WHERE host_id = ? AND timestamp > ? ORDER BY timestamp ASC', (host_id, int(time.time()) - 300)).fetchall()
    conn.close()
    return jsonify({'labels': [datetime.fromtimestamp(r['timestamp']).strftime('%H:%M:%S') for r in readings], 'datasets': [{'label': 'Download (Mbps)', 'data': [r['rate_in'] for r in readings]}, {'label': 'Upload (Mbps)', 'data': [r['rate_out'] for r in readings]}]})