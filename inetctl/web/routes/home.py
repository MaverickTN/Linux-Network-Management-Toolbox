# inetctl/web/routes/home.py

from flask import Blueprint, render_template, request
from inetctl.core.dnsmasq import get_active_assignments
from inetctl.core.netplan import get_vlan_subnets
from inetctl.theme import get_theme

home_bp = Blueprint('home', __name__)

@home_bp.route("/")
def dashboard():
    vlans = get_vlan_subnets()
    hosts = get_active_assignments()
    theme = get_theme()  # You can pass user or global theme here

    return render_template("home.html", vlans=vlans, hosts=hosts, theme=theme)
