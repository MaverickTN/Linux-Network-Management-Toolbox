#!/usr/bin/env python3

import os
import re
import logging
from typing import List, Dict, Optional

LEASES_FILE = "/var/lib/misc/dnsmasq.leases"
CONFIG_FILE = "/etc/dnsmasq.d/lnmt-reservations.conf"

logger = logging.getLogger("lnmt.core.dnsmasq")

def parse_leases_file(leases_path: str = LEASES_FILE) -> List[Dict]:
    leases = []
    try:
        with open(leases_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    lease = {
                        "expiry": int(parts[0]),
                        "mac": parts[1].lower(),
                        "ip": parts[2],
                        "hostname": parts[3] if parts[3] != "*" else "",
                        "client_id": parts[4]
                    }
                    leases.append(lease)
    except Exception as e:
        logger.exception("Failed to read leases file")
    return leases

def load_reservations(config_path: str = CONFIG_FILE) -> List[Dict]:
    reservations = []
    if not os.path.exists(config_path):
        return reservations
    try:
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("dhcp-host="):
                    parts = line[len("dhcp-host="):].split(",")
                    if len(parts) >= 2:
                        reservations.append({
                            "mac": parts[0].lower(),
                            "ip": parts[1],
                            "hostname": parts[2] if len(parts) > 2 else ""
                        })
    except Exception as e:
        logger.exception("Failed to read reservations")
    return reservations

def save_reservations(reservations: List[Dict], config_path: str = CONFIG_FILE):
    try:
        with open(config_path, "w") as f:
            for res in reservations:
                line = f"dhcp-host={res['mac']},{res['ip']}"
                if res.get("hostname"):
                    line += f",{res['hostname']}"
                f.write(line + "\n")
    except Exception as e:
        logger.exception("Failed to save reservations")

def add_reservation(mac: str, ip: str, hostname: str = ""):
    mac = mac.lower()
    reservations = load_reservations()
    reservations = [r for r in reservations if r["mac"] != mac]
    reservations.append({"mac": mac, "ip": ip, "hostname": hostname})
    save_reservations(reservations)

def remove_reservation(mac: str):
    mac = mac.lower()
    reservations = load_reservations()
    reservations = [r for r in reservations if r["mac"] != mac]
    save_reservations(reservations)

def reload_dnsmasq():
    try:
        result = os.system("systemctl reload dnsmasq")
        if result != 0:
            logger.warning("dnsmasq reload returned non-zero status")
    except Exception as e:
        logger.exception("Failed to reload dnsmasq")
