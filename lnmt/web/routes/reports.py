#!/usr/bin/env python3

from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
import sqlite3

DB_PATH = "/etc/lnmt/lnmt_stats.db"
reports_bp = Blueprint("reports_bp", __name__)

@reports_bp.route("/reports")
def traffic_report():
    days = int(request.args.get("days", 1))
    vlan = request.args.get("vlan")
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = '''
        SELECT timestamp, vlan, ip, hostname, app, seconds_used
        FROM usage_sessions
        WHERE timestamp >= ?
    '''
    args = [since]

    if vlan:
        query += " AND vlan = ?"
        args.append(vlan)

    query += " ORDER BY timestamp DESC"
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()

    return render_template("traffic_report.html", rows=rows, vlan=vlan, days=days)
