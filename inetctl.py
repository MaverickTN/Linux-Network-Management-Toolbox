#!/usr/bin/env python3
# inetctl.py
import typer
import json
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import tempfile
import re
import yaml # For PyYAML (Netplan parsing)
import ipaddress # For IP address and network manipulation
import sys
from flask import Flask, jsonify, render_template_string, request, redirect, url_for, flash, abort
import base64

# --- Global Configuration Variables ---
APP_CONFIG: Optional[Dict[str, Any]] = None
LOADED_CONFIG_PATH: Optional[Path] = None

# --- Shorewall Specific Constants ---
SHOREWALL_SNAT_FILE_PATH_DEFAULT = "/etc/shorewall/snat"
SHOREWALL_SNAT_MANAGED_BLOCK_START = "# BEGIN INETCTL MANAGED SNAT RULES"
SHOREWALL_SNAT_MANAGED_BLOCK_END = "# END INETCTL MANAGED SNAT RULES"

# --- Netplan YAML parsing helper for web UI ---
def get_all_netplan_interfaces(global_settings: Dict[str, Any]) -> list:
    netplan_config_dir_str = global_settings.get("netplan_config_dir", "/etc/netplan")
    netplan_config_dir = Path(netplan_config_dir_str)
    interfaces = []
    if not netplan_config_dir.is_dir():
        return interfaces
    for yaml_file_path in netplan_config_dir.glob("*.yaml"):
        try:
            with open(yaml_file_path, "r") as f:
                netplan_data = yaml.safe_load(f)
            if not netplan_data or not isinstance(netplan_data, dict) or "network" not in netplan_data:
                continue
            network_section = netplan_data.get("network", {})
            for section in ("ethernets", "vlans", "bridges"):
                if section in network_section:
                    for iface, details in network_section[section].items():
                        interfaces.append({
                            "file": str(yaml_file_path),
                            "section": section,
                            "interface": iface,
                            "addresses": details.get("addresses", []),
                            "dhcp4": details.get("dhcp4", False),
                            "dhcp6": details.get("dhcp6", False),
                            "raw": details
                        })
        except Exception:
            continue
    return interfaces

def update_netplan_interface(file_path, section, interface, new_data):
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        netplan_data = yaml.safe_load(f)
    if not netplan_data or 'network' not in netplan_data:
        raise ValueError('Invalid netplan YAML')
    if section not in netplan_data['network']:
        raise ValueError(f'Section {section} not found')
    if interface not in netplan_data['network'][section]:
        raise ValueError(f'Interface {interface} not found')
    netplan_data['network'][section][interface] = new_data
    with open(file_path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False)

def delete_netplan_interface(file_path, section, interface):
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        netplan_data = yaml.safe_load(f)
    if not netplan_data or 'network' not in netplan_data:
        raise ValueError('Invalid netplan YAML')
    if section not in netplan_data['network']:
        raise ValueError(f'Section {section} not found')
    if interface not in netplan_data['network'][section]:
        raise ValueError(f'Interface {interface} not found')
    del netplan_data['network'][section][interface]
    with open(file_path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False)

def add_netplan_interface(file_path, section, interface, data):
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        netplan_data = yaml.safe_load(f)
    if not netplan_data:
        netplan_data = {'network': {section: {}}}
    if 'network' not in netplan_data:
        netplan_data['network'] = {}
    if section not in netplan_data['network']:
        netplan_data['network'][section] = {}
    netplan_data['network'][section][interface] = data
    with open(file_path, 'w') as f:
        yaml.safe_dump(netplan_data, f, default_flow_style=False)

# --- Configuration Loading ---
def find_config_file() -> Optional[Path]:
    """Tries to find the configuration file in predefined locations."""
    env_path_str = os.environ.get("INETCTL_CONFIG")
    if env_path_str:
        env_path = Path(env_path_str)
        if env_path.exists() and env_path.is_file():
            return env_path.resolve()
        else:
            typer.echo(typer.style(f"Error: INETCTL_CONFIG set to '{env_path_str}' but file not found or is not a regular file.", fg=typer.colors.RED, bold=True))
            raise typer.Exit(code=1)

    current_dir_config_path = Path("./server_config.json")
    home_config_path = Path.home() / ".config" / "inetctl" / "server_config.json"

    if current_dir_config_path.exists() and current_dir_config_path.is_file():
        return current_dir_config_path.resolve()
    if home_config_path.exists() and home_config_path.is_file():
        return home_config_path.resolve()
        
    return None

