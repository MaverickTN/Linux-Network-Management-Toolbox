from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def get_all_netplan_interfaces(global_settings: Dict[str, Any]) -> List[Dict]:
    """Parses all Netplan YAML files and returns a list of found interfaces."""
    netplan_config_dir_str = global_settings.get("netplan_config_dir", "/etc/netplan")
    netplan_config_dir = Path(netplan_config_dir_str)
    interfaces = []
    if not netplan_config_dir.is_dir():
        return interfaces
        
    for yaml_file_path in netplan_config_dir.glob("*.yaml"):
        try:
            with open(yaml_file_path, "r") as f:
                netplan_data = yaml.safe_load(f)
            if not netplan_data or not isinstance(netplan_data, dict) or "network" not in netplan_data:
                continue
            network_section = netplan_data.get("network", {})
            for section in ("ethernets", "vlans", "bridges"):
                if section in network_section and network_section[section] is not None:
                    for iface, details in network_section[section].items():
                        interfaces.append({
                            "file": str(yaml_file_path),
                            "section": section,
                            "interface": iface,
                            "addresses": details.get("addresses", []),
                            "dhcp4": details.get("dhcp4", False),
                            "dhcp6": details.get("dhcp6", False),
                            "raw": details
                        })
        except Exception:
            continue
    return interfaces


def update_netplan_interface(file_path: str, section: str, interface: str, new_data: Dict):
    """Updates a specific interface within a Netplan YAML file."""
    path = Path(file_path)
    with open(path, 'r') as f:
        netplan_data = yaml.safe_load(f)
    
    if not netplan_data or 'network' not in netplan_data:
        raise ValueError('Invalid netplan YAML structure')
    if section not in netplan_data['network']:
        raise ValueError(f'Section {section} not found in {file_path}')
    if interface not in netplan_data['network'][section]:
        raise ValueError(f'Interface {interface} not found in section {section}')
        
    netplan_data['network'][section][interface] = new_data
    
    with open(path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False, indent=2)


def delete_netplan_interface(file_path: str, section: str, interface: str):
    """Deletes a specific interface from a Netplan YAML file."""
    path = Path(file_path)
    with open(path, 'r') as f:
        netplan_data = yaml.safe_load(f)

    if (
        not netplan_data or 'network' not in netplan_data or
        section not in netplan_data['network'] or
        interface not in netplan_data['network'][section]
    ):
        raise ValueError(f"Interface '{interface}' not found in '{section}' of '{file_path}'")

    del netplan_data['network'][section][interface]
    
    with open(path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False, indent=2)


def add_netplan_interface(file_path: str, section: str, interface: str, data: Dict):
    """Adds a new interface to a Netplan YAML file."""
    path = Path(file_path)
    with open(path, 'r') as f:
        netplan_data = yaml.safe_load(f) or {}

    if 'network' not in netplan_data:
        netplan_data['network'] = {}
    if section not in netplan_data['network']:
        netplan_data['network'][section] = {}

    if interface in netplan_data['network'][section]:
        raise ValueError(f"Interface '{interface}' already exists in section '{section}'")

    netplan_data['network'][section][interface] = data

    with open(path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False, indent=2)

# --- NEW: Function to add a route ---
def add_route_to_netplan_interface(file_path: str, section: str, interface: str, to: str, via: Optional[str] = None, on_link: bool = False):
    """Adds a static route to a specific interface in a Netplan YAML file."""
    path = Path(file_path)
    with open(path, 'r') as f:
        netplan_data = yaml.safe_load(f)

    details = netplan_data['network'][section][interface]
    if 'routes' not in details:
        details['routes'] = []

    new_route = {'to': to}
    if on_link:
        new_route['on-link'] = True
    elif via:
        new_route['via'] = via
    else:
        raise ValueError("A route must have either a 'via' gateway or be 'on-link'.")

    # Prevent duplicate routes
    if new_route in details['routes']:
        raise ValueError("This exact route already exists for this interface.")
        
    details['routes'].append(new_route)
    
    with open(path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False, indent=2)

# --- NEW: Function to delete a route ---
def delete_route_from_netplan_interface(file_path: str, section: str, interface: str, to: str, via: Optional[str] = None):
    """Deletes a static route from a specific interface in a Netplan YAML file."""
    path = Path(file_path)
    with open(path, 'r') as f:
        netplan_data = yaml.safe_load(f)

    details = netplan_data['network'][section][interface]
    if 'routes' not in details:
        raise ValueError("No routes found for this interface.")

    # Find the route to delete. If via is None, it's an on-link route.
    route_to_delete = None
    if via:
        route_to_delete = {'to': to, 'via': via}
    else:
        route_to_delete = {'to': to, 'on-link': True}

    if route_to_delete not in details['routes']:
        raise ValueError("The specified route to delete was not found.")
        
    details['routes'].remove(route_to_delete)

    # If no routes are left, remove the empty 'routes' key
    if not details['routes']:
        del details['routes']

    with open(path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False, indent=2)
