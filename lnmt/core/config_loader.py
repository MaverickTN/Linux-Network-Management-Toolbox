# lnmt/core/config_loader.py

import json
import shutil
import os
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".config" / "lnmt"
CONFIG_PATH = CONFIG_DIR / "server_config.json"
CONFIG_BACKUP_PATH = CONFIG_DIR / f"server_config_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

def backup_config():
    if CONFIG_PATH.exists():
        shutil.copy2(CONFIG_PATH, CONFIG_BACKUP_PATH)

def validate_config(config):
    # Basic validation for required keys
    required_keys = ["global_settings", "system_paths", "networks"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Config is missing required key: {key}")
    # Add more validation as your schema evolves

def repair_config():
    # Placeholder for auto-repair logic; can attempt to fix minor issues
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        validate_config(config)
        return config
    except Exception as e:
        backup_config()
        # If can't repair, raise error
        raise RuntimeError(f"Config is irreparable: {e}")

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        validate_config(config)
        return config
    except Exception as e:
        # Try repair if invalid
        return repair_config()

def save_config(config):
    validate_config(config)
    backup_config()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def find_config_file():
    if CONFIG_PATH.exists():
        return str(CONFIG_PATH)
    return None

def get_config_path():
    return str(CONFIG_PATH)
