from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
import tempfile
from lnmt.core.auth import require_role, current_user_groups
from lnmt.core.pihole_api import PiHoleAPI
from lnmt.config.loader import get_config

bp = Blueprint("pihole_dns", __name__)

def get_api():
    cfg = get_config(section="dns")
    return PiHoleAPI(
        cfg["pihole_api_url"],
        cfg["pihole_api_key"],
        test_mode=cfg.getboolean("test_mode", fallback=False),
        retries=cfg.getint("retries", fallback=3),
        retry_delay=cfg.getint("retry_delay", fallback=2)
    )

@bp.route("/dns")
@require_role("dns_manage")
def view_records():
    api = get_api()
    try:
        records = api.list_records()
        user_groups = current_user_groups()
        if "admin" not in user_groups:
            records = [r for r in records if r.get("group", "default") in user_groups]
        return render_template("pihole_dns.html", records=records, test_mode=api.test_mode)
    except Exception as e:
        flash(str(e), "error")
        return render_template("pihole_dns.html", records=[], test_mode=True)

@bp.route("/dns/add", methods=["POST"])
@require_role("dns_manage")
def add_record():
    name = request.form["name"]
    ip = request.form["ip"]
    group = request.form.get("group", "default")
    api = get_api()
    try:
        api.add_or_update_record(name, ip, group)
        flash("DNS record added/updated")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("pihole_dns.view_records"))

@bp.route("/dns/delete/<id>")
@require_role("dns_manage")
def delete_record(id):
    api = get_api()
    try:
        api.delete_record(id)
        flash("DNS record deleted")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("pihole_dns.view_records"))

@bp.route("/dns/export")
@require_role("dns_manage")
def export_records():
    api = get_api()
    try:
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        path = api.export_records(tmp_file.name)
        return send_file(path, as_attachment=True)
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("pihole_dns.view_records"))

@bp.route("/dns/import", methods=["POST"])
@require_role("dns_manage")
def import_records():
    file = request.files.get("import_file")
    if file:
        try:
            tmp_path = os.path.join(tempfile.gettempdir(), file.filename)
            file.save(tmp_path)
            api = get_api()
            api.import_records(tmp_path)
            flash("DNS records imported")
        except Exception as e:
            flash(str(e), "error")
    return redirect(url_for("pihole_dns.view_records"))
