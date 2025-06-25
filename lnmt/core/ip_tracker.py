#!/usr/bin/env python3

import sqlite3
import time
import os
from datetime import datetime

LEASE_FILE = "/var/lib/misc/dnsmasq.leases"
DB_PATH = "/etc/lnmt/lnmt_stats.db"
CHECK_INTERVAL = 30  # seconds

def read_leases():
    leases = {}
    if os.path.exists(LEASE_FILE):
        with open(LEASE_FILE, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3:
                    mac = parts[1].lower()
                    ip = parts[2]
                    leases[mac] = ip
    return leases

def update_reservation_ip(mac, new_ip):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE reservations
        SET ip = ?, updated = ?
        WHERE mac = ? AND ip IS NOT NULL AND ip != ?
    """, (new_ip, datetime.now().isoformat(), mac, new_ip))
    conn.commit()
    conn.close()

def main():
    while True:
        leases = read_leases()
        for mac, ip in leases.items():
            update_reservation_ip(mac, ip)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
