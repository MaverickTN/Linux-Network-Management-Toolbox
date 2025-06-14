import sqlite3
import subprocess
import time
import re
import json
from pathlib import Path
from typing import Dict, Any

# This script will now run without needing a subprocess call to itself.
from inetctl.core.config_loader import load_config
from inetctl.cli.shorewall import sync_shorewall as run_shorewall_sync

DB_FILE = Path("./inetctl_stats.db")
SYNC_INTERVAL_SECONDS = 15
DATA_RETENTION_DAYS = 10

def get_active_leases(leases_file_path: str) -> list:
    if not Path(leases_file_path).exists(): return []
    leases = []
    try:
        with open(leases_file_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if len(parts) >= 4:
                    leases.append({'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3] if parts[3] != '*' else '(unknown)'})
    except IOError:
        return []
    return leases

def get_iptables_counters(active_devices: list) -> dict:
    """
    This is the debug version of the function.
    It will print detailed output to the system log.
    """
    counters = {}
    for device in active_devices:
        ip, mac_sanitized = device.get("ip"), device.get("mac", "").replace(":", "")
        if not ip or not mac_sanitized: continue
        chain_name = f"acct_{mac_sanitized}"
        try:
            result = subprocess.run(["sudo", "iptables", "-v", "-x", "-n", "-L", chain_name], capture_output=True, text=True, check=True)
            
            # --- DEBUGGING: Print the raw output to the log ---
            print("--- DEBUG IPTABLES OUTPUT ---")
            print(f"Chain: {chain_name}")
            print(result.stdout)
            print("--- END DEBUG ---")

            byte_pattern = re.compile(r"^\s*\d+\s+(\d+)\s+")
            lines = result.stdout.strip().splitlines()
            
            if len(lines) >= 4:
                try:
                    # Isolate the parsing in its own try/except to see if it's the source of a silent error
                    download_bytes_str = byte_pattern.match(lines[2]).group(1)
                    upload_bytes_str = byte_pattern.match(lines[3]).group(1)
                    counters[mac_sanitized] = {
                        'in': int(download_bytes_str), 
                        'out': int(upload_bytes_str), 
                        'ip': ip
                    }
                except AttributeError:
                    print(f"DEBUG: Regex parse failed for chain {chain_name}. Skipping.")
                    continue
        except subprocess.CalledProcessError as e:
            # This will catch cases where the 'acct_' chain does not exist, which is normal on startup
            print(f"DEBUG: Could not get iptables counters for {chain_name}. This is expected if the chain isn't active. Error: {e.stderr}")
            continue
    return counters

def setup_database(config: Dict):
    """Sets up the bandwidth table and purges old data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bandwidth (
        timestamp INTEGER, host_id TEXT, ip_address TEXT,
        bytes_in INTEGER, bytes_out INTEGER, rate_in REAL, rate_out REAL,
        PRIMARY KEY (timestamp, host_id)
    )
    """)
    retention_days = config.get("global_settings", {}).get("database_retention_days", DATA_RETENTION_DAYS)
    purge_before_timestamp = int(time.time()) - (retention_days * 24 * 60 * 60)
    cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?", (purge_before_timestamp,))
    deleted_rows = cursor.rowcount
    if deleted_rows > 0: print(f"Purged {deleted_rows} old records.")
    conn.commit()
    conn.close()

def main_loop():
    print("--- Starting inetctl Data Synchronizer (DEBUG MODE) ---")
    last_counters = {}; last_timestamp = time.time(); last_purge_time = 0

    while True:
        try:
            config = load_config()
            if not config:
                print("Config file not found or invalid. Sleeping...")
                time.sleep(60)
                continue

            if time.time() - last_purge_time > (24 * 60 * 60):
                print("Running daily database maintenance...")
                setup_database(config)
                last_purge_time = time.time()

            gs = config.get("global_settings", {})
            leases_file_path = gs.get("dnsmasq_leases_file", "")
            if not leases_file_path:
                print("Warning: dnsmasq_leases_file not set. Skipping accounting.")
            else:
                active_leases = get_active_leases(leases_file_path)
                current_timestamp = time.time()
                current_counters = get_iptables_counters(active_leases)
                time_delta = current_timestamp - last_timestamp

                if time_delta > 0 and current_counters:
                    records = []
                    for mac_sanitized, counts in current_counters.items():
                        last_counts = last_counters.get(mac_sanitized, {'in': 0, 'out': 0})
                        bytes_in_delta = counts['in'] - last_counts['in'] if counts['in'] >= last_counts['in'] else counts['in']
                        bytes_out_delta = counts['out'] - last_counts['out'] if counts['out'] >= last_counts['out'] else counts['out']
                        rate_in_mbps = (bytes_in_delta * 8) / (time_delta * 1_000_000)
                        rate_out_mbps = (bytes_out_delta * 8) / (time_delta * 1_000_000)
                        records.append((int(current_timestamp), mac_sanitized, counts['ip'], counts['in'], counts['out'], round(rate_in_mbps, 2), round(rate_out_mbps, 2)))
                    
                    if records:
                        conn = sqlite3.connect(DB_FILE)
                        conn.executemany("INSERT OR REPLACE INTO bandwidth VALUES (?, ?, ?, ?, ?, ?, ?)", records)
                        conn.commit()
                        conn.close()
                        print(f"[{time.strftime('%H:%M:%S')}] Logged {len(records)} bandwidth records.")
                
                last_counters, last_timestamp = current_counters, current_timestamp
        
        except Exception as e:
            print(f"ERROR in sync.py main loop: {e}")
        
        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()