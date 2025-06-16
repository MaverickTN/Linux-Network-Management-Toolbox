import yaml
import ipaddress
from pathlib import Path

CONFIG_PATH = Path('/etc/netplan/01-netcfg.yaml')

def load_config(path=CONFIG_PATH):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def save_config(config, path=CONFIG_PATH):
    with open(path, 'w') as f:
        yaml.safe_dump(config, f)

def list_interfaces(config=None):
    if config is None:
        config = load_config()
    return list(config['network'].get('ethernets', {}).keys())

def list_vlans(config=None):
    if config is None:
        config = load_config()
    return list(config['network'].get('vlans', {}).keys())

def get_vlan_info(config=None):
    if config is None:
        config = load_config()
    vlans = []
    for name, vlan in config['network'].get('vlans', {}).items():
        vlan_id = vlan.get('id', name)
        link = vlan.get('link', '')
        addresses = vlan.get('addresses', [])
        vlans.append({
            'name': name,
            'id': vlan_id,
            'link': link,
            'addresses': addresses,
        })
    return vlans

# --- New helper: Build subnet->VLAN mapping ---
def build_vlan_subnet_map(config=None):
    if config is None:
        config = load_config()
    mapping = {}
    for vlan in get_vlan_info(config):
        vlan_id = str(vlan.get('id'))
        for addr in vlan.get('addresses', []):
            try:
                network = ipaddress.ip_network(addr, strict=False)
                mapping[network] = vlan_id
            except Exception:
                pass
    # Main LAN (untagged, treat as VLAN 1)
    for eth in list_interfaces(config):
        eth_data = config['network']['ethernets'][eth]
        for addr in eth_data.get('addresses', []):
            try:
                network = ipaddress.ip_network(addr, strict=False)
                mapping[network] = "1"
            except Exception:
                pass
    return mapping

# --- New helper: Get VLAN ID for IP ---
def get_vlan_id_for_ip(ip, config=None):
    mapping = build_vlan_subnet_map(config)
    ip_obj = ipaddress.ip_address(ip)
    for subnet, vlan_id in mapping.items():
        if ip_obj in subnet:
            return vlan_id
    return "1"  # fallback
