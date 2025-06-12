import os
import subprocess
import typer
import ipaddress
import platform
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

def run_command(command: List[str], dry_run: bool, suppress_output: bool = False, check: bool = True, return_output: bool = False) -> Any:
    """Helper to run a system command. Can now optionally return output."""
    if dry_run:
        typer.echo(typer.style(f"DRY RUN: Would execute: sudo {' '.join(command)}", fg=typer.colors.CYAN))
        return True if not return_output else ""
    
    try:
        result = subprocess.run(["sudo"] + command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            if return_output:
                return result.stdout
            if not suppress_output and result.stdout:
                typer.echo(result.stdout)
            return True
        else:
            if check:
                if not suppress_output:
                    typer.echo(typer.style(f"Error executing: {' '.join(command)}", fg=typer.colors.RED))
                    if result.stderr:
                        typer.echo(typer.style(result.stderr, fg=typer.colors.RED))
            return False if not return_output else result.stderr
    except Exception as e:
        if not suppress_output:
            typer.echo(typer.style(f"Failed to execute command '{' '.join(command)}': {e}", fg=typer.colors.RED, bold=True))
        return False if not return_output else str(e)

def is_host_online(ip: str) -> bool:
    """
    Performs a quick ping to check if a host is online.
    Returns True if online, False otherwise.
    """
    if not ip or ip == 'N/A':
        return False
    try:
        param_count = "-n" if platform.system() == "Windows" else "-c"
        param_timeout = "-w" if platform.system() == "Windows" else "-W"
        timeout_val = "1000" if platform.system() == "Windows" else "1"
        command = ["ping", param_count, "1", param_timeout, timeout_val, ip]
        return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except Exception:
        return False

def check_multiple_hosts_online(ip_list: List[str]) -> Dict[str, bool]:
    """
    Pings a list of IP addresses concurrently and returns their online status.
    """
    online_statuses = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ip = {executor.submit(is_host_online, ip): ip for ip in ip_list}
        for future in future_to_ip:
            ip = future_to_ip[future]
            try:
                online_statuses[ip] = future.result()
            except Exception:
                online_statuses[ip] = False
    return online_statuses

def check_root_privileges(action_description: str):
    """Checks for root privileges and exits if not available."""
    if os.geteuid() != 0:
        typer.echo(typer.style(f"Error: Root privileges are required to {action_description}.", fg=typer.colors.RED, bold=True))
        typer.echo("Please try running this command using 'sudo'.")
        raise typer.Exit(code=1)

def get_network_config_by_id_or_name(config: Dict[str, Any], id_or_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific network configuration entry by its VLAN ID or Name."""
    networks = config.get("networks", [])
    try:
        target_vlan_id = int(id_or_name)
        for net_config in networks:
            if net_config.get("vlan_id") == target_vlan_id:
                return net_config
    except ValueError:
        for net_config in networks:
            if net_config.get("name", "").lower() == id_or_name.lower():
                return net_config
    return None

def get_host_config_by_id(config: Dict[str, Any], host_id_to_find: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific host configuration entry by its ID from 'hosts_dhcp_reservations'."""
    hosts_reservations = config.get("hosts_dhcp_reservations", [])
    for host_config in hosts_reservations:
        if host_config.get("id", "").lower() == host_id_to_find.lower():
            return host_config
    return None

def print_item_details(item: Dict[str, Any], title_prefix: str = ""):
    """Helper to print details of a dictionary item from server_config.json."""
    item_id_keys = ["id", "vlan_id", "name"] 
    item_id_val = "Unknown Item"
    title_extra = ""

    for key in item_id_keys:
        if item.get(key) is not None:
            item_id_val = str(item.get(key))
            break
    
    if "name" in item and item['name'] != item_id_val:
        title_extra += f" (Name: {item['name']})"
    
    if "vlan_id" in item and str(item['vlan_id']) != item_id_val and "name" in item: 
         title = f"{title_prefix}{item.get('name', '')} (VLAN ID: {item.get('vlan_id')})"
    else:
        title = f"{title_prefix}{item_id_val}{title_extra}"

    typer.echo(typer.style(f"\n{title}:", bold=True))
    for key, value in item.items():
        if key == "id" and str(value) == item_id_val and title.startswith(title_prefix + item_id_val):
            continue
        if key == "name" and str(value) == item.get('name') and title_extra and f"(Name: {str(value)})" in title_extra :
            continue
        if key == "vlan_id" and str(value) == str(item.get('vlan_id')) and f"(VLAN ID: {str(value)})" in title:
             continue
        typer.echo(f"  {key.replace('_', ' ').title()}: {value}")

def get_active_leases(leases_file_path_str: str, static_reservations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parses the dnsmasq.leases file and returns a list of active leases."""
    leases_file_path = Path(leases_file_path_str)
    leases = []
    if not leases_file_path.exists():
        return leases
    
    try:
        with open(leases_file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    lease = {'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3] if parts[3] != '*' else '(unknown)'}
                    leases.append(lease)
    except Exception as e:
        typer.echo(typer.style(f"Warning: Could not read or parse leases file '{leases_file_path}': {e}", fg=typer.colors.YELLOW, bold=True))
    
    return leases

def generate_tc_commands(interface: str, policies: list, hosts: list, default_rate: str, default_ceil: str) -> list:
    """Generates the list of tc commands to apply QoS policies based on config."""
    commands = []
    
    commands.append(['tc', 'qdisc', 'del', 'dev', interface, 'root'])
    commands.append(['tc', 'qdisc', 'add', 'dev', interface, 'root', 'handle', '1:', 'htb', 'default', '30'])
    commands.append(['tc', 'class', 'add', 'dev', interface, 'parent', '1:', 'classid', '1:1', 'htb', 'rate', default_ceil])
    
    policy_map = {}
    for i, policy in enumerate(policies):
        classid = f"1:{10 + i}"
        policy_id = policy.get("id")
        if not policy_id: continue
        policy_map[policy_id] = classid
        rate = policy.get("rate_down", "1mbit")
        ceil = policy.get("ceil_down", rate)
        prio = policy.get("priority", 5)
        commands.append(['tc', 'class', 'add', 'dev', interface, 'parent', '1:1', 'classid', classid, 'htb', 'rate', rate, 'ceil', ceil, 'prio', str(prio)])

    commands.append(['tc', 'class', 'add', 'dev', interface, 'parent', '1:1', 'classid', '1:30', 'htb', 'rate', default_rate, 'ceil', default_ceil, 'prio', '7'])

    for host in hosts:
        policy_id = host.get("tc_policy_id")
        ip_str = host.get("ip_address")
        if policy_id and ip_str and policy_id in policy_map:
            classid_for_host = policy_map[policy_id]
            try:
                ipaddress.ip_address(ip_str)
                commands.append(['tc', 'filter', 'add', 'dev', interface, 'parent', '1:', 'protocol', 'ip', 'prio', '1', 'u32', 'match', 'ip', 'dst', f'{ip_str}/32', 'flowid', classid_for_host])
            except ValueError:
                typer.echo(f"Warning: Skipping TC rule for host '{host.get('id')}' due to invalid IP '{ip_str}'.", err=True)
                
    return commands

def get_subnet_from_netplan(global_settings: Dict[str, Any], net_config_entry: Dict[str, Any], silent: bool = False) -> Optional[str]:
    """
    Parses Netplan configuration to find the subnet CIDR for a given network interface.
    The 'silent' flag suppresses diagnostic output for web UI usage.
    """
    netplan_config_dir_str = global_settings.get("netplan_config_dir")
    if not netplan_config_dir_str:
        if not silent: typer.echo(typer.style("Error: 'netplan_config_dir' not defined in global_settings.", fg=typer.colors.RED, bold=True))
        return None

    netplan_config_dir = Path(netplan_config_dir_str)
    if not netplan_config_dir.is_dir():
        if not silent: typer.echo(typer.style(f"Error: Netplan config directory '{netplan_config_dir}' not found.", fg=typer.colors.RED, bold=True))
        return None

    base_interface = global_settings.get("primary_host_lan_interface_base")
    interface_suffix = net_config_entry.get("netplan_interface_suffix")

    if not base_interface or interface_suffix is None:
        return None
    
    target_interface_name = base_interface + interface_suffix

    for yaml_file_path in netplan_config_dir.glob("*.yaml"):
        try:
            with open(yaml_file_path, "r") as f:
                netplan_data = yaml.safe_load(f)
            if not netplan_data or "network" not in netplan_data: continue

            network_section = netplan_data.get("network", {})
            for section_key in ("vlans", "ethernets", "bridges"):
                if target_interface_name in network_section.get(section_key, {}):
                    interface_details = network_section[section_key][target_interface_name]
                    addresses = interface_details.get("addresses", [])
                    if addresses and addresses[0]:
                        ip_iface = ipaddress.ip_interface(addresses[0])
                        return str(ip_iface.network)
        except Exception:
            continue
    return None
