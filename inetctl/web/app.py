import sqlite3
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path

from inetctl.core.config_loader import load_config, save_config, find_config_file
from inetctl.core.utils import (
    get_host_by_mac,
    run_command,
    check_multiple_hosts_online
)

DB_FILE = Path("./inetctl_stats.db")

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-me' # It's okay for local-only app

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    config = load_config()
    all_hosts = config.get("known_hosts", [])
    networks = config.get("networks", [])
    
    # Create a mapping of vlan_id to network name for easy lookup
    network_map = {net['id']: net['name'] for net in networks}
    
    # Group hosts by VLAN
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
         
    # Check online status concurrently
    ips_to_ping = [h['ip_assignment']['ip'] for h in all_hosts if h.get('ip_assignment', {}).get('ip')]
    online_statuses = check_multiple_hosts_online(ips_to_ping)
    
    # Add online status to each host dict
    for vlan_id in hosts_by_vlan:
        for host in hosts_by_vlan[vlan_id]:
             ip = host.get('ip_assignment', {}).get('ip')
             host['is_online'] = online_statuses.get(ip, False)

    return render_template(
        'home.html',
        hosts_by_vlan=hosts_by_vlan,
        network_map=network_map,
        networks=networks # For the "Add Host" modal
    )

@app.route('/host/edit/<host_mac>', methods=['GET', 'POST'])
def edit_host(host_mac):
    config = load_config()
    host, index = get_host_by_mac(config, host_mac) # CORRECTED FUNCTION CALL
    if host is None:
        flash(f'Host with MAC {host_mac} not found.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Update basic info
        host['description'] = request.form['description']
        host['vlan_id'] = request.form['vlan_id']

        # Update IP assignment
        if 'ip_assignment.ip' in request.form and request.form['ip_assignment.ip']:
            host['ip_assignment'] = {
                'type': 'static',
                'ip': request.form['ip_assignment.ip']
            }
        else: # Revert to DHCP
             host['ip_assignment'] = {'type': 'dhcp'}


        # Update block status
        host['network_access_blocked'] = 'network_access_blocked' in request.form
        
        save_config(config)
        flash(f'Host {host.get("hostname", host_mac)} updated successfully!', 'success')
        return redirect(url_for('home'))

    networks = config.get("networks", [])
    return render_template('edit_host.html', host=host, networks=networks)
    
@app.route('/host/add', methods=['POST'])
def add_host():
    config = load_config()
    mac = request.form.get('mac', '').lower().strip()
    
    if not mac:
        flash('MAC address is required.', 'error')
        return redirect(url_for('home'))

    existing_host, _ = get_host_by_mac(config, mac) # CORRECTED FUNCTION CALL
    if existing_host:
        flash(f'Host with MAC {mac} already exists.', 'error')
        return redirect(url_for('home'))

    new_host = {
        "mac": mac,
        "hostname": request.form.get('hostname', '(unknown)').strip(),
        "description": request.form.get('description', '').strip(),
        "vlan_id": request.form.get('vlan_id'),
        "ip_assignment": {'type': 'dhcp'},
        "network_access_blocked": False
    }
    
    if "known_hosts" not in config:
        config["known_hosts"] = []
        
    config['known_hosts'].append(new_host)
    config['known_hosts'] = sorted(config['known_hosts'], key=lambda x: x.get('hostname', 'z'))
    
    save_config(config)
    flash(f"Host {mac} added successfully.", 'success')
    return redirect(url_for('home'))
    
@app.route('/host/delete/<host_mac>', methods=['POST'])
def delete_host(host_mac):
    config = load_config()
    host, index = get_host_by_mac(config, host_mac) # CORRECTED FUNCTION CALL
    
    if index is not None:
        config['known_hosts'].pop(index)
        save_config(config)
        flash(f'Host {host_mac} has been deleted.', 'success')
    else:
        flash(f'Host {host_mac} not found.', 'error')
        
    return redirect(url_for('home'))

@app.route('/host/sync-firewall', methods=['POST'])
def sync_firewall():
    # Use the CLI command as the single source of truth for this action
    result = run_command(["./inetctl-runner.py", "shorewall", "sync"])
    if result['returncode'] == 0:
        flash('Firewall synchronization successful!', 'success')
    else:
        flash(f"Firewall sync failed: {result['stderr']}", 'error')
    return redirect(url_for('home'))
    
@app.route('/data/bandwidth/<host_id>')
def get_bandwidth_data(host_id):
    conn = get_db_connection()
    # Get the last 5 minutes of data
    time_threshold = int(time.time()) - (5 * 60)
    readings = conn.execute(
        'SELECT timestamp, rate_in, rate_out FROM bandwidth WHERE host_id = ? AND timestamp > ? ORDER BY timestamp ASC', 
        (host_id, time_threshold)
    ).fetchall()
    conn.close()
    
    # Format for chart.js
    labels = [time.strftime('%H:%M:%S', time.localtime(r['timestamp'])) for r in readings]
    data_in = [r['rate_in'] for r in readings]
    data_out = [r['rate_out'] for r in readings]
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {'label': 'Download (Mbps)', 'data': data_in, 'borderColor': '#36a2eb'},
            {'label': 'Upload (Mbps)', 'data': data_out, 'borderColor': '#ff6384'}
        ]
    })