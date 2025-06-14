import sqlite3
import subprocess
import time
import json
from pathlib import Path
from typing import Dict

from inetctl.core.config_loader import load_config

# --- Configuration ---
DB_FILE = Path("./inetctl_stats.db")
SYNC_INTERVAL_SECONDS = 15
DATA_RETENTION_DAYS = 10

# --- Helper Functions ---
def get_active_leases(leases_file_path: str) -> list:
    if not Path(leases_file_path).exists(): return []
    leases = []
    try:
        with open(leases_file_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if len(parts) >= 4:
                    leases.append({'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3] if parts[3] != '*' else '(unknown)'})
    except IOError as e:
        print(f"Error reading leases file: {e}")
        return []
    return leases

def setup_database(config: Dict):
    """Ensures bandwidth table exists and purges old data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bandwidth (
        timestamp INTEGER, host_id TEXT, ip_address TEXT,
        bytes_in INTEGER, bytes_out INTEGER, rate_in REAL, rate_out REAL,
        PRIMARY KEY (timestamp, host_id)
    )
    """)
    retention = config.get("global_settings", {}).get("database_retention_days", DATA_RETENTION_DAYS)
    purge_ts = int(time.time()) - (retention * 86400)
    cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?", (purge_ts,))
    if cursor.rowcount > 0: print(f"Purged {cursor.rowcount} old bandwidth records.")
    conn.commit()
    conn.close()

def get_nfacct_counters() -> Dict[str, Dict[str, int]]:
    """
    Dumps accounting data using the 'nfacct' utility and parses the JSON output.
    Returns a dictionary mapping host_id (sanitized MAC) to its byte counters.
    """
    counters = {}
    try:
        result = subprocess.run(["sudo", "nfacct", "get", "-J"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        for acct_obj in data.get("nfacct", []):
            obj_name = acct_obj.get("name")
            if obj_name and obj_name.startswith("inetctl_"):
                host_id = obj_name.replace("inetctl_", "")
                if host_id not in counters: counters[host_id] = {'bytes': 0}
                counters[host_id]['bytes'] += acct_obj.get('bytes', 0)
    except FileNotFoundError:
        print("ERROR: 'nfacct' command not found. Please ensure it is installed and in the system's PATH.")
        return {}
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Error getting or parsing nfacct data: {e}")
        return {}
    return counters

def main_loop():
    print("--- Starting inetctl Data Synchronizer (nfacct Method) ---")
    
    last_counters = {}; last_timestamp = time.time(); last_purge_time = 0

    while True:
        try:
            config = load_config()
            if not config: time.sleep(60); continue

            if time.time() - last_purge_time > 86400:
                print("Running daily database maintenance..."); setup_database(config); last_purge_time = time.time()
                
            current_timestamp = time.time()
            current_counters = get_nfacct_counters()
            time_delta = current_timestamp - last_timestamp
            
            if time_delta > 0 and current_counters:
                records = []
                gs = config.get("global_settings",{})
                leases_file = gs.get("dnsmasq_leases_file","")
                mac_to_ip_map = {l['mac'].replace(':',''): l['ip'] for l in get_active_leases(leases_file)}
                
                for host_id, counts in current_counters.items():
                    last_total_bytes = last_counters.get(host_id, {}).get('bytes', 0)
                    total_bytes_delta = counts['bytes'] - last_total_bytes if counts['bytes'] >= last_total_bytes else counts['bytes']
                    rate_mbps = (total_bytes_delta * 8) / (time_delta * 1000000)
                    
                    records.append((
                        int(current_timestamp), host_id, mac_to_ip_map.get(host_id, "N/A"),
                        counts['bytes'], 0, round(rate_mbps, 2), 0.0
                    ))
                
                if records:
                    conn = sqlite3.connect(DB_FILE)
                    conn.executemany("INSERT OR REPLACE INTO bandwidth VALUES (?, ?, ?, ?, ?, ?, ?)", records)
                    conn.commit()
                    conn.close()
                    print(f"[{time.strftime('%H:%M:%S')}] Logged {len(records)} nfacct bandwidth records.")
            
            last_counters, last_timestamp = current_counters, current_timestamp
        
        except Exception as e:
            print(f"ERROR in sync.py main loop: {e}")

        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()