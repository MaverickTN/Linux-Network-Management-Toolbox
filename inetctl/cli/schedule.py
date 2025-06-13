import typer
import json
import subprocess
from datetime import datetime
from typing import List, Optional

from inetctl.core.config_loader import load_config, save_config, find_config_file
from inetctl.core.utils import run_command, get_host_by_mac  # <-- THIS LINE IS CORRECTED

app = typer.Typer(
    name="schedule",
    help="Manage and apply time-based access control schedules.",
    no_args_is_help=True
)

# Day mapping for validation and conversion
VALID_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def is_time_in_range(start_str: str, end_str: str, check_time: datetime.time) -> bool:
    """Checks if a time is within a given range, handling overnight periods."""
    try:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
    except ValueError:
        return False # Invalid time format in config

    if start_time <= end_time:
        # Same-day range (e.g., 09:00 - 17:00)
        return start_time <= check_time < end_time
    else:
        # Overnight range (e.g., 21:00 - 07:00)
        return check_time >= start_time or check_time < end_time

@app.command()
def apply():
    """
    Checks all host schedules against the current time and applies firewall changes.
    This is intended to be run by a cron job every minute.
    """
    config_path = find_config_file()
    if not config_path:
        typer.echo("Error: Configuration file not found.", err=True)
        raise typer.Exit(code=1)

    config = load_config(config_path)
    known_hosts = config.get("known_hosts", [])
    config_changed = False

    now = datetime.now()
    current_day_str = list(VALID_DAYS.keys())[now.weekday()]
    current_time = now.time()

    typer.echo(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Running schedule check...")

    for host in known_hosts:
        schedule = host.get("schedule")
        if not schedule or not schedule.get("enabled"):
            continue

        host_mac = host.get('mac')
        schedule_days = schedule.get("days", [])
        if current_day_str not in schedule_days:
            continue

        start_time = schedule.get("start_time")
        end_time = schedule.get("end_time")
        block_during = schedule.get("block_during_schedule", True)

        if not all([host_mac, start_time, end_time]):
            typer.echo(f"Warning: Incomplete schedule for {host_mac}. Skipping.", err=True)
            continue
            
        is_in_scheduled_period = is_time_in_range(start_time, end_time, current_time)

        # Determine if the host should be blocked based on the schedule logic
        should_be_blocked = (is_in_scheduled_period and block_during) or \
                            (not is_in_scheduled_period and not block_during)

        # If the desired state is different from the current state, update it
        if host.get("network_access_blocked") != should_be_blocked:
            typer.echo(
                f"  - State change for {host.get('hostname', host_mac)}: "
                f"Setting network_access_blocked to {should_be_blocked}"
            )
            host["network_access_blocked"] = should_be_blocked
            config_changed = True

    if config_changed:
        typer.echo("Configuration updated. Saving and syncing firewall.")
        save_config(config, config_path)
        # Call the robust shorewall sync command to apply the changes
        sync_result = run_command(["./inetctl-runner.py", "shorewall", "sync"])
        if sync_result["returncode"] == 0:
            typer.echo(typer.style("Firewall sync successful.", fg=typer.colors.GREEN))
        else:
            typer.echo(typer.style(f"Firewall sync failed:\n{sync_result['stderr']}", fg=typer.colors.RED), err=True)
    else:
        typer.echo("No schedule-based changes required.")

@app.command(name="set")
def set_schedule(
    mac: str = typer.Argument(..., help="The MAC address of the host."),
    start_time: Optional[str] = typer.Option(None, "--start", help="Schedule start time (HH:MM)."),
    end_time: Optional[str] = typer.Option(None, "--end", help="Schedule end time (HH:MM)."),
    days: Optional[str] = typer.Option(None, "--days", help="Comma-separated days (mon,tue,wed,thu,fri,sat,sun)."),
    block_during: bool = typer.Option(True, "--block-during/--allow-during", help="Block during the schedule vs. allow only during the schedule."),
    enable: bool = typer.Option(None, "--enable/--disable", help="Enable or disable the schedule."),
    remove: bool = typer.Option(False, "--remove", help="Remove the schedule from the host entirely."),
):
    """
    Create, update, or remove an access schedule for a host.
    """
    config = load_config()
    host, _ = get_host_by_mac(config, mac)
    if not host:
        typer.echo(f"Error: Host with MAC address {mac} not found.", err=True)
        raise typer.Exit(code=1)

    if remove:
        if "schedule" in host:
            del host["schedule"]
            save_config(config)
            typer.echo(f"Successfully removed schedule for host {mac}.")
        else:
            typer.echo(f"No schedule found for host {mac}. Nothing to remove.")
        raise typer.Exit()

    # Get or create the schedule object
    if "schedule" not in host:
        host["schedule"] = {
            "enabled": True,
            "block_during_schedule": True,
            "start_time": "00:00",
            "end_time": "00:00",
            "days": []
        }
    
    schedule = host["schedule"]

    if start_time is not None:
        try:
            datetime.strptime(start_time, "%H:%M")
            schedule["start_time"] = start_time
        except ValueError:
            typer.echo("Error: Invalid start_time format. Use HH:MM.", err=True)
            raise typer.Exit(code=1)

    if end_time is not None:
        try:
            datetime.strptime(end_time, "%H:%M")
            schedule["end_time"] = end_time
        except ValueError:
            typer.echo("Error: Invalid end_time format. Use HH:MM.", err=True)
            raise typer.Exit(code=1)

    if days is not None:
        day_list = [d.strip().lower() for d in days.split(',')]
        if not all(d in VALID_DAYS for d in day_list):
            typer.echo(f"Error: Invalid day specified. Use comma-separated values from: {', '.join(VALID_DAYS.keys())}", err=True)
            raise typer.Exit(code=1)
        schedule["days"] = sorted(list(set(day_list)), key=lambda d: VALID_DAYS[d])

    # This handles the bool flag correctly
    schedule["block_during_schedule"] = block_during

    if enable is not None:
        schedule["enabled"] = enable

    save_config(config)
    typer.echo(typer.style(f"Successfully updated schedule for host {mac}.", fg=typer.colors.GREEN))
    typer.echo(json.dumps(schedule, indent=2))