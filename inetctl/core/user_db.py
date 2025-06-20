import json
from pathlib import Path
from threading import Lock

# Location for user profiles
USER_DB_PATH = Path("/etc/inetctl/userdb.json")
USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_db_lock = Lock()

THEME_DEFAULT = "dark"
THEME_DEFS = {
    "dark": "Dark",
    "light": "Light",
    "black": "Blackout",
    "solarized": "Solarized",
    "oceanic": "Oceanic",
    "nord": "Nord",
    "gruvbox": "Gruvbox",
    "material": "Material",
    "retro_terminal": "Retro Terminal",
    "matrix": "Green Matrix"
}

# ------------- Internal DB helpers ---------------

def _load_db():
    if USER_DB_PATH.exists():
        with _db_lock, USER_DB_PATH.open("r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def _save_db(db):
    with _db_lock, USER_DB_PATH.open("w") as f:
        json.dump(db, f, indent=2)

# ------------- Profile API ---------------

def get_user_profile(username):
    db = _load_db()
    return db.get(username)

def create_user_profile(username, **kwargs):
    db = _load_db()
    if username in db:
        return db[username]
    db[username] = {
        "email": "",
        "contact": "",
        "theme": kwargs.get("theme", THEME_DEFAULT),
        "notify": [],
    }
    _save_db(db)
    return db[username]

def update_user_profile(username, email=None, contact=None, theme=None, notify=None):
    db = _load_db()
    if username not in db:
        db[username] = {}
    if email is not None:
        db[username]["email"] = email
    if contact is not None:
        db[username]["contact"] = contact
    if theme is not None:
        db[username]["theme"] = theme
    if notify is not None:
        db[username]["notify"] = notify
    _save_db(db)
    return db[username]

def list_themes():
    return list(THEME_DEFS.keys())

def get_theme_for_user(username):
    db = _load_db()
    profile = db.get(username)
    return profile.get("theme") if profile else THEME_DEFAULT
