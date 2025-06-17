import typer
from pathlib import Path
import json
from datetime import time

from inetctl.core.config_loader import (
    load_config, save_config, find_config_file, get_title
)
from inetctl.theme import THEMES

app = typer.Typer(
    name="schedule",
    help=f"Manage scheduled network access for hosts ({get_title()})."
)

def print_t(text, style="primary"):
    theme = THEMES["dark"]
    cli = theme["cli"]
    print(f"{cli.get(style, '')}{text}{cli['reset']}")

def parse_timeblock(block_str):
    """Parse a block in 'HH:MM-HH:MM' format."""
    try:
        start, end = block_str.split("-")
        sh, sm = map(int, start.strip().split(":"))
        eh, em = map(int, end.strip().split(":"))
        return (time(sh, sm), time(eh, em))
    except Exception:
        raise ValueError("Time block must be in format HH:MM-HH:MM")

def overlap(t1, t2):
    """Check if t1 and t2 (tuples of (start, end)) overlap."""
    return not (t1[1] <= t2[0] or t2[1] <= t1[0])

def timeblock_to_str(tblock):
    return f"{tblock[0].strftime('%H:%M')}-{tblock[1].strftime('%H:%M')}"

def get_host_by_mac(config, mac):
    return next((h for h in config.get("known_hosts", []) if h.get("mac") == mac), None)

@app.command()
def list(mac: str = typer.Option(None, help="MAC address (shows all if blank)")):
    """Show all schedule blocks for one or all hosts."""
    config = load_config()
    hosts = config["known_hosts"] if not mac else [get_host_by_mac(config, mac)]
    for host in hosts:
        if not host: continue
        print_t(f"{host.get('description', '(unnamed)')} [{host['mac']}]", "primary")
        for i, s in enumerate(host.get("schedules", [])):
            print_t(f"  {i+1}) {s['block']} ({s.get('desc','')})", "success")
        if not host.get("schedules"):
            print_t("  No schedules set.", "warning")

@app.command()
def add(mac: str, block: str = typer.Option(None, help="Time block HH:MM-HH:MM"),
        desc: str = typer.Option("", help="Optional description")):
    """Add a schedule block to a host. Prevents overlap."""
    config = load_config()
    host = get_host_by_mac(config, mac)
    if not host:
        print_t("No such host.", "danger")
        raise typer.Exit(1)

    if not block:
        block = typer.prompt("Time block (HH:MM-HH:MM)")
    try:
        new_block = parse_timeblock(block)
    except ValueError as e:
        print_t(str(e), "danger")
        raise typer.Exit(1)

    # Check overlap
    for sched in host.get("schedules", []):
        try:
            if overlap(new_block, parse_timeblock(sched["block"])):
                print_t(f"Overlaps with existing block: {sched['block']}", "danger")
                raise typer.Exit(1)
        except Exception:
            continue

    if "schedules" not in host:
        host["schedules"] = []
    host["schedules"].append({"block": block, "desc": desc})
    save_config(config)
    print_t(f"Added schedule {block} for {mac}.", "success")

@app.command()
def remove(mac: str):
    """Remove a schedule block from a host (pick interactively)."""
    config = load_config()
    host = get_host_by_mac(config, mac)
    if not host or not host.get("schedules"):
        print_t("No such host or no schedules.", "danger")
        raise typer.Exit(1)

    for i, s in enumerate(host["schedules"]):
        print_t(f"{i+1}) {s['block']} ({s.get('desc','')})", "primary")
    idx = typer.prompt("Which to remove?", type=int) - 1
    if 0 <= idx < len(host["schedules"]):
        b = host["schedules"].pop(idx)
        save_config(config)
        print_t(f"Removed schedule {b['block']}.", "success")
    else:
        print_t("Invalid index.", "danger")

@app.command()
def clear(mac: str):
    """Remove ALL schedule blocks from a host."""
    config = load_config()
    host = get_host_by_mac(config, mac)
    if not host or not host.get("schedules"):
        print_t("No such host or no schedules.", "danger")
        raise typer.Exit(1)
    host["schedules"] = []
    save_config(config)
    print_t(f"Cleared all schedules for {mac}.", "success")

@app.command()
def interactive():
    """Menu-driven scheduling management."""
    config = load_config()
    macs = [h["mac"] for h in config["known_hosts"]]
    for i, m in enumerate(macs, 1):
        print_t(f"{i}) {m}", "primary")
    idx = typer.prompt("Select host", type=int) - 1
    mac = macs[idx]
    while True:
        print_t(f"1) List 2) Add 3) Remove 4) Clear 5) Back", "info")
        choice = typer.prompt("Option", type=int)
        if choice == 1:
            list(mac)
        elif choice == 2:
            add(mac)
        elif choice == 3:
            remove(mac)
        elif choice == 4:
            clear(mac)
        elif choice == 5:
            break

if __name__ == "__main__":
    app()
