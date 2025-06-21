import datetime
from inetctl.core.config_loader import load_config, save_config

def list_hosts_with_schedules():
    config = load_config()
    return list(config.get("schedules", {}).keys())

def get_host_schedules(host):
    config = load_config()
    return config.get("schedules", {}).get(host, [])

def validate_new_block(host, new_block):
    """
    Ensure new block does not overlap with existing for the host.
    Returns (True/False, message)
    """
    blocks = get_host_schedules(host)
    ns, ne = (
        datetime.datetime.fromisoformat(new_block["start"]),
        datetime.datetime.fromisoformat(new_block["end"])
    )
    for b in blocks:
        bs = datetime.datetime.fromisoformat(b["start"])
        be = datetime.datetime.fromisoformat(b["end"])
        # Overlap if start < be and end > bs
        if ns < be and ne > bs:
            return False, f"Overlaps with block {bs} to {be}"
    return True, ""

def add_schedule_block(host, block):
    config = load_config()
    schedules = config.setdefault("schedules", {})
    host_blocks = schedules.setdefault(host, [])
    host_blocks.append(block)
    # Sort by start time
    host_blocks.sort(key=lambda x: x["start"])
    save_config(config)

def remove_schedule_block(host, idx):
    config = load_config()
    host_blocks = config.get("schedules", {}).get(host, [])
    if 0 <= idx < len(host_blocks):
        del host_blocks[idx]
        save_config(config)
        return True
    return False

def find_next_available_block(host, after_dt=None):
    """
    Suggests the next free time after 'after_dt' (datetime), returns (start, end) or None
    """
    blocks = get_host_schedules(host)
    if not blocks:
        return None
    blocks = sorted(blocks, key=lambda b: b["start"])
    if not after_dt:
        after_dt = datetime.datetime.now()
    for b in blocks:
        bs = datetime.datetime.fromisoformat(b["start"])
        if after_dt < bs:
            return after_dt, bs
        after_dt = max(after_dt, datetime.datetime.fromisoformat(b["end"]))
    return (after_dt, None)

def full_schedule_for_all_hosts():
    config = load_config()
    return config.get("schedules", {})
