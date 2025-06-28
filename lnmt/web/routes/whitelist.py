from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.core.auth import require_role
from lnmt.core.dns_whitelist import get_whitelist, add_domain, remove_domain

bp = Blueprint("whitelist", __name__)

@bp.route("/settings/whitelist", methods=["GET", "POST"])
@require_role("admin")
def whitelist():
    if request.method == "POST":
        domain = request.form.get("domain")
        description = request.form.get("description", "")
        if domain:
            add_domain(domain.strip(), description.strip())
            flash("Domain added.")
        return redirect(url_for("whitelist.whitelist"))
    entries = get_whitelist()
    return render_template("dns_whitelist.html", entries=entries)

@bp.route("/settings/whitelist/delete/<int:domain_id>")
@require_role("admin")
def delete_domain(domain_id):
    remove_domain(domain_id)
    flash("Domain removed.")
    return redirect(url_for("whitelist.whitelist"))
