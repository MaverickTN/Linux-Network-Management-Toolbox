import os
import json
import yaml
import sqlite3
import ipaddress
from pathlib import Path
from flask import Flask, render_template, jsonify, request

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "db.sqlite3"
NETPLAN_PATH = BASE_DIR / "netplan.yaml"
LEASES_PATH = BASE_DIR / "dhcp.leases"
RESERVATIONS_PATH = BASE_DIR / "dhcp.reservations.json"
BLACKLIST_PATH = BASE_DIR / "blacklist.txt"

app = Flask(__name__)

# --- Helper: Netplan loading & subnet map ---
def load_netplan():
    with open(NETPLAN_PATH, "r") as f:
        return yaml.safe_load(f)

def build_subnet_map(netplan, base_vlan="1"):
    subnet_map = {}
    ethernets = netplan["network"].get("ethernets", {})
    for eth in ethernets.values():
        cidr = eth.get("cidr")
        if cidr:
            subnet_map[ipaddress.ip_network(cidr)] = base_vlan
    vlans = netplan["network"].get("vlans", {})
    for vlan in vlans.values():
        vlan_id = str(vlan["id"])
        cidr = vlan.get("cidr")
        if cidr:
            subnet_map[ipaddress.ip_network(cidr)] = vlan_id
    return subnet_map

def get_vlan_id_for_ip(ip, subnet_map):
    try:
        ip_obj = ipaddress.ip_address(ip)
        for subnet, vlan_id in subnet_map.items():
            if ip_obj in subnet:
                return vlan_id
    except Exception:
        pass
    return "1"

# --- Helper: Leases & reservations ---
def load_leases():
    leases = []
    if not os.path.exists(LEASES_PATH):
        return leases
    with open(LEASES_PATH, "r") as f:
        for line in f:
            if not line.strip(): continue
            parts = line.split()
            if len(parts) >= 5:
                leases.append({
                    "expires": int(parts[0]),
                    "mac": parts[1].lower(),
                    "ip": parts[2],
                    "hostname": parts[3],
                })
    return leases

def load_reservations():
    if not os.path.exists(RESERVATIONS_PATH):
        return []
    with open(RESERVATIONS_PATH, "r") as f:
        return json.load(f)

# --- Helper: Blacklist (simple) ---
def load_blacklist():
    if not os.path.exists(BLACKLIST_PATH):
        return set()
    with open(BLACKLIST_PATH, "r") as f:
        return set(line.strip().lower() for line in f if line.strip())

# --- Helper: Host config in SQLite ---
def load_hosts_db():
    hosts = {}
    if not os.path.exists(DB_PATH):
        return hosts
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS hosts (mac TEXT PRIMARY KEY, description TEXT, qos_profile TEXT, qos_dl TEXT, qos_ul TEXT, schedule TEXT)")
        for row in cur.execute("SELECT mac, description, qos_profile, qos_dl, qos_ul, schedule FROM hosts"):
            mac, description, qos_profile, qos_dl, qos_ul, schedule = row
            hosts[mac.lower()] = {
                "description": description,
                "qos_profile": qos_profile,
                "qos_dl": qos_dl,
                "qos_ul": qos_ul,
                "schedule": schedule
            }
    except Exception:
        pass
    conn.close()
    return hosts

