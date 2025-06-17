import yaml
import os
import ipaddress

NETPLAN_PATHS = [
    "/etc/netplan/",
    "/usr/local/etc/netplan/"
]

def load_netplan_files():
    configs = []
    for path in NETPLAN_PATHS:
        if os.path.isdir(path):
            for fname in os.listdir(path):
                if fname.endswith('.yaml') or fname.endswith('.yml'):
                    with open(os.path.join(path, fname)) as f:
                        try:
                            configs.append(yaml.safe_load(f))
                        except Exception as e:
                            print(f"Warning: Failed to parse {fname}: {e}")
    return configs

def get_all_netplan_interfaces():
    configs = load_netplan_files()
    interfaces = []
    for cfg in configs:
        for net in cfg.get("network", {}).get("ethernets", {}):
            intf = cfg["network"]["ethernets"][net]
            interfaces.append({
                "name": net,
                "type": "ethernet",
                "subnet": intf.get("addresses", ["0.0.0.0/24"])[0].split("/")[0],
                "mask": intf.get("addresses", ["0.0.0.0/24"])[0].split("/")[1],
                "vlan_id": None
            })
        for vlan in cfg.get("network", {}).get("vlans", {}):
            vcfg = cfg["network"]["vlans"][vlan]
            vlan_id = None
            # VLAN names typically end with .<vid>
            if '.' in vlan:
                vlan_id = vlan.split('.')[-1]
            interfaces.append({
                "name": vlan,
                "type": "vlan",
                "subnet": vcfg.get("addresses", ["0.0.0.0/24"])[0].split("/")[0],
                "mask": vcfg.get("addresses", ["0.0.0.0/24"])[0].split("/")[1],
                "vlan_id": vlan_id
            })
    return interfaces

def get_vlan_subnets():
    result = {}
    for intf in get_all_netplan_interfaces():
        if intf["type"] == "vlan" and intf["vlan_id"]:
            result[intf["vlan_id"]] = {
                "subnet": intf["subnet"],
                "mask": intf["mask"]
            }
        elif intf["type"] == "ethernet":
            result["1"] = {
                "subnet": intf["subnet"],
                "mask": intf["mask"]
            }
    return result

def subnet_for_vlan_id(vlan_id):
    subnets = get_vlan_subnets()
    if vlan_id in subnets:
        return subnets[vlan_id]["subnet"]
    return None

def get_vlan_id_for_ip(ip):
    """Match IP address to VLAN ID by subnet"""
    ip = ipaddress.IPv4Address(ip)
    for vlan_id, info in get_vlan_subnets().items():
        net = ipaddress.IPv4Network(f"{info['subnet']}/{info['mask']}", strict=False)
        if ip in net:
            return vlan_id
    return "1"

# Optional: update functions, validation, etc.
def update_netplan_interface(name, new_settings):
    configs = load_netplan_files()
    updated = False
    for cfg in configs:
        for key in ("ethernets", "vlans"):
            if name in cfg.get("network", {}).get(key, {}):
                cfg["network"][key][name].update(new_settings)
                updated = True
    if updated:
        # Save logic as needed (write-back to netplan YAML)
        pass
    return updated

