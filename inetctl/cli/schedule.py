import typer
import getpass
import json
from pathlib import Path
from datetime import datetime, time

from inetctl.core.auth import require_group
from inetctl.theme import cli_color

SCHEDULE_FILE = Path("/etc/lnmt/schedules.json")

app = typer.Typer(
    name="schedule",
    help="Manage network access schedules for hosts (multi-block, overlap prevention).",
    no_args_is_help=True
)

def load_schedules():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_schedules(data):
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def parse_time(timestr):
    return datetime.strptime(timestr, "%H:%M").time()

def blocks_overlap(block1, block2):
    # block: {"start": "HH:MM", "end": "HH:MM"}
    start1, end1 = parse_time(block1["start"]), parse_time(block1["end"])
    start2, end2 = parse_time(block2["start"]), parse_time(block2["end"])
    return not (end1 <= start2 or end2 <= start1)

@app.command("list")
@require_group(["lnmtadm", "lnmt", "lnmtv"])
def list_schedules(
    host: str = typer.Option(None, help="Filter by host (optional)")
):
    data = load_schedules()
    if not data:
        typer.echo(cli_color("No schedules set.", "info"))
        return
    if host:
        blocks = data.get(host)
        if not blocks:
            typer.echo(cli_color(f"No schedule for {host}", "warning"))
            return
        typer.echo(cli_color(f"Schedule for {host}:", "primary"))
        for idx, block in enumerate(blocks):
            typer.echo(f"  Block {idx+1}: {block['start']}-{block['end']} ({block['days']})")
    else:
        for host, blocks in data.items():
            typer.echo(cli_color(f"Host: {host}", "primary"))
            for idx, block in enumerate(blocks):
                typer.echo(f"  Block {idx+1}: {block['start']}-{block['end']} ({block['days']})")

@app.command("add")
@require_group(["lnmtadm", "lnmt"])
def add_schedule(
    host: str = typer.Argument(..., help="Host to schedule"),
    start: str = typer.Argument(..., help="Start time (HH:MM, 24hr)"),
    end: str = typer.Argument(..., help="End time (HH:MM, 24hr)"),
    days: str = typer.Argument(..., help="Days (e.g. Mon,Tue,Wed)")
):
    data = load_schedules()
    block = {"start": start, "end": end, "days": days, "added_by": getpass.getuser(), "added_at": datetime.now().isoformat()}
    blocks = data.setdefault(host, [])
    for b in blocks:
        if set(days.split(',')) & set(b["days"].split(',')) and blocks_overlap(b, block):
            typer.echo(cli_color("Overlapping schedule detected!", "danger"))
            return
    blocks.append(block)
    save_schedules(data)
    typer.echo(cli_color("Schedule block added.", "success"))

@app.command("remove")
@require_group(["lnmtadm"])
def remove_block(
    host: str = typer.Argument(..., help="Host"),
    index: int = typer.Argument(..., help="Block index (1-based, see list)")
):
    data = load_schedules()
    if host not in data or not data[host]:
        typer.echo(cli_color(f"No schedule for {host}", "warning"))
        return
    try:
        removed = data[host].pop(index - 1)
        if not data[host]:
            del data[host]
        save_schedules(data)
        typer.echo(cli_color(f"Removed block: {removed['start']}-{removed['end']} ({removed['days']})", "success"))
    except IndexError:
        typer.echo(cli_color("Invalid block index.", "danger"))

@app.command("menu")
@require_group(["lnmtadm", "lnmt"])
def interactive_menu():
    while True:
        typer.echo(cli_color("\n--- Scheduling Menu ---", "primary"))
        typer.echo("1. List Schedules\n2. Add Schedule\n3. Remove Block\n4. Exit")
        choice = typer.prompt("Select an option")
        if choice == "1":
            host = typer.prompt("Host to view (leave blank for all)", default="")
            list_schedules(host if host else None)
        elif choice == "2":
            host = typer.prompt("Host")
            start = typer.prompt("Start time (HH:MM)")
            end = typer.prompt("End time (HH:MM)")
            days = typer.prompt("Days (comma-separated, e.g. Mon,Tue,Wed)")
            add_schedule(host, start, end, days)
        elif choice == "3":
            host = typer.prompt("Host")
            list_schedules(host)
            idx = typer.prompt("Block index to remove", type=int)
            remove_block(host, idx)
        elif choice == "4":
            break
        else:
            typer.echo(cli_color("Invalid choice.", "warning"))
