# lnmt/core/dnsmasq.py

import os
import re
import logging
from typing import List, Dict, Optional

LEASES_FILE = "/var/lib/misc/dnsmasq.leases"
CONFIG_DIR = "/etc/dnsmasq.d/"
logger = logging.getLogger("lnmt.core.dnsmasq")

def parse_leases_file(leases_path: str = LEASES_FILE) -> List[Dict]:
    """
    Parse the dnsmasq leases file and return a list of dicts:
    [
        {
            "expiry": int,
            "mac": str,
            "ip": str,
            "hostname": str,
            "client_id": str
        }, ...
    ]
    """
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
        logger.error(f"Failed to parse dnsmasq leases: {e}")
    return leases

def get_reservations(config_dir: str = CONFIG_DIR) -> List[Dict]:
    """
    Parse static DHCP reservations from config files in dnsmasq.d.
    """
    reservations = []
    try:
        for fname in os.listdir(config_dir):
            if not fname.endswith(".conf"):
                continue
            fpath = os.path.join(config_dir, fname)
            with open(fpath, "r") as f:
                for line in f:
                    line = line.strip()
                    # Example: dhcp-host=00:11:22:33:44:55,set:mytag,192.168.1.50
                    match = re.match(r"dhcp-host=([^,]+),([^,]+),([^,]+)", line)
                    if match:
                        mac, tag, ip = match.groups()
                        reservations.append({
                            "mac": mac.lower(),
                            "tag": tag,
                            "ip": ip
                        })
    except Exception as e:
        logger.error(f"Failed to parse reservations: {e}")
    return reservations

def find_lease_by_mac(mac: str, leases: Optional[List[Dict]] = None) -> Optional[Dict]:
    if leases is None:
        leases = parse_leases_file()
    for lease in leases:
        if lease["mac"].lower() == mac.lower():
            return lease
    return None

def find_reservation_by_mac(mac: str, reservations: Optional[List[Dict]] = None) -> Optional[Dict]:
    if reservations is None:
        reservations = get_reservations()
    for r in reservations:
        if r["mac"].lower() == mac.lower():
            return r
    return None

def assign_vlan_to_lease(lease: Dict, vlan_subnet_map: Dict[str, int]) -> int:
    """
    Given a lease {"ip": "10.0.1.23"} and a mapping of subnet->VLAN,
    return the vlan_id for this lease.
    """
    for subnet, vlan_id in vlan_subnet_map.items():
        if lease["ip"].startswith(subnet):
            return vlan_id
    return 1  # Default to VLAN 1 (base) if not matched

def format_lease_display(lease: Dict, reservation: Optional[Dict] = None) -> Dict:
    """
    For dashboard table display: returns status, type, etc.
    """
    return {
        "status": "online" if lease.get("expiry", 0) > 0 else "offline",
        "assignment_type": "Reservation" if reservation else "Dynamic",
        "mac": lease["mac"],
        "ip": lease["ip"],
        "hostname": lease.get("hostname", ""),
        "reservation_ip": reservation["ip"] if reservation else "",
    }

def reload_dnsmasq():
    """
    Reload the dnsmasq service after config/reservation changes.
    """
    os.system("systemctl reload dnsmasq")
    logger.info("dnsmasq reloaded.")

def add_reservation(mac: str, ip: str, config_dir: str = CONFIG_DIR, tag: str = "reserved"):
    """
    Add a static reservation for a MAC/IP in dnsmasq.
    """
    # Choose a filename based on MAC
    fname = os.path.join(config_dir, f"host_{mac.replace(':', '').lower()}.conf")
    line = f"dhcp-host={mac},{tag},{ip}\n"
    with open(fname, "w") as f:
        f.write(line)
    reload_dnsmasq()
    logger.info(f"Added reservation: {mac} -> {ip}")

def remove_reservation(mac: str, config_dir: str = CONFIG_DIR):
    fname = os.path.join(config_dir, f"host_{mac.replace(':', '').lower()}.conf")
    try:
        os.remove(fname)
        reload_dnsmasq()
        logger.info(f"Removed reservation for {mac}")
    except FileNotFoundError:
        logger.warning(f"No reservation file found for {mac}")

# For CLI/Job Queue integration
def reservation_job(mac: str, ip: str, action: str):
    """
    For job queue: queue add/remove reservation jobs.
    """
    logger.info(f"Queueing reservation job: {action} {mac} -> {ip}")
    # Here you would put job in JobQueueService
    # Example: JobQueueService.add_job(...)
    if action == "add":
        add_reservation(mac, ip)
    elif action == "remove":
        remove_reservation(mac)
    else:
        logger.error(f"Unknown reservation action: {action}")

