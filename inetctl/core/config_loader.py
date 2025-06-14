import json
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple

from inetctl.core.netplan import get_all_netplan_interfaces

# Define the search paths for the configuration file
CONFIG_SEARCH_PATHS = [
    "./server_config.json",
    Path.home() / ".config/inetctl/server_config.json"
]

# This global variable will store the path once found, so we don't have to search repeatedly.
# Re-adding this variable to fix the ImportError.
LOADED_CONFIG_PATH: Optional[Path] = None

def find_config_file() -> Optional[Path]:
    """Finds the config file and caches the result."""
    global LOADED_CONFIG_PATH
    if LOADED_CONFIG_PATH and LOADED_CONFIG_PATH.exists():
        return LOADED_CONFIG_PATH
    
    for path in CONFIG_SEARCH_PATHS:
        p = Path(path)
        if p.exists():
            LOADED_CONFIG_PATH = p
            return p
    return None

def load_config(config_path: Optional[Path] = None) -> Dict:
    """Loads the main server_config.json file."""
    path = config_path or find_config_file()
    if not path:
        return {} # Return an empty dict if no config file is found
    try:
        with open(path, "r") as f:
            config = json.load(f)
            # Sync networks from netplan into the config object
            sync_networks_from_netplan(config)
            return config
    except (IOError, json.JSONDecodeError):
        return {}

def save_config(config_data: Dict, config_path: Optional[Path] = None):
    """Saves the configuration dictionary back to the file."""
    path = config_path or find_config_file()
    if not path:
        # If no config file was found, create a new one in the default user location.
        path = Path(CONFIG_SEARCH_PATHS[-1])
        path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        # Dump the config with 2-space indentation for readability
        json.dump(config_data, f, indent=2)

def sync_networks_from_netplan(config: Dict):
    """
    Ensures the 'networks' list in server_config.json is up-to-date
    with the system's actual Netplan configuration for VLANs and Bridges.
    This dynamically populates the network tabs on the dashboard.
    """
    try:
        netplan_ifaces = get_all_netplan_interfaces()
        if not netplan_ifaces:
            return
    except Exception as e:
        print(f"Warning: Could not read Netplan configuration to sync networks. Error: {e}")
        return

    config.setdefault("networks", [])
    config_net_ids = {net['id'] for net in config['networks']}
    
    changed = False
    for iface_type in ['vlans', 'bridges']:
        for iface_id in netplan_ifaces.get(iface_type, []):
            if iface_id not in config_net_ids:
                new_net = {
                    "id": iface_id,
                    "name": iface_id.replace('vlan', 'VLAN ').replace('br','Bridge ').capitalize(),
                    "purpose": "unassigned" # Default purpose for newly discovered networks
                }
                config["networks"].append(new_net)
                changed = True
                print(f"Discovered and auto-added new network from Netplan: {iface_id}")
    
    if changed:
        # Sort for consistent display order in the UI
        config['networks'] = sorted(config['networks'], key=lambda x: x.get('id', 'z'))