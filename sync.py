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

def setup_database(config: Dict): # Unchanged
def get_active_leases(leases_file_path: str) -> list: # Unchanged

def get_nfacct_counters() -> Dict[str, Dict[str, int]]:
    """
    Dumps accounting data using the 'nfacct' utility and parses the JSON output.
    Returns a dictionary mapping host_id (sanitized MAC) to its byte counters.
    """
    counters = {}
    try:
        # The 'nfacct get' command with '-J' dumps the data as clean JSON
        result = subprocess.run(["sudo", "nfacct", "get", "-J"], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # The JSON is a list of accounting objects
        for acct_obj in data.get("nfacct", []):
            obj_name = acct_obj.get("name")
            if obj_name and obj_name.startswith("inetctl_"):
                # Extract the host_id (sanitized MAC) from the object name
                host_id = obj_name.replace("inetctl_", "")
                
                # Each object has a 'pkts' and 'bytes' counter
                if host_id not in counters: counters[host_id] = {'bytes': 0, 'pkts': 0}
                counters[host_id]['bytes'] += acct_obj.get('bytes', 0)
                counters[host_id]['pkts'] += acct_obj.get('pkts', 0)
    
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
                print("Running daily database maintenance...")
                setup_database(config); last_purge_time = time.time()
                
            current_timestamp = time.time()
            # Get counters from our new, clean function
            current_counters = get_nfacct_counters()
            time_delta = current_timestamp - last_timestamp
            
            if time_delta > 0 and current_counters:
                records = []
                mac_to_ip_map = {l['mac'].replace(':',''): l['ip'] for l in get_active_leases(config.get("global_settings",{}).get("dnsmasq_leases_file",""))}
                
                for host_id, counts in current_counters.items():
                    # The nfacct data combines upload and download, so we will log the total bytes
                    # and split it into in/out for the db schema for now.
                    # In a future refactor, we might simplify the db schema.
                    last_total_bytes = last_counters.get(host_id, {}).get('bytes', 0)
                    total_bytes_delta = counts['bytes'] - last_total_bytes if counts['bytes'] >= last_total_bytes else counts['bytes']
                    
                    rate_mbps = (total_bytes_delta * 8) / (time_delta * 1_000_000)
                    
                    # For now, we put all traffic in 'in' and zero in 'out' for simplicity.
                    # This correctly calculates total rate.
                    records.append((
                        int(current_timestamp), host_id, mac_to_ip_map.get(host_id, "N/A"),
                        counts['bytes'], 0, # bytes_in, bytes_out
                        round(rate_mbps, 2), 0.0 # rate_in, rate_out
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