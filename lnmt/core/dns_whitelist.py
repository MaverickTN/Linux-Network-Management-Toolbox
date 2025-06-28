import sqlite3

DB_PATH = "/etc/lnmt/lnmt.db"

def get_whitelist():
    with sqlite3.connect(DB_PATH) as conn:
        return [
            {"id": row[0], "domain": row[1], "description": row[2]}
            for row in conn.execute("SELECT id, domain, description FROM dns_whitelist")
        ]

def add_domain(domain, description=""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO dns_whitelist (domain, description) VALUES (?, ?)",
            (domain, description)
        )
        conn.commit()

def remove_domain(domain_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM dns_whitelist WHERE id=?", (domain_id,))
        conn.commit()
