import yaml
from pathlib import Path
from typing import Dict, Optional
import ipaddress

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

def get_vlan_subnets() -> Dict[str, str]:
    """
    Parses netplan config to get a mapping of VLAN interface names to their subnets.
    For example: {'vlan15': '10.0.2.0/27'}
    """
    netplan_config = load_netplan_config()
    if not netplan_config or 'network' not in netplan_config:
        return {}

    subnets = {}
    # Handles both vlans and bridges over vlans, which is a common setup.
    for device_type in ['vlans', 'bridges']:
        devices = netplan_config['network'].get(device_type, {})
        for device_name, details in devices.items():
            addresses = details.get('addresses', [])
            if addresses:
                try:
                    # Using ip_interface correctly finds the network address from an interface address
                    iface = ipaddress.ip_interface(addresses[0])
                    subnets[device_name] = str(iface.network)
                except ValueError:
                    continue # Ignore non-IP address entries
                    
    return subnets