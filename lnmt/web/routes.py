# lnmt/web/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from lnmt.core.config_loader import load_config, save_config
from lnmt.core.theme_manager import get_theme_names, set_active_theme

main_bp = Blueprint('main', __name__)

@main_bp.route("/settings/theme", methods=["GET", "POST"])
def settings_theme():
    if request.method == "POST":
        selected_theme = request.form.get("theme", "dark")
        session["theme"] = selected_theme
        set_active_theme(selected_theme)
        flash(f"Theme changed to {get_theme_names().get(selected_theme, selected_theme)}.", "success")
        return redirect(url_for("main.settings_theme"))
    return render_template(
        "settings_theme.html",
        theme_options=get_theme_names(),
        active_theme=session.get("theme", "dark")
    )

def register_routes(app):
    app.register_blueprint(main_bp)
