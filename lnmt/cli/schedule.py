import typer
from lnmt.core.schedule import remove_expired_blocks
from lnmt.core.schedule import (
    list_host_schedules,
    add_schedule_block,
    remove_schedule_block,
    validate_schedule_block,
)
from lnmt.theme import cli_color

app = typer.Typer(name="schedule", help="Manage host network schedules")

@app.command("list")
def list_schedules(mac: str):
    """List schedule blocks for a given MAC address."""
    schedules = list_host_schedules(mac)
    if not schedules:
        print(cli_color(f"No schedules found for {mac}.", "warning"))
        return
    print(cli_color(f"Schedules for {mac}:", "primary"))
    for i, block in enumerate(schedules):
        print(cli_color(f"{i+1}. {block['start']} - {block['end']}", "info"))

@app.command("add")
def add_block(
    mac: str,
    start: str = typer.Argument(..., help="Start time (e.g., 22:00)"),
    end: str = typer.Argument(..., help="End time (e.g., 06:00)"),
):
    """Add a schedule block for a MAC."""
    valid, msg = validate_schedule_block(mac, start, end)
    if not valid:
        print(cli_color(f"Invalid: {msg}", "danger"))
        raise typer.Exit(1)
    add_schedule_block(mac, start, end)
    print(cli_color(f"Added schedule block: {start}-{end} for {mac}", "success"))

@app.command("remove")
def remove_block(
    mac: str,
    index: int = typer.Argument(..., help="Schedule block index to remove (see list)")
):
    """Remove a schedule block by index."""
    removed = remove_schedule_block(mac, index-1)
    if removed:
        print(cli_color(f"Removed block #{index} for {mac}", "success"))
    else:
        print(cli_color(f"Failed to remove block #{index} for {mac}", "danger"))

@app.command("purge-expired")
def purge_expired(mac: str = typer.Argument(..., help="MAC address to clean up expired schedule blocks")):
    """
    Remove expired schedule blocks for a specific MAC address.
    """
    remove_expired_blocks(mac)
    typer.echo(f"Expired schedule blocks removed for {mac}")
