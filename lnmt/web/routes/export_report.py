from flask import Blueprint, Response
import sqlite3
import csv
import io
import json

export = Blueprint("export_report", __name__)
DB_PATH = "/etc/lnmt/lnmt_stats.db"

@export.route("/export/<ftype>")
def export_file(ftype):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT vlan, host, seconds_used FROM usage_sessions")
    usage = cur.fetchall()

    cur.execute("SELECT vlan, app, seconds_used FROM app_sessions")
    apps = cur.fetchall()
    conn.close()

    if ftype == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["VLAN", "Host", "Seconds"])
        writer.writerows(usage)
        buf.write("\n\n")
        writer.writerow(["VLAN", "App", "Seconds"])
        writer.writerows(apps)
        return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=lnmt_report.csv"})
    elif ftype == "json":
        out = {
            "usage": [{"vlan": v, "host": h, "seconds": s} for v, h, s in usage],
            "apps": [{"vlan": v, "app": a, "seconds": s} for v, a, s in apps]
        }
        return Response(json.dumps(out, indent=2), mimetype="application/json", headers={"Content-Disposition": "attachment; filename=lnmt_report.json"})
