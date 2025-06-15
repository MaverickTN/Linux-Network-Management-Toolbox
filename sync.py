import sqlite3
import subprocess
import time
import re
import csv
from io import StringIO
from pathlib import Path
from typing import Dict, List

from inetctl.core.config_loader import load_config
from inetctl.core.shorewall import parse_shorewall_interfaces
from inetctl.core.utils import get_active_leases

DB_FILE = Path("./inetctl_stats.db")
SYNC_INTERVAL_SECONDS = 15
DATA_RETENTION_DAYS = 10

def setup_database(config: Dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS bandwidth (timestamp INTEGER, host_id TEXT, ip_address TEXT, bytes_in INTEGER, bytes_out INTEGER, rate_in REAL, rate_out REAL, PRIMARY KEY (timestamp, host_id))")
    retention = config.get("global_settings",{}).get("database_retention_days", DATA_RETENTION_DAYS)
    purge_ts = int(time.time()) - (retention * 86400)
    cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?", (purge_ts,))
    if cursor.rowcount > 0: print(f"Purged {cursor.rowcount} old bandwidth records.")
    conn.commit(); conn.close()

def get_iptaccount_counters() -> Dict[str, Dict[str, int]]:
    """
    Iterates through configured Shorewall zones, ignoring unnecessary ones.
    """
    all_counters = {}
    zone_map = parse_shorewall_interfaces()
    if not zone_map: return {}
    
    # --- THIS IS THE CORRECTED LOGIC ---
    # The zone ignore list is now present, just like in shorewall.py
    ZONES_TO_IGNORE = {'net', 'local', 'docker', 'fw', '?FORMAT'}

    for zone_name in zone_map.keys():
        # Skip trying to read data for zones we know we don't account for
        if zone_name in ZONES_TO_IGNORE:
            continue
            
        try:
            result = subprocess.run(["sudo", "iptaccount", "-l", zone_name, "-f"], capture_output=True, text=True, check=True)
            pattern = re.compile(r"IP: ([\d.]+)\s+SRC\s+packets: \d+\s+bytes: (\d+)\s+DST\s+packets: \d+\s+bytes: (\d+)")
            for match in pattern.finditer(result.stdout):
                ip, bytes_out, bytes_in = match.groups()
                if ip not in all_counters: all_counters[ip] = {'in': 0, 'out': 0}
                all_counters[ip]['in'] += int(bytes_in)
                all_counters[ip]['out'] += int(bytes_out)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
            
    return all_counters

def get_active_leases(leases_file_path: str) -> list:
    if not Path(leases_file_path).exists(): return []
    leases=[]
    try:
        with open(leases_file_path,'r') as f:
            for line in f.readlines():
                parts=line.strip().split()
                if len(parts)>=4: leases.append({'mac':parts[1].lower(),'ip':parts[2],'hostname':parts[3] if parts[3]!='*' else '(unknown)'})
    except IOError as e: print(f"Error reading leases file: {e}"); return []
    return leases

def main_loop():
    print("--- Starting inetctl Data Synchronizer (Zone-based iptaccount) ---")
    last_purge_time = 0
    while True:
        try:
            config = load_config()
            if not config: time.sleep(60); continue

            if time.time() - last_purge_time > 86400:
                print("Running daily database maintenance..."); setup_database(config)
                last_purge_time = time.time()
                
            current_counters = get_iptaccount_counters()
            
            if current_counters:
                current_timestamp = int(time.time())
                paths = config.get("system_paths", {})
                leases_file = paths.get("dnsmasq_leases_file", "")
                ip_to_mac_map = {l['ip']: l['mac'].replace(':', '') for l in get_active_leases(leases_file)} if leases_file else {}
                records = []
                
                for ip, counts in current_counters.items():
                    if ip not in ip_to_mac_map: continue
                    mac_sanitized = ip_to_mac_map[ip]
                    rate_in_mbps = (counts['in'] * 8) / (SYNC_INTERVAL_SECONDS * 1000000)
                    rate_out_mbps = (counts['out'] * 8) / (SYNC_INTERVAL_SECONDS * 1000000)
                    records.append((current_timestamp, mac_sanitized, ip, counts['in'], counts['out'], round(rate_in_mbps, 2), round(rate_out_mbps, 2)))
                
                if records:
                    conn = sqlite3.connect(DB_FILE);
                    insert_query = """INSERT INTO bandwidth VALUES (?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(timestamp, host_id) DO UPDATE SET 
                                    bytes_in=bytes_in + excluded.bytes_in, bytes_out=bytes_out + excluded.bytes_out,
                                    rate_in=excluded.rate_in, rate_out=excluded.rate_out"""
                    conn.executemany(insert_query, records); conn.commit(); conn.close()
                    print(f"[{time.strftime('%H:%M:%S')}] Logged {len(records)} iptaccount bandwidth records.")
        except Exception as e:
            print(f"ERROR in sync.py main loop: {e}")
        
        time.sleep(SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()