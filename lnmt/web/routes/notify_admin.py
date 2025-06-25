from flask import Blueprint, render_template
import os

notify = Blueprint("notify_admin", __name__)
LOG_PATH = "/etc/lnmt/notifications.log"

@notify.route("/notifications")
def notifications():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            lines = f.readlines()[-100:]
    else:
        lines = []
    return render_template("notifications.html", log_lines=lines)
