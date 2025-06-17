import typer
import json
from pathlib import Path
from inetctl.core.config_loader import (
    load_config,
    save_config,
    find_config_file,
    validate_config
)
app = typer.Typer(
    name="config",
    help="Manage the Linux Network Management Toolbox configuration file.",
    no_args_is_help=True
)

@app.command(name="init")
def init_config(
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite an existing config file."
    )
):
    """
    Creates a new server_config.json file interactively.
    """
    config_path = Path(find_config_file() or "/etc/inetctl/server_config.json")
    if config_path.exists() and not force:
        typer.echo(f"Configuration file already exists at {config_path}")
        typer.echo("Use --force to overwrite.")
        raise typer.Exit(code=1)
    config = {
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
    save_config(config, config_path)
    typer.echo(f"Created new configuration at {config_path}")

@app.command(name="validate")
def validate():
    config = load_config()
    if validate_config(config):
        typer.echo("Config is valid.")
    else:
        typer.echo("Config is INVALID.", err=True)

@app.command(name="show")
def show():
    config = load_config()
    typer.echo(json.dumps(config, indent=2))

@app.command(name="backup")
def backup():
    from shutil import copy2
    cfg = find_config_file()
    if not cfg:
        typer.echo("No config file found.", err=True)
        raise typer.Exit(1)
    backup_path = f"{cfg}.bak"
    copy2(cfg, backup_path)
    typer.echo(f"Backup saved to {backup_path}")

# (Add other subcommands as needed)
if __name__ == "__main__":
    app()
