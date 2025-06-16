import yaml
import ipaddress
from pathlib import Path

# Update this path if your Netplan config is elsewhere!
CONFIG_PATH = Path('/etc/netplan/01-netcfg.yaml')

def load_config(path=CONFIG_PATH):
    """Load the Netplan YAML configuration as a Python dict."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config, path=CONFIG_PATH):
    """Write the Python dict config back to YAML."""
    with open(path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)

def get_all_netplan_interfaces(config=None):
    """
    Return a list of all network interfaces in the Netplan configuration,
    including both ethernets and vlans.
    """
    if config is None:
        config = load_config()
    interfaces = []
    network = config.get("network", {})
    if "ethernets" in network:
        interfaces.extend(network["ethernets"].keys())
    if "vlans" in network:
        interfaces.extend(network["vlans"].keys())
    return interfaces

def get_vlan_subnets(config=None):
    """
    Returns a dictionary mapping VLAN interface names to their VLAN ID and subnet.
    Example:
        {
            'enp2s0.10': {'vlan_id': 10, 'subnet': '10.0.10.0/24'},
            ...
        }
    """
    if config is None:
        config = load_config()
    vlan_subnets = {}
    network = config.get("network", {})
    vlans = network.get("vlans", {})
    for vlan_name, vlan_data in vlans.items():
        vlan_id = vlan_data.get("id", vlan_name)
        addresses = vlan_data.get("addresses", [])
        for addr in addresses:
            try:
                net = ipaddress.ip_network(addr, strict=False)
                vlan_subnets[vlan_name] = {
                    "vlan_id": vlan_id,
                    "subnet": str(net)
                }
            except Exception:
                continue
    return vlan_subnets

def get_vlan_id_for_ip(ip, config=None):
    """
    Given an IP address as string, returns the VLAN ID it belongs to, or None.
    """
    if config is None:
        config = load_config()
    vlan_subnets = get_vlan_subnets(config)
    ip_obj = ipaddress.ip_address(ip)
    for v in vlan_subnets.values():
        subnet = ipaddress.ip_network(v["subnet"], strict=False)
        if ip_obj in subnet:
            return str(v["vlan_id"])
    return None

def get_base_interface_subnets(config=None):
    """
    Returns a dict of base ethernet interface names to their subnets.
    Example:
        {'enp2s0': '10.0.1.0/24', ...}
    """
    if config is None:
        config = load_config()
    base_subnets = {}
    network = config.get("network", {})
    ethernets = network.get("ethernets", {})
    for eth, eth_data in ethernets.items():
        for addr in eth_data.get("addresses", []):
            try:
                net = ipaddress.ip_network(addr, strict=False)
                base_subnets[eth] = str(net)
            except Exception:
                continue
    return base_subnets

def get_base_interface_for_ip(ip, config=None):
    """
    Given an IP address as string, returns the base (untagged) interface it belongs to, or None.
    """
    if config is None:
        config = load_config()
    base_subnets = get_base_interface_subnets(config)
    ip_obj = ipaddress.ip_address(ip)
    for iface, subnet in base_subnets.items():
        if ip_obj in ipaddress.ip_network(subnet, strict=False):
            return iface
    return None

# For easy CLI debugging
if __name__ == "__main__":
    import sys
    cfg = load_config()
    print("All interfaces:", get_all_netplan_interfaces(cfg))
    print("VLAN subnets:", get_vlan_subnets(cfg))
    print("Base subnets:", get_base_interface_subnets(cfg))
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        print(f"VLAN ID for {ip}: {get_vlan_id_for_ip(ip, cfg)}")
        print(f"Base iface for {ip}: {get_base_interface_for_ip(ip, cfg)}")
