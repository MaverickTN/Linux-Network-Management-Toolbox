import sqlite3
import subprocess
import time
import csv
from io import StringIO
from pathlib import Path
from typing import Dict

from inetctl.core.config_loader import load_config

# --- Configuration ---
DB_FILE = Path("./inetctl_stats.db")
SYNC_INTERVAL_SECONDS = 15
DATA_RETENTION_DAYS = 10
# The xt_ACCOUNT module creates one table per network interface. We are interested in traffic
# on the main LAN-side bridge interface (e.g., br0, or whatever the user has).
# We'll pull this from the config file.

def get_active_leases(leases_file_path: str) -> list: # Unchanged
    if not Path(leases_file_path).exists(): return []
    leases=[]
    try:
        with open(leases_file_path,'r') as f:
            for line in f.readlines():
                parts=line.strip().split();
                if len(parts)>=4: leases.append({'mac':parts[1].lower(),'ip':parts[2],'hostname':parts[3] if parts[3]!='*' else '(unknown)'})
    except IOError as e: print(f"Error reading leases file: {e}"); return []
    return leases

def setup_database(config: Dict): # Unchanged
    conn=sqlite3.connect(DB_FILE); cursor=conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS bandwidth (timestamp INTEGER, host_id TEXT, ip_address TEXT, bytes_in INTEGER, bytes_out INTEGER, rate_in REAL, rate_out REAL, PRIMARY KEY (timestamp, host_id))")
    retention=config.get("global_settings",{}).get("database_retention_days",DATA_RETENTION_DAYS); purge_ts=int(time.time())-(retention*86400)
    cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?",(purge_ts,)); conn.commit(); conn.close()

def get_iptaccount_counters(iface: str) -> Dict[str, Dict[str, int]]:
    """
    Dumps accounting data using the 'iptaccount' utility and parses its CSV output.
    Returns a dictionary mapping IP addresses to their byte counters.
    """
    counters = {}
    if not iface:
        print("Warning: No accounting interface defined. Skipping stats collection.")
        return counters
        
    try:
        # The '-s' flag gives clean CSV; '-f' flushes counters after reading.
        result = subprocess.run(["sudo", "iptaccount", "-l", iface, "-s", "-f"], capture_output=True, text=True, check=True)
        # Use the csv module to reliably parse the output
        reader = csv.reader(StringIO(result.stdout))
        
        for row in reader:
            if not row or len(row) < 5: continue
            ip, _, _, bytes_out, bytes_in = row[0], row[1], row[2], int(row[3]), int(row[4])
            counters[ip] = {'in': bytes_in, 'out': bytes_out}

    except FileNotFoundError:
        print("ERROR: 'iptaccount' command not found. Is xtables-addons installed?")
    except subprocess.CalledProcessError as e:
        # This error is normal if the table doesn't exist yet, especially on first run
        # or if there's no traffic. We can safely ignore it.
        if "No such file or directory" not in e.stderr:
            print(f"Warning: Error running iptaccount for interface '{iface}': {e.stderr.strip()}")
            
    return counters


def main_loop():
    print("--- Starting inetctl Data Synchronizer (iptaccount Method) ---")
    
    last_counters = {}; last_timestamp = time.time(); last_purge_time = 0

    while True:
        try:
            config = load_config()
            if not config: time.sleep(60); continue

            gs = config.get("global_settings", {})
            accounting_iface = gs.get("accounting_interface") # e.g., "br0"

            if not accounting_iface:
                print("Warning: 'accounting_interface' not set in config. Accounting is disabled.")
                time.sleep(300) # Sleep longer if misconfigured
                continue

            if time.time() - last_purge_time > 86400:
                print("Running daily database maintenance..."); setup_database(config)
                last_purge_time = time.time()
                
            current_timestamp = time.time()
            current_counters = get_iptaccount_counters(accounting_iface)
            time_delta = current_timestamp - last_timestamp
            
            if time_delta > 0 and current_counters:
                records = []; leases_file = gs.get("dnsmasq_leases_file", "")
                ip_to_mac_map = {l['ip']: l['mac'].replace(':', '') for l in get_active_leases(leases_file)}
                
                for ip, counts in current_counters.items():
                    if ip not in ip_to_mac_map: continue
                    mac_sanitized = ip_to_mac_map[ip]

                    # This is now a simple rate calculation, no 'delta' needed since we flush the counters.
                    rate_in_mbps = (counts['in'] * 8) / (time_delta * 1000000)
                    rate_out_mbps = (counts['out'] * 8) / (time_delta * 1000000)
                    
                    # NOTE: We now get real In/Out data, so we can log it correctly.
                    records.append((
                        int(current_timestamp), mac_sanitized, ip,
                        counts['in'], counts['out'],
                        round(rate_in_mbps, 2), round(rate_out_mbps, 2)
                    ))
                
                if records:
                    conn = sqlite3.connect(DB_FILE);
                    conn.executemany("INSERT OR REPLACE INTO bandwidth VALUES (?,?,?,?,?,?,?)", records)
                    conn.commit(); conn.close()
                    print(f"[{time.strftime('%H:%M:%S')}] Logged {len(records)} iptaccount bandwidth records.")
            
            last_timestamp = current_timestamp
        
        except Exception as e:
            print(f"ERROR in sync.py main loop: {e}")

        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
