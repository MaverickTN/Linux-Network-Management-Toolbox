import os
import sys
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from lnmt.web.views import register_blueprints
from lnmt.core.config_loader import load_config
from lnmt.core.theme import THEMES, get_theme
from lnmt.core.user import User, get_user_by_username, pam_authenticate, get_or_create_profile
from lnmt.core.job_queue_service import job_queue
from lnmt.core.logger import log_event
from lnmt.core.notify import send_notification, broadcast_notification
from lnmt.core.cli_groups import user_is_in_group, required_groups
from lnmt.core.netplan import get_vlan_list, get_vlan_map
from lnmt.core.hosts import get_hosts_by_vlan, get_host_data, update_host_config
from lnmt.core.transfer import get_transfer_history
from lnmt.core.schedules import get_schedules, validate_schedule, add_schedule_block
from lnmt.core.validators import validate_config
from lnmt.core.settings import APP_TITLE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(APP_TITLE)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "insecure_dev_key")

# Flask-Login config
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Modular blueprint registration
register_blueprints(app)

# Theming context processor
@app.context_processor
def inject_theme():
    user_theme = getattr(current_user, "theme", None)
    theme_key = user_theme or session.get("theme") or "dark"
    theme = get_theme(theme_key)
    return dict(THEMES=THEMES, theme=theme, theme_key=theme_key, APP_TITLE=APP_TITLE)

# --- Login Management ---
@login_manager.user_loader
def load_user(user_id):
    return get_user_by_username(user_id)

@app.before_request
def before_request():
    # Apply group authentication to CLI calls
    if current_user.is_authenticated:
        if not user_is_in_group(current_user.username):
            logger.warning(f"User {current_user.username} attempted access without correct group membership.")
            logout_user()
            flash("You are not authorized for CLI or web access. Please contact your administrator.", "error")
            return redirect(url_for('auth.login'))
    # Check for config validation
    if not validate_config():
        logger.error("Configuration validation failed.")
        flash("Configuration file is corrupted or invalid. Please check your server or contact admin.", "error")
        return redirect(url_for('admin.config_repair'))
    # PAM auto-profile creation for web logins
    if current_user.is_authenticated:
        get_or_create_profile(current_user.username)

# --- Home / Dashboard ---
@app.route("/")
@login_required
def home():
    # VLAN tab info
    vlan_list = get_vlan_list()
    vlan_map = get_vlan_map()  # e.g. {vlan_id: {name, interface, ...}}
    selected_vlan = request.args.get("vlan", "1")
    hosts_by_vlan = {vlan_id: get_hosts_by_vlan(vlan_id) for vlan_id in vlan_list}
    schedules = get_schedules()
    notifications = session.pop("notifications", [])
    return render_template(
        "home.html",
        vlan_list=vlan_list,
        vlan_map=vlan_map,
        selected_vlan=selected_vlan,
        hosts_by_vlan=hosts_by_vlan,
        schedules=schedules,
        notifications=notifications,
        APP_TITLE=APP_TITLE,
    )

# --- Host Edit Overlay ---
@app.route("/api/host/<mac>", methods=["GET", "POST"])
@login_required
def host_edit(mac):
    if request.method == "GET":
        host = get_host_data(mac)
        return jsonify(host)
    # Save edited host info
    data = request.json
    update_host_config(mac, data)
    job_queue.enqueue("update_host", mac=mac, data=data)
    log_event("host_edit", f"User {current_user.username} edited host {mac}")
    send_notification(f"Host {mac} configuration updated.", users=[current_user.username])
    return jsonify({"success": True})

# --- Transfer Graph API ---
@app.route("/api/transfer/<mac>")
@login_required
def transfer_api(mac):
    hours = int(request.args.get("hours", 1))
    history = get_transfer_history(mac, hours)
    return jsonify(history)

# --- Toggle Network Access (Block/Allow) ---
@app.route("/toggle_access", methods=["POST"])
@login_required
def toggle_access():
    mac = request.json["mac"]
    result = job_queue.enqueue("toggle_access", mac=mac, user=current_user.username)
    broadcast_notification(f"Network access for {mac} queued for update.")
    log_event("access_toggle", f"{current_user.username} queued access toggle for {mac}")
    return jsonify({
        "queued": True,
        "message": "Access change queued for host.",
        "job_id": result.job_id,
    })

@app.route("/job_status/<job_id>")
@login_required
def job_status(job_id):
    job = job_queue.status(job_id)
    return jsonify(job)

# --- Theme selection / Profile ---
@app.route("/profile", methods=["GET", "POST"])
@login_required
def user_profile():
    if request.method == "GET":
        return render_template("profile.html", user=current_user, THEMES=THEMES)
    # Update profile (theme, notification prefs, etc.)
    theme = request.form.get("theme")
    notification_options = request.form.getlist("notifications")
    current_user.update_profile(theme=theme, notifications=notification_options)
    session["theme"] = theme
    flash("Profile updated.", "success")
    return redirect(url_for("user_profile"))

# --- Admin/config repair page ---
@app.route("/admin/config_repair", methods=["GET", "POST"])
@login_required
def config_repair():
    if request.method == "GET":
        return render_template("config_repair.html")
    # Attempt repair (auto-backup, restore, notify)
    repaired = validate_config(auto_repair=True)
    if repaired:
        flash("Configuration was automatically repaired!", "success")
    else:
        flash("Auto-repair failed. Manual intervention required.", "error")
    return redirect(url_for("home"))

# --- Scheduler API (Multiple schedule blocks) ---
@app.route("/api/schedule/<mac>", methods=["POST"])
@login_required
def schedule_api(mac):
    schedule_blocks = request.json.get("blocks", [])
    # Validate and add (no overlaps)
    result, message = add_schedule_block(mac, schedule_blocks)
    if result:
        job_queue.enqueue("schedule_update", mac=mac, blocks=schedule_blocks)
        send_notification(f"Schedule updated for {mac}.")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": message})

# --- Run the Flask app ---
if __name__ == "__main__":
    # This is a demo/dev runner. Use gunicorn/production server in prod.
    app.run(host="0.0.0.0", port=8080, debug=True)
