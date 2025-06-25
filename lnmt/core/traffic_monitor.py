#!/usr/bin/env python3

import time
import sqlite3
import subprocess
import logging
from datetime import datetime

DB_PATH = "/etc/lnmt/lnmt_stats.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrafficMonitor")

def parse_traffic():
    # Placeholder for Shorewall or iptables accounting
    # Simulate with dummy data
    traffic_data = [
        {"mac": "AA:BB:CC:DD:EE:01", "bytes_in": 1000, "bytes_out": 1500},
        {"mac": "AA:BB:CC:DD:EE:02", "bytes_in": 2000, "bytes_out": 500}
    ]
    return traffic_data

def update_db(traffic_data):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS traffic (
                mac TEXT,
                timestamp TEXT,
                bytes_in INTEGER,
                bytes_out INTEGER
            )
        """)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for entry in traffic_data:
            cur.execute("""
                INSERT INTO traffic (mac, timestamp, bytes_in, bytes_out)
                VALUES (?, ?, ?, ?)
            """, (entry["mac"], timestamp, entry["bytes_in"], entry["bytes_out"]))
        conn.commit()
        conn.close()
        logger.debug("Traffic data committed to DB.")
    except Exception as e:
        logger.exception("Failed to update traffic database")

def traffic_loop():
    logger.info("Traffic accounting loop started (3s intervals)")
    while True:
        try:
            data = parse_traffic()
            update_db(data)
        except Exception as e:
            logger.exception("Error in traffic loop")
        time.sleep(3)
