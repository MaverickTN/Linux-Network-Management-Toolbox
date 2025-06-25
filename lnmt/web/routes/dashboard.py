from flask import Blueprint, render_template, request
import sqlite3

dashboard = Blueprint("dashboard", __name__)

DB_PATH = "/etc/lnmt/lnmt_stats.db"

@dashboard.route("/dashboard")
def show_dashboard():
    vlan = request.args.get("vlan")
    date = request.args.get("date")
    app = request.args.get("app")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT vlan FROM usage_sessions")
    vlans = [v[0] for v in cur.fetchall()]

    cur.execute("SELECT DISTINCT app FROM app_sessions")
    apps = [a[0] for a in cur.fetchall()]

    query = "SELECT vlan, host, SUM(seconds_used) FROM usage_sessions WHERE 1=1"
    args = []

    if vlan:
        query += " AND vlan=?"
        args.append(vlan)
    if date:
        query += " AND timestamp LIKE ?"
        args.append(f"{date}%")

    query += " GROUP BY vlan, host"

    cur.execute(query, args)
    usage_data = cur.fetchall()

    cur.execute("SELECT vlan, app, SUM(seconds_used) FROM app_sessions GROUP BY vlan, app")
    app_data = cur.fetchall()

    conn.close()
    return render_template("dashboard.html", usage_data=usage_data, app_data=app_data, vlans=vlans, apps=apps)
