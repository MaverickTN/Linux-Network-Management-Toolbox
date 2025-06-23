# lnmt/core/config_loader.py

import json
from pathlib import Path
import shutil
import time

CONFIG_FILENAME = "lnmt_config.json"
CONFIG_DIR = Path.home() / ".lnmt"
CONFIG_PATH = CONFIG_DIR / CONFIG_FILENAME
CONFIG_BACKUP_PATH = CONFIG_DIR / f"{CONFIG_FILENAME}.bak"

DEFAULT_CONFIG = {
    "global_settings": {
        "wan_interface": "enp1s0",
        "lan_interface": "enp2s0",
        "database_retention_days": 14
    },
    "system_paths": {
        "dnsmasq_config_dir": "/etc/dnsmasq.d/",
        "dnsmasq_leases_file": "/var/lib/misc/dnsmasq.leases",
        "netplan_config_dir": "/etc/netplan/",
        "wireguard_config_dir": "/etc/wireguard/",
        "database_file": str(CONFIG_DIR / "lnmt.sqlite3")
    },
    "networks": [],
    "known_hosts": [],
    "security": {
        "tls_cert_path": None,
        "tls_key_path": None
    },
    "web_portal": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False
    },
    "qos_policies": {
        "bulk": {
            "description": "Low Priority (Torrents, Backups)",
            "priority": 5,
            "fw_mark": 5,
            "guaranteed_mbit": 1,
            "limit_mbit": 100
        },
        "normal": {
            "description": "Normal Priority (Browsing)",
            "priority": 3,
            "fw_mark": 3,
            "guaranteed_mbit": 5,
            "limit_mbit": 200
        },
        "priority": {
            "description": "High Priority (VoIP, Gaming)",
            "priority": 1,
            "fw_mark": 1,
            "guaranteed_mbit": 10,
            "limit_mbit": 250
        }
    },
    "pihole": {
        "enabled": False,
        "host": "",
        "api_key": ""
    },
    "wireguard": {
        "enabled": False,
        "config_dir": "/etc/wireguard/"
    }
}

def backup_config_file():
    if CONFIG_PATH.exists():
        shutil.copy(CONFIG_PATH, CONFIG_BACKUP_PATH)
        return True
    return False

def validate_config(config):
    # Check for critical top-level sections
    for key in DEFAULT_CONFIG:
        if key not in config:
            raise ValueError(f"Missing required config section: {key}")
    # Add further validation logic as needed
    return True

def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r") as f:
        try:
            config = json.load(f)
            validate_config(config)
            return config
        except Exception as e:
            # Attempt to auto-restore from backup if possible
            if CONFIG_BACKUP_PATH.exists():
                shutil.copy(CONFIG_BACKUP_PATH, CONFIG_PATH)
                with open(CONFIG_PATH, "r") as f2:
                    config = json.load(f2)
                validate_config(config)
                return config
            else:
                raise RuntimeError(f"Config file is invalid and no backup exists: {e}")

def save_config(config, config_path=CONFIG_PATH):
    backup_config_file()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return True

def find_config_file():
    # Always return main config path for now
    return str(CONFIG_PATH)
