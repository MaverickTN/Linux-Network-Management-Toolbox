# lnmt/web/routes/home.py

from flask import Blueprint, render_template, request
from lnmt.core.dnsmasq import get_active_assignments
from lnmt.core.netplan import get_vlan_subnets
from lnmt.theme import get_theme

home_bp = Blueprint('home', __name__)

@home_bp.route("/")
def dashboard():
    vlans = get_vlan_subnets()
    hosts = get_active_assignments()
    theme = get_theme()  # You can pass user or global theme here

    return render_template("home.html", vlans=vlans, hosts=hosts, theme=theme)
