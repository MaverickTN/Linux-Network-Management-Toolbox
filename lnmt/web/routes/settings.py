from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.core.auth import require_role
from lnmt.core.settings import get_setting, set_setting

bp = Blueprint("settings", __name__)

@bp.route("/settings/detection", methods=["GET", "POST"])
@require_role("admin")
def detection_settings():
    keys = ['ping_window', 'min_bytes_in', 'min_bytes_out']
    if request.method == "POST":
        for key in keys:
            val = request.form.get(key)
            if val is not None:
                set_setting(key, val)
        flash("Settings updated.")
        return redirect(url_for("settings.detection_settings"))
    current = {k: get_setting(k) for k in keys}
    return render_template("detection_settings.html", settings=current)
