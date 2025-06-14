import typer
import yaml
import json
from typing import Optional, List
from inetctl.core.netplan import (add_netplan_interface, delete_netplan_interface, get_all_netplan_interfaces, apply_netplan_config, update_netplan_interface, add_route_to_netplan_interface, delete_route_from_netplan_interface)
from inetctl.core.config_loader import load_config, save_config

app = typer.Typer(name="network", help="Manage Netplan network configurations.", no_args_is_help=True)

@app.command()
def add(
    iface_type: str = typer.Argument(..., help="The type of interface (e.g., 'vlans', 'bridges')."),
    iface_name: str = typer.Argument(..., help="The name of the new interface (e.g., 'vlan10')."),
    link: Optional[str] = typer.Option(None, help="Parent interface (e.g. 'br0')."),
    address: Optional[str] = typer.Option(None, help="CIDR address (e.g. 192.168.1.1/24)."),
    name: Optional[str] = typer.Option(None, "--name", help="A friendly name for this network (used in UI)."),
    settings_json: Optional[str] = typer.Option(None, "--settings-json", help="Raw JSON settings string."),
):
    """Adds a new interface to the Netplan configuration."""
    if settings_json:
        settings = json.loads(settings_json)
    else:
        if iface_type == 'vlans':
            if not all([link, address, name]):
                typer.echo("Error: --link, --address, and --name are required for adding VLANs via CLI.", err=True); raise typer.Exit(1)
            settings = {'id': int(iface_name.replace('vlan','')), 'link': link, 'addresses': [address]}
        else:
            typer.echo("Error: Please provide full settings via --settings-json for non-VLAN types.", err=True); raise typer.Exit(1)
            
    add_netplan_interface(iface_type, iface_name, settings)
    
    # Also add a corresponding entry to our own config
    config = load_config()
    config.setdefault("networks", [])
    if not any(n['id'] == iface_name for n in config['networks']):
        config['networks'].append({"id": iface_name, "name": name or iface_name, "purpose": "lan"})
        save_config(config)
    
    typer.echo(f"Successfully added {iface_type} '{iface_name}'. Run 'network apply' to activate.")

@app.command()
def delete(iface_type: str, iface_name: str):
    """Removes an interface from the Netplan configuration."""
    delete_netplan_interface(iface_type, iface_name)
    config = load_config()
    config['networks'] = [n for n in config.get('networks', []) if n.get('id') != iface_name]
    save_config(config)
    typer.echo(f"Successfully removed {iface_name}. Run 'network apply' to finalize.")
    
@app.command()
def apply():
    """Applies the current Netplan configuration to the system."""
    success, output = apply_netplan_config()
    if success:
        typer.echo("Netplan configuration applied successfully.")
    else:
        typer.echo(f"Error applying Netplan config:\n{output}", err=True)

# Other commands remain for potential CLI/backend use but are not the focus.
@app.command(name="list")
def list_interfaces():
    #...
    pass