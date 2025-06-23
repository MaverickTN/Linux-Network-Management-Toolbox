# lnmt/web/app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from lnmt.core.theme_manager import get_active_theme
from lnmt.core.config_loader import load_config
from lnmt.web.routes import register_routes

def create_app():
    app = Flask(__name__)
    app.secret_key = "your_super_secret_key"  # Set securely in production

    @app.context_processor
    def inject_globals():
        return {
            "theme": get_active_theme(),
        }

    # Register all blueprints/routes here
    register_routes(app)

    @app.route("/")
    def home():
        config = load_config()
        return render_template("home.html", config=config)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", theme=get_active_theme()), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html", theme=get_active_theme()), 500

    return app
