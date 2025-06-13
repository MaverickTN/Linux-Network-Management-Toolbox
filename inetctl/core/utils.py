import os
import subprocess
import json
import typer
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

def run_command(command: list, check: bool = False) -> dict:
    """Runs a shell command and returns its output, stderr, and return code."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check,
            timeout=10
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "returncode": 127,
        }
    except subprocess.CalledProcessError as e:
        return {
            "stdout": e.stdout.strip(),
            "stderr": e.stderr.strip(),
            "returncode": e.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out: {' '.join(command)}",
            "returncode": 124,
        }


def check_root_privileges(action: str = "perform this action"):
    """Exits with an error if the script is not run as root."""
    if os.geteuid() != 0:
        typer.echo(
            typer.style(f"Error: You must run this command as root to {action}.", fg=typer.colors.RED),
            err=True,
        )
        raise typer.Exit(code=1)


def get_host_by_mac(config: Dict, mac_address: str) -> Tuple[Optional[Dict], Optional[int]]:
    """
    Finds a host in the configuration by its MAC address.

    Args:
        config: The loaded server_config.json dictionary.
        mac_address: The MAC address to search for.

    Returns:
        A tuple containing the host dictionary (or None) and its index (or None).
    """
    mac_lower = mac_address.lower()
    known_hosts = config.get("known_hosts", [])
    for i, host in enumerate(known_hosts):
        if host.get("mac", "").lower() == mac_lower:
            return host, i
    return None, None


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
                    leases.append({
                        'mac': parts[1].lower(),
                        'ip': parts[2],
                        'hostname': parts[3] if parts[3] != '*' else '(unknown)'
                    })
    except IOError as e:
        typer.echo(f"Warning: Could not read leases file at {leases_file_path_str}: {e}", err=True)

    return leases


def get_shorewall_dynamic_blocked() -> List[str]:
    """
    Parses the output of `shorewall show dynamic` to get a list of currently blocked IPs.
    """
    result = run_command(["sudo", "shorewall", "show", "dynamic"])
    if result["returncode"] != 0:
        typer.echo("Warning: Could not get dynamic list from Shorewall.", err=True)
        return []

    blocked_ips = []
    lines = result["stdout"].splitlines()
    # Find the line for the 'blocked' zone
    try:
        start_index = lines.index("Shorewall dynamic blacklists for zone blocked:") + 1
        for line in lines[start_index:]:
            if line.strip() == "":
                break # End of this section
            parts = line.split()
            if len(parts) > 0:
                blocked_ips.append(parts[0])
    except ValueError:
        # Section not found, which is fine if no IPs are dynamically blocked
        pass

    return blocked_ips