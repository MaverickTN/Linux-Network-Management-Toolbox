# lnmt/core/config_loader.py

import os
import json
import shutil
from pathlib import Path

CONFIG_FILENAME = "server_config.json"
CONFIG_DIR = "/etc/lnmt"
CONFIG_SEARCH_PATHS = [
    os.path.expanduser("~/.lnmt/" + CONFIG_FILENAME),
    "/etc/lnmt/" + CONFIG_FILENAME,
    "./" + CONFIG_FILENAME,
]

def find_config_file():
    for path in CONFIG_SEARCH_PATHS:
        if os.path.isfile(path):
            return path
    return CONFIG_SEARCH_PATHS[-1]

def load_config():
    config_path = find_config_file()
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        validate_config(config)
        return config
    except Exception as e:
        backup_config(config_path)
        repaired = auto_repair_config(config_path)
        if repaired:
            return repaired
        raise RuntimeError(f"Configuration invalid or corrupted: {e}")

def save_config(config, config_path=None):
    if config_path is None:
        config_path = find_config_file()
    # Backup before write
    backup_config(config_path)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def backup_config(config_path):
    if not os.path.isfile(config_path):
        return
    backup_path = config_path + ".bak"
    shutil.copy2(config_path, backup_path)

def validate_config(config):
    # Simple validation for essential sections
    required_sections = [
        "global_settings", "system_paths", "networks",
        "security", "web_portal", "qos_policies"
    ]
    for sec in required_sections:
        if sec not in config:
            raise ValueError(f"Missing config section: {sec}")
    # Add more validation rules as needed

def auto_repair_config(config_path):
    # Try to restore from backup if exists
    backup_path = config_path + ".bak"
    if os.path.isfile(backup_path):
        shutil.copy2(backup_path, config_path)
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            validate_config(config)
            return config
        except Exception:
            pass
    return None
