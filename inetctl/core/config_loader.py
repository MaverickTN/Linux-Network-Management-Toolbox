import json
import yaml
from pathlib import Path
from typing import Dict, Optional

# Now depends on the netplan parser to be self-aware
from inetctl.core.netplan import get_all_netplan_interfaces

CONFIG_SEARCH_PATHS = ["./server_config.json", Path.home() / ".config/inetctl/server_config.json"]

def find_config_file() -> Optional[Path]:
    for path in CONFIG_SEARCH_PATHS:
        if Path(path).exists(): return Path(path)
    return None

def load_config(config_path: Optional[Path] = None) -> Dict:
    path = config_path or find_config_file()
    if not path: return {}
    try:
        with open(path, "r") as f:
            config = json.load(f)
            # --- NEW SELF-CONFIGURING LOGIC ---
            sync_networks_from_netplan(config)
            return config
    except (IOError, json.JSONDecodeError): return {}

def save_config(config_data: Dict, config_path: Optional[Path] = None):
    path = config_path or find_config_file()
    if not path:
        # If no config exists, create it in the user's home directory
        path = CONFIG_SEARCH_PATHS[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f: json.dump(config_data, f, indent=2)

def sync_networks_from_netplan(config: Dict):
    """
    Ensures the 'networks' list in server_config.json is in sync with the
    system's actual Netplan configuration for VLANs and Bridges.
    This fixes the 'missing tabs' problem.
    """
    netplan_ifaces = get_all_netplan_interfaces()
    if not netplan_ifaces: return

    config.setdefault("networks", [])
    config_iface_ids = {net['id'] for net in config['networks']}
    
    # Check for vlans and bridges from netplan
    for iface_type in ['vlans', 'bridges']:
        for iface_id in netplan_ifaces.get(iface_type, []):
            if iface_id not in config_iface_ids:
                # Add the missing interface to our config
                new_net = {
                    "id": iface_id,
                    "name": iface_id.replace('vlan', 'VLAN ').capitalize(), # e.g. vlan15 -> VLAN 15
                    "purpose": "unassigned"
                }
                config["networks"].append(new_net)
                print(f"Discovered and auto-added new network from Netplan: {iface_id}")
    
    # Sort for consistency
    config['networks'] = sorted(config['networks'], key=lambda x: x['id'])