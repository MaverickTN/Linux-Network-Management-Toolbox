import sqlite3
import subprocess
import time
import re
import json
from pathlib import Path

# --- Configuration ---
DB_FILE = Path("./inetctl_stats.db")
CONFIG_FILE = Path("./server_config.json")
COLLECTION_INTERVAL_SECONDS = 5
DATA_RETENTION_DAYS = 10 # Configurable data retention

def setup_database():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Store by a stable ID (MAC address), not the changing IP
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
    conn.commit()
    conn.close()

def purge_old_data():
    """Removes data older than the retention period from the database."""
    purge_before_timestamp = int(time.time()) - (DATA_RETENTION_DAYS * 24 * 60 * 60)
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bandwidth WHERE timestamp < ?", (purge_before_timestamp,))
        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()
        if deleted_rows > 0:
            print(f"Purged {deleted_rows} old records from the database.")
    except Exception as e:
        print(f"Error purging old data: {e}")

def get_live_monitored_hosts() -> list:
    """Loads the DHCP lease file and returns a list of all active hosts."""
    if not CONFIG_FILE.exists():
        return []
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file")
        if not leases_file or not Path(leases_file).exists():
            return []
            
        with open(leases_file, 'r') as f:
            leases_raw = f.readlines()
            
        active_hosts = []
        for line in leases_raw:
            parts = line.strip().split()
            if len(parts) >= 3:
                # We need mac and ip for accounting
                active_hosts.append({'mac': parts[1].lower(), 'ip': parts[2]})
        return active_hosts
    except Exception as e:
        print(f"Error loading config or leases: {e}")
        return []

def get_iptables_counters(hosts: list) -> dict:
    """Parses iptables accounting chains for each monitored host."""
    counters = {}
    for host in hosts:
        ip = host.get("ip")
        mac_sanitized = host.get("mac", "").replace(":", "")
        if not ip or not mac_sanitized:
            continue

        chain_name = f"acct_{mac_sanitized}" # Shorewall v5.2+ uses this format
        
        try:
            result = subprocess.run(
                ["sudo", "iptables", "-v", "-x", "-n", "-L", chain_name],
                capture_output=True, text=True, check=True
            )

            byte_pattern = re.compile(r"^\s*\d+\s+(\d+)\s+")
            lines = result.stdout.strip().splitlines()
            
            if len(lines) >= 4:
                upload_match = byte_pattern.match(lines[2])
                download_match = byte_pattern.match(lines[3])
                
                if upload_match and download_match:
                    counters[mac_sanitized] = {'out': int(upload_match.group(1)), 'in': int(download_match.group(1)), 'ip': ip}

        except subprocess.CalledProcessError:
            continue
        except Exception as e:
            print(f"Error processing chain {chain_name}: {e}")
            
    return counters

def main_loop():
    """The main collection loop."""
    print("Starting inetctl statistics collector...")
    setup_database()
    
    last_counters = {}
    last_timestamp = time.time()
    last_purge_time = 0

    while True:
        # Purge data once every ~24 hours
        if time.time() - last_purge_time > (24 * 60 * 60):
            purge_old_data()
            last_purge_time = time.time()

        current_timestamp = time.time()
        live_hosts = get_live_monitored_hosts()
        if not live_hosts:
            time.sleep(30)
            continue
            
        current_counters = get_iptables_counters(live_hosts)
        time_delta = current_timestamp - last_timestamp
        if time_delta == 0:
            time.sleep(COLLECTION_INTERVAL_SECONDS)
            continue

        records_to_insert = []
        for host_id, counts in current_counters.items(): # host_id is now the sanitized MAC
            last_in = last_counters.get(host_id, {}).get('in', 0)
            last_out = last_counters.get(host_id, {}).get('out', 0)
            
            bytes_in_delta = counts['in'] - last_in if counts['in'] >= last_in else counts['in']
            bytes_out_delta = counts['out'] - last_out if counts['out'] >= last_out else counts['out']

            rate_in_mbps = (bytes_in_delta * 8) / (time_delta * 1_000_000)
            rate_out_mbps = (bytes_out_delta * 8) / (time_delta * 1_000_000)
            
            records_to_insert.append((int(current_timestamp), host_id, counts['ip'], counts['in'], counts['out'], round(rate_in_mbps, 2), round(rate_out_mbps, 2)))
        
        if records_to_insert:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.executemany("INSERT OR REPLACE INTO bandwidth VALUES (?, ?, ?, ?, ?, ?, ?)", records_to_insert)
            conn.commit()
            conn.close()
            print(f"Logged {len(records_to_insert)} records at {time.strftime('%Y-%m-%d %H:%M:%S')}")

        last_counters = current_counters
        last_timestamp = current_timestamp
        
        time.sleep(COLLECTION_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
