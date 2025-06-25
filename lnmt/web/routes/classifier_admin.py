from flask import Blueprint, render_template, request, redirect
import sqlite3

admin = Blueprint("classifier_admin", __name__)
DB_PATH = "/etc/lnmt/lnmt_stats.db"

def get_all_config():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS dns_whitelist (host TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS app_patterns (app TEXT, pattern TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS vlan_thresholds (vlan TEXT PRIMARY KEY, threshold_kbps INTEGER, window_secs INTEGER, session_limit_secs INTEGER)")

    cur.execute("SELECT host FROM dns_whitelist")
    whitelist = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT app, pattern FROM app_patterns")
    app_patterns = cur.fetchall()

    cur.execute("SELECT * FROM vlan_thresholds")
    thresholds = cur.fetchall()

    conn.close()
    return whitelist, app_patterns, thresholds

@admin.route("/classifiers", methods=["GET", "POST"])
def classifiers():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST":
        if "add_whitelist" in request.form:
            cur.execute("INSERT OR IGNORE INTO dns_whitelist (host) VALUES (?)", (request.form["add_whitelist"],))
        if "remove_whitelist" in request.form:
            cur.execute("DELETE FROM dns_whitelist WHERE host=?", (request.form["remove_whitelist"],))
        if "app" in request.form and "pattern" in request.form:
            cur.execute("INSERT INTO app_patterns (app, pattern) VALUES (?, ?)", (request.form["app"], request.form["pattern"]))
        if "remove_pattern" in request.form:
            cur.execute("DELETE FROM app_patterns WHERE pattern=?", (request.form["remove_pattern"],))
        if "vlan" in request.form:
            cur.execute("REPLACE INTO vlan_thresholds (vlan, threshold_kbps, window_secs, session_limit_secs) VALUES (?, ?, ?, ?)",
                        (request.form["vlan"], request.form["kbps"], request.form["window"], request.form["limit"]))
        conn.commit()
        conn.close()
        return redirect("/classifiers")

    whitelist, app_patterns, thresholds = get_all_config()
    return render_template("classifier_admin.html", whitelist=whitelist, app_patterns=app_patterns, thresholds=thresholds)
