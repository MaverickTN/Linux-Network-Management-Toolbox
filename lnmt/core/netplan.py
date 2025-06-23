# lnmt/core/netplan.py

import yaml
import os
from pathlib import Path

NETPLAN_PATH = "/etc/netplan/"  # Can be overridden in config
DEFAULT_CONFIG_FILE = "01-netcfg.yaml"

def _find_netplan_files(path=NETPLAN_PATH):
    """Find all netplan YAML files in directory."""
    if not os.path.isdir(path):
        return []
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.yaml') or f.endswith('.yml')]

def get_netplan_yaml(path=NETPLAN_PATH):
    """Return current netplan YAML as dict (first file only)."""
    files = _find_netplan_files(path)
    if not files:
        return {}
    with open(files[0], 'r') as f:
        return yaml.safe_load(f)

def write_netplan_yaml(config, path=NETPLAN_PATH, filename=None):
    """Write the netplan config dict as YAML."""
    if not filename:
        files = _find_netplan_files(path)
        filename = os.path.basename(files[0]) if files else DEFAULT_CONFIG_FILE
    fullpath = os.path.join(path, filename)
    with open(fullpath, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)

def get_all_netplan_interfaces(path=NETPLAN_PATH):
    """List all interfaces (including VLANs) from netplan YAML."""
    cfg = get_netplan_yaml(path)
    interfaces = []
    if not cfg or 'network' not in cfg:
        return interfaces
    for iface_type in ('ethernets', 'vlans', 'bonds', 'bridges'):
        if iface_type in cfg['network']:
            for name in cfg['network'][iface_type]:
                interfaces.append({
                    "name": name,
                    "type": iface_type,
                    "config": cfg['network'][iface_type][name]
                })
    return interfaces

def get_vlan_subnets(path=NETPLAN_PATH):
    """Return mapping: vlan_id -> subnet, description (from netplan YAML)."""
    cfg = get_netplan_yaml(path)
    vlans = {}
    if not cfg or 'network' not in cfg or 'vlans' not in cfg['network']:
        return vlans
    for name, vcfg in cfg['network']['vlans'].items():
        # vlan.<ID> or just <name>
        vlan_id = None
        if '.' in name:
            vlan_id = name.split('.')[-1]
        elif 'id' in vcfg:
            vlan_id = str(vcfg['id'])
        else:
            vlan_id = name
        subnet = None
        desc = vcfg.get('description', '')
        for ip in vcfg.get('addresses', []):
            if '/' in ip:
                subnet = ip
                break
        vlans[vlan_id] = {
            "name": name,
            "subnet": subnet,
            "description": desc,
            "base_iface": vcfg.get('link')
        }
    return vlans

def find_vlan_by_subnet(ip_addr, path=NETPLAN_PATH):
    """Given an IP/subnet, return VLAN ID it belongs to (for host->VLAN mapping)."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(ip_addr)
    except Exception:
        return None
    vlans = get_vlan_subnets(path)
    for vlan_id, vcfg in vlans.items():
        if vcfg["subnet"]:
            try:
                net = ipaddress.ip_network(vcfg["subnet"], strict=False)
                if ip in net:
                    return vlan_id
            except Exception:
                continue
    return None

def validate_netplan_yaml(yaml_content):
    """Validate YAML syntax and basic structure for netplan."""
    try:
        cfg = yaml.safe_load(yaml_content)
        # Check for required 'network' section
        if not cfg or "network" not in cfg:
            return False, ["Missing 'network' section."]
        # Could add more checks here if desired
        return True, []
    except Exception as e:
        return False, [str(e)]

def update_vlan(vlan_id, new_subnet=None, description=None, path=NETPLAN_PATH):
    """Update the subnet or description of a VLAN."""
    cfg = get_netplan_yaml(path)
    found = False
    if 'network' in cfg and 'vlans' in cfg['network']:
        for name, vcfg in cfg['network']['vlans'].items():
            match_id = name.split('.')[-1] if '.' in name else str(vcfg.get('id', name))
            if str(vlan_id) == match_id:
                found = True
                if new_subnet:
                    # Replace addresses
                    vcfg['addresses'] = [new_subnet]
                if description is not None:
                    vcfg['description'] = description
                break
    if not found:
        raise KeyError(f"VLAN {vlan_id} not found")
    write_netplan_yaml(cfg, path)
    return True

def delete_vlan(vlan_id, path=NETPLAN_PATH):
    """Delete a VLAN by ID."""
    cfg = get_netplan_yaml(path)
    found = False
    if 'network' in cfg and 'vlans' in cfg['network']:
        to_del = None
        for name, vcfg in cfg['network']['vlans'].items():
            match_id = name.split('.')[-1] if '.' in name else str(vcfg.get('id', name))
            if str(vlan_id) == match_id:
                to_del = name
                found = True
                break
        if to_del:
            del cfg['network']['vlans'][to_del]
    if not found:
        raise KeyError(f"VLAN {vlan_id} not found")
    write_netplan_yaml(cfg, path)
    return True
