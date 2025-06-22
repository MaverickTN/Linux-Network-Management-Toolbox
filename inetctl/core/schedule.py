import json
from pathlib import Path

SCHEDULE_FILE = Path("/etc/lnmt/host_schedules.json")  # Adjust path as needed

def load_schedules():
    if not SCHEDULE_FILE.exists():
        return {}
    with open(SCHEDULE_FILE, "r") as f:
        return json.load(f)

def save_schedules(data):
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def list_host_schedules(mac):
    schedules = load_schedules()
    return schedules.get(mac.lower(), [])

def add_schedule_block(mac, start, end):
    schedules = load_schedules()
    mac = mac.lower()
    blocks = schedules.get(mac, [])
    blocks.append({"start": start, "end": end})
    schedules[mac] = blocks
    save_schedules(schedules)

def remove_schedule_block(mac, index):
    schedules = load_schedules()
    mac = mac.lower()
    if mac not in schedules or not (0 <= index < len(schedules[mac])):
        return False
    schedules[mac].pop(index)
    save_schedules(schedules)
    return True

def validate_schedule_block(mac, start, end):
    """Ensure new block does not overlap existing for this MAC."""
    from datetime import datetime as dt
    fmt = "%H:%M"
    try:
        s1 = dt.strptime(start, fmt)
        e1 = dt.strptime(end, fmt)
    except Exception:
        return False, "Time must be in HH:MM 24h format."
    blocks = list_host_schedules(mac)
    for b in blocks:
        s2 = dt.strptime(b["start"], fmt)
        e2 = dt.strptime(b["end"], fmt)
        # Check overlap
        if (s1 < e2 and e1 > s2):
            return False, f"Overlaps existing block {b['start']}-{b['end']}"
    return True, ""
