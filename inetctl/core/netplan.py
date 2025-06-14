import yaml
from pathlib import Path
from typing import Dict, List, Optional
import ipaddress
import subprocess

def find_netplan_config_file() -> Optional[Path]:
    """Finds the first .yaml file in /etc/netplan/."""
    netplan_dir = Path("/etc/netplan/")
    if not netplan_dir.is_dir():
        return None
    try:
        return next(netplan_dir.glob('*.yaml'))
    except StopIteration:
        return None

def load_netplan_config() -> Optional[Dict]:
    """Loads and parses the system's netplan configuration file."""
    config_file = find_netplan_config_file()
    if not config_file:
        return None
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        print(f"Warning: Could not load or parse netplan config: {e}")
        return None

def save_netplan_config(config: Dict):
    """Saves a dictionary back to the netplan configuration file."""
    config_file = find_netplan_config_file()
    if not config_file:
        raise FileNotFoundError("No Netplan config file found to save.")
    with open(config_file, 'w') as f:
        yaml.dump(config, f, sort_keys=False, indent=2)

def get_vlan_subnets() -> Dict[str, str]:
    """
    Parses netplan config to get a mapping of VLAN interface names to their subnets.
    For example: {'vlan15': '10.0.2.0/27'}
    """
    netplan_config = load_netplan_config()
    if not netplan_config or 'network' not in netplan_config:
        return {}
    subnets = {}
    for device_type in ['vlans', 'bridges']:
        devices = netplan_config['network'].get(device_type, {})
        for device_name, details in devices.items():
            addresses = details.get('addresses', [])
            if addresses:
                try:
                    iface = ipaddress.ip_interface(addresses[0])
                    subnets[device_name] = str(iface.network)
                except ValueError:
                    continue
    return subnets

def get_all_netplan_interfaces() -> Dict[str, List[str]]:
    """
    Gets a list of all configured interfaces grouped by type,
    explicitly skipping the 'version' and 'ethernets' keys.
    """
    config = load_netplan_config()
    if not config or 'network' not in config:
        return {}
    interfaces = {}
    for key, value in config['network'].items():
        if isinstance(value, dict) and key not in ['version', 'ethernets']:
            interfaces[key] = list(value.keys())
    return interfaces

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
    if config and iface_name in config.get('network', {}).get(iface_type, {}):
        del config['network'][iface_type][iface_name]
        save_netplan_config(config)

def update_netplan_interface(iface_type: str, iface_name: str, key: str, value: str):
    """Updates a specific key for a given interface in the netplan config."""
    config = load_netplan_config()
    if config and iface_name in config.get('network', {}).get(iface_type, {}):
        config['network'][iface_type][iface_name][key] = value
        save_netplan_config(config)
        return True
    return False

def add_route_to_netplan_interface(iface_type: str, iface_name: str, to: str, via: str):
    """Adds a new static route to a given interface."""
    config = load_netplan_config()
    iface = config.get('network', {}).get(iface_type, {}).get(iface_name)
    if iface:
        iface.setdefault('routes', []).append({'to': to, 'via': via})
        save_netplan_config(config)
        return True
    return False

def delete_route_from_netplan_interface(iface_type: str, iface_name: str, to: str, via: str):
    """Deletes a static route from a given interface."""
    config = load_netplan_config()
    iface = config.get('network', {}).get(iface_type, {}).get(iface_name)
    if iface and 'routes' in iface:
        route_to_remove = {'to': to, 'via': via}
        if route_to_remove in iface['routes']:
            iface['routes'].remove(route_to_remove)
            if not iface['routes']: del iface['routes']
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