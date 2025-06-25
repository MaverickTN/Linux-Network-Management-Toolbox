import sqlite3
import json
import os
from lnmt.core.admin_eventlog import log_admin_event

DB_PATH = "/etc/lnmt/lnmt_stats.db"
STATIC_JSON = "/etc/lnmt/static_roles.json"

def migrate_roles():
    if not os.path.exists(STATIC_JSON):
        print("No static roles file found.")
        return

    with open(STATIC_JSON) as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS permissions (id INTEGER PRIMARY KEY, role_id INTEGER, permission TEXT)")

    for role, perms in data.items():
        cur.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (role,))
        cur.execute("SELECT id FROM roles WHERE name=?", (role,))
        role_id = cur.fetchone()[0]
        for p in perms:
            cur.execute("INSERT INTO permissions (role_id, permission) VALUES (?, ?)", (role_id, p))

        log_admin_event("migrate_role", actor="system", target=role, details=f"Migrated with {len(perms)} permissions")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_roles()
