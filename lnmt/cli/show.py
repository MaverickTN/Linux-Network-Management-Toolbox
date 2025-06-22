from typing import Optional

import typer

# Import from our new core modules
from inetctl.core.config_loader import load_config
from inetctl.core.utils import print_item_details

# Define a new Typer application for the 'show' subcommand
app = typer.Typer(
    name="show", help="Show various aspects of the network configuration.", no_args_is_help=True
)


@app.command("networks")
def show_networks_cmd(
    vlan: Optional[int] = typer.Option(None, "--vlan", help="Filter by VLAN ID.")
):
    """Show configured networks (VLANs) from server_config.json."""
    config = load_config()
    networks = config.get("networks", [])
    if not networks:
        typer.echo("No networks defined in the configuration.")
        raise typer.Exit()

    typer.echo(
        typer.style(
            "Configured Networks (VLANs):", fg=typer.colors.BRIGHT_BLUE, bold=True
        )
    )
    found_any = False
    for net_config_entry in networks:
        if vlan is None or net_config_entry.get("vlan_id") == vlan:
            found_any = True
            print_item_details(net_config_entry, "Network ")

    if not found_any and vlan is not None:
        typer.echo(typer.style(f"No network found with VLAN ID: {vlan}", fg=typer.colors.YELLOW))


@app.command("hosts")
def show_hosts_cmd(
    vlan: Optional[int] = typer.Option(None, "--vlan", help="Filter by VLAN ID."),
    mac: Optional[str] = typer.Option(
        None, "--mac", help="Filter by MAC address (case-insensitive)."
    ),
    host_id: Optional[str] = typer.Option(
        None, "--id", help="Filter by host ID (case-insensitive)."
    ),
):
    """Show configured DHCP host reservations and their details."""
    config = load_config()
    hosts = config.get("hosts_dhcp_reservations", [])
    if not hosts:
        typer.echo("No DHCP host reservations defined in the configuration.")
        raise typer.Exit()

    typer.echo(
        typer.style(
            "Configured DHCP Host Reservations:", fg=typer.colors.BRIGHT_BLUE, bold=True
        )
    )

    filtered_hosts = hosts
    if vlan is not None:
        filtered_hosts = [h for h in filtered_hosts if h.get("vlan_id") == vlan]
    if mac is not None:
        filtered_hosts = [
            h for h in filtered_hosts if h.get("mac_address", "").lower() == mac.lower()
        ]
    if host_id is not None:
        filtered_hosts = [
            h for h in filtered_hosts if h.get("id", "").lower() == host_id.lower()
        ]

    if not filtered_hosts:
        typer.echo(
            typer.style("No hosts found matching your criteria.", fg=typer.colors.YELLOW)
        )
        if vlan is not None or mac is not None or host_id is not None:
            return
        raise typer.Exit()

    for host_config_entry in filtered_hosts:
        print_item_details(host_config_entry, "Host ID: ")


@app.command("remote-hosts")
def show_remote_hosts_cmd(
    remote_id: Optional[str] = typer.Option(
        None, "--id", help="Filter by Remote Host ID (case-insensitive)."
    )
):
    """Show configured remote hosts and their details."""
    config = load_config()
    remote_hosts_list = config.get("remote_hosts", [])
    if not remote_hosts_list:
        typer.echo("No remote hosts defined in the configuration.")
        raise typer.Exit()

    typer.echo(
        typer.style("Configured Remote Hosts:", fg=typer.colors.BRIGHT_BLUE, bold=True)
    )
    found_any = False
    for r_host_config in remote_hosts_list:
        if remote_id is None or r_host_config.get("id", "").lower() == remote_id.lower():
            found_any = True
            print_item_details(r_host_config, "Remote Host ID: ")

    if not found_any and remote_id is not None:
        typer.echo(
            typer.style(f"No remote host found with ID: {remote_id}", fg=typer.colors.YELLOW)
        )


@app.command("setting")
def show_setting_cmd(
    setting_name: str = typer.Argument(
        ...,
        help="The name of the global setting to display (e.g., 'wan_interface').",
    )
):
    """Show a specific global setting's value from server_config.json."""
    config = load_config()
    global_settings = config.get("global_settings", {})

    if setting_name in global_settings:
        typer.echo(
            typer.style(
                f"Global Setting '{setting_name}':",
                fg=typer.colors.BRIGHT_BLUE,
                bold=True,
            )
        )
        typer.echo(f"  Value: {global_settings[setting_name]}")
    else:
        typer.echo(
            typer.style(
                f"Error: Global setting '{setting_name}' not found.",
                fg=typer.colors.RED,
                bold=True,
            )
        )
        if global_settings:
            typer.echo("Available global settings are:")
            for key in global_settings.keys():
                typer.echo(f"  - {key}")
        else:
            typer.echo("  (No global settings defined in the configuration)")
        raise typer.Exit(code=1)
