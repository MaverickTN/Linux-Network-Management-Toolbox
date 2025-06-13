import tempfile
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set

ACCOUNTING_MANAGED_BLOCK_START = "# BEGIN INETCTL MANAGED ACCOUNTING"
ACCOUNTING_MANAGED_BLOCK_END = "# END INETCTL MANAGED ACCOUNTING"

def generate_accounting_config(active_hosts: List[Dict[str, Any]]) -> str:
    """
    Generates the content for the Shorewall accounting file using the correct,
    modern, section-based format.
    """
    if not active_hosts:
        return "?SECTION FORWARD\n"

    all_lines = ["?SECTION FORWARD"]
    processed_macs = set()

    for host in active_hosts:
        mac_sanitized = host.get("mac", "").replace(":", "")
        ip_addr = host.get("ip")
        
        if not mac_sanitized or not ip_addr:
            continue
        
        chain_name = f"acct_{mac_sanitized}"
        
        # Only create the chain definition ONCE per unique MAC address.
        if mac_sanitized not in processed_macs:
            all_lines.append(f"# Rules for device {host.get('hostname', mac_sanitized)}")
            # ACTION is COUNT, CHAIN is our custom chain. This defines the chain and a simple counting rule.
            all_lines.append(f"COUNT\t{chain_name}")
            processed_macs.add(mac_sanitized)

        # The ACTION is the chain name, which creates a JUMP from the FORWARD chain to our custom chain.
        # Download Traffic to Host
        all_lines.append(f"{chain_name}\t-\t{ip_addr}")
        # Upload Traffic from Host
        all_lines.append(f"{chain_name}\t{ip_addr}\t-")
        all_lines.append("#") # Separator for readability

    return "\n".join(all_lines)


def write_shorewall_file(content: str, file_path_str: str, start_marker: str, end_marker: str, dry_run: bool) -> bool:
    """A generic and robust function to write content into a managed block in a Shorewall file."""
    file_path = Path(file_path_str)
    
    original_lines = []
    if file_path.exists():
        try:
            with open(file_path, "r") as f:
                original_lines = f.read().splitlines()
        except IOError as e:
            print(f"Error reading file {file_path_str}: {e}")
            return False

    before_block, after_block = [], []
    in_managed_block, start_found = False, False
    for line in original_lines:
        if line.strip() == start_marker:
            in_managed_block = True
            start_found = True
        elif line.strip() == end_marker:
            in_managed_block = False
            continue
        if not start_found:
            before_block.append(line)
        elif not in_managed_block:
            after_block.append(line)

    new_content_lines = before_block
    if not start_found:
        new_content_lines.extend(original_lines)
        
    new_content_lines.append(f"\n{start_marker}")
    if content:
        new_content_lines.extend(content.splitlines())
    new_content_lines.append(end_marker)
    if start_found:
        new_content_lines.extend(after_block)

    final_content = "\n".join(new_content_lines) + "\n"

    if dry_run:
        print(f"\n--- DRY RUN: Proposed changes to {file_path_str} ---\n{final_content.strip()}\n--- END DRY RUN ---")
        return True

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path_str = tempfile.mkstemp(dir=str(file_path.parent))
        with os.fdopen(fd, "w") as tmp_file:
            tmp_file.write(final_content)
        os.replace(temp_path_str, str(file_path))
        return True
    except Exception as e:
        print(f"Error writing to {file_path_str}: {e}")
        if 'temp_path_str' in locals() and os.path.exists(temp_path_str):
            os.remove(temp_path_str)
        return False

def get_currently_blocked_ips(zone: str) -> Set[str]:
    """
    Executes 'shorewall show dynamic' and parses the output to get a set of
    IPs currently in the specified dynamic zone.
    """
    blocked_ips = set()
    try:
        result = subprocess.run(
            ["sudo", "shorewall", "show", "dynamic"],
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            return set()

        in_zone = False
        for line in result.stdout.splitlines():
            if line.strip().startswith(f"Shorewall dynamic blacklist for zone {zone}"):
                in_zone = True
                continue
            if in_zone:
                if "TOTAL" in line or not line.strip():
                    in_zone = False
                    continue
                parts = line.strip().split()
                if len(parts) > 0:
                    blocked_ips.add(parts[0])
    except FileNotFoundError:
        return set()
    return blocked_ips