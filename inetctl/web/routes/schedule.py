from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from inetctl.core import schedule
from inetctl.job_queue_service import queue_job
from inetctl.web.utils import log_web_event

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")

@bp.route("/<mac>", methods=["GET"])
@login_required
def get_host_schedules(mac):
    blocks = schedule.list_schedules(mac)
    return jsonify({"blocks": blocks})

@bp.route("/<mac>/add", methods=["POST"])
@login_required
def add_schedule_block(mac):
    data = request.json
    # Data must contain: start, end, days, comment
    block = {
        "start": data.get("start"),
        "end": data.get("end"),
        "days": data.get("days"),
        "comment": data.get("comment", "")
    }
    def do_add():
        new_block = schedule.add_schedule(mac, block["start"], block["end"], block["days"], block["comment"])
        log_web_event(current_user.username, f"Added schedule for {mac}: {schedule.describe_block(new_block)}")
        return new_block

    job = queue_job("Add schedule block", do_add)
    return jsonify({"queued": True, "job_id": job.id, "desc": f"Scheduling block for {mac} queued"})

@bp.route("/<mac>/<int:block_idx>", methods=["DELETE"])
@login_required
def remove_schedule_block(mac, block_idx):
    def do_remove():
        removed = schedule.remove_schedule(mac, block_idx)
        log_web_event(current_user.username, f"Removed schedule for {mac}: {schedule.describe_block(removed)}")
        return removed

    job = queue_job("Remove schedule block", do_remove)
    return jsonify({"queued": True, "job_id": job.id})

@bp.route("/<mac>/<int:block_idx>", methods=["PATCH"])
@login_required
def update_schedule_block(mac, block_idx):
    data = request.json
    def do_update():
        old, new = schedule.update_schedule(
            mac, block_idx,
            data.get("start"), data.get("end"),
            data.get("days"), data.get("comment")
        )
        log_web_event(current_user.username, f"Updated schedule for {mac}: {schedule.describe_block(new)}")
        return new

    job = queue_job("Update schedule block", do_update)
    return jsonify({"queued": True, "job_id": job.id})
