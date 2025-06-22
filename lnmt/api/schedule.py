# inetctl/api/schedule.py

from flask import Blueprint, request, jsonify
from inetctl.core.config_loader import load_config, save_config
from datetime import datetime

schedule_api = Blueprint('schedule_api', __name__)

def time_to_minutes(tstr):
    try:
        h, m = map(int, tstr.split(":"))
        return h * 60 + m
    except Exception:
        return None

def blocks_overlap(a, b):
    return not (time_to_minutes(a["end"]) <= time_to_minutes(b["start"]) or time_to_minutes(a["start"]) >= time_to_minutes(b["end"]))

def is_overlapping(blocks, new_block, skip_idx=None):
    new_start = time_to_minutes(new_block["start"])
    new_end = time_to_minutes(new_block["end"])
    if new_start is None or new_end is None or new_end <= new_start:
        return True
    for idx, block in enumerate(blocks):
        if skip_idx is not None and idx == skip_idx:
            continue
        if blocks_overlap(block, new_block):
            return True
    return False

def get_host_schedule(mac):
    config = load_config()
    schedules = config.get("schedules", {})
    return schedules.get(mac, {"blocks": []})

def save_host_schedule(mac, sched):
    config = load_config()
    if "schedules" not in config:
        config["schedules"] = {}
    config["schedules"][mac] = sched
    save_config(config)

@schedule_api.route('/schedule/<mac>', methods=['GET'])
def api_get_schedule(mac):
    return jsonify(get_host_schedule(mac))

@schedule_api.route('/schedule/<mac>/add', methods=['POST'])
def api_add_schedule(mac):
    req = request.get_json()
    start = req.get("start")
    end = req.get("end")
    sched = get_host_schedule(mac)
    new_block = {"start": start, "end": end}
    if is_overlapping(sched["blocks"], new_block):
        return jsonify({"success": False, "message": "Block overlaps with existing."})
    sched["blocks"].append(new_block)
    save_host_schedule(mac, sched)
    return jsonify({"success": True})

@schedule_api.route('/schedule/<mac>/remove/<int:idx>', methods=['POST'])
def api_remove_schedule(mac, idx):
    sched = get_host_schedule(mac)
    if 0 <= idx < len(sched["blocks"]):
        sched["blocks"].pop(idx)
        save_host_schedule(mac, sched)
    return jsonify({"success": True})

@schedule_api.route('/schedule/<mac>/update/<int:idx>', methods=['POST'])
def api_update_schedule(mac, idx):
    req = request.get_json()
    start = req.get("start")
    end = req.get("end")
    sched = get_host_schedule(mac)
    if not (0 <= idx < len(sched["blocks"])):
        return jsonify({"success": False, "message": "Invalid block index"})
    # check overlap except for itself
    new_block = {"start": start, "end": end}
    if is_overlapping(sched["blocks"], new_block, skip_idx=idx):
        return jsonify({"success": False, "message": "Block overlaps"})
    sched["blocks"][idx] = new_block
    save_host_schedule(mac, sched)
    return jsonify({"success": True})

