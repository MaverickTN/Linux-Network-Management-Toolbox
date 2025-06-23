# lnmt/web/host.py

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from lnmt.core.config_loader import load_config, save_config
from lnmt.core.dnsmasq import get_leases, update_reservation, remove_reservation, block_host, allow_host
from lnmt.core.schedule import get_host_schedules, add_host_schedule, remove_host_schedule
from lnmt.core.logging import log_event
from lnmt.job_queue_service import JobQueueService

host_bp = Blueprint('host', __name__, url_prefix='/host')

@host_bp.route('/', methods=['GET'])
def host_overview():
    config = load_config()
    leases = get_leases()
    return render_template("host.html", config=config, leases=leases)

@host_bp.route('/<mac>', methods=['GET'])
def host_details(mac):
    config = load_config()
    host_info = next((h for h in config['known_hosts'] if h['mac'] == mac), None)
    lease = next((l for l in get_leases() if l['mac'] == mac), None)
    schedules = get_host_schedules(mac)
    return render_template(
        "host_detail.html",
        host=host_info, lease=lease, schedules=schedules
    )

@host_bp.route('/<mac>/edit', methods=['POST'])
def edit_host(mac):
    config = load_config()
    form = request.form.to_dict()
    for host in config['known_hosts']:
        if host['mac'] == mac:
            host.update(form)
            break
    else:
        config['known_hosts'].append({**form, "mac": mac})
    save_config(config)
    log_event("host", f"Host {mac} updated", details=form)
    flash("Host configuration updated.", "success")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/block', methods=['POST'])
def block(mac):
    job = JobQueueService.queue_job(
        description=f"Block host {mac}",
        command=lambda: block_host(mac)
    )
    log_event("host", f"Block queued for {mac}")
    flash(f"Host {mac} block queued as job #{job.id}", "info")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/allow', methods=['POST'])
def allow(mac):
    job = JobQueueService.queue_job(
        description=f"Allow host {mac}",
        command=lambda: allow_host(mac)
    )
    log_event("host", f"Allow queued for {mac}")
    flash(f"Host {mac} allow queued as job #{job.id}", "info")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/reservation', methods=['POST'])
def reservation(mac):
    form = request.form.to_dict()
    job = JobQueueService.queue_job(
        description=f"Update reservation for {mac}",
        command=lambda: update_reservation(mac, form)
    )
    log_event("host", f"Reservation update queued for {mac}", details=form)
    flash(f"Reservation update queued for {mac} as job #{job.id}", "info")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/reservation/remove', methods=['POST'])
def remove_res(mac):
    job = JobQueueService.queue_job(
        description=f"Remove reservation for {mac}",
        command=lambda: remove_reservation(mac)
    )
    log_event("host", f"Reservation removal queued for {mac}")
    flash(f"Reservation removal queued for {mac} as job #{job.id}", "info")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/schedule/add', methods=['POST'])
def add_schedule(mac):
    form = request.form.to_dict()
    schedules = get_host_schedules(mac)
    # Overlap prevention logic here
    for sch in schedules:
        if sch['start'] < form['end'] and form['start'] < sch['end']:
            flash("Schedule block overlaps existing block!", "danger")
            return redirect(url_for('host.host_details', mac=mac))
    add_host_schedule(mac, form)
    log_event("host", f"Schedule block added for {mac}", details=form)
    flash("Schedule block added.", "success")
    return redirect(url_for('host.host_details', mac=mac))

@host_bp.route('/<mac>/schedule/remove/<schedule_id>', methods=['POST'])
def remove_schedule(mac, schedule_id):
    remove_host_schedule(mac, schedule_id)
    log_event("host", f"Schedule block {schedule_id} removed for {mac}")
    flash("Schedule block removed.", "success")
    return redirect(url_for('host.host_details', mac=mac))

# API endpoints can be added as needed (e.g. /api/hosts, /api/host/<mac>)

