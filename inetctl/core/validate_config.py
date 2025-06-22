import json
import shutil
from pathlib import Path

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

BACKUP_SUFFIX = ".bak"

def backup_config_file(config_path):
    backup_path = config_path.with_suffix(config_path.suffix + BACKUP_SUFFIX)
    shutil.copy2(config_path, backup_path)
    return backup_path

def validate_config(config, auto_repair=False):
    errors = []
    # Check top-level keys and types
    for key, expected_type in CONFIG_SCHEMA.items():
        if key not in config:
            errors.append(f"Missing required key: {key}")
            if auto_repair:
                if expected_type is dict:
                    config[key] = {}
                elif expected_type is list:
                    config[key] = []
        elif not isinstance(config[key], expected_type):
            errors.append(f"Invalid type for '{key}': expected {expected_type.__name__}, got {type(config[key]).__name__}")
            if auto_repair:
                if expected_type is dict:
                    config[key] = {}
                elif expected_type is list:
                    config[key] = []
    # Optionally, add more granular schema checks here
    return errors

def load_and_validate_config(config_path, auto_repair=True, make_backup=True):
    config_path = Path(config_path)
    with open(config_path, "r") as f:
        try:
            config = json.load(f)
        except Exception as e:
            raise ValueError(f"Configuration file is not valid JSON: {e}")

    errors = validate_config(config, auto_repair=auto_repair)

    if errors:
        if make_backup:
            backup_config_file(config_path)
        if auto_repair:
            # Save repaired config
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        return config, errors
    return config, []

def validate_config_file(config_path, auto_repair=False):
    config, errors = load_and_validate_config(config_path, auto_repair=auto_repair)
    return errors

def is_config_valid(config_path):
    _, errors = load_and_validate_config(config_path, auto_repair=False)
    return len(errors) == 0
