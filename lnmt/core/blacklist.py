import sqlite3
from datetime import datetime, timedelta
import subprocess
from lnmt.core.admin_eventlog import log_admin_event

DB_PATH = "/etc/lnmt/lnmt_stats.db"
PENDING_WINDOW_SECS = 120  # grace period before enforcing blacklist

def get_today_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

def smooth_usage(samples):
    # Moving average smoothing
    if not samples:
        return 0
    return sum(samples[-5:]) / min(len(samples), 5)

def enforce_blacklist():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS vlan_blacklist_status (vlan TEXT PRIMARY KEY, status TEXT, last_change TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS blacklist_events (id INTEGER PRIMARY KEY, vlan TEXT, timestamp TEXT, action TEXT, reason TEXT)")

    cur.execute("SELECT vlan_id, session_limit_secs FROM vlan_thresholds")
    thresholds = {str(v): t for v, t in cur.fetchall()}

    today = get_today_str()
    for vlan, limit in thresholds.items():
        cur.execute(
            "SELECT timestamp, seconds_used FROM usage_sessions WHERE vlan=? AND timestamp LIKE ? ORDER BY timestamp DESC",
            (vlan, today + "%")
        )
        samples = [r[1] for r in cur.fetchall()]
        total_today = sum(samples)
        avg_usage = smooth_usage(samples)

        cur.execute("SELECT status, last_change FROM vlan_blacklist_status WHERE vlan=?", (vlan,))
        row = cur.fetchone()
        now = datetime.utcnow().isoformat()

        if total_today >= limit:
            if row and row[0] == "pending":
                # If grace expired, enforce blacklist
                last_change = datetime.fromisoformat(row[1])
                if datetime.utcnow() - last_change > timedelta(seconds=PENDING_WINDOW_SECS):
                    try:
                        subprocess.run(["shorewall", "drop", "vlan:" + vlan], check=True)
                        log_admin_event("blacklist", target=vlan, details=f"Exceeded {limit}, avg={avg_usage:.1f}")
                        cur.execute("INSERT INTO blacklist_events (vlan, timestamp, action, reason) VALUES (?, ?, ?, ?)",
                                    (vlan, now, "blacklist", f"Exceeded {limit}s threshold"))
                        cur.execute("UPDATE vlan_blacklist_status SET status='blacklisted', last_change=? WHERE vlan=?", (now, vlan))
                    except Exception as e:
                        log_admin_event("blacklist", target=vlan, success=False, details=str(e))
            elif not row:
                cur.execute("INSERT INTO vlan_blacklist_status (vlan, status, last_change) VALUES (?, ?, ?)",
                            (vlan, "pending", now))
                log_admin_event("blacklist_pending", target=vlan, details=f"Over limit, grace started")
            elif row[0] == "blacklisted":
                pass  # Already blacklisted
            else:
                cur.execute("UPDATE vlan_blacklist_status SET status='pending', last_change=? WHERE vlan=?", (now, vlan))
        else:
            if row and row[0] == "blacklisted":
                # Un-blacklist if back under limit
                try:
                    subprocess.run(["shorewall", "allow", "vlan:" + vlan], check=True)
                    log_admin_event("unblacklist", target=vlan, details=f"Usage back under {limit}, avg={avg_usage:.1f}")
                    cur.execute("INSERT INTO blacklist_events (vlan, timestamp, action, reason) VALUES (?, ?, ?, ?)",
                                (vlan, now, "unblacklist", "Usage normalized"))
                except Exception as e:
                    log_admin_event("unblacklist", target=vlan, success=False, details=str(e))
                cur.execute("UPDATE vlan_blacklist_status SET status='ok', last_change=? WHERE vlan=?", (now, vlan))
            elif row and row[0] != "ok":
                cur.execute("UPDATE vlan_blacklist_status SET status='ok', last_change=? WHERE vlan=?", (now, vlan))
            elif not row:
                cur.execute("INSERT INTO vlan_blacklist_status (vlan, status, last_change) VALUES (?, ?, ?)",
                            (vlan, "ok", now))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    enforce_blacklist()
