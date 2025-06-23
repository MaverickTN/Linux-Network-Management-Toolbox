import typer
import json
from lnmt.core.config_loader import load_config, save_config, validate_config, backup_config
from pathlib import Path

app = typer.Typer(
    name="schedule",
    help="Manage network schedule blocks per host (for blacklisting/offline periods)."
)

def find_host_by_mac(config, mac):
    for host in config.get("known_hosts", []):
        if host["mac"].lower() == mac.lower():
            return host
    return None

def time_range_overlap(a_start, a_end, b_start, b_end):
    """Return True if two time ranges (in HH:MM) overlap."""
    a_s = int(a_start.replace(':',''))
    a_e = int(a_end.replace(':',''))
    b_s = int(b_start.replace(':',''))
    b_e = int(b_end.replace(':',''))
    return (a_s < b_e and b_s < a_e)

@app.command("list")
def list_schedules(mac: str = typer.Argument(..., help="MAC address of host")):
    """List all schedule blocks for a host."""
    config = load_config()
    host = find_host_by_mac(config, mac)
    if not host or not host.get("schedule_blocks"):
        typer.echo("No schedule blocks found.")
        return
    for idx, block in enumerate(host["schedule_blocks"], 1):
        typer.echo(f"{idx}. {block['start']} - {block['end']}")

@app.command("add")
def add_schedule(
    mac: str = typer.Argument(..., help="MAC address of host"),
    start: str = typer.Option(..., help="Start time (HH:MM)"),
    end: str = typer.Option(..., help="End time (HH:MM)")
):
    """
    Add a schedule block for a host (times in 24h HH:MM format).
    Prevents overlap with existing blocks.
    """
    config = load_config()
    host = find_host_by_mac(config, mac)
    if not host:
        typer.secho(f"No host found for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)
    host.setdefault("schedule_blocks", [])
    for block in host["schedule_blocks"]:
        if time_range_overlap(start, end, block["start"], block["end"]):
            typer.secho(f"New block {start}-{end} overlaps with {block['start']}-{block['end']}", fg=typer.colors.RED)
            raise typer.Exit(1)
    host["schedule_blocks"].append({"start": start, "end": end})
    backup_config()
    save_config(config)
    typer.secho(f"Schedule block added for {mac}: {start}-{end}", fg=typer.colors.GREEN)
    validate_config()

@app.command("remove")
def remove_schedule(
    mac: str = typer.Argument(..., help="MAC address of host"),
    index: int = typer.Argument(..., help="Schedule block number (from 'list')")
):
    """Remove a schedule block by number."""
    config = load_config()
    host = find_host_by_mac(config, mac)
    if not host or not host.get("schedule_blocks"):
        typer.secho(f"No schedule blocks found for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)
    idx = index - 1
    if idx < 0 or idx >= len(host["schedule_blocks"]):
        typer.secho(f"Invalid index. Use 'list' to view schedule blocks.", fg=typer.colors.RED)
        raise typer.Exit(1)
    block = host["schedule_blocks"].pop(idx)
    backup_config()
    save_config(config)
    typer.secho(f"Removed schedule block: {block['start']}-{block['end']}", fg=typer.colors.GREEN)
    validate_config()

@app.command("edit")
def edit_schedule(
    mac: str = typer.Argument(..., help="MAC address of host"),
    index: int = typer.Argument(..., help="Schedule block number (from 'list')"),
    start: str = typer.Option(None, help="New start time (HH:MM)"),
    end: str = typer.Option(None, help="New end time (HH:MM)")
):
    """Edit a schedule block."""
    config = load_config()
    host = find_host_by_mac(config, mac)
    if not host or not host.get("schedule_blocks"):
        typer.secho(f"No schedule blocks found for {mac}", fg=typer.colors.RED)
        raise typer.Exit(1)
    idx = index - 1
    if idx < 0 or idx >= len(host["schedule_blocks"]):
        typer.secho(f"Invalid index. Use 'list' to view schedule blocks.", fg=typer.colors.RED)
        raise typer.Exit(1)
    block = host["schedule_blocks"][idx]
    old_start, old_end = block["start"], block["end"]
    # Check overlap
    new_start = start if start else block["start"]
    new_end = end if end else block["end"]
    for i, other in enumerate(host["schedule_blocks"]):
        if i == idx:
            continue
        if time_range_overlap(new_start, new_end, other["start"], other["end"]):
            typer.secho(f"Edit would overlap with block {other['start']}-{other['end']}", fg=typer.colors.RED)
            raise typer.Exit(1)
    block["start"] = new_start
    block["end"] = new_end
    backup_config()
    save_config(config)
    typer.secho(f"Schedule block updated: {old_start}-{old_end} → {new_start}-{new_end}", fg=typer.colors.GREEN)
    validate_config()

@app.command("interactive")
def interactive_schedule(mac: str = typer.Argument(..., help="MAC address of host")):
    """Interactively add a new schedule block."""
    start = typer.prompt("Start time (HH:MM)")
    end = typer.prompt("End time (HH:MM)")
    add_schedule(mac, start, end)
