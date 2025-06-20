from datetime import time
import json

def load_hosts():
    # Replace this with your actual loading logic
    from inetctl.core.hosts import load_hosts as _load
    return _load()

def save_hosts():
    # Replace this with your actual saving logic
    from inetctl.core.hosts import save_hosts as _save
    _save()

def get_schedule_blocks(host):
    # Each host dict should have a 'schedules' key, which is a list of dicts {"start": "HH:MM", "end": "HH:MM"}
    return host.get("schedules", [])

def list_schedule_blocks(host):
    return get_schedule_blocks(host)

def validate_schedule_blocks(blocks):
    # blocks: list of dicts with keys "start" and "end" as "HH:MM"
    parsed = []
    for blk in blocks:
        try:
            s = _parse_time(blk["start"])
            e = _parse_time(blk["end"])
        except Exception:
            return False, "Invalid time format in block"
        parsed.append((s, e))
    # check for overlap
    for i, (s1, e1) in enumerate(parsed):
        for j, (s2, e2) in enumerate(parsed):
            if i == j:
                continue
            if _blocks_overlap(s1, e1, s2, e2):
                return False, f"Blocks {i} and {j} overlap"
    return True, ""

def add_schedule_block(host, start, end):
    """
    Adds a new schedule block. Prevents overlaps.
    start/end: datetime.time objects
    """
    if start >= end:
        return False, "End time must be after start time."
    blocks = get_schedule_blocks(host)
    new_block = {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")}
    # Check overlap with existing blocks
    for idx, blk in enumerate(blocks):
        s = _parse_time(blk["start"])
        e = _parse_time(blk["end"])
        if _blocks_overlap(start, end, s, e):
            return False, f"Overlaps with block #{idx} ({blk['start']}-{blk['end']})"
    # Add
    blocks.append(new_block)
    host["schedules"] = blocks
    return True, "Block added."

def remove_schedule_block(host, index):
    blocks = get_schedule_blocks(host)
    if not (0 <= index < len(blocks)):
        return False
    blocks.pop(index)
    host["schedules"] = blocks
    return True

def _parse_time(ts: str) -> time:
    h, m = map(int, ts.split(":"))
    return time(h, m)

def _blocks_overlap(s1, e1, s2, e2):
    # Return True if [s1, e1) overlaps [s2, e2)
    return max(s1, s2) < min(e1, e2)

# ----- For Web Use -----
def can_block_now(host, check_time=None):
    """Returns True if host is scheduled to be blocked at current time."""
    import datetime
    now = check_time or datetime.datetime.now().time()
    for blk in get_schedule_blocks(host):
        s = _parse_time(blk["start"])
        e = _parse_time(blk["end"])
        if s < now < e:
            return True
    return False

def get_next_block(host, check_time=None):
    """Returns next scheduled block (start, end) after now."""
    import datetime
    now = check_time or datetime.datetime.now().time()
    next_blk = None
    min_delta = None
    for blk in get_schedule_blocks(host):
        s = _parse_time(blk["start"])
        if s > now:
            delta = (datetime.datetime.combine(datetime.date.today(), s) -
                     datetime.datetime.combine(datetime.date.today(), now)).total_seconds()
            if min_delta is None or delta < min_delta:
                min_delta = delta
                next_blk = blk
    return next_blk
