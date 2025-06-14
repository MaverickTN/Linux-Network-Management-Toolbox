import typer
import json
from pathlib import Path

from inetctl.core.config_loader import (
    load_config,
    save_config,
    find_config_file,
    CONFIG_SEARCH_PATHS,
)

app = typer.Typer(
    name="config", 
    help="Manage the Linux Network Management Toolbox configuration file.", 
    no_args_is_help=True
)

# --- NEW: A Comprehensive Default Configuration ---
DEFAULT_CONFIG = {
    "global_settings": {
        "dnsmasq_leases_file": "/var/lib/misc/dnsmasq.leases",
        "accounting_interface": "br0", # Important for iptaccount
        "wan_network_id": "wan",
        "database_retention_days": 14,
        # Section for defining the main internet connection's speed
        "wan_bandwidth": {
            "upload_mbps": 20,
            "download_mbps": 250
        }
    },
    # The networks list will be auto-populated from Netplan by the app
    "networks": [],
    # known_hosts is for device-specific reservations and settings
    "known_hosts": [],
    # Placeholders for future feature integration
    "security": {
        "tls_cert_path": None,
        "tls_key_path": None
    },
    "web_portal": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False
    },
    # Comprehensive QoS policies
    "qos_policies": {
        "bulk": { "description": "Low Priority (Torrents, Backups)", "priority": 5, "fw_mark": 5, "guaranteed_mbit": 1, "limit_mbit": 100 },
        "normal": { "description": "Normal Priority (General Browsing)", "priority": 3, "fw_mark": 3, "guaranteed_mbit": 5, "limit_mbit": 200 },
        "priority": { "description": "High Priority (VoIP, Gaming)", "priority": 1, "fw_mark": 1, "guaranteed_mbit": 10, "limit_mbit": 250 }
    },
    # Placeholder for future Pi-hole integration
    "pihole": {
        "enabled": False,
        "host_ip": "192.168.1.2",
        "api_key": "PASTE_YOUR_PIHOLE_API_KEY_HERE"
    },
    # Placeholder for future WireGuard VPN server integration
    "wireguard": {
        "enabled": False,
        "server": {
            "interface_name": "wg0",
            "private_key": "PASTE_SERVER_PRIVATE_KEY",
            "address": "10.100.100.1/24",
            "listen_port": 51820
        },
        # This list will hold "remote hosts" (client peers)
        "peers": [
            {
                "name": "my_phone",
                "public_key": "PASTE_PHONE_PUBLIC_KEY",
                "allowed_ips": "10.100.100.2/32"
            },
            {
                "name": "my_laptop",
                "public_key": "PASTE_LAPTOP_PUBLIC_KEY",
                "allowed_ips": "10.100.100.3/32"
            }
        ]
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
    config_path = Path(CONFIG_SEARCH_PATHS[-1])
    
    if config_path.exists() and not force:
        typer.echo(f"Configuration file already exists at {config_path}")
        typer.echo("Use --force to overwrite.")
        raise typer.Exit(code=1)

    typer.echo("Initializing new Linux Network Management Toolbox configuration...")
    
    new_config = DEFAULT_CONFIG.copy()

    listen_ip = typer.prompt("Enter the IP for the web portal to listen on", default="0.0.0.0")
    listen_port = typer.prompt("Enter the port for the web portal", default=8080, type=int)
    
    new_config["web_portal"]["host"] = listen_ip
    new_config["web_portal"]["port"] = listen_port

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        save_config(new_config, config_path=config_path)
        typer.echo(
            typer.style(f"\nSuccessfully created comprehensive configuration at {config_path}", fg=typer.colors.GREEN)
        )
        typer.echo("Please review the new file to add your WireGuard keys and other site-specific details.")
        typer.echo(f"Web portal will listen on: http://{listen_ip}:{listen_port}")
    except Exception as e:
        typer.echo(f"Failed to create configuration file: {e}", err=True)
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