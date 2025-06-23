# lnmt/cli/config.py

import typer
import json
from pathlib import Path

from lnmt.core.config_loader import (
    load_config,
    save_config,
    find_config_file,
    validate_config,
    backup_config
)

app = typer.Typer(
    name="config",
    help="Manage the Linux Network Management Toolbox configuration file.",
    no_args_is_help=True
)

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

@app.command(name="init")
def init_config(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite an existing config file."
    )
):
    """
    Creates a new, comprehensive server_config.json file interactively.
    """
    config_path = Path(find_config_file(default_new=True))

    if config_path.exists() and not force:
        typer.echo(f"Configuration file already exists at {config_path}")
        typer.echo("Use --force to overwrite.")
        raise typer.Exit(code=1)

    typer.echo("--- Initializing New LNMT Configuration ---")

    new_config = DEFAULT_CONFIG.copy()

    # --- Interactive Prompts for all key settings ---
    new_config["web_portal"]["host"] = typer.prompt(
        "Enter Web Portal IP to listen on",
        default="0.0.0.0"
    )
    new_config["web_portal"]["port"] = typer.prompt(
        "Enter Web Portal Port",
        default=8080,
        type=int
    )

    new_config["global_settings"]["wan_interface"] = typer.prompt(
        "Enter your primary WAN interface",
        default="enp1s0"
    )
    new_config["global_settings"]["lan_interface"] = typer.prompt(
        "Enter your primary LAN (or bridge) interface",
        default="enp2s0"
    )

    typer.echo("\n--- Path Configuration ---")
    new_config["system_paths"]["dnsmasq_leases_file"] = typer.prompt(
        "Path to dnsmasq.leases file",
        default="/var/lib/misc/dnsmasq.leases"
    )
    new_config["system_paths"]["netplan_config_dir"] = typer.prompt(
        "Path to netplan config directory",
        default="/etc/netplan/"
    )

    wg_dir = typer.prompt(
        "Path to WireGuard config directory",
        default="/etc/wireguard/"
    )
    new_config["system_paths"]["wireguard_config_dir"] = wg_dir
    new_config["wireguard"]["config_dir"] = wg_dir

    typer.echo("\n--- Pi-hole Integration (Optional) ---")
    if typer.confirm("Do you want to configure Pi-hole integration?"):
        new_config["pihole"]["enabled"] = True
        new_config["pihole"]["host"] = typer.prompt("Enter Pi-hole IP address")
        new_config["pihole"]["api_key"] = typer.prompt("Enter Pi-hole API Key", hide_input=True)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        backup_config(config_path)
        save_config(new_config, config_path=config_path)
        if validate_config(new_config):
            typer.echo(
                typer.style(f"\nSuccessfully created configuration at {config_path}", fg=typer.colors.GREEN)
            )
            typer.echo("Please review the generated file for any other site-specific adjustments.")
        else:
            typer.echo("Config was created, but failed validation. Please check.")
    except Exception as e:
        typer.echo(f"Failed to create configuration file: {e}", err=True)
        raise typer.Exit(code=1)

@app.command(name="validate")
def validate():
    """
    Validate current configuration file.
    """
    config = load_config()
    if validate_config(config):
        typer.echo("Config is valid.")
    else:
        typer.echo("Config is invalid or corrupted!", err=True)
        raise typer.Exit(code=1)

@app.command(name="path")
def show_config_path():
    """
    Shows the path to the currently used configuration file.
    """
    path = find_config_file()
    if path:
        typer.echo(path)
    else:
        typer.echo("No configuration file found.", err=True)
        raise typer.Exit(code=1)

@app.command(name="get")
def get_config_value(
    key: str = typer.Argument(..., help="The top-level key to retrieve (e.g., 'global_settings').")
):
    """
    Prints a specific top-level section of the config as JSON.
    """
    config = load_config()
    value = config.get(key)

    if value is not None:
        typer.echo(json.dumps(value, indent=2))
    else:
        typer.echo(f"Key '{key}' not found in configuration.", err=True)
        raise typer.Exit(code=1)
