import sqlite3

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def view_admin_events(limit=20):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, actor, action, target, success, details FROM admin_eventlog ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    for r in rows:
        status = "OK" if r[4] else "FAIL"
        print(f"[{r[0]}] ({status}) {r[1]} -> {r[2]} {r[3]} :: {r[5]}")
    conn.close()

if __name__ == "__main__":
    view_admin_events()
