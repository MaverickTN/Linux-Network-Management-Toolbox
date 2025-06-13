import sqlite3
import subprocess
import time
import re
import json
import ipaddress
from pathlib import Path
from typing import List, Dict, Any

# --- Configuration ---
DB_FILE = Path("./inetctl_stats.db")
CONFIG_FILE = Path("./server_config.json")
SYNC_INTERVAL_SECONDS = 15

def get_config() -> Dict:
    if not CONFIG_FILE.exists(): return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}

def get_active_leases(leases_file_path: str) -> List[Dict]:
    if not Path(leases_file_path).exists(): return []
    leases = []
    with open(leases_file_path, 'r') as f:
        for line in f.readlines():
            parts = line.strip().split()
            if len(parts) >= 4:
                leases.append({'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3]})
    return leases

def get_iptables_counters(active_devices: List[Dict]) -> Dict[str, Dict]:
    counters = {}
    for device in active_devices:
        ip = device.get("ip")
        mac_sanitized = device.get("mac", "").replace(":", "")
        if not ip or not mac_sanitized: continue
        chain_name = f"acct_{mac_sanitized}"
        try:
            result = subprocess.run(["sudo", "iptables", "-v", "-x", "-n", "-L", chain_name], capture_output=True, text=True, check=True)
            byte_pattern = re.compile(r"^\s*\d+\s+(\d+)\s+")
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 4:
                counters[mac_sanitized] = {'out': int(byte_pattern.match(lines[3]).group(1)), 'in': int(byte_pattern.match(lines[2]).group(1)), 'ip': ip}
        except (subprocess.CalledProcessError, AttributeError):
            continue
    return counters

def setup_database(config: Dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bandwidth (
        timestamp INTEGER,
        host_id TEXT,
        ip_address TEXT,
        bytes_in INTEGER,
        bytes_out INTEGER,
        rate_in REAL,
        rate_out REAL,
        PRIMARY KEY (timestamp, host_id)
    )
    """)
    retention_days = config.get("global_settings", {}).get("database_retention_days", 10)
    purge_before_timestamp = int(time.time()) - (retention_days * 24 * 60 * 60)
    cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?", (purge_before_timestamp,))
    deleted_rows = cursor.rowcount
    if deleted_rows > 0:
        print(f"Purged {deleted_rows} old records from the database.")
    conn.commit()
    conn.close()

def main_loop():
    print("Starting inetctl live synchronizer...")
    last_counters = {}
    last_timestamp = time.time()
    last_purge_time = 0

    while True:
        try:
            config = get_config()
            if not config:
                time.sleep(30)
                continue

            # Purge data once every ~24 hours
            if time.time() - last_purge_time > (24 * 60 * 60):
                setup_database(config)
                last_purge_time = time.time()

            gs = config.get("global_settings", {})
            active_leases = get_active_leases(gs.get("dnsmasq_leases_file", ""))
            
            # --- Firewall Sync ---
            # This logic can be expanded, for now we just run the CLI command
            # A more advanced version would have the logic directly here.
            subprocess.run(["./inetctl-runner.py", "shorewall", "sync"], capture_output=True)

            # --- Bandwidth Collection ---
            current_timestamp = time.time()
            current_counters = get_iptables_counters(active_leases)
            time_delta = current_timestamp - last_timestamp

            if time_delta > 0:
                records = []
                for mac, counts in current_counters.items():
                    last_in = last_counters.get(mac, {}).get('in', 0)
                    last_out = last_counters.get(mac, {}).get('out', 0)
                    
                    bytes_in_delta = counts['in'] - last_in if counts['in'] >= last_in else counts['in']
                    bytes_out_delta = counts['out'] - last_out if counts['out'] >= last_out else counts['out']

                    rate_in_mbps = (bytes_in_delta * 8) / (time_delta * 1_000_000)
                    rate_out_mbps = (bytes_out_delta * 8) / (time_delta * 1_000_000)
                    
                    records.append((int(current_timestamp), mac, counts['ip'], counts['in'], counts['out'], round(rate_in_mbps, 2), round(rate_out_mbps, 2)))
                
                if records:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.executemany("INSERT OR REPLACE INTO bandwidth VALUES (?, ?, ?, ?, ?, ?, ?)", records)
                    conn.commit()
                    conn.close()
                    print(f"[{time.strftime('%H:%M:%S')}] Logged {len(records)} bandwidth records.")

            last_counters = current_counters
            last_timestamp = current_timestamp
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")

        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()