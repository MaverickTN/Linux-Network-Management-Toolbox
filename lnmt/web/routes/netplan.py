#!/usr/bin/env python3

from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.core import netplan
from lnmt.web.utils import require_web_role

netplan_routes = Blueprint("netplan_routes", __name__)

@require_web_role("admin")
@netplan_routes.route("/netplan", methods=["GET"])
def netplan_list():
    files = netplan.list_netplan_files()
    configs = netplan.read_netplan_config()
    return render_template("netplan.html", files=files, configs=configs)

@require_web_role("admin")
@netplan_routes.route("/netplan/apply")
def netplan_apply():
    netplan.validate_netplan()
    netplan.apply_netplan()
    flash("Netplan configuration applied.", "success")
    return redirect(url_for("netplan_routes.netplan_list"))
