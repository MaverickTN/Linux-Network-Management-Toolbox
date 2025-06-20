# inetctl/core/config_loader.py

import os
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("inetctl.core.config_loader")

CONFIG_SEARCH_PATHS = [
    "/etc/inetctl/server_config.json",
    str(Path.home() / ".config" / "inetctl" / "server_config.json"),
    "./server_config.json"
]

CONFIG_SCHEMA = {
    "global_settings": dict,
    "system_paths": dict,
    "networks": list,
    "known_hosts": list,
    "security": dict,
    "web_portal": dict,
    "qos_policies": dict,
    "pihole": dict,
    "wireguard": dict,
}

def find_config_file() -> str:
    for path in CONFIG_SEARCH_PATHS:
        if os.path.isfile(path):
            return path
    # Default to last path if nothing found
    return CONFIG_SEARCH_PATHS[-1]

def backup_config(config_path: str):
    backup_path = config_path + ".bak"
    try:
        shutil.copy2(config_path, backup_path)
        logger.info(f"Config backup saved to {backup_path}")
    except Exception as e:
        logger.error(f"Failed to backup config: {e}")

def load_config(config_path: str = None, validate: bool = True) -> dict:
    config_path = config_path or find_config_file()
    if not os.path.isfile(config_path):
        logger.warning(f"No configuration file found at {config_path}. Returning empty config.")
        return {}
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        if validate:
            if not validate_config(config):
                logger.warning("Config validation failed. Attempting repair.")
                config = attempt_repair(config, config_path)
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        raise

def save_config(config: dict, config_path: str = None):
    config_path = config_path or find_config_file()
    backup_config(config_path)
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise

def validate_config(config: dict) -> bool:
    """
    Checks for the presence and type of all required top-level config fields.
    """
    missing = []
    for key, typ in CONFIG_SCHEMA.items():
        if key not in config or not isinstance(config[key], typ):
            missing.append(key)
    if missing:
        logger.error(f"Config missing keys or wrong types: {missing}")
        return False
    return True

def attempt_repair(config: dict, config_path: str) -> dict:
    """
    Tries to repair common config issues (missing sections).
    """
    changed = False
    for key, typ in CONFIG_SCHEMA.items():
        if key not in config or not isinstance(config[key], typ):
            # Populate with empty or sensible default
            if typ is dict:
                config[key] = {}
            elif typ is list:
                config[key] = []
            changed = True
            logger.warning(f"Repaired missing or invalid config section: {key}")
    if changed:
        save_config(config, config_path)
    return config

def get_config_section(section: str, config_path: str = None) -> dict:
    config = load_config(config_path)
    return config.get(section, {})

