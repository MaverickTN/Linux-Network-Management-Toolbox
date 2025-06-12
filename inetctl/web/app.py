import base64
import ipaddress
import os
import re
import sqlite3
import sys
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml
from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, url_for)

from inetctl.cli.access import app as access_cli_app
from inetctl.core.config_loader import load_config, save_config
from inetctl.core.netplan import (add_route_to_netplan_interface,
                                  delete_route_from_netplan_interface,
                                  get_all_netplan_interfaces,
                                  update_netplan_interface)
from inetctl.core.utils import (check_multiple_hosts_online,
                                check_root_privileges, get_active_leases,
                                get_host_config_by_id, get_subnet_from_netplan,
                                run_command)

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)
DB_FILE = "./inetctl_stats.db"


def get_dashboard_data() -> Dict[str, Any]:
    config = load_config(force_reload=True)
    gs = config.get("global_settings", {})
    
    static_reservations = config.get("hosts_dhcp_reservations", [])
    active_leases = get_active_leases(gs.get("dnsmasq_leases_file", ""), static_reservations)
    networks_config = config.get("networks", [])
    policies = {p['id']: p for p in config.get("traffic_control_policies", [])}

    subnet_to_vlan_map = {}
    vlan_id_to_name_map = {}
    all_vlan_names = set()
    netplan_interfaces = get_all_netplan_interfaces(gs)

    for iface in netplan_interfaces:
        if not iface.get("addresses"):
            continue
        try:
            subnet = ipaddress.ip_network(iface["addresses"][0], strict=False)
            vlan_id_match = re.search(r'\.(\d+)$', iface['interface'])
            vlan_id = int(vlan_id_match.group(1)) if vlan_id_match else None
            network_conf = next((n for n in networks_config if n.get("vlan_id") == vlan_id), None)
            vlan_name = network_conf.get("name") if network_conf else f"VLAN {vlan_id}" if vlan_id else iface['interface']
            subnet_to_vlan_map[subnet] = vlan_name
            all_vlan_names.add(vlan_name)
            if vlan_id: vlan_id_to_name_map[vlan_id] = vlan_name
        except (ValueError, IndexError):
            continue
            
    for net in networks_config:
        if net.get("name"):
            all_vlan_names.add(net.get("name"))

    all_devices = {}
    for res in static_reservations:
        mac = res.get("mac_address", "").lower()
        if not mac: continue
        all_devices[mac] = {
            'id': res.get('id'), 'mac': mac, 'ip': res.get('ip_address', 'N/A'),
            'hostname': res.get('desired_hostname', res.get('id')), 'type': 'STATIC',
            'promotable': False, 'vlan_id': res.get('vlan_id'),
            'network_access_blocked': res.get('network_access_blocked', False),
            'tc_policy_id': res.get('tc_policy_id')
        }
    
    for lease in active_leases:
        mac = lease['mac']
        if mac in all_devices:
            all_devices[mac].update({'type': 'LEASE+STATIC', 'ip': lease['ip'], 'hostname': lease['hostname']})
        else:
            all_devices[mac] = {
                'id': lease.get('id') or lease.get('mac'),
                'mac': mac, 'ip': lease['ip'], 'hostname': lease['hostname'],
                'type': 'LEASE', 'promotable': True, 'vlan_id': 'dynamic_unknown',
                'network_access_blocked': False, 'tc_policy_id': None
            }

    ips_to_ping = [dev['ip'] for dev in all_devices.values() if dev.get('ip') and dev.get('ip') != 'N/A']
    online_statuses = check_multiple_hosts_online(ips_to_ping)

    devices_by_vlan = OrderedDict()
    for vlan_name in sorted(list(all_vlan_names)):
        subnet = next((str(s) for s, v in subnet_to_vlan_map.items() if v == vlan_name), 'N/A')
        devices_by_vlan[vlan_name] = {'devices': [], 'subnet': subnet}
    
    unassigned_devices = []

    for device in all_devices.values():
        device['online_status'] = 'Online' if online_statuses.get(device['ip'], False) else 'Offline'
        
        assigned_vlan_name = vlan_id_to_name_map.get(device.get('vlan_id'))
        if not assigned_vlan_name:
            try:
                device_ip = ipaddress.ip_address(device['ip'])
                for subnet, vlan_name in subnet_to_vlan_map.items():
                    if device_ip in subnet:
                        assigned_vlan_name = vlan_name
                        break
            except (ValueError, KeyError):
                pass
        
        device['qos'] = policies.get(device.get('tc_policy_id'), {})

        if assigned_vlan_name and assigned_vlan_name in devices_by_vlan:
            devices_by_vlan[assigned_vlan_name]['devices'].append(device)
        else:
            unassigned_devices.append(device)

    for group_data in devices_by_vlan.values():
        for device in group_data['devices']:
            if device['type'] == 'LEASE': device['type_color'] = 'bg-yellow-500 text-yellow-900'
            elif device['type'] == 'STATIC': device['type_color'] = 'bg-cyan-500 text-cyan-900'
            elif device['type'] == 'LEASE+STATIC': device['type_color'] = 'bg-teal-500 text-teal-900'
            
            if device['online_status'] == 'Online': device['online_status_color'] = 'bg-green-500'
            else: device['online_status_color'] = 'bg-red-500'
        
        group_data['devices'].sort(key=lambda d: ipaddress.ip_address(d['ip']))
    
    if unassigned_devices:
        for device in unassigned_devices:
            if device['type'] == 'LEASE': device['type_color'] = 'bg-yellow-500 text-yellow-900'
            if device['online_status'] == 'Online': device['online_status_color'] = 'bg-green-500'
            else: device['online_status_color'] = 'bg-red-500'
        devices_by_vlan["VLAN 1 / Native"] = {'devices': sorted(unassigned_devices, key=lambda d: ipaddress.ip_address(d['ip'])), 'subnet': 'N/A'}

    return devices_by_vlan

