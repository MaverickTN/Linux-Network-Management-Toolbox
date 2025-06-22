import typer
import getpass
import json
from pathlib import Path
from datetime import datetime

from inetctl.core.config_loader import load_config, save_config, validate_config
from inetctl.core.auth import require_group
from inetctl.theme import cli_color

app = typer.Typer(
    name="reservation",
    help="Manage static IP/DHCP reservations for hosts.",
    no_args_is_help=True
)

RESERVATION_FILE = Path("/etc/lnmt/reservations.json")

def load_reservations():
    if RESERVATION_FILE.exists():
        with open(RESERVATION_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_reservations(data):
    RESERVATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESERVATION_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.command("list")
@require_group(["lnmtadm", "lnmt"])
def list_reservations():
    data = load_reservations()
    if not data:
        typer.echo(cli_color("No reservations set.", "info"))
        return
    typer.echo(cli_color("Reservations:", "primary"))
    for host, info in data.items():
        typer.echo(f"- {host}: {info['ip']} ({info.get('mac','')})")

@app.command("add")
@require_group(["lnmtadm"])
def add_reservation(
    host: str = typer.Argument(..., help="Host identifier (e.g. name)"),
    ip: str = typer.Argument(..., help="IP address to reserve"),
    mac: str = typer.Option("", help="MAC address (optional)")
):
    data = load_reservations()
    if host in data:
        typer.echo(cli_color("Reservation for host already exists.", "warning"))
        return
    data[host] = {
        "ip": ip,
        "mac": mac,
        "added_by": getpass.getuser(),
        "added_at": datetime.now().isoformat()
    }
    save_reservations(data)
    typer.echo(cli_color("Reservation added.", "success"))

@app.command("remove")
@require_group(["lnmtadm"])
def remove_reservation(
    host: str = typer.Argument(..., help="Host to remove reservation for")
):
    data = load_reservations()
    if host not in data:
        typer.echo(cli_color("Reservation not found.", "danger"))
        return
    data.pop(host)
    save_reservations(data)
    typer.echo(cli_color(f"Reservation for {host} removed.", "success"))

@app.command("menu")
@require_group(["lnmtadm", "lnmt"])
def interactive_menu():
    while True:
        typer.echo(cli_color("\n--- Reservations Menu ---", "primary"))
        typer.echo("1. List Reservations\n2. Add Reservation\n3. Remove Reservation\n4. Exit")
        choice = typer.prompt("Select an option")
        if choice == "1":
            list_reservations()
        elif choice == "2":
            host = typer.prompt("Host")
            ip = typer.prompt("IP address")
            mac = typer.prompt("MAC address", default="")
            add_reservation(host, ip, mac)
        elif choice == "3":
            host = typer.prompt("Host")
            remove_reservation(host)
        elif choice == "4":
            break
        else:
            typer.echo(cli_color("Invalid choice.", "warning"))
