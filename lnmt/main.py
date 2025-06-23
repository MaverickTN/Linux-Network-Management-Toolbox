# lnmt/main.py

from flask import Flask, render_template, session, redirect, url_for, request, jsonify, g
from flask_login import LoginManager, current_user, login_required

from lnmt.web.views.home import home_bp
from lnmt.web.views.netplan import netplan_bp
from lnmt.web.views.dnsmasq import dnsmasq_bp
from lnmt.web.views.schedule import schedule_bp
from lnmt.web.views.hosts import hosts_bp
from lnmt.web.views.settings import settings_bp
from lnmt.core.job_queue import job_queue
from lnmt.core.theme import get_theme, list_theme_names

from lnmt.core.auth import user_in_group, get_user_theme, get_current_username

import os

APP_TITLE = os.environ.get("LNMT_APP_TITLE", "Linux Network Management Toolbox")

app = Flask(__name__)
app.secret_key = os.environ.get("LNMT_SECRET_KEY", "dev-key")

# Register Blueprints (each view in its own file)
app.register_blueprint(home_bp)
app.register_blueprint(netplan_bp, url_prefix="/netplan")
app.register_blueprint(dnsmasq_bp, url_prefix="/dnsmasq")
app.register_blueprint(schedule_bp, url_prefix="/schedule")
app.register_blueprint(hosts_bp, url_prefix="/hosts")
app.register_blueprint(settings_bp, url_prefix="/settings")

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

# Inject title, user, and theme info into every template
@app.context_processor
def inject_globals():
    user = get_current_username()
    theme_key = get_user_theme(user)
    return dict(
        app_title=APP_TITLE,
        theme=get_theme(theme_key),
        theme_list=list_theme_names(),
        current_user=user
    )

@app.route("/job_status/<job_id>")
@login_required
def job_status(job_id):
    job_info = job_queue.get_status(job_id)
    if job_info:
        return jsonify(job_info)
    return jsonify({"status": "not found"}), 404

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html", message=str(error)), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", message=str(error)), 404

@app.errorhandler(500)
def server_error(error):
    return render_template("500.html", message=str(error)), 500

# CLI user/group access and theming
@app.before_request
def before_request():
    # Example group enforcement (for CLI endpoints or API, if desired)
    user = get_current_username()
    if user and not user_in_group(user):
        return render_template("403.html", message="User does not belong to required group"), 403
    g.theme = get_theme(get_user_theme(user))

def run():
    app.run(host="0.0.0.0", port=8080, debug=True)

if __name__ == "__main__":
    run()
