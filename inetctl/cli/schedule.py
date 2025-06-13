import typer
import getpass
from datetime import datetime
from typing import Optional

from inetctl.core.config_loader import load_config, save_config, find_config_file
from inetctl.core.utils import run_command, get_host_by_mac, get_active_leases
from inetctl.core.logger import log_event

app = typer.Typer(
    name="schedule",
    help="Manage and apply time-based access control schedules.",
    no_args_is_help=True
)

VALID_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def is_time_in_range(start_str: str, end_str: str, check_time: datetime.time) -> bool:
    """Checks if a time is within a given range, handling overnight periods."""
    try:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
    except (ValueError, TypeError):
        return False

    if start_time <= end_time:
        # Same-day range (e.g., 09:00 - 17:00)
        return start_time <= check_time < end_time
    else:
        # Overnight range (e.g., 21:00 - 07:00)
        return check_time >= start_time or check_time < end_time

@app.command()
def apply():
    """Checks all host schedules against current time and applies firewall changes."""
    log_event("INFO", "schedule:apply", "Cron job starting schedule check.", username='SYSTEM')
    config_path = find_config_file()
    if not config_path:
        log_event("ERROR", "schedule:apply", "Configuration file not found.", username='SYSTEM')
        raise typer.Exit(code=1)

    config = load_config(config_path)
    config_changed = False
    now = datetime.now()
    current_day_str = list(VALID_DAYS.keys())[now.weekday()]
    current_time = now.time()

    for host in config.get("known_hosts", []):
        schedule = host.get("schedule")
        if not (schedule and schedule.get("enabled") and current_day_str in schedule.get("days", [])):
            continue

        is_in_period = is_time_in_range(schedule.get("start_time"), schedule.get("end_time"), current_time)
        block_during = schedule.get("block_during_schedule", True)
        should_be_blocked = (is_in_period and block_during) or (not is_in_period and not block_during)

        if host.get("network_access_blocked") != should_be_blocked:
            hostname = host.get("hostname", host.get("mac"))
            log_event("INFO", "schedule:apply", f"State change for '{hostname}': setting network_access_blocked to {should_be_blocked}.", username='SYSTEM')
            host["network_access_blocked"] = should_be_blocked
            config_changed = True

    if config_changed:
        log_event("INFO", "schedule:apply", "Configuration updated, invoking firewall sync.", username='SYSTEM')
        save_config(config, config_path)
        sync_result = run_command(["./inetctl-runner.py", "shorewall", "sync"])
        if sync_result["returncode"] != 0:
            log_event("ERROR", "schedule:apply", f"Firewall sync failed: {sync_result['stderr']}", username='SYSTEM')
    else:
        log_event("INFO", "schedule:apply", "No schedule-based changes required.", username='SYSTEM')

@app.command(name="set")
def set_schedule(
    mac: str = typer.Argument(..., help="MAC address of host. Can be from a new device with an active lease."),
    start_time: Optional[str] = typer.Option(None, "--start", help="Schedule start time (HH:MM)."),
    end_time: Optional[str] = typer.Option(None, "--end", help="Schedule end time (HH:MM)."),
    days: Optional[str] = typer.Option(None, "--days", help="Comma-separated days (mon,tue,wed,thu,fri,sat,sun)."),
    block_during: bool = typer.Option(True, "--block-during/--allow-during", help="Block during the schedule vs. allow only during the schedule."),
    enable: bool = typer.Option(None, "--enable/--disable", help="Enable or disable the schedule."),
    remove: bool = typer.Option(False, "--remove", help="Remove the schedule from the host entirely."),
):
    """Create, update, or remove an access schedule for a host from the CLI."""
    cli_user = getpass.getuser()
    config = load_config()
    mac_lower = mac.lower()
    host, _ = get_host_by_mac(config, mac_lower)

    if not host:
        leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file")
        if not leases_file:
            typer.echo("Error: dnsmasq_leases_file not defined in config global_settings.", err=True)
            raise typer.BadParameter("dnsmasq_leases_file not defined in config")

        active_lease = next((l for l in get_active_leases(leases_file) if l['mac'] == mac_lower), None)
        if not active_lease:
            raise typer.BadParameter(f"Host {mac_lower} not found in config file or in active leases.")

        networks = config.get("networks", [])
        lan_net = next((n for n in networks if n.get("purpose") == "lan"), None)
        host = {
            "mac": mac_lower, "hostname": active_lease['hostname'],
            "description": f"Auto-added by {cli_user} on {datetime.now().strftime('%Y-%m-%d')}",
            "vlan_id": lan_net['id'] if lan_net else (networks[0]['id'] if networks else None),
            "ip_assignment": {"type": "dhcp"}, "network_access_blocked": False
        }
        config.setdefault("known_hosts", []).append(host)
        config["known_hosts"] = sorted(config["known_hosts"], key=lambda h: h.get('hostname', 'z').lower())
        log_event("INFO", "cli:schedule:set", f"Host '{active_lease['hostname']}' not found, auto-creating from active lease.", username=cli_user)

    hostname_for_log = host.get("hostname", mac_lower)

    if remove:
        if "schedule" in host:
            del host["schedule"]
            log_event("INFO", "cli:schedule:set", f"Removed schedule from '{hostname_for_log}'.", username=cli_user)
            typer.echo(f"Successfully removed schedule for host {mac_lower}.")
        else:
            typer.echo(f"No schedule found for host {mac_lower}. Nothing to remove.")
    else:
        schedule = host.setdefault("schedule", {"enabled": True, "block_during_schedule": True, "days": []})
        
        updated_fields = []
        if start_time is not None:
            schedule["start_time"] = start_time
            updated_fields.append(f"start_time to {start_time}")
        if end_time is not None:
            schedule["end_time"] = end_time
            updated_fields.append(f"end_time to {end_time}")
        if days is not None:
            schedule["days"] = sorted(list(set(d.strip().lower() for d in days.split(',') if d.strip())), key=lambda d: VALID_DAYS[d])
            updated_fields.append(f"days to {','.join(schedule['days'])}")
        if block_during is not None:
            schedule["block_during_schedule"] = block_during
            updated_fields.append(f"mode to {'block' if block_during else 'allow'}")
        if enable is not None:
            schedule["enabled"] = enable
            updated_fields.append(f"status to {'enabled' if enable else 'disabled'}")
        
        if updated_fields:
            log_msg = f"Schedule updated for '{hostname_for_log}': set {', '.join(updated_fields)}."
            log_event("INFO", "cli:schedule:set", log_msg, username=cli_user)
        
        typer.echo(typer.style(f"Successfully updated schedule for host {mac_lower}.", fg=typer.colors.GREEN))
        
    save_config(config)