# lnmt/core/config_loader.py

import json
from pathlib import Path
from lnmt.core.logging_utils import log_event, log_warning, log_error

CONFIG_SEARCH_PATHS = [
    "/etc/lnmt/lnmt_config.json",
    str(Path.home() / ".config" / "lnmt" / "lnmt_config.json"),
    "./lnmt_config.json"
]

def find_config_file():
    for path in CONFIG_SEARCH_PATHS:
        if Path(path).is_file():
            return path
    return CONFIG_SEARCH_PATHS[0]  # default to first if not found

def load_config(config_path=None):
    config_path = config_path or find_config_file()
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        # Validation check (basic structure)
        if not isinstance(config, dict) or "global_settings" not in config:
            raise ValueError("Config missing core structure.")
        return config
    except Exception as e:
        log_error(f"Config load failed at {config_path}: {e}")
        raise

def save_config(config, config_path=None):
    config_path = config_path or find_config_file()
    backup_config(config_path)
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        log_event(f"Config saved to {config_path}")
        return True
    except Exception as e:
        log_error(f"Failed to save config to {config_path}: {e}")
        return False

def backup_config(config_path=None):
    config_path = config_path or find_config_file()
    try:
        backup_path = f"{config_path}.bak"
        if Path(config_path).exists():
            with open(config_path, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())
            log_event(f"Config backup created at {backup_path}")
    except Exception as e:
        log_warning(f"Failed to create config backup: {e}")

def validate_config_file(config_path=None):
    config_path = config_path or find_config_file()
    try:
        config = load_config(config_path)
        # Insert deeper validation logic here as needed
        return True
    except Exception:
        return False