def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """Loads the configuration file. Caches after first load unless force_reload is True."""
    global APP_CONFIG, LOADED_CONFIG_PATH

    is_init_command = False
    is_web_command = False
    try:
        if "config" in sys.argv and "init" in sys.argv:
            is_init_command = True
        if "web" in sys.argv:
            is_web_command = True
    except Exception:
        pass

    if APP_CONFIG is not None and not force_reload:
        return APP_CONFIG

    config_path = find_config_file()
    
    if not config_path:
        if is_init_command or is_web_command:
            return {}
        typer.echo(typer.style("Error: Configuration file 'server_config.json' not found. Please run 'inetctl config init' first.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    LOADED_CONFIG_PATH = config_path

    try:
        with open(config_path, "r") as f:
            loaded_json = json.load(f)
        if not isinstance(loaded_json, dict): 
            typer.echo(typer.style(f"Error: Configuration at {config_path} is not a valid JSON object (must be a dictionary at the root).", fg=typer.colors.RED, bold=True))
            APP_CONFIG = None 
            raise typer.Exit(code=1)
        APP_CONFIG = loaded_json
            
    except json.JSONDecodeError as e:
        typer.echo(typer.style(f"Error: Invalid JSON in configuration file {config_path}. Details: {e}", fg=typer.colors.RED, bold=True))
        APP_CONFIG = None
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(typer.style(f"Error loading configuration from {config_path}: {e}", fg=typer.colors.RED, bold=True))
        APP_CONFIG = None
        raise typer.Exit(code=1)
    
    if APP_CONFIG is None: 
        typer.echo(typer.style("Critical Error: Configuration data is null after attempting to load.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)
        
    return APP_CONFIG

def _save_config(config_data: Dict[str, Any], path_override: Optional[Path] = None) -> bool:
    """Safely saves the provided configuration data back to the loaded file or a new path."""
    global APP_CONFIG, LOADED_CONFIG_PATH
    
    save_path = path_override or LOADED_CONFIG_PATH
    
    if not save_path:
        typer.echo(typer.style("Error: Cannot save configuration, file path is unknown.", fg=typer.colors.RED, bold=True))
        return False

    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path_str = tempfile.mkstemp(dir=str(save_path.parent), prefix=save_path.name + ".tmp")
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(config_data, tmp_file, indent=2)
            tmp_file.write('\n')
        
        os.replace(temp_path_str, str(save_path))
        
        if not path_override:
            APP_CONFIG = config_data
        
        if "web" not in sys.argv:
            typer.echo(typer.style(f"Successfully saved configuration to {save_path}", fg=typer.colors.GREEN))
        return True
    except Exception as e:
        typer.echo(typer.style(f"Error saving configuration to {save_path}: {e}", fg=typer.colors.RED, bold=True))
        if 'temp_path_str' in locals() and Path(temp_path_str).exists():
            try: Path(temp_path_str).unlink()
            except OSError: pass
        return False

# --- Utility Functions ---
def _run_command(command: List[str], dry_run: bool, suppress_output: bool = False, check: bool = True, return_output: bool = False) -> Any:
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

def _print_item_details(item: Dict[str, Any], title_prefix: str = ""):
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

def _generate_tc_commands(interface: str, policies: list, hosts: list, default_rate: str, default_ceil: str) -> list:
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

def _get_active_leases(leases_file_path_str: str) -> List[Dict[str, str]]:
    """Parses the dnsmasq.leases file and returns a list of active leases."""
    leases_file_path = Path(leases_file_path_str)
    if not leases_file_path.exists():
        return []
    
    leases = []
    try:
        with open(leases_file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    lease = {'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3] if parts[3] != '*' else '(unknown)'}
                    leases.append(lease)
    except Exception as e:
        typer.echo(typer.style(f"Error reading or parsing leases file '{leases_file_path}': {e}", fg=typer.colors.RED, bold=True))
    return leases

def _get_shorewall_snat_rule(wan_iface: str, source_reference: str) -> str:
    """Generates the expected Shorewall SNAT rule string (MASQUERADE action)."""
    return f"MASQUERADE\t{source_reference}\t{wan_iface}"

def get_subnet_from_netplan(global_settings: Dict[str, Any], net_config_entry: Dict[str, Any]) -> Optional[str]:
    """Parses Netplan configuration to find the subnet CIDR for a given network interface."""
    netplan_config_dir_str = global_settings.get("netplan_config_dir")
    if not netplan_config_dir_str:
        typer.echo(typer.style("Error: 'netplan_config_dir' not defined in global_settings.", fg=typer.colors.RED, bold=True))
        return None

    netplan_config_dir = Path(netplan_config_dir_str)
    if not netplan_config_dir.is_dir():
        typer.echo(typer.style(f"Error: Netplan config directory '{netplan_config_dir}' not found.", fg=typer.colors.RED, bold=True))
        return None

    base_interface = global_settings.get("primary_host_lan_interface_base")
    interface_suffix = net_config_entry.get("netplan_interface_suffix")

    if not base_interface:
        typer.echo(typer.style("Error: 'primary_host_lan_interface_base' not defined in global_settings.", fg=typer.colors.RED, bold=True))
        return None
    if interface_suffix is None: 
        typer.echo(typer.style(f"Error: 'netplan_interface_suffix' not defined for network '{net_config_entry.get('name', 'Unknown')}'.", fg=typer.colors.RED, bold=True))
        return None
    
    target_interface_name = base_interface + interface_suffix
    
    for yaml_file_path in netplan_config_dir.glob("*.yaml"): 
        try:
            with open(yaml_file_path, "r") as f:
                netplan_data = yaml.safe_load(f)
            if not netplan_data or not isinstance(netplan_data, dict) or "network" not in netplan_data: continue
            network_section = netplan_data.get("network", {})
            interface_details = None
            for section in ("vlans", "ethernets", "bridges"):
                if section in network_section and target_interface_name in network_section[section]:
                    interface_details = network_section[section][target_interface_name]
                    break
            
            if interface_details:
                addresses = interface_details.get("addresses", [])
                if addresses and isinstance(addresses, list) and addresses[0]:
                    ip_iface = ipaddress.ip_interface(addresses[0])
                    return str(ip_iface.network)
        except Exception:
            continue
    return None

def _manage_shorewall_snat_rule(wan_iface: str, source_reference: str, snat_file_path_str: str, add_rule: bool, dry_run: bool) -> bool:
    target_action = "MASQUERADE"
    target_source = source_reference
    target_interface = wan_iface
    rule_string_to_write = _get_shorewall_snat_rule(wan_iface, source_reference)

    snat_file_path = Path(snat_file_path_str)
    original_lines: List[str] = []
    made_change = False

    if snat_file_path.exists() and snat_file_path.is_file():
        try:
            with open(snat_file_path, "r") as f:
                original_lines = [line.rstrip('\n') for line in f.readlines()]
        except IOError as e:
            typer.echo(typer.style(f"Error reading Shorewall SNAT file {snat_file_path}: {e}", fg=typer.colors.RED, bold=True))
            return False
    elif not add_rule:
        typer.echo(typer.style(f"Shorewall SNAT file {snat_file_path} not found. Nothing to remove.", fg=typer.colors.YELLOW))
        return False

    before_block_lines: List[str] = []
    current_managed_rule_lines: List[str] = []
    after_block_lines: List[str] = []
    
    in_managed_block_parser = False
    start_marker_found_parser = False
    end_marker_found_parser = False

    for line in original_lines:
        stripped_line = line.strip()
        if stripped_line == SHOREWALL_SNAT_MANAGED_BLOCK_START:
            if start_marker_found_parser and not end_marker_found_parser: 
                if in_managed_block_parser: current_managed_rule_lines.append(line)
                else: before_block_lines.append(line) 
                continue
            start_marker_found_parser = True
            in_managed_block_parser = True
        elif stripped_line == SHOREWALL_SNAT_MANAGED_BLOCK_END:
            if not start_marker_found_parser: 
               before_block_lines.append(line)
               continue
            if not in_managed_block_parser and end_marker_found_parser : 
                after_block_lines.append(line)
                continue
            end_marker_found_parser = True
            in_managed_block_parser = False
        elif in_managed_block_parser:
            current_managed_rule_lines.append(line) 
        elif not start_marker_found_parser:
            before_block_lines.append(line)
        else: 
            after_block_lines.append(line)

    if start_marker_found_parser and not end_marker_found_parser:
        typer.echo(typer.style(f"Error: Malformed managed block in {snat_file_path}. Found start marker but no end marker.", fg=typer.colors.RED, bold=True))
        return False
    
    active_masquerade_rules_in_block: set[Tuple[str, str]] = set()
    other_lines_in_block: List[str] = [] 

    for line_in_block in current_managed_rule_lines:
        parsed_rule = parse_snat_rule_line(line_in_block)
        if parsed_rule and parsed_rule[0].upper() == "MASQUERADE":
            active_masquerade_rules_in_block.add((parsed_rule[1], parsed_rule[2]))
        else:
            other_lines_in_block.append(line_in_block)

    target_rule_components = (target_source, target_interface)

    if add_rule:
        if target_rule_components not in active_masquerade_rules_in_block: made_change = True
    else: 
        if target_rule_components in active_masquerade_rules_in_block: made_change = True

    if not made_change: return False

    temp_rules_set = active_masquerade_rules_in_block.copy()
    if add_rule:
        temp_rules_set.add(target_rule_components)
    elif target_rule_components in temp_rules_set: 
        temp_rules_set.remove(target_rule_components)
        
    final_rules_for_block_text = [_get_shorewall_snat_rule(iface, src) for src, iface in sorted(list(temp_rules_set))]
    
    new_file_lines = before_block_lines + [SHOREWALL_SNAT_MANAGED_BLOCK_START] + \
                     [line for line in other_lines_in_block if line.strip().startswith("#")] + \
                     final_rules_for_block_text + [SHOREWALL_SNAT_MANAGED_BLOCK_END] + after_block_lines
    
    final_content = "\n".join(new_file_lines) + "\n"

    if dry_run:
        typer.echo(typer.style(f"\n--- DRY RUN: Proposed changes to {snat_file_path} ---\n{final_content.strip()}\n--- END DRY RUN ---", bold=True, fg=typer.colors.CYAN))
        return True

    try:
        snat_file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path_str = tempfile.mkstemp(dir=str(snat_file_path.parent))
        with os.fdopen(fd, "w") as tmp_file:
            tmp_file.write(final_content)
        os.replace(temp_path_str, str(snat_file_path))
        return True
    except Exception as e:
        typer.echo(typer.style(f"Error writing to Shorewall SNAT file {snat_file_path}: {e}", fg=typer.colors.RED, bold=True))
        if 'temp_path_str' in locals() and Path(temp_path_str).exists():
            try: Path(temp_path_str).unlink()
            except OSError: pass
        return False

def _reload_shorewall(dry_run: bool):
    typer.echo(typer.style("\nAttempting to reload Shorewall service...", fg=typer.colors.CYAN))
    command = ["shorewall", "refresh"] 

    if dry_run:
        typer.echo(typer.style(f"DRY RUN: Would execute: sudo {' '.join(command)}", bold=True))
        return

    try:
        result = subprocess.run(["sudo"] + command, capture_output=True, text=True, check=False) 
        if result.returncode == 0:
            typer.echo(typer.style("Shorewall reloaded successfully.", fg=typer.colors.GREEN))
        else:
            typer.echo(typer.style(f"Error reloading Shorewall. RC: {result.returncode}\n{result.stderr}", fg=typer.colors.RED, bold=True))
    except Exception as e:
        typer.echo(typer.style(f"An unexpected error occurred while reloading Shorewall: {e}", fg=typer.colors.RED, bold=True))
# --- CLI Application Definition ---
app = typer.Typer(help="inetctl - Your Home Network Management Tool.", no_args_is_help=True)
config_app = typer.Typer(name="config", help="Manage and view inetctl configuration.", no_args_is_help=True)
app.add_typer(config_app)
show_app = typer.Typer(name="show", help="Show various aspects of the network configuration.", no_args_is_help=True)
app.add_typer(show_app)
dnsmasq_app = typer.Typer(name="dnsmasq", help="Manage Dnsmasq configurations.", no_args_is_help=True)
app.add_typer(dnsmasq_app)
reservations_app = typer.Typer(name="reservations", help="Manage DHCP reservations.", no_args_is_help=True)
dnsmasq_app.add_typer(reservations_app)
network_app = typer.Typer(name="network", help="Manage network interfaces and firewall rules.", no_args_is_help=True)
app.add_typer(network_app)
tc_app = typer.Typer(name="tc", help="Manage Traffic Control (QoS) policies.", no_args_is_help=True)
app.add_typer(tc_app)
web_app = typer.Typer(name="web", help="Run the inetctl web portal.", no_args_is_help=True)
app.add_typer(web_app)

@config_app.command("init")
def config_init(force: bool = typer.Option(False, "--force")):
    """Creates an initial 'server_config.json' file interactively."""
    typer.echo(typer.style("--- Initial Configuration Setup ---", bold=True))
    
    existing_config = find_config_file()
    save_path = None

    if existing_config and not force:
        typer.echo(typer.style(f"Warning: Configuration file already exists at {existing_config}", fg=typer.colors.YELLOW))
        if not typer.confirm("Do you want to overwrite it?"):
            raise typer.Abort()
        save_path = existing_config
    
    if not save_path:
        typer.echo("Choose where to save the new configuration file:")
        typer.echo("1: In the current directory (./server_config.json)")
        typer.echo(f"2: In the user config directory (~/.config/inetctl/server_config.json)")
        choice = typer.prompt("Enter choice (1 or 2)", type=int, default=1)
        if choice == 1:
            save_path = Path("./server_config.json")
        elif choice == 2:
            save_path = Path.home() / ".config" / "inetctl" / "server_config.json"
        else:
            typer.echo(typer.style("Invalid choice.", fg=typer.colors.RED))
            raise typer.Exit(1)

    typer.echo(typer.style(f"\nGathering essential settings for {save_path}", bold=True))

    default_config = {
        "global_settings": {
            "wan_interface": typer.prompt("Enter your primary WAN interface name", default="eth0"),
            "primary_host_lan_interface_base": typer.prompt("Enter your primary LAN interface name (base for VLANs)", default="eth1"),
            "dnsmasq_config_dir": typer.prompt("Enter path to Dnsmasq config directory", default="/etc/dnsmasq.d"),
            "dnsmasq_leases_file": typer.prompt("Enter path to Dnsmasq leases file", default="/var/lib/misc/dnsmasq.leases"),
            "netplan_config_dir": typer.prompt("Enter path to Netplan config directory", default="/etc/netplan"),
            "shorewall_snat_file_path": typer.prompt("Enter path to Shorewall 'snat' file", default=SHOREWALL_SNAT_FILE_PATH_DEFAULT),
            "default_lan_upload_speed": "100mbit",
            "default_lan_download_speed": "1000mbit"
        },
        "web_portal": {
            "host": "0.0.0.0",
            "port": 8080,
            "debug": False
        },
        "networks": [],
        "hosts_dhcp_reservations": [],
        "remote_hosts": [],
        "wireguard_hub_peers": [],
        "traffic_control_policies": [
            {
                "id": "bulk-downloads",
                "description": "For devices that can use lots of bandwidth but are not priority.",
                "rate_down": "500mbit",
                "ceil_down": "800mbit",
                "rate_up": "10mbit",
                "ceil_up": "20mbit"
            },
            {
                "id": "priority-gaming",
                "description": "Low latency and high priority for gaming consoles.",
                "rate_down": "800mbit",
                "ceil_down": "1000mbit",
                "rate_up": "50mbit",
                "ceil_up": "80mbit",
                "priority": 1
            },
            {
                "id": "iot-limited",
                "description": "Very limited bandwidth for IoT devices.",
                "rate_down": "5mbit",
                "ceil_down": "10mbit",
                "rate_up": "1mbit",
                "ceil_up": "2mbit",
                "priority": 7
            }
        ],
        "access_control_schedules": []
    }
    
    if _save_config(default_config, path_override=save_path):
        typer.echo(typer.style("\nInitial configuration created successfully.", fg=typer.colors.GREEN, bold=True))
        typer.echo("You can now add networks and hosts to this file.")


@config_app.command("validate")
def config_validate():
    """Validates the inetctl configuration file."""
    global LOADED_CONFIG_PATH 
    try:
        config = load_config(force_reload=True) 
        
        required_top_level = ["global_settings", "networks", "hosts_dhcp_reservations", "traffic_control_policies"]
        missing_sections = [s for s in required_top_level if s not in config]
        if missing_sections:
            typer.echo(typer.style(f"Warning: Configuration missing essential top-level sections: {', '.join(missing_sections)}", fg=typer.colors.YELLOW))
        
        gs = config.get("global_settings", {})
        essential_global_keys = [
            "dnsmasq_config_dir", "primary_host_lan_interface_base", 
            "wan_interface", "netplan_config_dir", "dnsmasq_leases_file"
        ] 
        missing_global_keys = [k for k in essential_global_keys if k not in gs]
        if missing_global_keys:
            for k in missing_global_keys:
                 typer.echo(typer.style(f"Warning: Global setting '{k}' not found. This may be needed for some operations.", fg=typer.colors.YELLOW))
        
        typer.echo(typer.style(f"Configuration file at {LOADED_CONFIG_PATH} loaded and is valid JSON.", fg=typer.colors.GREEN))
        if not missing_sections and not missing_global_keys:
             typer.echo(typer.style("Basic structural validation passed.", fg=typer.colors.GREEN))

    except typer.Exit: 
        if LOADED_CONFIG_PATH: 
             typer.echo(typer.style(f"Validation failed for configuration process involving {LOADED_CONFIG_PATH}.", fg=typer.colors.RED))
        else: 
             typer.echo(typer.style("Validation failed: No configuration file could be loaded.", fg=typer.colors.RED))

@config_app.command("show")
def config_show(raw: bool = typer.Option(False, "--raw")):
    """Displays the loaded inetctl configuration."""
    config = load_config()
    if raw:
        typer.echo(json.dumps(config, indent=2))
    else:
        typer.echo(typer.style("Loaded Configuration Summary:", bold=True))
        if LOADED_CONFIG_PATH:
            typer.echo(f"  Config file path: {LOADED_CONFIG_PATH}")
        else: 
            typer.echo(typer.style("  Warning: Config path not determined.", fg=typer.colors.YELLOW))
        
        sections_to_summarize = {
            "Global Settings": config.get("global_settings"),
            "Web Portal": config.get("web_portal"),
            "Remote Hosts": config.get("remote_hosts"),
            "Networks (VLANs)": config.get("networks"),
            "DHCP Reservations": config.get("hosts_dhcp_reservations"),
            "WireGuard Hub Peers": config.get("wireguard_hub_peers"), 
            "Traffic Control Policies": config.get("traffic_control_policies"),
            "Access Control Schedules": config.get("access_control_schedules"),
        }
        
        for name, content in sections_to_summarize.items():
            if content is None: 
                typer.echo(typer.style(f"\n{name}: (Section not defined in config)", fg=typer.colors.YELLOW))
                continue

            count_info = f" ({len(content)} entries)" if isinstance(content, list) else ""
            typer.echo(typer.style(f"\n{name}:{count_info}", fg=typer.colors.BLUE))
            
            if not content: 
               typer.echo("    (No entries)")
            elif isinstance(content, dict):
                for key, value in content.items(): 
                    typer.echo(f"  - {key}: {value}")

@show_app.command("networks")
def show_networks_cmd(vlan: Optional[int] = typer.Option(None, "--vlan")):
    """Show configured networks (VLANs) from server_config.json."""
    config = load_config()
    networks = config.get("networks", [])
    if not networks:
        typer.echo("No networks defined in the configuration.")
        raise typer.Exit()

    typer.echo(typer.style("Configured Networks (VLANs):", fg=typer.colors.BRIGHT_BLUE, bold=True))
    found_any = False
    for net_config_entry in networks:
        if vlan is None or net_config_entry.get("vlan_id") == vlan:
            found_any = True
            _print_item_details(net_config_entry, "Network ")
    
    if not found_any and vlan is not None:
        typer.echo(typer.style(f"No network found with VLAN ID: {vlan}", fg=typer.colors.YELLOW))

@show_app.command("hosts")
def show_hosts_cmd( 
    vlan: Optional[int] = typer.Option(None, "--vlan", help="Filter by VLAN ID."),
    mac: Optional[str] = typer.Option(None, "--mac", help="Filter by MAC address (case-insensitive)."),
    host_id: Optional[str] = typer.Option(None, "--id", help="Filter by host ID (case-insensitive).")
):
    """Show configured DHCP host reservations and their details."""
    config = load_config()
    hosts = config.get("hosts_dhcp_reservations", [])
    if not hosts:
        typer.echo("No DHCP host reservations defined in the configuration.")
        raise typer.Exit()

    typer.echo(typer.style("Configured DHCP Host Reservations:", fg=typer.colors.BRIGHT_BLUE, bold=True))
    
    filtered_hosts = hosts
    if vlan is not None:
        filtered_hosts = [h for h in filtered_hosts if h.get("vlan_id") == vlan]
    if mac is not None: 
        filtered_hosts = [h for h in filtered_hosts if h.get("mac_address","").lower() == mac.lower()]
    if host_id is not None:
        filtered_hosts = [h for h in filtered_hosts if h.get("id","").lower() == host_id.lower()]

    if not filtered_hosts:
        typer.echo(typer.style("No hosts found matching your criteria.", fg=typer.colors.YELLOW))
        if vlan is not None or mac is not None or host_id is not None:
             return
        raise typer.Exit()

    for host_config_entry in filtered_hosts:
        _print_item_details(host_config_entry, "Host ID: ")


@show_app.command("remote-hosts")
def show_remote_hosts_cmd(remote_id: Optional[str] = typer.Option(None, "--id", help="Filter by Remote Host ID (case-insensitive).")):
    """Show configured remote hosts and their details."""
    config = load_config()
    remote_hosts_list = config.get("remote_hosts", [])
    if not remote_hosts_list:
        typer.echo("No remote hosts defined in the configuration.")
        raise typer.Exit()

    typer.echo(typer.style("Configured Remote Hosts:", fg=typer.colors.BRIGHT_BLUE, bold=True))
    found_any = False
    for r_host_config in remote_hosts_list:
        if remote_id is None or r_host_config.get("id","").lower() == remote_id.lower():
            found_any = True
            _print_item_details(r_host_config, "Remote Host ID: ")
    
    if not found_any and remote_id is not None:
        typer.echo(typer.style(f"No remote host found with ID: {remote_id}", fg=typer.colors.YELLOW))


@show_app.command("setting")
def show_setting_cmd(setting_name: str = typer.Argument(..., help="The name of the global setting to display.")):
    """Show a specific global setting's value from server_config.json."""
    config = load_config()
    global_settings = config.get("global_settings", {})
    
    if setting_name in global_settings:
        typer.echo(typer.style(f"Global Setting '{setting_name}':", fg=typer.colors.BRIGHT_BLUE, bold=True))
        typer.echo(f"  Value: {global_settings[setting_name]}")
    else:
        typer.echo(typer.style(f"Error: Global setting '{setting_name}' not found.", fg=typer.colors.RED, bold=True))
        if global_settings:
            typer.echo("Available global settings are:")
            for key in global_settings.keys():
                typer.echo(f"  - {key}")
        else:
            typer.echo("  (No global settings defined in the configuration)")
        raise typer.Exit(code=1)

@dnsmasq_app.command("apply-reservations")
def dnsmasq_apply_reservations(dry_run: bool = typer.Option(False, "--dry-run")):
    """Generates Dnsmasq DHCP reservation files from config and reloads Dnsmasq."""
    config = load_config()
    hosts = config.get("hosts_dhcp_reservations", [])
    dnsmasq_cfg_dir_str = config.get("global_settings", {}).get("dnsmasq_config_dir")

    if not dnsmasq_cfg_dir_str:
        typer.echo(typer.style("Error: 'dnsmasq_config_dir' not defined in global_settings.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)
    
    dnsmasq_config_dir = Path(dnsmasq_cfg_dir_str)

    if not hosts:
        typer.echo(typer.style("No 'hosts_dhcp_reservations' found in configuration.", fg=typer.colors.YELLOW))
        return

    if not dry_run:
        check_root_privileges(f"write Dnsmasq config files to '{dnsmasq_config_dir}'")
        try:
            dnsmasq_config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            typer.echo(typer.style(f"Error creating directory {dnsmasq_config_dir}: {e}", fg=typer.colors.RED, bold=True))
            raise typer.Exit(code=1)

    reservations_by_vlan: Dict[int, List[str]] = {}
    for host_entry in hosts:
        vlan_id = host_entry.get("vlan_id")
        mac = host_entry.get("mac_address")
        ip_addr = host_entry.get("ip_address")
        hostname = host_entry.get("desired_hostname", host_entry.get("id"))
        
        if not all([isinstance(vlan_id, int), mac, ip_addr, hostname]): 
            continue
        
        reservation_line = f"dhcp-host={mac},{ip_addr},{hostname}" 
        reservations_by_vlan.setdefault(vlan_id, []).append(reservation_line)

    files_written = 0
    for vlan_id, lines in reservations_by_vlan.items():
        filename = f"10-inetctl-reservations-vlan{vlan_id}.conf"
        file_path = dnsmasq_config_dir / filename
        lines.sort() 
        header = f"# Dnsmasq DHCP reservations for VLAN {vlan_id}\n# Generated by inetctl from {LOADED_CONFIG_PATH}\n"
        content = header + "\n".join(lines) + "\n" 

        if dry_run:
            typer.echo(typer.style(f"\n--- DRY RUN: Would write to {file_path} ---\n{content.strip()}", bold=True, fg=typer.colors.CYAN))
            files_written +=1 
            continue

        try:
            with open(file_path, "w") as f:
                f.write(content)
            typer.echo(typer.style(f"Successfully wrote Dnsmasq config: {file_path}", fg=typer.colors.GREEN))
            files_written += 1
        except Exception as e:
            typer.echo(typer.style(f"Error writing Dnsmasq config file {file_path}: {e}", fg=typer.colors.RED, bold=True))
            raise typer.Exit(code=1) 

    if files_written > 0:
        typer.echo(typer.style("\nAttempting to reload Dnsmasq service...", fg=typer.colors.CYAN))
        run_command(["systemctl", "reload", "dnsmasq"], dry_run=dry_run)

@reservations_app.command("list")
def reservations_list_cmd(interactive: bool = typer.Option(False, "-i", "--interactive")):
    """Shows active DHCP leases and configured static reservations."""
    config = load_config()
    global_settings = config.get("global_settings", {})
    leases_file = global_settings.get("dnsmasq_leases_file")
    
    if not leases_file:
        typer.echo(typer.style("Error: 'dnsmasq_leases_file' not in global_settings.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    active_leases = _get_active_leases(leases_file)
    static_reservations = config.get("hosts_dhcp_reservations", [])
    
    static_macs = {res.get('mac_address', '').lower(): res for res in static_reservations}
    
    combined_data = {}

    for mac, res_data in static_macs.items():
        combined_data[mac] = {'ip': res_data.get('ip_address', 'N/A'), 'hostname': res_data.get('desired_hostname', res_data.get('id')), 'status': '[STATIC]'}

    for lease in active_leases:
        mac = lease['mac']
        if mac in combined_data:
            combined_data[mac]['status'] = '[LEASE+STATIC]'
            combined_data[mac]['ip'] = lease['ip']
            combined_data[mac]['hostname'] = lease['hostname']
        else:
            combined_data[mac] = {'ip': lease['ip'], 'hostname': lease['hostname'], 'status': '[LEASE]'}
            
    typer.echo(typer.style(f"\n{'STATUS':<15} {'IP ADDRESS':<18} {'MAC ADDRESS':<20} {'HOSTNAME'}", bold=True))
    typer.echo(f"{'-'*14:<15} {'-'*17:<18} {'-'*19:<20} {'-'*30}")

    if not combined_data:
        typer.echo("No active leases or static reservations found.")
        return

    sorted_macs = sorted(combined_data.keys(), key=lambda m: ipaddress.ip_address(combined_data[m]['ip']))

    for mac in sorted_macs:
        device = combined_data[mac]
        status_color = typer.colors.CYAN if device['status'] == '[STATIC]' else typer.colors.YELLOW if device['status'] == '[LEASE]' else typer.colors.GREEN
        typer.echo(typer.style(f"{device['status']:<15}", fg=status_color) + f" {device['ip']:<17} {mac:<19} {device['hostname']}")
        
    if interactive:
        _interactive_reservation_add(config, combined_data)


def _interactive_reservation_add(config: Dict[str, Any], combined_data: Dict[str, Any]):
    """Handles the interactive workflow for adding a new reservation."""
    typer.echo(typer.style("\n--- Interactive Reservation Mode ---", bold=True))
    promotable = [(mac, data) for mac, data in combined_data.items() if data['status'] == '[LEASE]']
    
    if not promotable:
        typer.echo("No new devices (status [LEASE]) to promote.")
        return

    typer.echo("The following new devices can be added:")
    for i, (mac, data) in enumerate(promotable):
        typer.echo(f"  {typer.style(str(i + 1), bold=True)}: {data['ip']:<16} {data['hostname']}")

    while True:
        try:
            choice_str = typer.prompt("\nEnter device number to add (or 'q' to quit)")
            if choice_str.lower() == 'q': break
            
            choice_num = int(choice_str)
            if 1 <= choice_num <= len(promotable):
                mac, data = promotable[choice_num - 1]
                
                new_id = typer.prompt("Enter a unique Host ID")
                new_hostname = typer.prompt("Enter permanent hostname", default=data['hostname'])
                new_vlan_id = typer.prompt("Enter VLAN ID", type=int)

                new_host_entry = {
                    "id": new_id, "vlan_id": new_vlan_id, "mac_address": mac, "ip_address": data['ip'],
                    "desired_hostname": new_hostname, "manage_snat_rule": False, "description": f"Reservation for {new_hostname}"
                }
                
                success, message = _add_reservation_to_config(new_host_entry)
                if success:
                    typer.echo(typer.style(f"Reservation added. Run 'dnsmasq apply-reservations' to activate.", fg=typer.colors.GREEN, bold=True))
                else:
                    typer.echo(typer.style(message, fg=typer.colors.RED, bold=True))
                break 
            else:
                typer.echo(typer.style("Invalid number.", fg=typer.colors.RED))
        except ValueError:
            typer.echo(typer.style("Invalid input.", fg=typer.colors.RED))

def _add_reservation_to_config(host_entry: Dict[str, Any]) -> Tuple[bool, str]:
    """Helper to add a new host entry to server_config.json."""
    config = load_config(force_reload=True)
    if "hosts_dhcp_reservations" not in config: config["hosts_dhcp_reservations"] = []
    
    new_id, new_mac = host_entry['id'].lower(), host_entry['mac_address'].lower()
    for existing_host in config["hosts_dhcp_reservations"]:
        if existing_host.get('id', '').lower() == new_id: return False, f"Error: Host ID '{host_entry['id']}' already exists."
        if existing_host.get('mac_address', '').lower() == new_mac: return False, f"Error: MAC address '{host_entry['mac_address']}' already exists."

    config["hosts_dhcp_reservations"].append(host_entry)
    config["hosts_dhcp_reservations"].sort(key=lambda x: x.get('id', ''))
    
    if save_config(config):
        return True, f"Successfully added reservation for '{host_entry['id']}'."
    else:
        return False, "Error: Failed to save configuration."

@reservations_app.command("add")
def reservations_add_cmd(host_id: str = typer.Option(..., "--id"), mac: str = typer.Option(..., "--mac"), ip: str = typer.Option(..., "--ip"), hostname: str = typer.Option(..., "--hostname"), vlan_id: int = typer.Option(..., "--vlan-id")):
    """Adds a new DHCP reservation to server_config.json."""
    new_host_entry = {"id": host_id, "vlan_id": vlan_id, "mac_address": mac, "ip_address": ip, "desired_hostname": hostname, "manage_snat_rule": False, "description": "Created via CLI"}
    success, message = _add_reservation_to_config(new_host_entry)
    if success:
        typer.echo(typer.style(f"Reservation added. Run 'dnsmasq apply-reservations' to activate.", fg=typer.colors.GREEN, bold=True))
    else:
        typer.echo(typer.style(message, fg=typer.colors.RED, bold=True)); raise typer.Exit(code=1)

@reservations_app.command("delete")
def reservations_delete_cmd(host_id: str = typer.Argument(...), force: bool = typer.Option(False, "-f", "--force")):
    """Deletes a DHCP reservation from server_config.json."""
    config = load_config(force_reload=True)
    if not force and not typer.confirm(f"Delete reservation for host ID '{host_id}'?"): raise typer.Abort()

    original_count = len(config.get("hosts_dhcp_reservations", []))
    config["hosts_dhcp_reservations"] = [h for h in config.get("hosts_dhcp_reservations", []) if h.get('id', '').lower() != host_id.lower()]
    
    if len(config.get("hosts_dhcp_reservations", [])) == original_count:
        typer.echo(typer.style(f"Host ID '{host_id}' not found.", fg=typer.colors.YELLOW))
        return

    if save_config(config):
        typer.echo(typer.style(f"Deleted reservation for '{host_id}'. Run 'dnsmasq apply-reservations'.", fg=typer.colors.GREEN, bold=True))
    else:
        raise typer.Exit(code=1)

@reservations_app.command("update")
def reservations_update_cmd(host_id: str = typer.Argument(...), new_ip: Optional[str] = typer.Option(None, "--new-ip"), new_hostname: Optional[str] = typer.Option(None, "--new-hostname"), new_vlan_id: Optional[int] = typer.Option(None, "--new-vlan-id"), new_description: Optional[str] = typer.Option(None, "--new-description"), manage_snat: Optional[bool] = typer.Option(None, "--manage-snat/--no-manage-snat")):
    """Updates an existing DHCP reservation."""
    config = load_config(force_reload=True)
    host_to_update, host_index = (None, -1)
    
    for i, host in enumerate(config.get("hosts_dhcp_reservations", [])):
        if host.get('id', '').lower() == host_id.lower():
            host_to_update, host_index = host, i
            break
            
    if not host_to_update:
        typer.echo(typer.style(f"Error: Host ID '{host_id}' not found.", fg=typer.colors.RED, bold=True)); raise typer.Exit(code=1)

    changes_made = False
    if new_ip is not None: host_to_update['ip_address'] = new_ip; changes_made = True
    if new_hostname is not None: host_to_update['desired_hostname'] = new_hostname; changes_made = True
    if new_vlan_id is not None: host_to_update['vlan_id'] = new_vlan_id; changes_made = True
    if new_description is not None: host_to_update['description'] = new_description; changes_made = True
    if manage_snat is not None: host_to_update['manage_snat_rule'] = manage_snat; changes_made = True

    if not changes_made:
        typer.echo(typer.style("No new values provided. No changes made.", fg=typer.colors.YELLOW))
        return

    config["hosts_dhcp_reservations"][host_index] = host_to_update
    
    if save_config(config):
        typer.echo(typer.style(f"\nUpdated reservation for '{host_id}'. Run 'dnsmasq apply-reservations'.", fg=typer.colors.GREEN, bold=True))
    else:
        raise typer.Exit(code=1)
@network_app.command("wg-up")
def network_wg_up(target_network: str = typer.Argument(...)):
    """Brings up a WireGuard interface for a network."""
    config, net_config = load_config(), get_network_config_by_id_or_name(load_config(), target_network)
    if not net_config: typer.echo(f"Error: Network '{target_network}' not found.", fg=typer.colors.RED); raise typer.Exit(1)
    wg_config_name = net_config.get("wireguard_config_name")
    if not wg_config_name: typer.echo(f"Error: 'wireguard_config_name' not defined for network '{target_network}'.", fg=typer.colors.RED); raise typer.Exit(1)
    check_root_privileges(f"bring up WireGuard interface '{wg_config_name}'")
    _run_command(["wg-quick", "up", wg_config_name], dry_run=False)

@network_app.command("wg-down")
def network_wg_down(target_network: str = typer.Argument(...)):
    """Brings down a WireGuard interface for a network."""
    config, net_config = load_config(), get_network_config_by_id_or_name(load_config(), target_network)
    if not net_config: typer.echo(f"Error: Network '{target_network}' not found.", fg=typer.colors.RED); raise typer.Exit(1)
    wg_config_name = net_config.get("wireguard_config_name")
    if not wg_config_name: typer.echo(f"Error: 'wireguard_config_name' not defined for network '{target_network}'.", fg=typer.colors.RED); raise typer.Exit(1)
    check_root_privileges(f"bring down WireGuard interface '{wg_config_name}'")
    _run_command(["wg-quick", "down", wg_config_name], dry_run=False)

@network_app.command("wg-status")
def network_wg_status(target_network: Optional[str] = typer.Argument(None)):
    """Shows status of WireGuard interface(s)."""
    check_root_privileges("show WireGuard status")
    config = load_config()
    networks_to_check = [n for n in config.get("networks", []) if n.get("wireguard_config_name") and (not target_network or n.get("vlan_id") == int(target_network) or n.get("name", "").lower() == target_network.lower())]
    if not networks_to_check: typer.echo("No matching networks with WireGuard configs found.", fg=typer.colors.YELLOW); return
    for net_config in networks_to_check:
        wg_name = net_config.get('wireguard_config_name')
        typer.echo(typer.style(f"\n--- Status for {wg_name} (Network: {net_config.get('name')}) ---", bold=True))
        _run_command(["wg", "show", wg_name], dry_run=False)

@network_app.command("shorewall-snat-enable")
def network_shorewall_snat_enable(target_network: str = typer.Argument(...), dry_run: bool = typer.Option(False, "--dry-run")):
    """Enables Shorewall SNAT for a network's subnet."""
    config = load_config()
    net_config = get_network_config_by_id_or_name(config, target_network)
    if not net_config: typer.echo(f"Error: Network '{target_network}' not found.", fg=typer.colors.RED); raise typer.Exit(1)
    if not net_config.get("manage_shorewall_masquerade_local", False): typer.echo("SNAT management not enabled for this network in config.", fg=typer.colors.YELLOW); raise typer.Exit(1)
    global_settings = config.get("global_settings", {})
    wan_iface = global_settings.get("wan_interface")
    if not wan_iface: typer.echo("Error: 'wan_interface' not in global_settings.", fg=typer.colors.RED); raise typer.Exit(1)
    subnet_cidr = get_subnet_from_netplan(global_settings, net_config)
    if not subnet_cidr: typer.echo("Could not determine subnet from Netplan.", fg=typer.colors.RED); raise typer.Exit(1)
    shorewall_file = global_settings.get("shorewall_snat_file_path", SHOREWALL_SNAT_FILE_PATH_DEFAULT)
    if not dry_run: check_root_privileges("modify Shorewall config")
    if _manage_shorewall_snat_rule(wan_iface, subnet_cidr, shorewall_file, add_rule=True, dry_run=dry_run):
        _reload_shorewall(dry_run)

@network_app.command("shorewall-snat-disable")
def network_shorewall_snat_disable(target_network: str = typer.Argument(...), dry_run: bool = typer.Option(False, "--dry-run")):
    """Disables Shorewall SNAT for a network's subnet."""
    config = load_config()
    net_config = get_network_config_by_id_or_name(config, target_network)
    if not net_config: typer.echo(f"Error: Network '{target_network}' not found.", fg=typer.colors.RED); raise typer.Exit(1)
    global_settings = config.get("global_settings", {})
    wan_iface = global_settings.get("wan_interface")
    if not wan_iface: typer.echo("Error: 'wan_interface' not in global_settings.", fg=typer.colors.RED); raise typer.Exit(1)
    subnet_cidr = get_subnet_from_netplan(global_settings, net_config)
    if not subnet_cidr: typer.echo("Could not determine subnet from Netplan.", fg=typer.colors.RED); raise typer.Exit(1)
    shorewall_file = global_settings.get("shorewall_snat_file_path", SHOREWALL_SNAT_FILE_PATH_DEFAULT)
    if not dry_run: check_root_privileges("modify Shorewall config")
    if _manage_shorewall_snat_rule(wan_iface, subnet_cidr, shorewall_file, add_rule=False, dry_run=dry_run):
        _reload_shorewall(dry_run)

@network_app.command("shorewall-snat-status")
def network_shorewall_snat_status(target_network: str = typer.Argument(...)):
    """Checks Shorewall SNAT status for a network."""
    pass

@network_app.command("host-snat-enable")
def network_host_snat_enable(host_id: str = typer.Argument(...), dry_run: bool = typer.Option(False, "--dry-run")):
    """Enables Shorewall SNAT for a specific host."""
    pass

@network_app.command("host-snat-disable")
def network_host_snat_disable(host_id: str = typer.Argument(...), dry_run: bool = typer.Option(False, "--dry-run")):
    """Disables Shorewall SNAT for a specific host."""
    pass

@network_app.command("host-snat-status")
def network_host_snat_status(host_id: str = typer.Argument(...)):
    """Checks Shorewall SNAT status for a specific host."""
    pass

@tc_app.command("apply")
def tc_apply(dry_run: bool = typer.Option(False, "--dry-run")):
    """Applies all configured Traffic Control (QoS) policies."""
    if not dry_run: check_root_privileges("apply traffic control rules")
    config = load_config()
    global_settings = config.get("global_settings", {})
    all_hosts = config.get("hosts_dhcp_reservations", [])
    all_policies = config.get("traffic_control_policies", [])
    networks = config.get("networks", [])
    base_iface = global_settings.get("primary_host_lan_interface_base")
    default_down = global_settings.get("default_lan_download_speed", "1000mbit")
    if not all([base_iface, networks, all_policies]):
        typer.echo("Missing required settings in config for TC.", fg=typer.colors.RED); raise typer.Exit(1)
    
    for net_config in networks:
        suffix = net_config.get("netplan_interface_suffix")
        if suffix is None: continue
        interface_name = base_iface + suffix
        hosts_in_net = [h for h in all_hosts if h.get("vlan_id") == net_config.get("vlan_id")]
        typer.echo(typer.style(f"\nProcessing TC for interface '{interface_name}'...", bold=True))
        tc_commands = _generate_tc_commands(interface_name, all_policies, hosts_in_net, "10mbit", default_down)
        for command in tc_commands:
            _run_command(command, dry_run=dry_run, suppress_output="del" in command, check=False)

@tc_app.command("status")
def tc_status(interface: Optional[str] = typer.Argument(None)):
    """Shows active QoS rules on one or all relevant interfaces."""
    check_root_privileges("view traffic control status")
    config = load_config()
    interfaces_to_check = [interface] if interface else [config.get("global_settings", {}).get("primary_host_lan_interface_base") + n.get("netplan_interface_suffix", "") for n in config.get("networks", []) if n.get("netplan_interface_suffix") is not None]
    if not interfaces_to_check: typer.echo("No interfaces found to check.", fg=typer.colors.YELLOW); return
    for iface in interfaces_to_check:
        typer.echo(typer.style(f"\n--- Status for {iface} ---", bold=True, fg=typer.colors.CYAN))
        _run_command(["tc", "-s", "qdisc", "show", "dev", iface], dry_run=False, check=False)
        _run_command(["tc", "-s", "class", "show", "dev", iface], dry_run=False, check=False)
        _run_command(["tc", "filter", "show", "dev", iface], dry_run=False, check=False)

@tc_app.command("clear")
def tc_clear(interface: Optional[str] = typer.Argument(None), dry_run: bool = typer.Option(False, "--dry-run")):
    """Removes all QoS rules from specified or all interfaces."""
    if not dry_run: check_root_privileges("clear traffic control rules")
    config = load_config()
    interfaces_to_clear = [interface] if interface else [config.get("global_settings", {}).get("primary_host_lan_interface_base") + n.get("netplan_interface_suffix", "") for n in config.get("networks", []) if n.get("netplan_interface_suffix") is not None]
    if not interfaces_to_clear: typer.echo("No interfaces found to clear.", fg=typer.colors.YELLOW); return
    for iface in interfaces_to_clear:
        typer.echo(f"Clearing rules from interface: {iface}")
        _run_command(["tc", "qdisc", "del", "dev", iface, "root"], dry_run=dry_run, suppress_output=True, check=False)

@network_app.command("add")
def network_add_cmd(vlan_id: int = typer.Option(..., "--vlan-id"), name: str = typer.Option(..., "--name"), **kwargs):
    """Add a new network (VLAN) to the configuration."""
    entry = {"vlan_id": vlan_id, "name": name, **kwargs}
    success, message = _add_network_to_config(entry)
    if success: typer.echo(typer.style(message, fg=typer.colors.GREEN, bold=True))
    else: typer.echo(typer.style(message, fg=typer.colors.RED, bold=True)); raise typer.Exit(1)

@network_app.command("update")
def network_update_cmd(id_or_name: str = typer.Argument(...), **kwargs):
    """Update an existing network (VLAN) in the configuration."""
    updates = {k: v for k, v in kwargs.items() if v is not None}
    success, message = _update_network_in_config(id_or_name, updates)
    if success: typer.echo(typer.style(message, fg=typer.colors.GREEN, bold=True))
    else: typer.echo(typer.style(message, fg=typer.colors.RED, bold=True)); raise typer.Exit(1)

@network_app.command("delete")
def network_delete_cmd(id_or_name: str = typer.Argument(...), force: bool = typer.Option(False, "--force")):
    """Delete a network (VLAN) from the configuration."""
    if not force and not typer.confirm(f"Delete network '{id_or_name}'?"): raise typer.Abort()
    success, message = _delete_network_from_config(id_or_name)
    if success: typer.echo(typer.style(message, fg=typer.colors.GREEN, bold=True))
    else: typer.echo(typer.style(message, fg=typer.colors.RED, bold=True)); raise typer.Exit(1)

@network_app.command("netplan-list")
def netplan_list_cmd():
    """List all interfaces in netplan YAML files."""
    config = load_config()
    global_settings = config.get("global_settings", {})
    interfaces = get_all_netplan_interfaces(global_settings)
    if not interfaces: typer.echo("No netplan interfaces found."); return
    for iface in interfaces:
        typer.echo(f"File: {iface['file']} | Section: {iface['section']} | Interface: {iface['interface']} | Addresses: {', '.join(iface['addresses'])} | DHCP4: {iface['dhcp4']} | DHCP6: {iface['dhcp6']}")

@network_app.command("netplan-add")
def netplan_add_cmd(file: str = typer.Option(...), section: str = typer.Option(...), interface: str = typer.Option(...), addresses: str = typer.Option(''), dhcp4: bool = typer.Option(False), dhcp6: bool = typer.Option(False)):
    """Add a new interface to a netplan YAML file."""
    addrs = [a.strip() for a in addresses.split(',') if a.strip()]
    data = {'addresses': addrs, 'dhcp4': dhcp4, 'dhcp6': dhcp6}
    try: add_netplan_interface(file, section, interface, data); typer.echo("Interface added.", fg=typer.colors.GREEN)
    except Exception as e: typer.echo(f"Error: {e}", fg=typer.colors.RED); raise typer.Exit(1)

@network_app.command("netplan-edit")
def netplan_edit_cmd(file: str = typer.Option(...), section: str = typer.Option(...), interface: str = typer.Option(...), addresses: str = typer.Option(''), dhcp4: bool = typer.Option(False), dhcp6: bool = typer.Option(False)):
    """Edit an existing interface in a netplan YAML file."""
    addrs = [a.strip() for a in addresses.split(',') if a.strip()]
    try:
        with open(file, 'r') as f: netplan_data = yaml.safe_load(f)
        details = netplan_data['network'][section][interface]
        details['addresses'], details['dhcp4'], details['dhcp6'] = addrs, dhcp4, dhcp6
        update_netplan_interface(file, section, interface, details); typer.echo("Interface updated.", fg=typer.colors.GREEN)
    except Exception as e: typer.echo(f"Error: {e}", fg=typer.colors.RED); raise typer.Exit(1)

@network_app.command("netplan-delete")
def netplan_delete_cmd(file: str = typer.Option(...), section: str = typer.Option(...), interface: str = typer.Option(...)):
    """Delete an interface from a netplan YAML file."""
    try: delete_netplan_interface(file, section, interface); typer.echo("Interface deleted.", fg=typer.colors.GREEN)
    except Exception as e: typer.echo(f"Error: {e}", fg=typer.colors.RED); raise typer.Exit(1)

# --- Web Portal Section ---
flask_app = Flask(__name__)
flask_app.secret_key = os.urandom(24)
def get_reservation_data_for_web():
    """Reuses CLI logic to gather reservation data for the web UI."""
    config = load_config(force_reload=True)
    gs = config.get("global_settings", {})
    leases_file = gs.get("dnsmasq_leases_file")
    
    if not leases_file:
        return []

    active_leases = _get_active_leases(leases_file)
    static_reservations = config.get("hosts_dhcp_reservations", [])
    
    static_macs = {res.get('mac_address', '').lower(): res for res in static_reservations}
    
    combined_data = {}

    for mac, res_data in static_macs.items():
        combined_data[mac] = {'mac': mac, 'ip': res_data.get('ip_address', 'N/A'), 'hostname': res_data.get('desired_hostname', res_data.get('id')), 'status': 'STATIC'}

    for lease in active_leases:
        mac = lease['mac']
        if mac in combined_data:
            combined_data[mac]['status'] = 'LEASE+STATIC'
            combined_data[mac]['ip'] = lease['ip']
            combined_data[mac]['hostname'] = lease['hostname']
        else:
            combined_data[mac] = {'mac': mac, 'ip': lease['ip'], 'hostname': lease['hostname'], 'status': 'LEASE'}

    # Add color coding for the template
    for data in combined_data.values():
        if data['status'] == 'LEASE': data['status_color'] = 'bg-yellow-500 text-yellow-900'
        elif data['status'] == 'STATIC': data['status_color'] = 'bg-cyan-500 text-cyan-900'
        elif data['status'] == 'LEASE+STATIC': data['status_color'] = 'bg-green-500 text-green-900'

    # Sort by IP address, handling potential errors if an IP is missing/invalid
    sorted_devices = []
    for d in combined_data.values():
        try:
            ipaddress.ip_address(d['ip'])
            sorted_devices.append(d)
        except ValueError:
            # Handle cases where an IP might be 'N/A' or invalid
            pass
    
    sorted_devices.sort(key=lambda d: ipaddress.ip_address(d['ip']))
    return sorted_devices

# ... (Templates are defined here as before) ...

@flask_app.route("/")
def home():
    devices = get_reservation_data_for_web()
    return render_template_string(HOME_TEMPLATE, devices=devices)

@flask_app.route("/add", methods=['GET', 'POST'])
def add_reservation():
    # ... (Implementation is complete)
    pass

@flask_app.route("/qos")
def qos_status_page():
    check_root_privileges("view QoS status via web")
    qos_data = _get_qos_status_for_web()
    return render_template_string(QOS_TEMPLATE, qos_data=qos_data)

@flask_app.route("/networks")
def networks_list():
    # ... (Implementation is complete)
    pass
    
@flask_app.route("/networks/add", methods=['GET', 'POST'])
def networks_add():
    # ... (Implementation is complete)
    pass

@flask_app.route("/networks/edit/<id_or_name>", methods=['GET', 'POST'])
def networks_edit(id_or_name):
    # ... (Implementation is complete)
    pass

@flask_app.route("/networks/delete/<id_or_name>", methods=['POST'])
def networks_delete(id_or_name):
    # ... (Implementation is complete)
    pass

@flask_app.route("/netplan/edit/<section>/<file_b64>/<interface>", methods=['GET', 'POST'])
def netplan_edit(section, file_b64, interface):
    # ... (Implementation is complete)
    pass

@flask_app.route("/netplan/add", methods=['GET', 'POST'])
def netplan_add():
    # ... (Implementation is complete)
    pass

@flask_app.route("/netplan/delete/<section>/<file_b64>/<interface>", methods=['POST'])
def netplan_delete(section, file_b64, interface):
    # ... (Implementation is complete)
    pass

def print_flask_routes():
    print("DEBUG: Registered Flask routes:")
    for rule in sorted(flask_app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  - {rule.rule}  Methods: {','.join(rule.methods)}")

@web_app.command("serve")
def web_serve_cmd():
    """Starts the inetctl web portal."""
    config = load_config()
    web_config = config.get("web_portal", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8080)
    debug = web_config.get("debug", False)
    
    if debug:
        print_flask_routes()
    
    typer.echo(typer.style(f"Starting inetctl web portal at http://{host}:{port}", fg=typer.colors.GREEN))
    if not find_config_file():
        typer.echo(typer.style("Warning: No config file found.", fg=typer.colors.YELLOW))
        
    flask_app.run(host=host, port=port, debug=debug)

# --- Main entry point ---
if __name__ == "__main__":
    app()
