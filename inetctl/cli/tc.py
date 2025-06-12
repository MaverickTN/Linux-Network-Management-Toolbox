from typing import Optional

import typer

# Import from our new core modules
from inetctl.core.config_loader import load_config
from inetctl.core.utils import (
    check_root_privileges,
    generate_tc_commands,
    run_command,
)

app = typer.Typer(
    name="tc", help="Manage Traffic Control (QoS) policies.", no_args_is_help=True
)


@app.command("apply")
def tc_apply(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the tc commands that would be executed."
    )
):
    """Applies all configured Traffic Control (QoS) policies."""
    if not dry_run:
        check_root_privileges("apply traffic control rules")
    config = load_config()
    global_settings = config.get("global_settings", {})
    all_hosts = config.get("hosts_dhcp_reservations", [])
    all_policies = config.get("traffic_control_policies", [])
    networks = config.get("networks", [])
    base_iface = global_settings.get("primary_host_lan_interface_base")
    default_down = global_settings.get("default_lan_download_speed", "1000mbit")
    
    if not all([base_iface, networks, all_policies]):
        typer.echo(
            "Missing required settings in config for TC.", fg=typer.colors.RED
        )
        raise typer.Exit(1)

    for net_config in networks:
        suffix = net_config.get("netplan_interface_suffix")
        if suffix is None:
            continue
        interface_name = base_iface + suffix
        hosts_in_net = [
            h for h in all_hosts if h.get("vlan_id") == net_config.get("vlan_id")
        ]
        typer.echo(
            typer.style(
                f"\nProcessing TC for interface '{interface_name}'...", bold=True
            )
        )
        tc_commands = generate_tc_commands(
            interface_name, all_policies, hosts_in_net, "10mbit", default_down
        )
        for command in tc_commands:
            run_command(command, dry_run=dry_run, suppress_output="del" in command, check=False)


@app.command("status")
def tc_status(
    interface: Optional[str] = typer.Argument(
        None, help="The specific interface to check. Shows all if omitted."
    )
):
    """Shows active QoS rules on one or all relevant interfaces."""
    check_root_privileges("view traffic control status")
    config = load_config()
    base_iface = config.get("global_settings", {}).get(
        "primary_host_lan_interface_base"
    )
    interfaces_to_check = (
        [interface]
        if interface
        else [
            base_iface + n.get("netplan_interface_suffix", "")
            for n in config.get("networks", [])
            if n.get("netplan_interface_suffix") is not None
        ]
    )
    if not interfaces_to_check:
        typer.echo("No interfaces found to check.", fg=typer.colors.YELLOW)
        return
    for iface in interfaces_to_check:
        typer.echo(
            typer.style(f"\n--- Status for {iface} ---", bold=True, fg=typer.colors.CYAN)
        )
        run_command(["tc", "-s", "qdisc", "show", "dev", iface], dry_run=False, check=False)
        run_command(["tc", "-s", "class", "show", "dev", iface], dry_run=False, check=False)
        run_command(["tc", "filter", "show", "dev", iface], dry_run=False, check=False)


@app.command("clear")
def tc_clear(
    interface: Optional[str] = typer.Argument(
        None, help="The specific interface to clear. Clears all if omitted."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the commands that would be executed."
    ),
):
    """Removes all QoS rules from specified or all interfaces."""
    if not dry_run:
        check_root_privileges("clear traffic control rules")
    config = load_config()
    base_iface = config.get("global_settings", {}).get(
        "primary_host_lan_interface_base"
    )
    interfaces_to_clear = (
        [interface]
        if interface
        else [
            base_iface + n.get("netplan_interface_suffix", "")
            for n in config.get("networks", [])
            if n.get("netplan_interface_suffix") is not None
        ]
    )
    if not interfaces_to_clear:
        typer.echo("No interfaces found to clear.", fg=typer.colors.YELLOW)
        return
    for iface in interfaces_to_clear:
        typer.echo(f"Clearing rules from interface: {iface}")
        run_command(["tc", "qdisc", "del", "dev", iface, "root"], dry_run=dry_run, suppress_output=True, check=False)
