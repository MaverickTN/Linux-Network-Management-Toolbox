import typer
from rich import print as rprint
from rich.table import Table
from rich.prompt import Prompt
from datetime import time
from lnmt.core.config_loader import load_config, save_config
from lnmt.core.logging import log_event
from lnmt.core.user import require_cli_group

cli = typer.Typer(
    name="reservations",
    help="Manage DHCP/static IP reservations."
)

def validate_unique(reservations, mac, ip, exclude_idx=None):
    """Check that MAC and IP are not used in another reservation."""
    for idx, r in enumerate(reservations):
        if exclude_idx is not None and idx == exclude_idx:
            continue
        if r["mac"] == mac or r["ip"] == ip:
            return False
    return True

@cli.command("list")
@require_cli_group(["lnmtadm", "lnmt", "lnmtv"])
def list_reservations():
    """List all DHCP/static reservations."""
    config = load_config()
    reservations = config.get("reservations", [])
    table = Table("Index", "MAC", "IP", "Hostname", "Comment")
    for idx, r in enumerate(reservations, 1):
        table.add_row(
            str(idx),
            r.get("mac", ""),
            r.get("ip", ""),
            r.get("hostname", ""),
            r.get("comment", "")
        )
    rprint(table)

@cli.command("add")
@require_cli_group(["lnmtadm", "lnmt"])
def add_reservation(
    mac: str = typer.Argument(..., help="MAC address (format: aa:bb:cc:dd:ee:ff)"),
    ip: str = typer.Argument(..., help="IP address"),
    hostname: str = typer.Option("", "--hostname", "-h", help="Optional hostname"),
    comment: str = typer.Option("", "--comment", "-c", help="Optional comment"),
):
    """Add a DHCP/static reservation (MAC and IP must be unique)."""
    config = load_config()
    reservations = config.setdefault("reservations", [])
    entry = {"mac": mac, "ip": ip, "hostname": hostname, "comment": comment}
    if not validate_unique(reservations, mac, ip):
        rprint("[red]Error: This MAC or IP is already reserved.[/red]")
        raise typer.Exit(1)
    reservations.append(entry)
    save_config(config)
    log_event("cli", f"Added reservation: {entry}")
    rprint(f"[green]Reservation added for MAC {mac} → IP {ip}[/green]")

@cli.command("remove")
@require_cli_group(["lnmtadm"])
def remove_reservation(
    index: int = typer.Argument(..., help="Reservation index (see 'list', starting from 1)")
):
    """Remove a reservation by index."""
    config = load_config()
    reservations = config.get("reservations", [])
    if index < 1 or index > len(reservations):
        rprint("[red]Invalid index.[/red]")
        raise typer.Exit(1)
    removed = reservations.pop(index - 1)
    save_config(config)
    log_event("cli", f"Removed reservation: {removed}")
    rprint(f"[green]Removed reservation for MAC {removed['mac']}[/green]")

@cli.command("menu")
@require_cli_group(["lnmtadm", "lnmt", "lnmtv"])
def menu_mode():
    """Interactive, menu-driven reservation management."""
    while True:
        rprint("\n[reservations] Choose action: [1] List  [2] Add  [3] Remove  [4] Exit")
        act = Prompt.ask("Select", choices=["1", "2", "3", "4"], default="1")
        if act == "1":
            list_reservations()
        elif act == "2":
            mac = Prompt.ask("MAC address")
            ip = Prompt.ask("IP address")
            hostname = Prompt.ask("Hostname (optional)", default="")
            comment = Prompt.ask("Comment (optional)", default="")
            try:
                add_reservation(mac, ip, hostname, comment)
            except SystemExit:
                pass
        elif act == "3":
            list_reservations()
            idx = int(Prompt.ask("Reservation index to remove", default="1"))
            try:
                remove_reservation(idx)
            except SystemExit:
                pass
        else:
            rprint("[blue]Goodbye![/blue]")
            break
