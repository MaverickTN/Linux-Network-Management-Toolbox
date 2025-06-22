import json
import shutil
from pathlib import Path

CONFIG_PATH = Path("/etc/inetctl/server_config.json")
USER_PROFILES_PATH = Path("/etc/inetctl/user_profiles.json")

def backup_file(path):
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(str(path), str(backup))

def validate_json_file(path, required_keys=None):
    if not path.exists():
        return False, f"File {path} does not exist."
    try:
        with path.open("r") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"JSON parse error: {e}"
    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"Missing required keys: {missing}"
    return True, "OK"

def auto_repair_config(path, default_config):
    # Make a backup
    backup_file(path)
    # Attempt to repair (replace with default)
    with path.open("w") as f:
        json.dump(default_config, f, indent=2)

def validate_all():
    errors = []
    # Validate main config
    ok, msg = validate_json_file(CONFIG_PATH, ["global_settings", "system_paths", "networks"])
    if not ok:
        errors.append(f"Config: {msg}")
    # Validate user profiles
    ok, msg = validate_json_file(USER_PROFILES_PATH)
    if not ok:
        errors.append(f"User Profiles: {msg}")
    return errors

def run_validation_and_repair(default_config):
    errors = validate_all()
    repaired = []
    if errors:
        # Auto repair if possible
        if "Config:" in errors[0]:
            auto_repair_config(CONFIG_PATH, default_config)
            repaired.append("Config")
        # User profiles auto-repair (optional: clear if corrupted)
        if any("User Profiles:" in e for e in errors):
            backup_file(USER_PROFILES_PATH)
            with USER_PROFILES_PATH.open("w") as f:
                json.dump({}, f)
            repaired.append("User Profiles")
    return repaired, errors
