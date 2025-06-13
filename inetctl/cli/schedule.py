import typer
import json
from datetime import datetime
from typing import Optional

from inetctl.core.config_loader import load_config, save_config, find_config_file
from inetctl.core.utils import run_command, get_host_by_mac, get_active_leases
from inetctl.core.logger import log_event

app = typer.Typer(name="schedule", help="Manage time-based access control schedules.", no_args_is_help=True)
VALID_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

def is_time_in_range(start_str: str, end_str: str, check_time: datetime.time) -> bool:
    try:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
    except ValueError: return False
    return (start_time <= check_time < end_time) if start_time <= end_time else (check_time >= start_time or check_time < end_time)

@app.command()
def apply():
    """Checks all host schedules against current time and applies firewall changes."""
    log_event("INFO", "schedule:apply", "Cron job starting schedule check.")
    config_path = find_config_file()
    if not config_path: log_event("ERROR", "schedule:apply", "Config file not found."); raise typer.Exit(1)
    
    config = load_config(config_path)
    config_changed = False
    now = datetime.now()
    current_day_str = list(VALID_DAYS.keys())[now.weekday()]
    current_time = now.time()

    for host in config.get("known_hosts", []):
        schedule = host.get("schedule")
        if not schedule or not schedule.get("enabled"): continue

        if current_day_str not in schedule.get("days", []): continue
        
        is_in_period = is_time_in_range(schedule.get("start_time"), schedule.get("end_time"), current_time)
        block_during = schedule.get("block_during_schedule", True)
        should_be_blocked = (is_in_period and block_during) or (not is_in_period and not block_during)

        if host.get("network_access_blocked") != should_be_blocked:
            hostname = host.get("hostname", host.get("mac"))
            log_event("INFO", "schedule:apply", f"State change for '{hostname}': setting network_access_blocked to {should_be_blocked}.")
            host["network_access_blocked"] = should_be_blocked
            config_changed = True

    if config_changed:
        log_event("INFO", "schedule:apply", "Configuration updated, invoking firewall sync.")
        save_config(config, config_path)
        sync_result = run_command(["./inetctl-runner.py", "shorewall", "sync"])
        if sync_result["returncode"] != 0:
            log_event("ERROR", "schedule:apply", f"Firewall sync failed: {sync_result['stderr']}")
    else:
        log_event("INFO", "schedule:apply", "No schedule-based changes required.")

@app.command(name="set")
def set_schedule(
    mac: str = typer.Argument(..., help="MAC address of host."),
    start_time: Optional[str] = typer.Option(None, "--start"),
    end_time: Optional[str] = typer.Option(None, "--end"),
    days: Optional[str] = typer.Option(None, "--days"),
    block_during: bool = typer.Option(True, "--block-during/--allow-during"),
    enable: bool = typer.Option(None, "--enable/--disable"),
    remove: bool = typer.Option(False, "--remove"),
):
    """Create, update, or remove an access schedule for a host."""
    config = load_config()
    mac_lower, host = mac.lower(), get_host_by_mac(config, mac.lower())[0]

    if not host:
        leases_file = config.get("gs", {}).get("dnsmasq_leases_file")
        active_lease = next((l for l in get_active_leases(leases_file) if l['mac'] == mac_lower), None)
        if not active_lease: raise typer.BadParameter(f"Host {mac_lower} not found in config or active leases.")
        
        networks, lan_net = config.get("networks", []), next((n for n in config.get("networks",[]) if n.get("purpose") == "lan"), None)
        host = {
            "mac": mac_lower, "hostname": active_lease['hostname'],
            "description": f"Auto-added on {datetime.now().strftime('%Y-%m-%d')}",
            "vlan_id": lan_net['id'] if lan_net else (networks[0]['id'] if networks else None),
            "ip_assignment": {"type": "dhcp"}, "network_access_blocked": False
        }
        config.setdefault("known_hosts", []).append(host)
        config["known_hosts"] = sorted(config["known_hosts"], key=lambda h: h.get('hostname', 'z').lower())
        log_event("INFO", "schedule:set", f"Host '{active_lease['hostname']}' not found, auto-creating from active lease.")

    if remove:
        if "schedule" in host: del host["schedule"]
        log_event("INFO", "schedule:set", f"Removed schedule from {host.get('hostname')}.")
    else:
        schedule = host.setdefault("schedule", {"enabled": True, "block_during_schedule": True, "days": []})
        if start_time: schedule["start_time"] = start_time
        if end_time: schedule["end_time"] = end_time
        if days: schedule["days"] = sorted(list(set(d.strip().lower() for d in days.split(',') if d.strip())), key=lambda d: VALID_DAYS[d])
        schedule["block_during_schedule"] = block_during
        if enable is not None: schedule["enabled"] = enable
        log_event("INFO", "schedule:set", f"Schedule updated for {host.get('hostname')}.")

    save_config(config)
    typer.echo(f"Successfully updated schedule for host {mac_lower}.")