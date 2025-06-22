# inetctl/core/scheduler.py

import json
import datetime
from pathlib import Path
from typing import List, Dict, Any

SCHEDULE_FILE = Path("./data/host_schedules.json")

def load_all_schedules() -> Dict[str, List[dict]]:
    if not SCHEDULE_FILE.exists():
        return {}
    with open(SCHEDULE_FILE, "r") as f:
        return json.load(f)

def save_all_schedules(schedules: Dict[str, List[dict]]):
    SCHEDULE_FILE.parent.mkdir(exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedules, f, indent=2)

def get_host_schedules(mac: str) -> List[dict]:
    all_schedules = load_all_schedules()
    return all_schedules.get(mac.lower(), [])

def add_host_schedule(mac: str, new_block: dict) -> bool:
    """
    new_block should be: { "start": "22:00", "end": "06:00", "days": [0,1,2,3,4,5,6] }
    Returns True if added, False if overlaps detected.
    """
    mac = mac.lower()
    schedules = load_all_schedules()
    blocks = schedules.get(mac, [])
    if has_overlap(new_block, blocks):
        return False
    blocks.append(new_block)
    schedules[mac] = blocks
    save_all_schedules(schedules)
    return True

def remove_host_schedule(mac: str, idx: int) -> bool:
    mac = mac.lower()
    schedules = load_all_schedules()
    blocks = schedules.get(mac, [])
    if 0 <= idx < len(blocks):
        blocks.pop(idx)
        schedules[mac] = blocks
        save_all_schedules(schedules)
        return True
    return False

def has_overlap(new_block: dict, blocks: List[dict]) -> bool:
    """
    Checks that new_block does not overlap with any existing block in blocks.
    All times are strings "HH:MM" (24-hour).
    """
    for block in blocks:
        if set(new_block["days"]) & set(block.get("days", [])):
            # Overlapping days
            if times_overlap(new_block["start"], new_block["end"], block["start"], block["end"]):
                return True
    return False

def times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """
    Returns True if two time ranges overlap.
    Handles ranges crossing midnight.
    """
    s1, e1 = parse_time(start1), parse_time(end1)
    s2, e2 = parse_time(start2), parse_time(end2)
    def in_range(t, s, e):
        if s <= e:
            return s <= t < e
        else:
            # crosses midnight
            return t >= s or t < e
    # Check if start of block2 is in block1, or vice versa
    return in_range(s2, s1, e1) or in_range(s1, s2, e2)

def parse_time(tstr: str) -> int:
    """Return minutes since midnight for a string 'HH:MM'."""
    h, m = map(int, tstr.split(":"))
    return h * 60 + m

def check_if_blacklisted(mac: str, dt: datetime.datetime = None) -> bool:
    """
    Returns True if the device should be blacklisted at given datetime (default: now).
    """
    dt = dt or datetime.datetime.now()
    schedules = get_host_schedules(mac)
    for block in schedules:
        if dt.weekday() in block.get("days", []):
            s = parse_time(block["start"])
            e = parse_time(block["end"])
            now = dt.hour * 60 + dt.minute
            # Check block crossing midnight
            if s < e:
                if s <= now < e:
                    return True
            else:
                if now >= s or now < e:
                    return True
    return False

def cli_print_schedules(mac: str = None):
    """
    Print all schedules (or for a specific MAC).
    """
    schedules = load_all_schedules()
    if mac:
        blocks = schedules.get(mac.lower(), [])
        print(f"Schedules for {mac}:")
        for i, b in enumerate(blocks):
            print(f"  [{i}] {b['start']}-{b['end']} Days: {b['days']}")
    else:
        for m, blocks in schedules.items():
            print(f"{m}:")
            for i, b in enumerate(blocks):
                print(f"  [{i}] {b['start']}-{b['end']} Days: {b['days']}")

def cli_add_schedule(mac: str, start: str, end: str, days: str):
    """
    CLI helper: days as comma-separated (e.g. "0,1,2,3,4")
    """
    block = {
        "start": start,
        "end": end,
        "days": [int(d) for d in days.split(",") if d.strip().isdigit()]
    }
    ok = add_host_schedule(mac, block)
    if ok:
        print(f"Added schedule block for {mac}: {block}")
    else:
        print(f"Failed: schedule overlaps existing blocks.")

def cli_remove_schedule(mac: str, idx: int):
    ok = remove_host_schedule(mac, idx)
    if ok:
        print(f"Removed schedule {idx} for {mac}")
    else:
        print(f"Failed: index {idx} not valid for {mac}")

