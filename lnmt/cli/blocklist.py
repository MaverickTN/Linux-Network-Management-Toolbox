import typer
import getpass
import json
from pathlib import Path
from datetime import datetime

from lnmt.core.auth import require_group
from lnmt.theme import cli_color

BLOCKLIST_FILE = Path("/etc/lnmt/blocklist.json")

app = typer.Typer(
    name="blocklist",
    help="Manage blocklisted hosts (deny network access by host/IP/MAC).",
    no_args_is_help=True
)

def load_blocklist():
    if BLOCKLIST_FILE.exists():
        with open(BLOCKLIST_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_blocklist(data):
    BLOCKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOCKLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.command("list")
@require_group(["lnmtadm", "lnmt"])
def list_blocked():
    data = load_blocklist()
    if not data:
        typer.echo(cli_color("No blocklisted entries.", "info"))
        return
    typer.echo(cli_color("Blocklist:", "danger"))
    for entry, info in data.items():
        typer.echo(f"- {entry}: {info['reason']} (by {info.get('added_by', 'unknown')})")

@app.command("add")
@require_group(["lnmtadm"])
def add_block(
    entry: str = typer.Argument(..., help="Host/IP/MAC to block"),
    reason: str = typer.Option("policy", help="Reason for block")
):
    data = load_blocklist()
    if entry in data:
        typer.echo(cli_color("Entry already blocklisted.", "warning"))
        return
    data[entry] = {
        "reason": reason,
        "added_by": getpass.getuser(),
        "added_at": datetime.now().isoformat()
    }
    save_blocklist(data)
    typer.echo(cli_color("Blocklist entry added.", "success"))

@app.command("remove")
@require_group(["lnmtadm"])
def remove_block(
    entry: str = typer.Argument(..., help="Host/IP/MAC to unblock")
):
    data = load_blocklist()
    if entry not in data:
        typer.echo(cli_color("Not blocklisted.", "warning"))
        return
    data.pop(entry)
    save_blocklist(data)
    typer.echo(cli_color(f"Entry {entry} removed from blocklist.", "success"))

@app.command("menu")
@require_group(["lnmtadm", "lnmt"])
def interactive_menu():
    while True:
        typer.echo(cli_color("\n--- Blocklist Menu ---", "primary"))
        typer.echo("1. List Blocked\n2. Add Block\n3. Remove Block\n4. Exit")
        choice = typer.prompt("Select an option")
        if choice == "1":
            list_blocked()
        elif choice == "2":
            entry = typer.prompt("Host/IP/MAC to block")
            reason = typer.prompt("Reason for block", default="policy")
            add_block(entry, reason)
        elif choice == "3":
            entry = typer.prompt("Host/IP/MAC to unblock")
            remove_block(entry)
        elif choice == "4":
            break
        else:
            typer.echo(cli_color("Invalid choice.", "warning"))
