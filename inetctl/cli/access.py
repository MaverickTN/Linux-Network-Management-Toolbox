import typer

from inetctl.core.config_loader import load_config, save_config
from inetctl.core.shorewall import get_currently_blocked_ips
from inetctl.core.utils import (check_root_privileges, get_active_leases,
                                run_command)

app = typer.Typer(
    name="access", help="Manage host network access (total block).", no_args_is_help=True
)

def set_host_blocked_status(host_id: str, is_blocked: bool) -> bool:
    """Finds a host in the config and sets its 'network_access_blocked' status."""
    config = load_config(force_reload=True)
    hosts = config.get("hosts_dhcp_reservations", [])
    
    host_found = False
    for host in hosts:
        if host.get("id", "").lower() == host_id.lower():
            host["network_access_blocked"] = is_blocked
            host_found = True
            break
    
    if not host_found:
        typer.echo(typer.style(f"Error: Host ID '{host_id}' not found in configuration.", fg=typer.colors.RED))
        return False

    return save_config(config)


@app.command("sync")
def sync_access_rules(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying them.")
):
    """
    Synchronizes the Shorewall 'blocked' dynamic zone with the current config and active leases.
    """
    if not dry_run:
        check_root_privileges("apply access control rules to Shorewall")

    typer.echo("Syncing Shorewall dynamic 'blocked' zone...")
    
    config = load_config()
    gs = config.get("global_settings", {})
    hosts = config.get("hosts_dhcp_reservations", [])
    leases = get_active_leases(gs.get("dnsmasq_leases_file", ""), hosts)
    
    # 1. Get the current state from Shorewall
    currently_blocked_ips = get_currently_blocked_ips("blocked")
    
    # 2. Determine the desired state from our config and live leases
    active_ips = {lease.get("ip") for lease in leases}
    ips_that_should_be_blocked = {host.get("ip_address") for host in hosts if host.get("network_access_blocked")}
    
    # The final set of IPs to block is the intersection of what we WANT to block and what is ACTUALLY active
    desired_blocked_set = ips_that_should_be_blocked.intersection(active_ips)

    # 3. Reconcile the differences
    ips_to_add = desired_blocked_set - currently_blocked_ips
    ips_to_remove = currently_blocked_ips - desired_blocked_set

    if not ips_to_add and not ips_to_remove:
        typer.echo("Shorewall 'blocked' zone is already in sync. No changes needed.", fg=typer.colors.GREEN)
        return

    for ip in ips_to_remove:
        typer.echo(f"Removing stale or unblocked IP from zone 'blocked': {ip}")
        run_command(["shorewall", "delete", "blocked", ip], dry_run=dry_run)

    for ip in ips_to_add:
        typer.echo(f"Adding newly blocked IP to zone 'blocked': {ip}")
        run_command(["shorewall", "add", "blocked", ip], dry_run=dry_run)

    typer.echo(typer.style("Shorewall 'blocked' zone synchronization complete.", fg=typer.colors.GREEN, bold=True))


@app.command("block")
def access_block(
    host_id: str = typer.Argument(..., help="The unique 'id' of the host to block.")
):
    """Flags a host as blocked, then runs 'access sync' to apply changes."""
    typer.echo(f"Marking host '{host_id}' as blocked...")
    if set_host_blocked_status(host_id, is_blocked=True):
        typer.echo("Configuration updated. Now syncing firewall rules...")
        try:
            ctx = typer.Context(sync_access_rules)
            ctx.invoke(sync_access_rules, dry_run=False)
        except Exception as e:
            typer.echo(typer.style(f"Error during firewall sync: {e}", fg=typer.colors.RED))


@app.command("allow")
def access_allow(
    host_id: str = typer.Argument(..., help="The unique 'id' of the host to allow.")
):
    """Flags a host as allowed, then runs 'access sync' to apply changes."""
    typer.echo(f"Marking host '{host_id}' as allowed...")
    if set_host_blocked_status(host_id, is_blocked=False):
        typer.echo("Configuration updated. Now syncing firewall rules...")
        try:
            ctx = typer.Context(sync_access_rules)
            ctx.invoke(sync_access_rules, dry_run=False)
        except Exception as e:
            typer.echo(typer.style(f"Error during firewall sync: {e}", fg=typer.colors.RED))
