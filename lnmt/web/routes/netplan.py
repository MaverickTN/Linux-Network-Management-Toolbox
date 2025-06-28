from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.core.auth import require_role
from lnmt.core.netplan import list_configs, get_config, save_config, delete_config
import os

bp = Blueprint("netplan", __name__)

NETPLAN_STAGING_DIR = "/etc/lnmt/netplan_staging/"
os.makedirs(NETPLAN_STAGING_DIR, exist_ok=True)

@bp.route("/netplan")
@require_role("admin")
def netplan_list():
    configs = list_configs()
    return render_template("netplan_list.html", configs=configs)

@bp.route("/netplan/edit/<int:config_id>", methods=["GET", "POST"])
@require_role("admin")
def netplan_edit(config_id):
    config = get_config(config_id)
    if not config:
        flash("Config not found.")
        return redirect(url_for("netplan.netplan_list"))
    if request.method == "POST":
        yaml = request.form["yaml"]
        save_config(config["name"], yaml)
        flash("Config updated.")
        return redirect(url_for("netplan.netplan_list"))
    return render_template("netplan_edit.html", config=config)

@bp.route("/netplan/add", methods=["GET", "POST"])
@require_role("admin")
def netplan_add():
    if request.method == "POST":
        name = request.form["name"]
        yaml = request.form["yaml"]
        save_config(name, yaml)
        flash("Config added.")
        return redirect(url_for("netplan.netplan_list"))
    return render_template("netplan_edit.html", config=None)

@bp.route("/netplan/delete/<int:config_id>")
@require_role("admin")
def netplan_delete(config_id):
    delete_config(config_id)
    flash("Config deleted.")
    return redirect(url_for("netplan.netplan_list"))

@bp.route("/netplan/apply/<int:config_id>")
@require_role("admin")
def netplan_apply(config_id):
    config = get_config(config_id)
    if not config:
        flash("Config not found.")
        return redirect(url_for("netplan.netplan_list"))
    staging_path = os.path.join(NETPLAN_STAGING_DIR, f"{config['name']}.yaml")
    with open(staging_path, "w") as f:
        f.write(config["yaml"])
    flash(f"Config staged to {staging_path}. Please apply manually (as root): netplan apply")
    return redirect(url_for("netplan.netplan_list"))
