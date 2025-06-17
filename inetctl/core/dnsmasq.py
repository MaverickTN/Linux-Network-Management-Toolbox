import os
import re
import ipaddress

LEASES_PATH = "/var/lib/misc/dnsmasq.leases"
RESERVATIONS_PATH = "/etc/dnsmasq.d/static.conf"  # adjust if yours differs

def parse_leases():
    """Parse active DHCP leases."""
    if not os.path.exists(LEASES_PATH):
        return []
    leases = []
    with open(LEASES_PATH) as f:
        for line in f:
            # Format: <expiry> <mac> <ip> <hostname> <client-id>
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            leases.append({
                "expiry": int(parts[0]),
                "mac": parts[1].lower(),
                "ip": parts[2],
                "hostname": parts[3] if parts[3] != "*" else "",
                "client_id": parts[4],
                "active": True
            })
    return leases

def parse_reservations():
    """Parse static MAC/IP reservations."""
    if not os.path.exists(RESERVATIONS_PATH):
        return []
    reservations = []
    # Example line: dhcp-host=00:11:22:33:44:55,10.0.1.100,MyHost,infinite
    with open(RESERVATIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"dhcp-host=([0-9a-fA-F:]+),([\d\.]+),([^,]*),?", line)
            if m:
                mac, ip, hostname = m.group(1).lower(), m.group(2), m.group(3)
                reservations.append({
                    "mac": mac,
                    "ip": ip,
                    "hostname": hostname,
                    "reservation": True
                })
    return reservations

def get_active_assignments():
    """Return merged list of hosts with active leases and reservation info."""
    leases = parse_leases()
    reservations = parse_reservations()
    result = []
    res_by_mac = {r['mac']: r for r in reservations}
    # Add leases (active assignments)
    for lease in leases:
        host = lease.copy()
        if host['mac'] in res_by_mac:
            host['reservation'] = True
            host['hostname'] = res_by_mac[host['mac']]['hostname'] or host['hostname']
        else:
            host['reservation'] = False
        host['blocked'] = is_blocked(host['mac'])
        result.append(host)
    # Add unassigned reservations
    lease_macs = set(l['mac'] for l in leases)
    for r in reservations:
        if r['mac'] not in lease_macs:
            host = r.copy()
            host['active'] = False
            host['blocked'] = is_blocked(host['mac'])
            result.append(host)
    return result

def ip_in_subnet(ip, subnet):
    """Return True if IP is in subnet (str: '10.0.1.10', '10.0.1.0/24')"""
    try:
        return ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(subnet, strict=False)
    except Exception:
        return False

# -- Block/allow utilities (using Shorewall or simple file/blocklist) --

BLACKLIST_PATH = "/etc/inetctl/blacklist.txt"  # Adjust as needed

def is_blocked(mac):
    """Check if this MAC is in the blacklist file."""
    if not os.path.exists(BLACKLIST_PATH):
        return False
    with open(BLACKLIST_PATH) as f:
        return any(line.strip().lower() == mac for line in f)

def block_mac(mac):
    """Add MAC to blacklist."""
    with open(BLACKLIST_PATH, "a") as f:
        f.write(mac + "\n")
    # Optionally call Shorewall or reload rules here

def allow_mac(mac):
    """Remove MAC from blacklist."""
    if not os.path.exists(BLACKLIST_PATH):
        return
    with open(BLACKLIST_PATH) as f:
        lines = f.readlines()
    with open(BLACKLIST_PATH, "w") as f:
        for line in lines:
            if line.strip().lower() != mac:
                f.write(line)
    # Optionally reload Shorewall here

def get_host_info(mac):
    """Fetch merged lease/reservation info for this MAC."""
    for host in get_active_assignments():
        if host["mac"] == mac:
            return host
    return {"mac": mac, "ip": "", "subnet": "", "qos_profile": "Default"}

