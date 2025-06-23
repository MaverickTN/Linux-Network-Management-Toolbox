# lnmt/web/views/home.py

from flask import Blueprint, render_template, session
from lnmt.core.theme_manager import theme_manager

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/")
def home():
    user = session.get("user")
    theme = theme_manager.get_theme(user)
    return render_template(
        "home.html",
        title="Linux Network Management Toolbox",
        user=user,
        theme=theme,
        themes=theme_manager.list_themes()
    )
