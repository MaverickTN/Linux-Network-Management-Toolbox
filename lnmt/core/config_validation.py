import json
import shutil
from pathlib import Path
from typing import Tuple

REQUIRED_TOP_LEVEL_KEYS = [
    "global_settings", "system_paths", "networks", "known_hosts",
    "security", "web_portal", "qos_policies", "pihole", "wireguard"
]

DEFAULT_CONFIG_PATH = "/etc/lnmt/server_config.json"
BACKUP_PATH = "/etc/lnmt/server_config.json.bak"

def backup_config(config_path=DEFAULT_CONFIG_PATH):
    """Create a backup of the config file."""
    if Path(config_path).exists():
        shutil.copy2(config_path, BACKUP_PATH)

def validate_config_file(config_path=DEFAULT_CONFIG_PATH) -> Tuple[bool, str]:
    """Validate top-level structure, required keys, and JSON format."""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in config:
                return False, f"Missing required key: {key}"
        # Add additional nested checks here as desired
        return True, "Valid configuration"
    except Exception as e:
        return False, f"Validation failed: {e}"

def auto_repair_config(config_path=DEFAULT_CONFIG_PATH):
    """
    Attempt to restore from backup if corruption detected.
    Returns True if repaired, False otherwise.
    """
    backup = Path(BACKUP_PATH)
    if backup.exists():
        shutil.copy2(BACKUP_PATH, config_path)
        return True
    return False

def validate_and_repair_config(config_path=DEFAULT_CONFIG_PATH):
    """Validate, backup, and auto-repair if needed."""
    valid, msg = validate_config_file(config_path)
    if valid:
        backup_config(config_path)
        return True, msg
    # Attempt auto-repair
    repaired = auto_repair_config(config_path)
    if repaired:
        return True, "Auto-repaired configuration from backup."
    return False, msg
