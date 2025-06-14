import yaml
from pathlib import Path
from typing import Dict, List, Optional
import ipaddress
import subprocess

def find_netplan_config_file() -> Optional[Path]:
    """Finds the first .yaml file in /etc/netplan/."""
    netplan_dir = Path("/etc/netplan/")
    if not netplan_dir.is_dir(): return None
    try: return next(netplan_dir.glob('*.yaml'))
    except StopIteration: return None

def load_netplan_config() -> Optional[Dict]:
    """Loads and parses the system's netplan configuration file."""
    config_file = find_netplan_config_file()
    if not config_file: return None
    try:
        with open(config_file, 'r') as f: return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        print(f"Warning: Could not load or parse netplan config: {e}"); return None

def save_netplan_config(config: Dict):
    """Saves a dictionary back to the netplan configuration file."""
    config_file = find_netplan_config_file()
    if not config_file: raise FileNotFoundError("No Netplan config file found to save.")
    with open(config_file, 'w') as f: yaml.dump(config, f, indent=2)

def get_vlan_subnets() -> Dict[str, str]:
    """Parses netplan config to get a mapping of VLAN interface names to their subnets."""
    netplan_config = load_netplan_config()
    if not netplan_config or 'network' not in netplan_config: return {}
    subnets = {}
    for device_type in ['vlans', 'bridges']:
        devices = netplan_config['network'].get(device_type, {})
        for device_name, details in devices.items():
            addresses = details.get('addresses', [])
            if addresses:
                try:
                    iface = ipaddress.ip_interface(addresses[0])
                    subnets[device_name] = str(iface.network)
                except ValueError: continue
    return subnets

# --- All Functions for `inetctl network` Commands Restored ---

def add_netplan_interface(iface_type: str, iface_name: str, settings: Dict):
    """Adds a new interface definition (vlan, bridge) to netplan config."""
    config = load_netplan_config()
    if 'network' not in config: config['network'] = {}
    if iface_type not in config['network']: config['network'][iface_type] = {}
    config['network'][iface_type][iface_name] = settings
    save_netplan_config(config)

def delete_netplan_interface(iface_type: str, iface_name: str):
    """Removes an interface definition from netplan config."""
    config = load_netplan_config()
    if config and config.get('network', {}).get(iface_type, {}).get(iface_name):
        del config['network'][iface_type][iface_name]
        save_netplan_config(config)

def get_all_netplan_interfaces() -> Dict[str, List[str]]:
    """Gets a list of all configured interfaces grouped by type."""
    config = load_netplan_config()
    if not config or 'network' not in config: return {}
    interfaces = {}
    for key, value in config['network'].items():
        if isinstance(value, dict) and key != 'version':
            interfaces[key] = list(value.keys())
    return interfaces

def update_netplan_interface(iface_type: str, iface_name: str, key: str, value: str):
    """Updates a specific key for a given interface in the netplan config."""
    config = load_netplan_config()
    if config and config.get('network', {}).get(iface_type, {}).get(iface_name):
        # This simple update assumes a flat key-value pair under the interface.
        # For nested keys, a more complex recursive function would be needed.
        config['network'][iface_type][iface_name][key] = value
        save_netplan_config(config)
        return True
    return False

def apply_netplan_config():
    """Applies the netplan configuration using 'netplan apply'."""
    try:
        result = subprocess.run(["sudo", "netplan", "apply"], capture_output=True, text=True, check=True)
        return True, result.stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        error_output = e.stderr if hasattr(e, 'stderr') else "Command not found."
        return False, error_output