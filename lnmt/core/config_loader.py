import os
import json
import shutil
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "lnmt" / "server_config.json"
CONFIG_BACKUP_PATH = Path.home() / ".config" / "lnmt" / "server_config.backup.json"

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
        "wireguard_config_dir": "/etc/wireguard/"
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


def get_config_path():
    return DEFAULT_CONFIG_PATH


def backup_config():
    if DEFAULT_CONFIG_PATH.exists():
        shutil.copy(DEFAULT_CONFIG_PATH, CONFIG_BACKUP_PATH)
        return True
    return False


def validate_config(config):
    # Basic validation (can be expanded)
    required_keys = ["global_settings", "system_paths", "networks", "web_portal"]
    for key in required_keys:
        if key not in config:
            return False, f"Missing key: {key}"
    return True, ""


def load_config(auto_repair=True):
    path = get_config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG, config_path=path)
        return DEFAULT_CONFIG

    try:
        with open(path, "r") as f:
            config = json.load(f)
        valid, msg = validate_config(config)
        if not valid:
            raise ValueError(f"Invalid config: {msg}")
        return config
    except Exception as e:
        if auto_repair:
            print(f"Config load error: {e}, attempting to restore from backup.")
            if CONFIG_BACKUP_PATH.exists():
                shutil.copy(CONFIG_BACKUP_PATH, path)
                with open(path, "r") as f:
                    return json.load(f)
            else:
                save_config(DEFAULT_CONFIG, config_path=path)
                return DEFAULT_CONFIG
        else:
            raise


def save_config(config, config_path=None):
    if config_path is None:
        config_path = get_config_path()
    # Backup before writing
    backup_config()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def find_config_file():
    return str(get_config_path()) if get_config_path().exists() else None
