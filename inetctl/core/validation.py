import json
import shutil
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path("/etc/lnmt/server_config.json")
BACKUP_DIR = Path("/etc/lnmt/backup")

DEFAULT_CONFIG = {
    # ... full default config structure as previously defined ...
}

def backup_config():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"server_config_{timestamp}.json"
    if CONFIG_PATH.exists():
        shutil.copy(CONFIG_PATH, backup_path)
    return backup_path

def validate_config(config=None, repair=False):
    """
    Validate the loaded configuration.
    If repair=True, attempt to restore missing/invalid values from default.
    Returns (is_valid, repaired_config or None)
    """
    from inetctl.core.config_loader import load_config
    if config is None:
        config = load_config()
    is_valid = True
    repaired = False

    # Shallow validation - expand with deeper checks as needed!
    for key in DEFAULT_CONFIG:
        if key not in config:
            is_valid = False
            if repair:
                config[key] = DEFAULT_CONFIG[key]
                repaired = True
    # Add further field-level validation here

    if not is_valid and repair:
        backup_path = backup_config()
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        return False, config, backup_path
    return is_valid, (config if repair else None), None

def auto_validate_on_load():
    # This function can be called on config load, e.g. from config_loader.py
    valid, repaired_config, backup_path = validate_config(repair=True)
    if not valid and repaired_config:
        print(f"Config was invalid. Backed up old config to {backup_path} and auto-repaired.")
    return valid
