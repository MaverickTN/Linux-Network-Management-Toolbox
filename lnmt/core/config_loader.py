import os
import json
import shutil
from pathlib import Path
import datetime

CONFIG_DIR = Path("/etc/lnmt")
CONFIG_FILE = CONFIG_DIR / "server_config.json"
CONFIG_BACKUP_DIR = CONFIG_DIR / "backups"
CONFIG_SEARCH_PATHS = [
    CONFIG_FILE,
    Path("/usr/local/etc/lnmt/server_config.json"),
    Path("./server_config.json")
]

def find_config_file():
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return path
    return None

def backup_config(config_path=CONFIG_FILE):
    CONFIG_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = CONFIG_BACKUP_DIR / f"server_config_{ts}.json"
        shutil.copy2(config_path, backup_path)
        return backup_path
    return None

def validate_config(config):
    required_keys = ["global_settings", "system_paths", "networks", "known_hosts",
                     "security", "web_portal", "qos_policies", "pihole", "wireguard"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    # Add more structure/content checks as needed
    return True

def attempt_repair(config_path):
    try:
        # Try to read with errors, attempt to salvage if possible (naive JSON fix)
        with open(config_path, "r") as f:
            raw = f.read()
        # Remove trailing commas (naive, but sometimes helps)
        raw = raw.replace(",\n}", "\n}").replace(",\n]", "\n]")
        config = json.loads(raw)
        validate_config(config)
        save_config(config, config_path=config_path, backup=False)
        return config
    except Exception as e:
        raise RuntimeError(f"Unable to auto-repair config: {e}")

def load_config():
    path = find_config_file()
    if not path:
        raise FileNotFoundError("No config file found in expected locations.")
    try:
        with open(path, "r") as f:
            config = json.load(f)
        validate_config(config)
        return config
    except Exception as e:
        print(f"Config load failed: {e}")
        print("Attempting auto-repair...")
        config = attempt_repair(path)
        print("Auto-repair succeeded.")
        return config

def save_config(config, config_path=CONFIG_FILE, backup=True):
    if backup and config_path.exists():
        backup_config(config_path)
    validate_config(config)
    os.makedirs(config_path.parent, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def list_backups():
    if not CONFIG_BACKUP_DIR.exists():
        return []
    return sorted(CONFIG_BACKUP_DIR.glob("server_config_*.json"), reverse=True)
