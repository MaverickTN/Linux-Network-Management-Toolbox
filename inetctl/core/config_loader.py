# inetctl/core/config_loader.py

import json
import shutil
from pathlib import Path

CONFIG_SEARCH_PATHS = [
    "/etc/lnmt/server_config.json",
    str(Path.home() / ".lnmt_config.json"),
    str(Path.cwd() / "server_config.json"),
]

BACKUP_SUFFIX = ".bak"

def find_config_file():
    for path in CONFIG_SEARCH_PATHS:
        p = Path(path)
        if p.exists():
            return p
    return None

def load_config(config_path=None):
    """Load and validate the configuration file, repairing if possible."""
    config_path = Path(config_path or find_config_file() or CONFIG_SEARCH_PATHS[-1])
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")

    # Backup before load
    backup_config(config_path)

    with open(config_path, "r") as f:
        try:
            config = json.load(f)
            if not validate_config(config):
                raise ValueError("Configuration validation failed.")
            return config
        except Exception as e:
            # Attempt auto-repair if backup exists
            repaired = attempt_auto_repair(config_path)
            if repaired:
                return repaired
            raise e

def save_config(config, config_path=None):
    config_path = Path(config_path or find_config_file() or CONFIG_SEARCH_PATHS[-1])
    # Backup before save
    backup_config(config_path)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def backup_config(config_path):
    config_path = Path(config_path)
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + BACKUP_SUFFIX)
        shutil.copy2(config_path, backup_path)

def attempt_auto_repair(config_path):
    backup_path = Path(str(config_path) + BACKUP_SUFFIX)
    if backup_path.exists():
        try:
            with open(backup_path, "r") as f:
                config = json.load(f)
                if validate_config(config):
                    # Restore backup
                    shutil.copy2(backup_path, config_path)
                    return config
        except Exception:
            pass
    return None

def validate_config(config):
    """
    Validate the configuration structure.
    Extend this function as new keys are added.
    """
    # Minimal required keys for now
    required_top_keys = [
        "global_settings", "system_paths", "web_portal", "qos_policies"
    ]
    for k in required_top_keys:
        if k not in config:
            return False
    # Additional, deeper validation can be added here
    return True
