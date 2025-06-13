import sqlite3
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path
from datetime import datetime

from inetctl.core.config_loader import load_config, save_config
from inetctl.core.utils import (
    get_host_by_mac,
    run_command,
    check_multiple_hosts_online
)
from inetctl.core.logger import log_event

DB_FILE = Path("./inetctl_stats.db")

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-me' 

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.template_filter('format_datetime')
def format_datetime_filter(unix_timestamp):
    """Jinja2 filter to format a Unix timestamp into a readable string."""
    if unix_timestamp is None:
        return 'N/A'
    return datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def home():
    config = load_config()
    all_hosts = config.get("known_hosts", [])
    networks = config.get("networks", [])
    network_map = {net['id']: net['name'] for net in networks}
    hosts_by_vlan = {net['id']: [] for net in networks}
    unassigned_hosts = []

    for host in all_hosts:
        vlan_id = host.get("vlan_id")
        if vlan_id in hosts_by_vlan:
            hosts_by_vlan[vlan_id].append(host)
        else:
            unassigned_hosts.append(host)

    if unassigned_hosts:
         hosts_by_vlan['unassigned'] = unassigned_hosts
         network_map['unassigned'] = 'Unassigned'
         
    ips_to_ping = [h['ip_assignment']['ip'] for h in all_hosts if h.get('ip_assignment', {}).get('ip')]
    online_statuses = check_multiple_hosts_online(ips_to_ping)
    
    for vlan_id in hosts_by_vlan:
        for host in hosts_by_vlan[vlan_id]:
             ip = host.get('ip_assignment', {}).get('ip')
             host['is_online'] = online_statuses.get(ip, False)

    return render_template('home.html', hosts_by_vlan=hosts_by_vlan, network_map=network_map, networks=networks)

@app.route('/logs')
def logs():
    """Displays the event log with filtering."""
    conn = get_db_connection()
    query = "SELECT timestamp, level, source, message FROM event_log"
    params = []

    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    # Default to last 24 hours if no params given
    end_ts = int(time.time())
    start_ts = end_ts - 86400

    if start_time_str:
        try:
            start_ts = int(datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
        except ValueError:
            pass # Use default if format is bad

    if end_time_str:
        try:
            end_ts = int(datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S').timestamp())
        except ValueError:
            pass # Use default if format is bad

    query += " WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp DESC"
    params.extend([start_ts, end_ts])

    log_entries = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('logs.html', logs=log_entries)

@app.route('/host/edit/<host_mac>', methods=['GET', 'POST'])
def edit_host(host_mac):
    config = load_config()
    host, index = get_host_by_mac(config, host_mac)
    if host is None:
        flash(f'Host with MAC {host_mac} not found.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        host['description'] = request.form['description']
        host['vlan_id'] = request.form['vlan_id']

        if 'ip_assignment.ip' in request.form and request.form['ip_assignment.ip']:
            host['ip_assignment'] = {'type': 'static', 'ip': request.form['ip_assignment.ip']}
        else:
            host['ip_assignment'] = {'type': 'dhcp'}

        host['network_access_blocked'] = 'network_access_blocked' in request.form
        
        save_config(config)
        log_event("INFO", "web:host", f"Host configuration updated for {host.get('hostname', host_mac)}.")
        flash(f'Host {host.get("hostname", host_mac)} updated successfully!', 'success')
        return redirect(url_for('home'))

    networks = config.get("networks", [])
    return render_template('edit_host.html', host=host, networks=networks)
    
@app.route('/host/add', methods=['POST'])
def add_host():
    config = load_config()
    mac = request.form.get('mac', '').lower().strip()
    hostname = request.form.get('hostname', '(unknown)').strip()
    
    if not mac:
        flash('MAC address is required.', 'error'); return redirect(url_for('home'))

    if get_host_by_mac(config, mac)[0]:
        flash(f'Host with MAC {mac} already exists.', 'error'); return redirect(url_for('home'))

    new_host = {
        "mac": mac, "hostname": hostname,
        "description": request.form.get('description', '').strip(),
        "vlan_id": request.form.get('vlan_id'),
        "ip_assignment": {'type': 'dhcp'}, "network_access_blocked": False
    }
    config.setdefault("known_hosts", []).append(new_host)
    config['known_hosts'] = sorted(config['known_hosts'], key=lambda x: x.get('hostname', 'z'))
    
    save_config(config)
    log_event("INFO", "web:host", f"New host added: {hostname} ({mac}).")
    flash(f"Host {hostname} added successfully.", 'success')
    return redirect(url_for('home'))
    
@app.route('/host/delete/<host_mac>', methods=['POST'])
def delete_host(host_mac):
    config = load_config()
    host, index = get_host_by_mac(config, host_mac)
    
    if index is not None:
        hostname = host.get("hostname", host_mac)
        config['known_hosts'].pop(index)
        save_config(config)
        log_event("INFO", "web:host", f"Host deleted: {hostname} ({host_mac}).")
        flash(f'Host {hostname} has been deleted.', 'success')
    else:
        flash(f'Host {host_mac} not found.', 'error')
    return redirect(url_for('home'))

@app.route('/host/sync-firewall', methods=['POST'])
def sync_firewall():
    log_event("INFO", "web:sync", "Firewall synchronization triggered from web UI.")
    result = run_command(["./inetctl-runner.py", "shorewall", "sync"])
    if result['returncode'] == 0:
        flash('Firewall synchronization successful!', 'success')
    else:
        log_event("ERROR", "web:sync", f"Firewall sync failed: {result['stderr']}")
        flash(f"Firewall sync failed: {result['stderr']}", 'error')
    return redirect(url_for('home'))
    
@app.route('/data/bandwidth/<host_id>')
def get_bandwidth_data(host_id):
    conn = get_db_connection()
    time_threshold = int(time.time()) - (5 * 60)
    readings = conn.execute(
        'SELECT timestamp, rate_in, rate_out FROM bandwidth WHERE host_id = ? AND timestamp > ? ORDER BY timestamp ASC', 
        (host_id, time_threshold)
    ).fetchall()
    conn.close()
    
    labels = [datetime.fromtimestamp(r['timestamp']).strftime('%H:%M:%S') for r in readings]
    data_in = [r['rate_in'] for r in readings]
    data_out = [r['rate_out'] for r in readings]
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {'label': 'Download (Mbps)', 'data': data_in, 'borderColor': '#36a2eb'},
            {'label': 'Upload (Mbps)', 'data': data_out, 'borderColor': '#ff6384'}
        ]
    })