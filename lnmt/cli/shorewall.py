import typer
import getpass

from lnmt.core.config_loader import load_config
from lnmt.core.utils import (
    run_command, get_shorewall_blacklisted_ips,
    get_active_leases, check_root_privileges,
)
from lnmt.core.shorewall import (
    apply_shorewall_config, generate_accounting_rules,
    generate_mangle_rules,
)
from lnmt.core.logger import log_event

# The main Typer application for this CLI module
app = typer.Typer(
    name="shorewall",
    help="Manage and apply Shorewall configuration files.",
    no_args_is_help=True
)

@app.command(name="sync")
def sync_shorewall():
    """
    Synchronizes the Shorewall blacklist with the server_config.json.
    This command is designed to be called by other automated processes.
    """
    check_root_privileges("synchronize the firewall")
    config = load_config()
    
    known_hosts = config.get("known_hosts", [])
    # Corrected to look in the new 'system_paths' section
    leases_file = config.get("system_paths", {}).get("dnsmasq_leases_file", "")
    mac_to_ip_map = {lease["mac"]: lease["ip"] for lease in get_active_leases(leases_file)}

    desired_blocked_ips = set()
    live_blocked_ips = set(get_shorewall_blacklisted_ips())

    for host in known_hosts:
        if host.get("network_access_blocked"):
            assignment = host.get("ip_assignment", {})
            ip = assignment.get("ip") if assignment.get("type") == "static" else mac_to_ip_map.get(host.get("mac"))
            if ip:
                desired_blocked_ips.add(ip)

    ips_to_add = desired_blocked_ips - live_blocked_ips
    ips_to_remove = live_blocked_ips - desired_blocked_ips
    
    if not ips_to_add and not ips_to_remove:
        return

    for ip in ips_to_add:
        run_command(["sudo", "shorewall", "reject", ip])
    for ip in ips_to_remove:
        run_command(["sudo", "shorewall", "allow", ip])
    
@app.command(name="apply-config")
def apply_shorewall_full_config(
    force_reload: bool = typer.Option(
        False, "--force", "-f",
        help="Force a 'shorewall reload' even if files are unchanged."
    )
):
    """
    Generates lnmt-managed Shorewall files and reloads if needed.
    """
    cli_user = getpass.getuser()
    log_event("INFO", "cli:shorewall:apply", "User triggered config apply.", username=cli_user)
    check_root_privileges("apply Shorewall configuration")
    config = load_config()
    
    typer.echo("Generating lnmt-managed Shorewall files...")
    
    accounting_content = generate_accounting_rules(config)
    mangle_content = generate_mangle_rules(config)

    accounting_changed = apply_shorewall_config("/etc/shorewall/accounting", accounting_content)
    mangle_changed = apply_shorewall_config("/etc/shorewall/mangle", mangle_content)

    if accounting_changed or mangle_changed or force_reload:
        typer.echo("Configuration changed. Reloading Shorewall...")
        log_event("INFO", "cli:shorewall:apply", "Config files changed, reloading.", username=cli_user)
        result = run_command(["sudo", "shorewall", "reload"])
        if result["returncode"] == 0:
            log_event("INFO", "cli:shorewall:apply", "Shorewall reloaded successfully.", username=cli_user)
            typer.echo(typer.style("Shorewall reloaded successfully.", fg=typer.colors.GREEN))
        else:
            err_msg = f"Error reloading Shorewall:\n{result['stderr']}"
            log_event("ERROR", "cli:shorewall:apply", err_msg, username=cli_user)
            typer.echo(typer.style(err_msg, fg=typer.colors.RED), err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo("No changes detected in lnmt-managed files. Nothing to do.")