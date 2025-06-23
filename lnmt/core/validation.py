# lnmt/core/validation.py

import json
from pathlib import Path

REQUIRED_KEYS = {
    "global_settings": dict,
    "system_paths": dict,
    "networks": list,
    "known_hosts": list,
    "security": dict,
    "web_portal": dict,
    "qos_policies": dict,
    "pihole": dict,
    "wireguard": dict
}

def validate_config(config):
    """Checks config dict for required keys and value types."""
    errors = []
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in config:
            errors.append(f"Missing required section: {key}")
        elif not isinstance(config[key], expected_type):
            errors.append(f"Section {key} must be of type {expected_type.__name__}")
    # Add more specific validation logic here as needed.
    return errors

def validate_config_file(config_path: Path):
    """Validate config file at given path, returns list of errors (empty = OK)."""
    try:
        with open(config_path) as f:
            config = json.load(f)
        return validate_config(config)
    except Exception as e:
        return [f"Failed to load config: {e}"]
