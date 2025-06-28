import sqlite3
import datetime

DB_PATH = "/etc/lnmt/lnmt.db"

def list_configs():
    with sqlite3.connect(DB_PATH) as conn:
        return [
            {"id": row[0], "name": row[1], "yaml": row[2], "last_modified": row[3]}
            for row in conn.execute("SELECT id, name, yaml, last_modified FROM netplan_configs ORDER BY name")
        ]

def get_config(config_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, yaml, last_modified FROM netplan_configs WHERE id=?", (config_id,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "yaml": row[2], "last_modified": row[3]}
        return None

def save_config(name, yaml):
    now = datetime.datetime.utcnow()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO netplan_configs (name, yaml, last_modified) VALUES (?, ?, ?)",
            (name, yaml, now)
        )
        conn.commit()

def delete_config(config_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM netplan_configs WHERE id=?", (config_id,))
        conn.commit()