def save_host(mac, data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS hosts (mac TEXT PRIMARY KEY, description TEXT, qos_profile TEXT, qos_dl TEXT, qos_ul TEXT, schedule TEXT)")
    cur.execute("""
        INSERT OR REPLACE INTO hosts (mac, description, qos_profile, qos_dl, qos_ul, schedule)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        mac,
        data.get("description"),
        data.get("qos_profile"),
        data.get("qos_dl"),
        data.get("qos_ul"),
        data.get("schedule")
    ))
    conn.commit()
    conn.close()

# --- Main dashboard route ---
@app.route("/")
def home():
    netplan = load_netplan()
    subnet_map = build_subnet_map(netplan)
    leases = load_leases()
    reservations = load_reservations()
    hosts_db = load_hosts_db()
    blacklist = load_blacklist()

    vlan_ids = sorted([str(vlan["id"]) for vlan in netplan["network"].get("vlans", {}).values()], key=lambda v: int(v))
    if "1" not in vlan_ids:
        vlan_ids = ["1"] + vlan_ids

    active_by_vlan = {vlan: [] for vlan in vlan_ids}
    unassigned_by_vlan = {vlan: [] for vlan in vlan_ids}

    leased_macs = set([lease["mac"] for lease in leases])
    for lease in leases:
        vlan_id = get_vlan_id_for_ip(lease["ip"], subnet_map)
        db_info = hosts_db.get(lease["mac"], {})
        is_reserved = any(
            r["mac"].lower() == lease["mac"] and r["ip"] == lease["ip"]
            for r in reservations
        )
        device = {
            "mac": lease["mac"],
            "ip": lease["ip"],
            "hostname": lease["hostname"],
            "description": db_info.get("description", lease["hostname"]),
            "assignment_status": "Reservation" if is_reserved else "Dynamic",
            "is_online": True,
            "network_access_blocked": lease["ip"] in blacklist,
            # Add extra fields as needed for your logic
        }
        active_by_vlan.setdefault(vlan_id, []).append(device)

    for r in reservations:
        if r["mac"] not in leased_macs:
            vlan_id = get_vlan_id_for_ip(r["ip"], subnet_map)
            db_info = hosts_db.get(r["mac"], {})
            reservation = {
                "mac": r["mac"],
                "ip": r["ip"],
                "hostname": db_info.get("hostname", r.get("hostname", "")),
                "description": db_info.get("description", r.get("hostname", "")),
            }
            unassigned_by_vlan.setdefault(vlan_id, []).append(reservation)

    return render_template(
        "home.html",
        vlan_ids=vlan_ids,
        active_by_vlan=active_by_vlan,
        unassigned_by_vlan=unassigned_by_vlan
    )

# --- Toggle block/allow endpoint (stub; should use Shorewall/etc) ---
@app.route("/toggle_access", methods=["POST"])
def toggle_access():
    data = request.get_json()
    mac = data.get("mac")
    # Lookup lease for IP
    leases = load_leases()
    lease = next((l for l in leases if l["mac"] == mac), None)
    if not lease:
        return jsonify({"queued": False, "message": "MAC not found."})
    ip = lease["ip"]
    blacklist = load_blacklist()
    if ip in blacklist:
        # Allow: remove from blacklist
        lines = [line for line in open(BLACKLIST_PATH) if line.strip().lower() != ip]
        with open(BLACKLIST_PATH, "w") as f:
            f.writelines(lines)
        msg = f"Allowed {mac} ({ip})"
    else:
        # Block: add to blacklist
        with open(BLACKLIST_PATH, "a") as f:
            f.write(ip + "\n")
        msg = f"Blocked {mac} ({ip})"
    # TODO: run shorewall command, queue job, and notify
    return jsonify({"queued": True, "message": msg, "job_id": "fakejobid123"})

@app.route("/job_status/<jobid>")
def job_status(jobid):
    # Stub: always succeed instantly for demo
    return jsonify({"status": "success", "message": "Job completed"})

# --- API: host details ---
@app.route("/api/host/<mac>", methods=["GET", "POST"])
def api_host(mac):
    mac = mac.lower()
    if request.method == "GET":
        hosts_db = load_hosts_db()
        db_info = hosts_db.get(mac, {})
        leases = load_leases()
        reservations = load_reservations()
        lease = next((l for l in leases if l["mac"] == mac), None)
        reservation = next((r for r in reservations if r["mac"] == mac), None)
        ip = ""
        subnet = ""
        if lease:
            ip = lease["ip"]
        elif reservation:
            ip = reservation["ip"]
        if ip:
            netplan = load_netplan()
            subnet_map = build_subnet_map(netplan)
            for subnet_obj in subnet_map:
                if ipaddress.ip_address(ip) in subnet_obj:
                    subnet = str(subnet_obj.netmask)
        return jsonify({
            "mac": mac,
            "description": db_info.get("description", ""),
            "hostname": lease["hostname"] if lease else reservation["hostname"] if reservation else "",
            "ip": ip,
            "subnet": subnet or "255.255.255.0",
            "qos_profile": db_info.get("qos_profile", "Default"),
            "qos_dl": db_info.get("qos_dl", ""),
            "qos_ul": db_info.get("qos_ul", ""),
            "schedule": db_info.get("schedule", ""),
        })
    else:
        # POST: save changes
        data = request.get_json()
        save_host(mac, data)
        return jsonify({"success": True})

# --- API: transfer graph (stub data) ---
import time
@app.route("/api/transfer/<mac>")
def api_transfer(mac):
    # Demo data: 60 points, 1 per minute, random
    now = int(time.time())
    data = []
    for i in range(60):
        t = now - (60-i)*60
        data.append({"timestamp": t, "rx": 30000 + 5000 * (i % 5), "tx": 18000 + 3000 * (i % 3)})
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
