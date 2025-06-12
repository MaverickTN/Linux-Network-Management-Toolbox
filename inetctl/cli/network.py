import typer
from typing import Optional

# Import from our new core modules
from inetctl.core.config_loader import load_config
from inetctl.core.utils import (
    check_root_privileges,
    get_network_config_by_id_or_name,
    run_command,
)
# We need to import all the netplan helpers
from inetctl.core.netplan import (
    add_netplan_interface,
    delete_netplan_interface,
    get_all_netplan_interfaces,
    update_netplan_interface,
    add_route_to_netplan_interface,
    delete_route_from_netplan_interface,
)


app = typer.Typer(
    name="network",
    help="Manage network interfaces and related firewall rules.",
    no_args_is_help=True,
)

# ... (wg-up, wg-down, wg-status commands remain unchanged) ...

@app.command("wg-up")
def network_wg_up(target_network: str = typer.Argument(..., help="VLAN ID or Name of the network from server_config.json.")):
    # This function is unchanged
    pass

@app.command("wg-down")
def network_wg_down(target_network: str = typer.Argument(..., help="VLAN ID or Name of the network from server_config.json.")):
    # This function is unchanged
    pass

@app.command("wg-status")
def network_wg_status(target_network: Optional[str] = typer.Argument(None, help="Optional: Specific network. Shows all if omitted.")):
    # This function is unchanged
    pass

# --- Netplan CLI Commands ---

@app.command("netplan-list")
def netplan_list_cmd():
    """List all interfaces in netplan YAML files."""
    config = load_config()
    global_settings = config.get("global_settings", {})
    interfaces = get_all_netplan_interfaces(global_settings)
    if not interfaces:
        typer.echo("No netplan interfaces found.")
        return
    for iface in interfaces:
        typer.echo(
            f"File: {iface['file']} | Section: {iface['section']} | "
            f"Interface: {iface['interface']} | Addresses: {', '.join(iface['addresses'])} | "
            f"DHCP4: {iface['dhcp4']} | DHCP6: {iface['dhcp6']}"
        )

# ... (netplan-add, netplan-edit, netplan-delete commands remain unchanged) ...

@app.command("netplan-add")
def netplan_add_cmd(file: str, section: str, interface: str, addresses: str, dhcp4: bool, dhcp6: bool):
    # This function is unchanged
    pass

@app.command("netplan-edit")
def netplan_edit_cmd(file: str, section: str, interface: str, addresses: str, dhcp4: bool, dhcp6: bool):
    # This function is unchanged
    pass

@app.command("netplan-delete")
def netplan_delete_cmd(file: str, section: str, interface: str):
    # This function is unchanged
    pass


# --- NEW: Netplan Route CLI Commands ---

@app.command("netplan-route-add")
def netplan_route_add_cmd(
    file: str = typer.Option(..., "--file", help="YAML file path."),
    section: str = typer.Option(..., "--section", help="Section (e.g., ethernets, vlans)."),
    interface: str = typer.Option(..., "--interface", help="Interface name."),
    to: str = typer.Option(..., "--to", help="Destination CIDR (e.g., 10.0.0.0/8)."),
    via: Optional[str] = typer.Option(None, "--via", help="Gateway IP address."),
    on_link: bool = typer.Option(False, "--on-link", help="Set route as on-link (use instead of --via).")
):
    """Adds a static route to a Netplan interface."""
    if via and on_link:
        typer.echo("Error: Cannot use both --via and --on-link.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if not via and not on_link:
        typer.echo("Error: Must specify either --via or --on-link.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    try:
        add_route_to_netplan_interface(file, section, interface, to, via, on_link)
        typer.echo(f"Successfully added route to '{to}' via '{via or 'on-link'}' for interface '{interface}'.", fg=typer.colors.GREEN)
        typer.echo("Run 'sudo netplan apply' to activate changes.")
    except Exception as e:
        typer.echo(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command("netplan-route-delete")
def netplan_route_delete_cmd(
    file: str = typer.Option(..., "--file", help="YAML file path."),
    section: str = typer.Option(..., "--section", help="Section (e.g., ethernets, vlans)."),
    interface: str = typer.Option(..., "--interface", help="Interface name."),
    to: str = typer.Option(..., "--to", help="Destination CIDR of the route to delete."),
    via: Optional[str] = typer.Option(None, "--via", help="Gateway IP of the route to delete (omit for on-link).")
):
    """Deletes a static route from a Netplan interface."""
    try:
        delete_route_from_netplan_interface(file, section, interface, to, via)
        typer.echo(f"Successfully deleted route to '{to}' for interface '{interface}'.", fg=typer.colors.GREEN)
        typer.echo("Run 'sudo netplan apply' to activate changes.")
    except Exception as e:
        typer.echo(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
