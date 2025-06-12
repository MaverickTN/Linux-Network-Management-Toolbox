import typer
from typing import List, Dict, Any

from inetctl.core.config_loader import load_config
from inetctl.core.shorewall import (ACCOUNTING_MANAGED_BLOCK_END,
                                    ACCOUNTING_MANAGED_BLOCK_START,
                                    generate_accounting_config,
                                    write_shorewall_file,
                                    get_currently_blocked_ips)
from inetctl.core.utils import (check_root_privileges, get_active_leases,
                                run_command)

app = typer.Typer(name="shorewall", help="Synchronize and manage Shorewall state.", no_args_is_help=True)

@app.command("sync")
def sync_shorewall(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying them.")
):
    """
    Synchronizes Shorewall accounting and dynamic blacklist with the live network state.
    """
    if not dry_run:
        check_root_privileges("apply changes to Shorewall")

    config = load_config()
    gs = config.get("global_settings", {})
    hosts_config = config.get("hosts_dhcp_reservations", [])
    leases = get_active_leases(gs.get("dnsmasq_leases_file", ""), hosts_config)
    
    # --- Part 1: Sync Access Control via Dynamic Zone ---
    typer.echo(typer.style("Syncing Shorewall Dynamic 'blocked' Zone...", bold=True))
    currently_blocked = get_currently_blocked_ips("blocked")
    
    active_ips = {lease.get("ip") for lease in leases}
    ips_that_should_be_blocked = {host.get("ip_address") for host in hosts_config if host.get("network_access_blocked")}
    
    desired_blocked_set = ips_that_should_be_blocked.intersection(active_ips)

    ips_to_add = desired_blocked_set - currently_blocked
    ips_to_remove = currently_blocked - desired_blocked_set

    if not ips_to_add and not ips_to_remove:
        typer.echo("Access control rules are already in sync.")
    else:
        for ip in ips_to_remove:
            typer.echo(f"Removing stale or allowed IP from zone 'blocked': {ip}")
            run_command(["shorewall", "delete", "blocked", ip], dry_run=dry_run, suppress_output=True)
        for ip in ips_to_add:
            typer.echo(f"Adding newly blocked IP to zone 'blocked': {ip}")
            run_command(["shorewall", "add", "blocked", ip], dry_run=dry_run, suppress_output=True)
        
        if not dry_run:
            typer.echo("Refreshing Shorewall to apply dynamic zone changes...")
            run_command(["shorewall", "refresh"], dry_run=False)

    # --- Part 2: Sync Accounting File ---
    typer.echo(typer.style("\nSyncing Shorewall Accounting File...", bold=True))
    
    if not leases:
        typer.echo(typer.style("No active leases found to monitor.", fg=typer.colors.YELLOW))
        accounting_content = ""
    else:
        typer.echo(f"Found {len(leases)} active leases to generate accounting rules for.")
        accounting_content = generate_accounting_config(leases)
    
    # This writes the file, but a 'reload' is needed to apply it.
    write_shorewall_file(accounting_content, "/etc/shorewall/accounting", ACCOUNTING_MANAGED_BLOCK_START, ACCOUNTING_MANAGED_BLOCK_END, dry_run)

    typer.echo(typer.style("\nSynchronization check complete.", fg=typer.colors.GREEN, bold=True))
    typer.echo("Run 'inetctl shorewall reload' to apply any changes to the accounting file.")


@app.command("reload")
def reload_shorewall_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done.")
):
    """Performs a full 'shorewall reload' to apply config file changes."""
    typer.echo("Performing a full Shorewall reload...")
    run_command(["shorewall", "reload"], dry_run=dry_run)
    if not dry_run:
        typer.echo(typer.style("Shorewall reloaded successfully.", fg=typer.colors.GREEN))
