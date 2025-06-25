import sqlite3

def usage_summary():
    conn = sqlite3.connect("/etc/lnmt/lnmt_stats.db")
    cur = conn.cursor()

    cur.execute("SELECT vlan, host, SUM(seconds_used) FROM usage_sessions GROUP BY vlan, host")
    print("VLAN | Host | Seconds Used")
    for v, h, s in cur.fetchall():
        print(f"{v:<5} | {h:<15} | {s}")

    cur.execute("SELECT vlan, app, SUM(seconds_used) FROM app_sessions GROUP BY vlan, app")
    print("\nVLAN | App | Seconds Used")
    for v, a, s in cur.fetchall():
        print(f"{v:<5} | {a:<15} | {s}")

    conn.close()

if __name__ == "__main__":
    usage_summary()
