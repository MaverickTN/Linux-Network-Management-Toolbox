# inetctl/main.py

from flask import Flask
from inetctl.web.routes.home import home_bp
from inetctl.web.routes.netplan import netplan_bp
from inetctl.web.routes.api import api_bp
from inetctl.theme import apply_theme  # import if you have a theme engine

def create_app():
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(netplan_bp, url_prefix='/netplan')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Theme can be applied here if you want dynamic theming
    apply_theme(app)  # Only if your theme.py defines it

    app.config['SECRET_KEY'] = 'your-secret-key'  # Replace as needed

    return app
