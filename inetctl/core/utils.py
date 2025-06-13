import os
import subprocess
import json
import typer
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# --- Command Execution and Privileges ---

def run_command(command: list, check: bool = False) -> dict:
    """Runs a shell command and returns its output, stderr, and return code."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=check, timeout=10)
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "returncode": result.returncode}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"Command not found: {command[0]}", "returncode": 127}
    except subprocess.CalledProcessError as e:
        return {"stdout": e.stdout.strip(), "stderr": e.stderr.strip(), "returncode": e.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Command timed out: {' '.join(command)}", "returncode": 124}

def check_root_privileges(action: str = "perform this action"):
    """Exits with an error if the script is not run as root."""
    if os.geteuid() != 0:
        typer.echo(typer.style(f"Error: You must run this command as root to {action}.", fg=typer.colors.RED), err=True)
        raise typer.Exit(code=1)

# --- Config Parsers and Getters ---

def get_host_by_mac(config: Dict, mac_address: str) -> Tuple[Optional[Dict], Optional[int]]:
    """Finds a host in the configuration by its MAC address."""
    mac_lower = mac_address.lower()
    known_hosts = config.get("known_hosts", [])
    for i, host in enumerate(known_hosts):
        if host.get("mac", "").lower() == mac_lower:
            return host, i
    return None, None

def get_network_config_by_id_or_name(config: Dict, identifier: str) -> Optional[Dict]:
    """Finds a network configuration from server_config.json by its id or name."""
    for network in config.get("networks", []):
        if network.get("id") == identifier or network.get("name") == identifier:
            return network
    return None

# --- File and System State Parsers ---

def get_active_leases(leases_file_path_str: str) -> list:
    """Parses the dnsmasq.leases file and returns a simple list of active leases."""
    leases_file_path = Path(leases_file_path_str)
    if not leases_file_path.exists():
        return []
    leases = []
    try:
        with open(leases_file_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if len(parts) >= 4:
                    leases.append({'mac': parts[1].lower(), 'ip': parts[2], 'hostname': parts[3] if parts[3] != '*' else '(unknown)'})
    except IOError as e:
        typer.echo(f"Warning: Could not read leases file at {leases_file_path_str}: {e}", err=True)
    return leases

def get_shorewall_dynamic_blocked() -> List[str]:
    """Parses `shorewall show dynamic` to get a list of currently blocked IPs."""
    result = run_command(["sudo", "shorewall", "show", "dynamic"])
    if result["returncode"] != 0:
        return []
    blocked_ips = []
    lines = result["stdout"].splitlines()
    try:
        start_index = lines.index("Shorewall dynamic blacklists for zone blocked:") + 1
        for line in lines[start_index:]:
            if line.strip() == "": break
            parts = line.split()
            if len(parts) > 0:
                blocked_ips.append(parts[0])
    except ValueError:
        pass
    return blocked_ips

# --- Formatting and Display ---

def print_item_details(item: Dict, title: str):
    """Prints a formatted key-value summary of a dictionary."""
    typer.echo(typer.style(f"\n--- {title} ---", fg=typer.colors.CYAN, bold=True))
    if not item:
        typer.echo("Not found or no details available."); return
    for key, value in item.items():
        key_styled = typer.style(f"{key.replace('_', ' ').capitalize():<25}", fg=typer.colors.WHITE)
        if isinstance(value, bool):
            value_styled = typer.style(str(value), fg=typer.colors.GREEN if value else typer.colors.RED)
        elif isinstance(value, dict) or isinstance(value, list):
            value_styled = json.dumps(value)
        elif value is None:
            value_styled = typer.style("Not set", fg=typer.colors.YELLOW)
        else:
            value_styled = str(value)
        typer.echo(f"{key_styled}: {value_styled}")
    typer.echo("-" * (len(title) + 8))

# --- Traffic Control (QoS) ---

def generate_tc_commands(config: Dict, interface: str, parent_qdisc_id: str = "1:") -> List[str]:
    """Generates a list of tc commands for setting up QoS policies."""
    gs = config.get("global_settings", {})
    qos_policies = gs.get("qos_policies", {})
    if not qos_policies: return ["# No QoS policies defined in config."]
    wan_config = get_network_config_by_id_or_name(config, gs.get("wan_network_id", "wan"))
    if not wan_config or "bandwidth" not in wan_config: return ["# WAN network or bandwidth not configured."]
    upload_rate = wan_config["bandwidth"]["upload_mbit"]
    commands = [
        f"tc qdisc del dev {interface} root 2> /dev/null",
        f"tc qdisc add dev {interface} root handle {parent_qdisc_id} htb default 10",
        f"tc class add dev {interface} parent {parent_qdisc_id} classid {parent_qdisc_id}0 htb rate {upload_rate}mbit ceil {upload_rate}mbit",
    ]
    for policy_name, policy_details in qos_policies.items():
        prio, rate_mbit, ceil_mbit, fw_mark = (policy_details.get(k) for k in ["priority", "guaranteed_mbit", "limit_mbit", "fw_mark"])
        if fw_mark is None: continue
        class_id = f"{parent_qdisc_id}{fw_mark}"
        commands.append(f"tc class add dev {interface} parent {parent_qdisc_id}0 classid {class_id} htb rate {rate_mbit or 1}mbit ceil {ceil_mbit or upload_rate}mbit prio {prio or 99}")
        commands.append(f"tc filter add dev {interface} protocol ip parent {parent_qdisc_id}0 prio {prio or 99} handle {fw_mark} fw classid {class_id}")
    return commands

# --- Network Status ---

def is_host_online(ip: str) -> bool:
    """Pings a host once to check for liveness. Returns True if online, False otherwise."""
    # -c 1: one packet, -W 1: 1-second timeout
    result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True)
    return result.returncode == 0

def _ping_worker(ip: str, results: Dict):
    """Worker function for threading pings."""
    results[ip] = is_host_online(ip)

def check_multiple_hosts_online(ips: List[str]) -> Dict[str, bool]:
    """Pings a list of IP addresses concurrently and returns their online status."""
    threads = []
    results = {}
    for ip in ips:
        thread = threading.Thread(target=_ping_worker, args=(ip, results))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return results