import sqlite3

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def show_diffs(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, filepath, diff FROM config_diff ORDER BY id DESC LIMIT ?", (limit,))
    for ts, fp, df in cur.fetchall():
        print(f"=== {fp} @ {ts} ===\n{df}\n{'='*40}")
    conn.close()

if __name__ == "__main__":
    show_diffs()
