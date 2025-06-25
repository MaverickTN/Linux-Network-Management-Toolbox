#!/usr/bin/env python3

import threading
import time
import sqlite3
import os
from datetime import datetime

DB_PATH = "/etc/lnmt/lnmt_stats.db"
LEASE_FILE = "/var/lib/misc/dnsmasq.leases"
TRAFFIC_INTERVAL = 3
IPTRACK_INTERVAL = 30

def collect_traffic_data():
    while True:
        # Placeholder for traffic accounting logic
        print("[*] Collecting traffic data...")
        time.sleep(TRAFFIC_INTERVAL)

def track_ip_addresses():
    while True:
        leases = {}
        if os.path.exists(LEASE_FILE):
            with open(LEASE_FILE, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        mac = parts[1].lower()
                        ip = parts[2]
                        leases[mac] = ip

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for mac, new_ip in leases.items():
            cur.execute("""
                UPDATE reservations
                SET ip = ?, updated = ?
                WHERE mac = ? AND ip IS NOT NULL AND ip != ?
            """, (new_ip, datetime.now().isoformat(), mac, new_ip))
        conn.commit()
        conn.close()
        print("[*] Synced IP changes from leases.")
        time.sleep(IPTRACK_INTERVAL)

def main():
    print("[+] LNMT service starting with traffic + IP tracking...")
    traffic_thread = threading.Thread(target=collect_traffic_data, daemon=True)
    iptrack_thread = threading.Thread(target=track_ip_addresses, daemon=True)
    traffic_thread.start()
    iptrack_thread.start()
    traffic_thread.join()
    iptrack_thread.join()

if __name__ == "__main__":
    main()
