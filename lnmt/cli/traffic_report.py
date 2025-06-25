#!/usr/bin/env python3

import argparse
import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def query_usage(vlan=None, ip=None, app=None, days=1):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = "SELECT timestamp, vlan, ip, hostname, app, seconds_used FROM usage_sessions WHERE timestamp >= ?"
    args = [since]

    if vlan:
        query += " AND vlan = ?"
        args.append(vlan)
    if ip:
        query += " AND ip = ?"
        args.append(ip)
    if app:
        query += " AND app = ?"
        args.append(app)

    query += " ORDER BY timestamp DESC"
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()

    headers = ["Time", "VLAN", "IP", "Hostname", "App", "Seconds"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def summarize_usage(vlan=None, days=1):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = (
        """
        SELECT vlan, ip, hostname, app, SUM(seconds_used)
        FROM usage_sessions
        WHERE timestamp >= ?
        """
    )
    args = [since]

    if vlan:
        query += " AND vlan = ?"
        args.append(vlan)

    query += " GROUP BY vlan, ip, app ORDER BY SUM(seconds_used) DESC"
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()

    headers = ["VLAN", "IP", "Hostname", "App", "Total Seconds"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="LNMT Reporting CLI")
    parser.add_argument("--vlan", help="Filter by VLAN")
    parser.add_argument("--ip", help="Filter by IP")
    parser.add_argument("--app", help="Filter by App name")
    parser.add_argument("--days", type=int, default=1, help="Days back to report (default: 1)")
    parser.add_argument("--summary", action="store_true", help="Summarize totals instead of showing entries")
    args = parser.parse_args()

    if args.summary:
        summarize_usage(vlan=args.vlan, days=args.days)
    else:
        query_usage(vlan=args.vlan, ip=args.ip, app=args.app, days=args.days)

if __name__ == "__main__":
    main()