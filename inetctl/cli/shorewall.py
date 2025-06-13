import typer

from inetctl.core.config_loader import load_config
from inetctl.core.utils import (
    run_command, get_shorewall_blacklisted_ips,
    get_active_leases, check_root_privileges,
)
from inetctl.core.shorewall import (
    apply_shorewall_config, generate_accounting_rules,
    generate_mangle_rules, generate_policy_rules,
)
from inetctl.core.logger import log_event

app = typer.Typer(name="shorewall", help="Manage Shorewall firewall rules.", no_args_is_help=True)

@app.command(name="sync")
def sync_shorewall():
    """Synchronizes the Shorewall blacklist with the server_config.json."""
    check_root_privileges("synchronize the firewall")
    config = load_config()
    known_hosts = config.get("known_hosts", [])
    leases_file = config.get("global_settings", {}).get("dnsmasq_leases_file", "")
    mac_to_ip_map = {lease["mac"]: lease["ip"] for lease in get_active_leases(leases_file)}

    desired_blocked_ips = set()
    for host in known_hosts:
        if host.get("network_access_blocked"):
            assignment = host.get("ip_assignment", {})
            ip_to_block = assignment.get("ip") if assignment.get("type") == "static" else mac_to_ip_map.get(host.get("mac"))
            if ip_to_block: desired_blocked_ips.add(ip_to_block)

    live_blocked_ips = set(get_shorewall_blacklisted_ips())
    ips_to_add = desired_blocked_ips - live_blocked_ips
    ips_to_remove = live_blocked_ips - desired_blocked_ips

    if not ips_to_add and not ips_to_remove: 
        typer.echo("Shorewall blacklist is already in sync.")
        return

    log_event("INFO", "shorewall:sync", "Blacklist synchronization starting.")
    for ip in ips_to_add:
        log_event("INFO", "shorewall:sync", f"Blacklisting (rejecting) {ip}.")
        run_command(["sudo", "shorewall", "reject", ip])

    for ip in ips_to_remove:
        log_event("INFO", "shorewall:sync", f"Un-blacklisting (allowing) {ip}.")
        run_command(["sudo", "shorewall", "allow", ip])
    
    typer.echo("Sync complete.")
    log_event("INFO", "shorewall:sync", "Sync complete.")

@app.command(name="apply-config")
def apply_shorewall_full_config(force_reload: bool = typer.Option(False, "--force", "-f")):
    """Generates all Shorewall config files and reloads if needed."""
    check_root_privileges("apply full Shorewall configuration")
    config = load_config()
    typer.echo("Generating Shorewall configuration files...")
    
    policy_content = generate_policy_rules(config)
    accounting_content = generate_accounting_rules(config)
    mangle_content = generate_mangle_rules(config)
    policy_changed = apply_shorewall_config("/etc/shorewall/policy", policy_content)
    accounting_changed = apply_shorewall_config("/etc/shorewall/accounting", accounting_content)
    mangle_changed = apply_shorewall_config("/etc/shorewall/mangle", mangle_content)
    if policy_changed or accounting_changed or mangle_changed or force_reload:
        typer.echo("Configuration changed. Reloading Shorewall...")
        log_event("INFO", "shorewall:apply", "Configuration files changed, reloading Shorewall.")
        result = run_command(["sudo", "shorewall", "reload"])
        if result["returncode"] != 0:
            err_msg = f"Error reloading Shorewall:\n{result['stderr']}"
            log_event("ERROR", "shorewall:apply", err_msg)
            typer.echo(typer.style(err_msg, fg=typer.colors.RED), err=True)
            raise typer.Exit(code=1)
        else:
            log_event("INFO", "shorewall:apply", "Shorewall reloaded successfully.")
            typer.echo(typer.style("Shorewall reloaded successfully.", fg=typer.colors.GREEN))
    else:
        typer.echo("No changes detected in Shorewall configuration files. Nothing to do.")