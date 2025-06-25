import sqlite3
import csv
import json
import argparse

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def export_data(format="csv"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT vlan, host, seconds_used FROM usage_sessions")
    usage = cur.fetchall()

    cur.execute("SELECT vlan, app, seconds_used FROM app_sessions")
    apps = cur.fetchall()
    conn.close()

    if format == "csv":
        with open("usage_export.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["VLAN", "Host", "Seconds"])
            writer.writerows(usage)
        with open("app_export.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["VLAN", "App", "Seconds"])
            writer.writerows(apps)
        print("CSV export complete.")
    elif format == "json":
        with open("usage_export.json", "w") as f:
            json.dump([{"vlan": v, "host": h, "seconds": s} for v, h, s in usage], f, indent=2)
        with open("app_export.json", "w") as f:
            json.dump([{"vlan": v, "app": a, "seconds": s} for v, a, s in apps], f, indent=2)
        print("JSON export complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()
    export_data(args.format)
