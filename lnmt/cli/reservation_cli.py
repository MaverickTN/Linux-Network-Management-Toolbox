import typer
import json
from inetctl.core.config_loader import load_config, save_config, validate_config, backup_config
from pathlib import Path
import datetime

app = typer.Typer(
    name="reservation",
    help="Manage static DHCP reservations."
)

CONFIG_PATH = None  # Use default logic in load_config

def find_host_by_mac(config, mac):
    for host in config.get("known_hosts", []):
        if host["mac"].lower() == mac.lower():
            return host
    return None

@app.command("list")
def list_reservations():
    """List all DHCP reservations."""
    config = load_config()
    hosts = config.get("known_hosts", [])
    if not hosts:
        typer.echo("No DHCP reservations found.")
        return
    for idx, host in enumerate(hosts, 1):
        typer.echo(f"{idx}. {host.get('hostname', '(unknown)')} | MAC: {host['mac']} | IP: {host.get('ip', '(dynamic)')}")

@app.command("add")
def add_reservation(
    mac: str = typer.Argument(..., help="MAC address"),
    ip: str = typer.Option(None, help="Reserved IP address"),
    hostname: str = typer.Option(None, help="Optional hostname/description")
):
    """Add a new DHCP reservation."""
    config = load_config()
    if find_host_by_mac(config, mac):
        typer.secho(f"Reservation already exists for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)

    host = {
        "mac": mac,
        "ip": ip if ip else "",
        "hostname": hostname if hostname else ""
    }
    config.setdefault("known_hosts", []).append(host)
    backup_config()
    save_config(config)
    typer.secho(f"Reservation for {mac} added.", fg=typer.colors.GREEN)
    validate_config()

@app.command("remove")
def remove_reservation(mac: str = typer.Argument(..., help="MAC address")):
    """Remove a DHCP reservation."""
    config = load_config()
    hosts = config.get("known_hosts", [])
    new_hosts = [h for h in hosts if h["mac"].lower() != mac.lower()]
    if len(new_hosts) == len(hosts):
        typer.secho(f"No reservation found for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)
    config["known_hosts"] = new_hosts
    backup_config()
    save_config(config)
    typer.secho(f"Reservation for {mac} removed.", fg=typer.colors.GREEN)
    validate_config()

@app.command("edit")
def edit_reservation(
    mac: str = typer.Argument(..., help="MAC address"),
    ip: str = typer.Option(None, help="New IP address"),
    hostname: str = typer.Option(None, help="New hostname/description")
):
    """Edit a DHCP reservation."""
    config = load_config()
    host = find_host_by_mac(config, mac)
    if not host:
        typer.secho(f"No reservation found for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)
    if ip is not None:
        host["ip"] = ip
    if hostname is not None:
        host["hostname"] = hostname
    backup_config()
    save_config(config)
    typer.secho(f"Reservation for {mac} updated.", fg=typer.colors.GREEN)
    validate_config()

@app.command("interactive")
def interactive_add():
    """Add a new reservation interactively."""
    mac = typer.prompt("MAC address")
    ip = typer.prompt("Reserved IP address", default="")
    hostname = typer.prompt("Hostname/description", default="")
    add_reservation(mac, ip if ip else None, hostname if hostname else None)