def get_qos_status_for_web() -> Dict[str, Dict[str, str]]:
    config = load_config()
    status_data = {}
    base_iface = config.get("global_settings", {}).get("primary_host_lan_interface_base")
    networks = config.get("networks", [])
    if not base_iface or not networks: return {}
    interfaces = [base_iface + n.get("netplan_interface_suffix", "") for n in networks if n.get("netplan_interface_suffix") is not None]
    for iface in interfaces:
        status_data[iface] = {
            "qdiscs": run_command(["tc", "-s", "qdisc", "show", "dev", iface], dry_run=False, check=False, return_output=True) or "No qdiscs found.",
            "classes": run_command(["tc", "-s", "class", "show", "dev", iface], dry_run=False, check=False, return_output=True) or "No classes found.",
            "filters": run_command(["tc", "filter", "show", "dev", iface], dry_run=False, check=False, return_output=True) or "No filters found."
        }
    return status_data

def _add_reservation_to_config(host_entry: Dict[str, Any]) -> Tuple[bool, str]:
    config = load_config(force_reload=True)
    if "hosts_dhcp_reservations" not in config:
        config["hosts_dhcp_reservations"] = []
    
    new_id = host_entry['id'].lower()
    new_mac = host_entry['mac_address'].lower()
    for existing_host in config["hosts_dhcp_reservations"]:
        if existing_host.get('id', '').lower() == new_id:
            return False, f"Error: A host with ID '{host_entry['id']}' already exists."
        if existing_host.get('mac_address', '').lower() == new_mac:
            return False, f"Error: A host with MAC address '{host_entry['mac_address']}' already exists."

    config["hosts_dhcp_reservations"].append(host_entry)
    config["hosts_dhcp_reservations"].sort(key=lambda x: x.get('id', ''))
    
    if save_config(config):
        return True, f"Successfully added reservation for '{host_entry['id']}'."
    else:
        return False, "Error: Failed to save configuration file."

def _add_network_to_config(network_entry: Dict[str, Any]) -> Tuple[bool, str]:
    config = load_config(force_reload=True)
    if "networks" not in config:
        config["networks"] = []
    new_vlan_id = network_entry.get('vlan_id')
    new_name = network_entry.get('name', '').lower()
    for existing in config["networks"]:
        if existing.get('vlan_id') == new_vlan_id:
            return False, f"Error: A network with VLAN ID '{new_vlan_id}' already exists."
        if existing.get('name', '').lower() == new_name:
            return False, f"Error: A network with name '{network_entry.get('name')}' already exists."
    config["networks"].append(network_entry)
    config["networks"].sort(key=lambda x: x.get('vlan_id', 0))
    if save_config(config):
        return True, f"Successfully added network '{network_entry.get('name')}' (VLAN {new_vlan_id})."
    else:
        return False, "Error: Failed to save configuration file."

