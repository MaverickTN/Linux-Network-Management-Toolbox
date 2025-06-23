import typer
from datetime import time
from typing import List
from lnmt.theme import cli_color, APP_TITLE
from lnmt.core.config_loader import load_config, save_config

app = typer.Typer(help=cli_color("Manage scheduled blocks for hosts", "primary"))

def validate_time_range(start: str, end: str) -> bool:
    """Ensure start < end and proper HH:MM format"""
    try:
        s = time.fromisoformat(start)
        e = time.fromisoformat(end)
        return s < e
    except Exception:
        return False

@app.command("add")
def add_schedule(mac: str = typer.Argument(...),
                 start: str = typer.Argument(...),
                 end: str = typer.Argument(...)):
    """Add a scheduled block for host. Format: HH:MM (24h)"""
    if not validate_time_range(start, end):
        typer.echo(cli_color("Invalid time range! Format: HH:MM and start < end.", "danger"))
        raise typer.Exit(1)
    config = load_config()
    for host in config.get("known_hosts", []):
        if host.get("mac") == mac:
            blocks = host.setdefault("schedule_blocks", [])
            # Check overlap
            for block in blocks:
                if not (end <= block["start"] or start >= block["end"]):
                    typer.echo(cli_color("Block overlaps with existing schedule!", "danger"))
                    raise typer.Exit(1)
            blocks.append({"start": start, "end": end})
            save_config(config)
            typer.echo(cli_color("Schedule block added!", "success"))
            return
    typer.echo(cli_color("Host not found.", "danger"))

@app.command("menu")
def schedule_menu():
    """Menu-driven scheduling CLI"""
    typer.echo(cli_color("Schedule Management Menu", "primary"))
    mac = typer.prompt(cli_color("Enter MAC address", "info"))
    start = typer.prompt(cli_color("Start time (HH:MM)", "info"))
    end = typer.prompt(cli_color("End time (HH:MM)", "info"))
    add_schedule(mac, start, end)
