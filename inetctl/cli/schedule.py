import typer
from rich import print as rprint
from rich.table import Table
from inetctl.core.config_loader import load_config, save_config
from inetctl.core.logging import log_event
from inetctl.core.user import require_cli_group

cli = typer.Typer(name="schedule", help="Manage scheduled network access for hosts.")

def find_host(mac):
    config = load_config()
    for host in config.get("known_hosts", []):
        if host.get("mac") == mac:
            return host, config
    return None, config

def overlaps(blocks, start, end, skip_idx=None):
    s = int(start[:2])*60 + int(start[3:])
    e = int(end[:2])*60 + int(end[3:])
    for idx, blk in enumerate(blocks):
        if skip_idx is not None and idx == skip_idx:
            continue
        bs = int(blk["start"][:2])*60 + int(blk["start"][3:])
        be = int(blk["end"][:2])*60 + int(blk["end"][3:])
        if not (e <= bs or s >= be):
            return True
    return False

@cli.command("list")
@require_cli_group(["lnmtadm", "lnmt", "lnmtv"])
def list_blocks(mac: str):
    """List all schedule blocks for a host."""
    host, _ = find_host(mac)
    if not host:
        rprint("[red]Host not found.[/red]")
        raise typer.Exit(1)
    table = Table("Index", "Start", "End")
    for idx, blk in enumerate(host.get("schedules", [])):
        table.add_row(str(idx), blk["start"], blk["end"])
    rprint(table)

@cli.command("add")
@require_cli_group(["lnmtadm", "lnmt"])
def add_block(mac: str, start: str = typer.Argument(..., help="Start time (HH:MM)"), end: str = typer.Argument(..., help="End time (HH:MM)")):
    """Add a schedule block to a host."""
    host, config = find_host(mac)
    if not host:
        rprint("[red]Host not found.[/red]")
        raise typer.Exit(1)
    blocks = host.setdefault("schedules", [])
    if start >= end:
        rprint("[red]Start must be before end.[/red]")
        raise typer.Exit(1)
    if overlaps(blocks, start, end):
        rprint("[yellow]Block overlaps with an existing entry.[/yellow]")
        raise typer.Exit(1)
    blocks.append({"start": start, "end": end})
    save_config(config)
    log_event("cli", f"Added schedule {start}-{end} to {mac}")
    rprint("[green]Block added successfully.[/green]")

@cli.command("edit")
@require_cli_group(["lnmtadm", "lnmt"])
def edit_block(mac: str, idx: int, start: str = typer.Option(None), end: str = typer.Option(None)):
    """Edit an existing schedule block by index."""
    host, config = find_host(mac)
    if not host:
        rprint("[red]Host not found.[/red]")
        raise typer.Exit(1)
    blocks = host.setdefault("schedules", [])
    if not (0 <= idx < len(blocks)):
        rprint("[red]Invalid block index.[/red]")
        raise typer.Exit(1)
    old = blocks[idx]
    s = start or old["start"]
    e = end or old["end"]
    if s >= e:
        rprint("[red]Start must be before end.[/red]")
        raise typer.Exit(1)
    if overlaps(blocks, s, e, skip_idx=idx):
        rprint("[yellow]Block overlaps with an existing entry.[/yellow]")
        raise typer.Exit(1)
    blocks[idx] = {"start": s, "end": e}
    save_config(config)
    log_event("cli", f"Edited schedule {old['start']}-{old['end']} -> {s}-{e} for {mac}")
    rprint("[green]Block updated successfully.[/green]")

@cli.command("remove")
@require_cli_group(["lnmtadm", "lnmt"])
def remove_block(mac: str, idx: int):
    """Remove a schedule block by index."""
    host, config = find_host(mac)
    if not host:
        rprint("[red]Host not found.[/red]")
        raise typer.Exit(1)
    blocks = host.setdefault("schedules", [])
    if not (0 <= idx < len(blocks)):
        rprint("[red]Invalid block index.[/red]")
        raise typer.Exit(1)
    removed = blocks.pop(idx)
    save_config(config)
    log_event("cli", f"Removed schedule {removed['start']}-{removed['end']} from {mac}")
    rprint("[green]Block removed successfully.[/green]")