def _update_network_in_config(id_or_name: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    config = load_config(force_reload=True)
    networks = config.get("networks", [])
    found = False
    for i, net in enumerate(networks):
        if str(net.get("vlan_id")) == str(id_or_name) or net.get("name", "").lower() == str(id_or_name).lower():
            found = True
            for k, v in updates.items():
                if v is not None:
                    net[k] = v
            config["networks"][i] = net
            break
    if not found:
        return False, f"Error: Network '{id_or_name}' not found."
    if save_config(config):
        return True, f"Successfully updated network '{id_or_name}'."
    else:
        return False, "Error: Failed to save configuration file."

def _delete_network_from_config(id_or_name: str) -> Tuple[bool, str]:
    config = load_config(force_reload=True)
    networks = config.get("networks", [])
    new_networks = [n for n in networks if str(n.get("vlan_id")) != str(id_or_name) and n.get("name", "").lower() != str(id_or_name).lower()]
    if len(new_networks) == len(networks):
        return False, f"Error: Network '{id_or_name}' not found."
    config["networks"] = new_networks
    if save_config(config):
        return True, f"Successfully deleted network '{id_or_name}'."
    else:
        return False, "Error: Failed to save configuration file."

@app.route("/")
def home():
    device_groups = get_dashboard_data()
    return render_template("home.html", device_groups=device_groups)

@app.route('/favicon.ico')
def favicon():
    return ('', 204)

@app.route("/qos")
def qos_status_page():
    check_root_privileges("view QoS status via web")
    qos_data = get_qos_status_for_web()
    return render_template("qos_status.html", qos_data=qos_data)

@app.route("/host/<host_id>")
def host_detail(host_id):
    config = load_config()
    host_info = get_host_config_by_id(config, host_id)
    if not host_info:
        abort(404)
    return render_template("host_detail.html", host=host_info)

@app.route("/host/edit/<host_id>", methods=['GET', 'POST'])
def edit_host(host_id):
    config = load_config(force_reload=True)
    host_info = get_host_config_by_id(config, host_id)
    if not host_info:
        abort(404)

    if request.method == 'POST':
        try:
            for i, host in enumerate(config['hosts_dhcp_reservations']):
                if host['id'] == host_id:
                    config['hosts_dhcp_reservations'][i]['description'] = request.form.get('description', host.get('description'))
                    
                    tc_policy_id = request.form.get('tc_policy_id')
                    if tc_policy_id:
                        config['hosts_dhcp_reservations'][i]['tc_policy_id'] = tc_policy_id
                    elif 'tc_policy_id' in config['hosts_dhcp_reservations'][i]:
                        del config['hosts_dhcp_reservations'][i]['tc_policy_id']
                    
                    break
            
            if save_config(config):
                flash(f"Host '{host_id}' updated successfully.", "success")
            else:
                flash(f"Error saving configuration for host '{host_id}'.", "error")
            
            return redirect(url_for('home'))
        except Exception as e:
            flash(f"An error occurred while updating the host: {e}", "error")
            return redirect(url_for('edit_host', host_id=host_id))

    policies = config.get("traffic_control_policies", [])
    return render_template("edit_host.html", host=host_info, policies=policies)

@app.route("/api/bandwidth/<host_id>")
def api_bandwidth(host_id):
    config = load_config()
    host_info = get_host_config_by_id(config, host_id)
    if not host_info:
        return jsonify({"error": "Host not found"}), 404
    host_ip = host_info.get("ip_address")
    if not host_ip:
        return jsonify({"error": "Host has no IP address"}), 400
    since_timestamp = int(time.time()) - 300 
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM bandwidth WHERE host_ip = ? AND timestamp > ? ORDER BY timestamp ASC",
        (host_ip, since_timestamp)
    )
    rows = cursor.fetchall()
    conn.close()
    data = {"timestamps": [r["timestamp"] for r in rows], "rates_in": [r["rate_in"] for r in rows], "rates_out": [r["rate_out"] for r in rows]}
    return jsonify(data)
    
@app.route("/add_reservation", methods=['GET', 'POST'])
def add_reservation():
    if request.method == 'POST':
        try:
            new_host_entry = {
                "id": request.form.get('host_id'), "vlan_id": int(request.form.get('vlan_id')),
                "mac_address": request.form.get('mac_address'), "ip_address": request.form.get('ip_address'),
                "desired_hostname": request.form.get('desired_hostname'), "manage_snat_rule": False,
                "description": "Reservation created via web portal."
            }
            success, message = _add_reservation_to_config(new_host_entry)
            if success: flash(message, 'success')
            else: flash(message, 'error')
        except Exception as e:
            flash(f"An error occurred: {e}", "error")
        return redirect(url_for('home'))
    return render_template("add_reservation.html")

