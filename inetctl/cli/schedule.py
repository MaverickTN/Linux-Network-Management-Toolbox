import typer
from typing import List
from inetctl.core import schedule

app = typer.Typer(
    name="schedule",
    help="Manage host blacklist/online schedules (multi-block per host, non-overlapping).",
    no_args_is_help=True
)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

@app.command("list")
def list_schedules(mac: str = typer.Argument(None, help="MAC address of the host (optional, lists all if omitted)")):
    """
    List all scheduled blacklist/online blocks for a host, or all hosts.
    """
    data = schedule.list_schedules(mac)
    if mac:
        if not data:
            typer.echo(f"No schedules found for {mac}")
            raise typer.Exit()
        typer.echo(f"Schedules for {mac}:")
        for i, block in enumerate(data):
            typer.echo(f"  [{i}] {schedule.describe_block(block)}")
    else:
        for mac, blocks in data.items():
            typer.echo(f"{mac}:")
            for i, block in enumerate(blocks):
                typer.echo(f"  [{i}] {schedule.describe_block(block)}")
    raise typer.Exit()

@app.command("add")
def add_block(
    mac: str = typer.Argument(..., help="MAC address"),
    start: str = typer.Option(None, "--start", "-s", help="Block start time, HH:MM"),
    end: str = typer.Option(None, "--end", "-e", help="Block end time, HH:MM"),
    days: List[str] = typer.Option([], "--day", "-d", help="Day(s) of week, e.g. --day Mon --day Tue"),
    comment: str = typer.Option("", "--comment", "-c", help="Comment or label for this block"),
):
    """
    Add a schedule block for a host.
    """
    # Interactive if not provided
    if not start:
        start = typer.prompt("Start time (HH:MM)")
    if not end:
        end = typer.prompt("End time (HH:MM)")
    if not days:
        typer.echo("Select days (comma-separated, e.g. Mon,Tue,Wed or 'all'):")
        s = typer.prompt("Days")
        if s.strip().lower() == "all":
            days = DAYS
        else:
            days = [d.strip().capitalize()[:3] for d in s.split(",")]
    block = schedule.add_schedule(mac, start, end, days, comment)
    typer.secho(f"Added: {schedule.describe_block(block)}", fg=typer.colors.GREEN)

@app.command("remove")
def remove_block(
    mac: str = typer.Argument(..., help="MAC address"),
    idx: int = typer.Argument(None, help="Index of block to remove (from 'list')")
):
    """
    Remove a schedule block by index.
    """
    if idx is None:
        # List blocks and prompt
        blocks = schedule.list_schedules(mac)
        if not blocks:
            typer.echo("No blocks for this host.")
            raise typer.Exit()
        for i, block in enumerate(blocks):
            typer.echo(f"[{i}] {schedule.describe_block(block)}")
        idx = typer.prompt("Index to remove", type=int)
    removed = schedule.remove_schedule(mac, idx)
    typer.secho(f"Removed: {schedule.describe_block(removed)}", fg=typer.colors.RED)

@app.command("update")
def update_block(
    mac: str = typer.Argument(..., help="MAC address"),
    idx: int = typer.Argument(..., help="Index of block to update (from 'list')"),
    start: str = typer.Option(None, "--start", "-s", help="New start time"),
    end: str = typer.Option(None, "--end", "-e", help="New end time"),
    days: List[str] = typer.Option(None, "--day", "-d", help="Day(s) of week, e.g. --day Fri"),
    comment: str = typer.Option(None, "--comment", "-c", help="New comment"),
):
    """
    Update a schedule block by index.
    """
    old, new = schedule.update_schedule(mac, idx, start, end, days, comment)
    typer.secho(f"Updated block [{idx}]:", fg=typer.colors.GREEN)
    typer.echo(f"Old: {schedule.describe_block(old)}")
    typer.echo(f"New: {schedule.describe_block(new)}")

@app.command("menu")
def interactive_menu():
    """
    Menu-driven scheduling for hosts.
    """
    while True:
        typer.echo("\n--- Host Schedule Menu ---")
        typer.echo("1) List all schedules")
        typer.echo("2) Add block")
        typer.echo("3) Remove block")
        typer.echo("4) Update block")
        typer.echo("0) Exit")
        choice = typer.prompt("Select", type=int)
        if choice == 0:
            raise typer.Exit()
        elif choice == 1:
            mac = typer.prompt("MAC address (blank for all)", default="")
            list_schedules(mac or None)
        elif choice == 2:
            mac = typer.prompt("MAC address")
            add_block(mac)
        elif choice == 3:
            mac = typer.prompt("MAC address")
            remove_block(mac)
        elif choice == 4:
            mac = typer.prompt("MAC address")
            idx = typer.prompt("Block index", type=int)
            update_block(mac, idx)
        else:
            typer.echo("Invalid.")

if __name__ == "__main__":
    app()
