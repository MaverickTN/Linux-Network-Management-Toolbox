import json
from datetime import datetime, timedelta

CONFIG_FILE = "/etc/inetctl/server_config.json"  # Update path if needed

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_host_schedule(hostname):
    config = load_config()
    for host in config.get("known_hosts", []):
        if host.get("hostname") == hostname:
            return host.get("schedules", [])
    return []

def set_host_schedule(hostname, schedules):
    config = load_config()
    for host in config.get("known_hosts", []):
        if host.get("hostname") == hostname:
            host["schedules"] = schedules
            break
    save_config(config)

def is_overlap(new_start, new_end, existing_schedules):
    """Return True if new block overlaps with any existing schedule blocks."""
    new_start = datetime.fromisoformat(new_start)
    new_end = datetime.fromisoformat(new_end)
    for sched in existing_schedules:
        s_start = datetime.fromisoformat(sched["start"])
        s_end = datetime.fromisoformat(sched["end"])
        if (new_start < s_end) and (new_end > s_start):
            return True
    return False

def add_schedule_block(hostname, new_block):
    """
    Add a schedule block to the given host, preventing overlap.
    new_block: dict with 'start' and 'end' (ISO8601)
    """
    schedules = get_host_schedule(hostname)
    if is_overlap(new_block["start"], new_block["end"], schedules):
        raise ValueError("Schedule block overlaps with existing block.")
    schedules.append(new_block)
    set_host_schedule(hostname, schedules)
    return True

def remove_schedule_block(hostname, block_index):
    schedules = get_host_schedule(hostname)
    if 0 <= block_index < len(schedules):
        schedules.pop(block_index)
        set_host_schedule(hostname, schedules)
        return True
    return False

def next_scheduled_block(hostname):
    schedules = get_host_schedule(hostname)
    now = datetime.now()
    future = [
        sched for sched in schedules
        if datetime.fromisoformat(sched["start"]) > now
    ]
    return sorted(future, key=lambda s: s["start"])[0] if future else None