@app.route("/make_static", methods=['GET', 'POST'])
def make_static():
    if request.method == 'POST':
        try:
            new_host_entry = {
                "id": request.form.get('host_id'), "vlan_id": int(request.form.get('vlan_id')),
                "mac_address": request.form.get('mac_address'), "ip_address": request.form.get('ip_address'),
                "desired_hostname": request.form.get('desired_hostname'), "manage_snat_rule": False,
                "description": "Reservation created from active lease."
            }
            success, message = _add_reservation_to_config(new_host_entry)
            if success: flash(f"{message} Run 'dnsmasq apply-reservations'.", 'success')
            else: flash(message, 'error')
        except Exception as e:
            flash(f"An error occurred: {e}", "error")
        return redirect(url_for('home'))
    
    mac = request.args.get('mac')
    ip = request.args.get('ip')
    hostname = request.args.get('hostname')
    return render_template("make_static_form.html", mac=mac, ip=ip, hostname=hostname)

@app.route("/networks")
def networks_list():
    config = load_config(force_reload=True)
    networks = config.get("networks", [])
    global_settings = config.get("global_settings", {})
    netplan_interfaces = get_all_netplan_interfaces(global_settings)
    for iface in netplan_interfaces:
        iface['file_b64'] = base64.urlsafe_b64encode(iface['file'].encode()).decode()
        iface['filename'] = os.path.basename(iface['file'])
    return render_template("networks_list.html", networks=networks, netplan_interfaces=netplan_interfaces)

@app.route("/networks/add", methods=['GET', 'POST'])
def networks_add():
    if request.method == 'POST':
        try:
            entry = {"vlan_id": int(request.form.get('vlan_id')), "name": request.form.get('name'), "netplan_interface_suffix": request.form.get('netplan_interface_suffix', ''), "description": request.form.get('description', '')}
            success, message = _add_network_to_config(entry)
            if success: flash(message, 'success')
            else: flash(message, 'error')
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('networks_list'))
    return render_template("network_form.html", net=None, edit=False)

@app.route("/networks/edit/<id_or_name>", methods=['GET', 'POST'])
def networks_edit(id_or_name):
    config = load_config(force_reload=True)
    net = next((n for n in config.get("networks", []) if str(n.get("vlan_id")) == str(id_or_name) or n.get("name", "").lower() == str(id_or_name).lower()), None)
    if not net: abort(404)
    if request.method == 'POST':
        try:
            updates = {"name": request.form.get('name'), "netplan_interface_suffix": request.form.get('netplan_interface_suffix', ''), "description": request.form.get('description', '')}
            success, message = _update_network_in_config(id_or_name, updates)
            if success: flash(message, 'success')
            else: flash(message, 'error')
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('networks_list'))
    return render_template("network_form.html", net=net, edit=True)

@app.route("/networks/delete/<id_or_name>", methods=['POST'])
def networks_delete(id_or_name):
    try:
        success, message = _delete_network_from_config(id_or_name)
        if success: flash(message, 'success')
        else: flash(message, 'error')
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('networks_list'))

@app.route("/netplan/edit/<section>/<file_b64>/<interface>", methods=['GET', 'POST'])
def netplan_edit(section, file_b64, interface):
    try:
        file_path_decoded = base64.urlsafe_b64decode(file_b64).decode()
    except Exception:
        abort(400)
    config = load_config(force_reload=True)
    global_settings = config.get("global_settings", {})
    netplan_interfaces = get_all_netplan_interfaces(global_settings)
    iface = next((i for i in netplan_interfaces if i['section'] == section and i['interface'] == interface and i['file'] == file_path_decoded), None)
    if not iface:
        abort(404)
    if request.method == 'POST':
        try:
            new_data = dict(iface['raw'])
            new_data['addresses'] = [a.strip() for a in request.form.get('addresses', '').split(',') if a.strip()]
            new_data['dhcp4'] = 'dhcp4' in request.form
            new_data['dhcp6'] = 'dhcp6' in request.form
            update_netplan_interface(file_path_decoded, section, interface, new_data)
            flash(f"Successfully updated interface '{interface}'.", 'success')
            return redirect(url_for('netplan_edit', section=section, file_b64=file_b64, interface=interface))
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')
    return render_template("netplan_form.html", iface=iface, edit=True)

