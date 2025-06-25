#!/usr/bin/env python3

import sqlite3
from datetime import datetime, timedelta
import re

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def classify_usage(data_points):
    '''
    Accepts: list of dicts with keys: vlan, ip, hostname, bytes, timestamp, dns_query
    Returns: list of (ip, seconds_used, app_group, vlan)
    '''
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Load thresholds
    cur.execute("SELECT vlan_id, threshold_kbps, time_window_secs FROM vlan_thresholds")
    thresholds = {str(row[0]): (row[1]*1024, row[2]) for row in cur.fetchall()}

    # Load DNS whitelist
    cur.execute("SELECT pattern FROM dns_whitelist")
    dns_whitelist = [row[0] for row in cur.fetchall()]

    # Load app patterns
    cur.execute("SELECT app_categories.name, app_patterns.pattern FROM app_patterns JOIN app_categories ON app_patterns.app_id = app_categories.id")
    app_patterns = [(name, re.compile(pat)) for name, pat in cur.fetchall()]

    sessions = {}

    for entry in data_points:
        vlan = str(entry["vlan"])
        ip = entry["ip"]
        hostname = entry.get("hostname")
        bytes_used = entry["bytes"]
        timestamp = entry["timestamp"]
        dns_query = entry.get("dns_query", "")

        # Skip if whitelisted
        if any(re.search(pat, dns_query) for pat in dns_whitelist):
            continue

        # Determine app group
        app = None
        for name, pattern in app_patterns:
            if pattern.search(dns_query):
                app = name
                break

        # Check usage threshold
        threshold_bytes, window_secs = thresholds.get(vlan, (1024*15, 15))  # default 15 KB/s over 15 sec
        if bytes_used >= threshold_bytes:
            key = (vlan, ip, app)
            if key not in sessions:
                sessions[key] = 0
            sessions[key] += window_secs

    # Store in DB
    now = datetime.utcnow().isoformat()
    for (vlan, ip, app), secs in sessions.items():
        cur.execute("INSERT INTO usage_sessions (timestamp, vlan, ip, hostname, app, seconds_used) VALUES (?, ?, ?, ?, ?, ?)",
                    (now, vlan, ip, hostname, app, secs))
    conn.commit()
    conn.close()
