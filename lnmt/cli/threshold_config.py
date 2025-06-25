#!/usr/bin/env python3

import argparse
import sqlite3
from tabulate import tabulate

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def list_thresholds():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vlan_id, threshold_kbps, time_window_secs, session_limit_secs FROM vlan_thresholds ORDER BY vlan_id")
    rows = cur.fetchall()
    conn.close()

    print(tabulate(rows, headers=["VLAN", "Threshold (kbps)", "Time Window (s)", "Session Limit (s)"], tablefmt="grid"))

def set_threshold(vlan_id, threshold_kbps, time_window, session_limit):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO vlan_thresholds (vlan_id, threshold_kbps, time_window_secs, session_limit_secs)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(vlan_id) DO UPDATE SET
            threshold_kbps = excluded.threshold_kbps,
            time_window_secs = excluded.time_window_secs,
            session_limit_secs = excluded.session_limit_secs
    """, (vlan_id, threshold_kbps, time_window, session_limit))
    conn.commit()
    conn.close()
    print(f"Threshold for VLAN {vlan_id} set.")

def main():
    parser = argparse.ArgumentParser(description="LNMT VLAN Threshold Config Tool")
    sub = parser.add_subparsers(dest="command")

    list_cmd = sub.add_parser("list", help="List all VLAN thresholds")

    set_cmd = sub.add_parser("set", help="Set threshold for a VLAN")
    set_cmd.add_argument("vlan_id", type=int)
    set_cmd.add_argument("threshold_kbps", type=int, help="Bandwidth threshold in kilobits per second")
    set_cmd.add_argument("time_window_secs", type=int, help="How many seconds per sample")
    set_cmd.add_argument("session_limit_secs", type=int, help="Session time before blacklisting")

    args = parser.parse_args()
    if args.command == "list":
        list_thresholds()
    elif args.command == "set":
        set_threshold(args.vlan_id, args.threshold_kbps, args.time_window_secs, args.session_limit_secs)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
