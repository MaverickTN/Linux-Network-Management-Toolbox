import typer
import json
from pathlib import Path
import shutil
from datetime import datetime

from lnmt.core.config_loader import (
    load_config,
    save_config,
    find_config_file,
    validate_config,
    auto_repair_config,
    backup_config,
    DEFAULT_CONFIG
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
    Creates a new configuration file interactively, with validation and backup.
    """
    config_path = Path(find_config_file(create=True))

    if config_path.exists() and not force:
        typer.echo(f"Configuration file already exists at {config_path}")
        typer.echo("Use --force to overwrite.")
        raise typer.Exit(code=1)

    typer.echo("--- Initializing New Toolbox Configuration ---")

    # Copy the default and prompt for key values
    new_config = DEFAULT_CONFIG.copy()

    new_config["web_portal"]["host"] = typer.prompt("Enter Web Portal IP to listen on", default="0.0.0.0")
    new_config["web_portal"]["port"] = typer.prompt("Enter Web Portal Port", default=8080, type=int)
    new_config["global_settings"]["wan_interface"] = typer.prompt("Enter your primary WAN interface", default="enp1s0")
    new_config["global_settings"]["lan_interface"] = typer.prompt("Enter your primary LAN (or bridge) interface", default="enp2s0")

    typer.echo("\n--- Path Configuration ---")
    new_config["system_paths"]["dnsmasq_leases_file"] = typer.prompt("Path to dnsmasq.leases file", default="/var/lib/misc/dnsmasq.leases")
    new_config["system_paths"]["netplan_config_dir"] = typer.prompt("Path to netplan config directory", default="/etc/netplan/")
    wg_dir = typer.prompt("Path to WireGuard config directory", default="/etc/wireguard/")
    new_config["system_paths"]["wireguard_config_dir"] = wg_dir
    new_config["wireguard"]["config_dir"] = wg_dir

    typer.echo("\n--- Pi-hole Integration (Optional) ---")
    if typer.confirm("Do you want to configure Pi-hole integration?"):
        new_config["pihole"]["enabled"] = True
        new_config["pihole"]["host"] = typer.prompt("Enter Pi-hole IP address")
        new_config["pihole"]["api_key"] = typer.prompt("Enter Pi-hole API Key", hide_input=True)

    # Backup if existing and not force
    if config_path.exists():
        backup_config(config_path)
        typer.echo(f"Existing config backed up to {config_path}.bak")

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        save_config(new_config, config_path=config_path)
        typer.secho(f"\nSuccessfully created configuration at {config_path}", fg=typer.colors.GREEN)
        typer.echo("Please review the generated file for any other site-specific adjustments.")
    except Exception as e:
        typer.secho(f"Failed to create configuration file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app.command(name="validate")
def validate():
    """
    Validate the current configuration file and report any problems.
    """
    config_path = find_config_file()
    if not config_path:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    config = load_config()
    valid, errors = validate_config(config)
    if valid:
        typer.secho("Configuration is valid! 🚀", fg=typer.colors.GREEN)
    else:
        typer.secho("Configuration has problems:", fg=typer.colors.RED)
        for error in errors:
            typer.echo(f"  - {error}")

@app.command(name="repair")
def repair():
    """
    Attempt to automatically repair configuration file issues.
    """
    config_path = find_config_file()
    if not config_path:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    config = load_config()
    repaired, message = auto_repair_config(config)
    if repaired:
        save_config(repaired, config_path=config_path)
        typer.secho("Config repaired and saved.", fg=typer.colors.GREEN)
    else:
        typer.secho("Unable to repair config: " + message, fg=typer.colors.RED)

@app.command(name="backup")
def backup():
    """
    Create a backup of the current configuration file.
    """
    config_path = find_config_file()
    if not config_path:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    path = backup_config(config_path)
    typer.secho(f"Backup created: {path}", fg=typer.colors.GREEN)

@app.command(name="path")
def show_config_path():
    """
    Shows the path to the currently used configuration file.
    """
    path = find_config_file()
    if path:
        typer.echo(path)
    else:
        typer.secho("No configuration file found.", fg=typer.colors.RED)
        raise typer.Exit(1)

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
        typer.secho(f"Key '{key}' not found in configuration.", fg=typer.colors.RED)
        raise typer.Exit(1)

# Extra: Export config, or any other utility CLI actions as needed.