@app.route("/netplan/delete/<section>/<file_b64>/<interface>", methods=['POST'])
def netplan_delete(section, file_b64, interface):
    try:
        file_path_decoded = base64.urlsafe_b64decode(file_b64).decode()
    except Exception:
        abort(400)
    try:
        delete_netplan_interface(file_path_decoded, section, interface)
        flash(f"Successfully deleted interface '{interface}'.", 'success')
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('networks_list'))

@app.route("/netplan/route/add/<section>/<file_b64>/<interface>", methods=['POST'])
def netplan_route_add(section, file_b64, interface):
    try:
        file_path = base64.urlsafe_b64decode(file_b64).decode()
        to, via = request.form.get('to'), request.form.get('via')
        on_link = 'on_link' in request.form
        add_route_to_netplan_interface(file_path, section, interface, to, via if via else None, on_link)
        flash(f"Route to '{to}' added. Run 'sudo netplan apply' to activate.", "success")
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('netplan_edit', section=section, file_b64=file_b64, interface=interface))

@app.route("/netplan/route/delete/<section>/<file_b64>/<interface>", methods=['POST'])
def netplan_route_delete(section, file_b64, interface):
    try:
        file_path = base64.urlsafe_b64decode(file_b64).decode()
        to, via = request.form.get('to'), request.form.get('via')
        gateway = via if via else None
        delete_route_from_netplan_interface(file_path, section, interface, to, gateway)
        flash(f"Route to '{to}' deleted. Run 'sudo netplan apply' to activate.", "success")
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('netplan_edit', section=section, file_b64=file_b64, interface=interface))

@app.route("/access/toggle/host/<host_id>", methods=['POST'])
def access_toggle_host(host_id):
    check_root_privileges("toggle network access via web UI")
    config = load_config()
    host_to_update = get_host_config_by_id(config, host_id)
    if not host_to_update:
        flash(f"Error: Host '{host_id}' not found.", 'error')
        return redirect(url_for('home'))
    
    current_status = host_to_update.get('network_access_blocked', False)
    host_to_update['network_access_blocked'] = not current_status
    
    if not save_config(config):
        flash(f"Error: Failed to save configuration for host '{host_id}'.", 'error')
        return redirect(url_for('home'))

    action = "Blocked" if not current_status else "Allowed"
    flash(f"Access for '{host_id}' set to '{action}'. Applying changes...", 'success')

    try:
        sync_cmd = typer.main.get_command(access_cli_app)
        ctx = typer.Context(sync_cmd)
        with open(os.devnull, 'w') as devnull:
            original_stdout, sys.stdout = sys.stdout, devnull
            try:
                ctx.invoke(sync_cmd, dry_run=False)
            finally:
                sys.stdout = original_stdout
    except Exception as e:
        flash(f"Error applying firewall rules: {e}", 'error')

    return redirect(url_for('home'))

@app.route("/access/toggle/subnet", methods=['POST'])
def access_toggle_subnet():
    check_root_privileges("toggle network access for subnet via web UI")
    subnet_to_toggle = request.form.get('subnet')
    action = request.form.get('action')
    
    if not subnet_to_toggle or not action:
        flash("Error: Missing subnet or action.", "error")
        return redirect(url_for('home'))
        
    config = load_config()
    hosts = config.get("hosts_dhcp_reservations", [])
    
    target_subnet = ipaddress.ip_network(subnet_to_toggle)
    hosts_updated_count = 0
    
    for host in hosts:
        try:
            host_ip = ipaddress.ip_address(host.get("ip_address", ""))
            if host_ip in target_subnet:
                host['network_access_blocked'] = (action == 'block')
                hosts_updated_count += 1
        except ValueError:
            continue

    if hosts_updated_count > 0:
        if not save_config(config):
            flash("Error saving configuration.", 'error')
            return redirect(url_for('home'))
        flash(f"Set access to '{action}' for {hosts_updated_count} host(s) in {subnet_to_toggle}. Applying changes...", 'success')
        
        try:
            sync_cmd = typer.main.get_command(access_cli_app)
            ctx = typer.Context(sync_cmd)
            with open(os.devnull, 'w') as devnull:
                original_stdout, sys.stdout = sys.stdout, devnull
                try:
                    ctx.invoke(sync_cmd, dry_run=False)
                finally:
                    sys.stdout = original_stdout
        except Exception as e:
            flash(f"An error applying firewall rules: {e}", 'error')
    else:
        flash(f"No configured hosts found in subnet {subnet_to_toggle}.", "warning")

    return redirect(url_for('home'))
