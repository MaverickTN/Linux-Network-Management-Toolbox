import json
import shutil
from pathlib import Path
import typer

DEFAULT_CONFIG_PATH = "/etc/inetctl/server_config.json"
BACKUP_SUFFIX = ".bak"
TITLE = "Linux Network Management Toolbox"  # Used for all pages and CLI

# Define minimum expected config structure for validation
CONFIG_SCHEMAS = {
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

def find_config_file():
    # Prioritize env, home, /etc, cwd
    paths = [
        Path(DEFAULT_CONFIG_PATH),
        Path.home() / ".inetctl" / "server_config.json",
        Path.cwd() / "server_config.json"
    ]
    for p in paths:
        if p.exists():
            return p
    return None

def load_config(config_path=None, validate=True, auto_repair=True):
    config_path = Path(config_path) if config_path else find_config_file()
    if not config_path or not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path or '[no default paths]'}")

    # Always backup before reading (in case of repair)
    try:
        backup_path = str(config_path) + BACKUP_SUFFIX
        shutil.copy2(config_path, backup_path)
    except Exception as e:
        typer.echo(f"Warning: Could not backup config: {e}")

    with open(config_path, "r") as f:
        try:
            config = json.load(f)
        except Exception as e:
            typer.echo(f"Error loading config: {e}", err=True)
            # Try to repair
            if auto_repair:
                if backup_path and Path(backup_path).exists():
                    typer.echo("Attempting to restore backup...", err=True)
                    shutil.copy2(backup_path, config_path)
                    with open(config_path, "r") as fb:
                        config = json.load(fb)
                else:
                    raise

    # Validate and optionally repair
    if validate:
        valid = validate_config(config)
        if not valid and auto_repair:
            typer.echo("Configuration invalid. Attempting repair...", err=True)
            config = repair_config(config, config_path)
            if not validate_config(config):
                typer.echo("Automatic repair failed. Exiting.", err=True)
                raise typer.Exit(1)
    return config

def save_config(config, config_path=None):
    config_path = Path(config_path) if config_path else find_config_file() or Path(DEFAULT_CONFIG_PATH)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    # After save, create backup
    try:
        shutil.copy2(config_path, str(config_path) + BACKUP_SUFFIX)
    except Exception as e:
        typer.echo(f"Warning: Could not backup config: {e}")

def validate_config(config):
    # Validate all top-level keys
    if not isinstance(config, dict):
        return False
    for k, typ in CONFIG_SCHEMAS.items():
        if k not in config or not isinstance(config[k], typ):
            return False
    # Check for required subkeys, e.g. ["wan_interface"] in global_settings
    if "wan_interface" not in config["global_settings"] or "lan_interface" not in config["global_settings"]:
        return False
    if "host" not in config["web_portal"] or "port" not in config["web_portal"]:
        return False
    # Add more as needed
    return True

def repair_config(config, config_path=None):
    """
    Attempt to add missing keys and fix obvious problems.
    """
    repaired = False
    # Patch all missing keys with reasonable defaults
    defaults = {
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
        "qos_policies": {},
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
    for key, default in defaults.items():
        if key not in config or not isinstance(config[key], type(default)):
            config[key] = default
            repaired = True

    # Validate hosts list
    if "known_hosts" in config:
        for h in config["known_hosts"]:
            if "mac" not in h:
                h["mac"] = ""
            if "ip" not in h:
                h["ip"] = ""
            if "schedules" not in h:
                h["schedules"] = []
    if repaired and config_path:
        save_config(config, config_path)
    return config

def migrate_config(config, version=None):
    """
    (Optional) Migrate older config to current schema.
    """
    # Example: check version key and upgrade if needed
    return config

def backup_config(config_path=None):
    config_path = Path(config_path) if config_path else find_config_file()
    if not config_path or not config_path.exists():
        typer.echo("No config file to backup.", err=True)
        return
    backup_path = str(config_path) + BACKUP_SUFFIX
    shutil.copy2(config_path, backup_path)
    typer.echo(f"Backup saved to {backup_path}")

def show_config(config_path=None):
    config = load_config(config_path)
    typer.echo(json.dumps(config, indent=2))

def get_title():
    return TITLE

# For CLI/menu
def menu_style_text(text, style="primary"):
    from inetctl.theme import THEMES
    theme = THEMES.get("dark")  # Choose current or user-selected
    cli = theme["cli"]
    return f"{cli[style]}{text}{cli['reset']}"

