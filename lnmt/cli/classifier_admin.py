import sqlite3
DB_PATH = "/etc/lnmt/lnmt_stats.db"

def list_configs():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=== DNS Whitelist ===")
    cur.execute("SELECT host FROM dns_whitelist")
    for r in cur.fetchall():
        print(" -", r[0])

    print("\n=== App Patterns ===")
    cur.execute("SELECT app, pattern FROM app_patterns")
    for r in cur.fetchall():
        print(f" {r[0]} => {r[1]}")

    print("\n=== VLAN Thresholds ===")
    cur.execute("SELECT vlan, threshold_kbps, window_secs, session_limit_secs FROM vlan_thresholds")
    for v, k, w, l in cur.fetchall():
        print(f" VLAN {v}: {k} kbps, {w}s window, limit {l}s")

    conn.close()

if __name__ == "__main__":
    list_configs()
