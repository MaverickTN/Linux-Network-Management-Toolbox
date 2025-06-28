
import requests
import sqlite3
import time
from packaging.version import Version, InvalidVersion

CACHE_REFRESH_HOURS = 6

def get_db_conn():
    return sqlite3.connect('/etc/lnmt/lnmt.db')

def get_current_version():
    # Reads from DB, falls back to version.py
    try:
        with get_db_conn() as db:
            cur = db.execute("SELECT value FROM meta WHERE key='current_version'")
            return cur.fetchone()[0]
    except Exception:
        return "0.0.0"

def get_latest_version(config):
    # Try cached first
    try:
        with get_db_conn() as db:
            cur = db.execute("SELECT value FROM meta WHERE key='latest_version_cache'")
            cache = cur.fetchone()
            cur = db.execute("SELECT value FROM meta WHERE key='latest_version_cache_time'")
            cache_time = float(cur.fetchone()[0])
            if cache and (time.time() - cache_time) < (CACHE_REFRESH_HOURS * 3600):
                return cache[0]
    except Exception:
        pass
    # If not cached or expired, fetch remote
    url = config.get('update_check_url')
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        latest = resp.json().get('version')  # expects {"version": "0.4.1"}
        if latest:
            with get_db_conn() as db:
                db.execute("UPDATE meta SET value=? WHERE key='latest_version_cache'", (latest,))
                db.execute("UPDATE meta SET value=? WHERE key='latest_version_cache_time'", (str(time.time()),))
            return latest
    except Exception:
        return None
    return None

def compare_versions(v1, v2):
    try:
        return Version(v1) < Version(v2)
    except InvalidVersion:
        return False

# ... other core logic for admin-only update/dismiss actions ...
