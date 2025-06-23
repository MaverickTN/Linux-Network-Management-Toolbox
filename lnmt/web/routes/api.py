# lnmt/web/routes/api.py

from flask import Blueprint, jsonify, request
from lnmt.core.dnsmasq import get_host_by_mac
from lnmt.core.transfer import get_transfer_history
from lnmt.core.hosts import update_host_config, get_host_schedule_blocks
from lnmt.theme import get_theme

api_bp = Blueprint('api', __name__)

@api_bp.route("/host/<mac>", methods=['GET'])
def api_host(mac):
    host = get_host_by_mac(mac)
    if not host:
        return jsonify({"error": "Host not found"}), 404
    # Add additional data as needed
    host['schedule_blocks'] = get_host_schedule_blocks(mac)
    return jsonify(host)

@api_bp.route("/host/<mac>", methods=['POST'])
def api_host_save(mac):
    data = request.json
    result, message = update_host_config(mac, data)
    return jsonify({"success": result, "message": message})

@api_bp.route("/transfer/<mac>", methods=['GET'])
def api_transfer(mac):
    hours = int(request.args.get("hours", 1))
    data = get_transfer_history(mac, hours=hours)
    return jsonify(data)
