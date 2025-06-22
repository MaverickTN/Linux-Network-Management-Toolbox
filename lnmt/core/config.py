import typer
import json
from pathlib import Path
import sys
from inetctl.core.config_loader import (
    load_config,
    save_config,
    find_config_file,
    repair_config,
    backup_config,
    validate_config,
    get_title,
)
from inetctl.theme import THEMES, list_theme_names

app = typer.Typer(
    name="config",
    help=f"Manage the {get_title()} configuration file.",
    no_args_is_help=False
)

DEFAULT_CONFIG_PATH = "/etc/inetctl/server_config.json"

def print_t(text, style="primary"):
    theme = THEMES["dark"]  # Could swap for user setting
    cli = theme["cli"]
    print(f"{cli.get(style, '')}{text}{cli['reset']}")

@app.command()
def menu():
    """Interactive, menu-driven config management."""
    while True:
        print_t(f"\n{get_title()} - Config Menu", "primary")
        print_t("1) Initialize/Reset config file", "info")
        print_t("2) Show config file", "success")
        print_t("3) Validate config", "info")
        print_t("4) Repair config", "warning")
        print_t("5) Backup config", "success")
        print_t("6) Set theme", "info")
        print_t("7) Exit", "danger")
        choice = input("Choose option: ").strip()
        if choice == "1":
            init_config(force=True)
        elif choice == "2":
            show_config()
        elif choice == "3":
            validate_config_cmd()
        elif choice == "4":
            repair_config_cmd()
        elif choice == "5":
            backup_config()
        elif choice == "6":
            theme_select()
        elif choice == "7":
            sys.exit(0)
        else:
            print_t("Invalid option.", "danger")

@app.command()
def init_config(force: bool = typer.Option(False, "--force", "-f", help="Overwrite config if exists.")):
    """
    Create or reset config interactively.
    """
    config_path = Path(DEFAULT_CONFIG_PATH)
    if config_path.exists() and not force:
        print_t("Config exists. Use --force to overwrite.", "warning")
        raise typer.Exit(1)

    print_t("Initializing configuration...", "info")
    # Collect minimal interactive info (or load defaults)
    config = {
        "global_settings": {
            "wan_interface": typer.prompt("WAN interface", default="enp1s0"),
            "lan_interface": typer.prompt("LAN interface", default="enp2s0"),
            "database_retention_days": typer.prompt("DB retention days", default=14, type=int)
        },
        "system_paths": {
            "dnsmasq_config_dir": typer.prompt("dnsmasq config dir", default="/etc/dnsmasq.d/"),
            "dnsmasq_leases_file": typer.prompt("dnsmasq leases file", default="/var/lib/misc/dnsmasq.leases"),
            "netplan_config_dir": typer.prompt("Netplan config dir", default="/etc/netplan/"),
            "wireguard_config_dir": typer.prompt("WireGuard config dir", default="/etc/wireguard/")
        },
        "networks": [],
        "known_hosts": [],
        "security": {
            "tls_cert_path": None,
            "tls_key_path": None
        },
        "web_portal": {
            "host": typer.prompt("Web portal bind host", default="0.0.0.0"),
            "port": typer.prompt("Web portal port", default=8080, type=int),
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
    save_config(config, config_path)
    print_t(f"Config initialized at {config_path}", "success")

@app.command()
def show_config():
    """Print the entire config file."""
    config = load_config()
    print(json.dumps(config, indent=2))

@app.command()
def get_config_value(key: str):
    """Get a top-level config value."""
    config = load_config()
    val = config.get(key)
    if val is None:
        print_t(f"No such key '{key}'", "danger")
        raise typer.Exit(1)
    print(json.dumps(val, indent=2))

@app.command()
def set_config_value(key: str, value: str):
    """Set a top-level config value (JSON required for dicts/lists)."""
    config = load_config()
    try:
        if value.startswith("{") or value.startswith("["):
            value = json.loads(value)
        config[key] = value
        save_config(config)
        print_t(f"Set '{key}' updated.", "success")
    except Exception as e:
        print_t(f"Failed to set '{key}': {e}", "danger")

@app.command()
def validate_config_cmd():
    """Validate config structure."""
    config = load_config(validate=False)
    if validate_config(config):
        print_t("Config is valid.", "success")
    else:
        print_t("Config is INVALID!", "danger")

@app.command()
def repair_config_cmd():
    """Attempt to repair the config file."""
    config_path = find_config_file()
    config = load_config(validate=False)
    config = repair_config(config, config_path)
    save_config(config, config_path)
    print_t("Config repaired and saved.", "success")

@app.command()
def backup():
    """Create a backup of the config file."""
    backup_config()
    print_t("Backup created.", "success")

@app.command()
def reset_config():
    """Delete config file (after confirmation)."""
    config_path = find_config_file()
    if not config_path:
        print_t("No config found.", "warning")
        return
    if typer.confirm(f"Delete {config_path}?"):
        config_path.unlink()
        print_t("Deleted.", "danger")

@app.command()
def theme_select():
    """Pick a CLI/web theme."""
    themes = list_theme_names()
    print_t("Available Themes:", "info")
    for i, (k, name) in enumerate(themes.items(), 1):
        print_t(f"{i}) {name} ({k})", "primary")
    idx = int(input("Pick a theme number: ").strip()) - 1
    theme = list(themes.keys())[idx]
    # Persist selection in config or .inetctlrc if needed
    print_t(f"Selected theme: {themes[theme]}", "success")

@app.command()
def path():
    """Show config file path."""
    path = find_config_file()
    print(path if path else "No config found.")

# CLI entrypoint
if __name__ == "__main__":
    if len(sys.argv) == 1:
        menu()
    else:
        app()
