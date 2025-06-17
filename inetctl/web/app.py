import os
import json
import sqlite3
from flask import Flask, render_template, jsonify, request

from inetctl.core import netplan  # << USE YOUR CORE

# Paths (adjust as needed)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
LEASES_PATH = os.path.join(BASE_DIR, "dhcp.leases")
RESERVATIONS_PATH = os.path.join(BASE_DIR, "dhcp.reservations.json")

app = Flask(__name__)

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

@app.route("/")
def home():
    config = netplan.load_config()
    vlan_info = netplan.get_vlan_info(config)
    vlan_ids = [str(vlan['id']) for vlan in vlan_info]
    if "1" not in vlan_ids:
        vlan_ids = ["1"] + vlan_ids  # Always include base VLAN 1
    vlan_ids = sorted(set(vlan_ids), key=lambda v: int(v))

    leases = load_leases()
    reservations = load_reservations()
    hosts_db = load_hosts_db()

    active_by_vlan = {vlan: [] for vlan in vlan_ids}
    unassigned_by_vlan = {vlan: [] for vlan in vlan_ids}

    leased_macs = set([lease["mac"] for lease in leases])
    for lease in leases:
        vlan_id = netplan.get_vlan_id_for_ip(lease["ip"], config)
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
            "network_access_blocked": False,
        }
        active_by_vlan.setdefault(vlan_id, []).append(device)

    for r in reservations:
        if r["mac"] not in leased_macs:
            vlan_id = netplan.get_vlan_id_for_ip(r["ip"], config)
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

# [rest of your Flask endpoints, unchanged...]

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
