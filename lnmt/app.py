# lnmt/app.py

from flask import Flask
from lnmt.core.theme_manager import theme_manager
from lnmt.web.views.home import home_bp
from lnmt.web.views.users import users_bp
from lnmt.web.views.config import config_bp
from lnmt.web.views.schedule import schedule_bp
from lnmt.web.views.blocklist import blocklist_bp
from lnmt.web.views.reservations import reservations_bp

def create_app():
    app = Flask(__name__)

    # Register blueprints for modular routes
    app.register_blueprint(home_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(blocklist_bp)
    app.register_blueprint(reservations_bp)

    # Inject theme into templates via context processor
    @app.context_processor
    def inject_theme():
        return dict(
            theme=theme_manager.get_theme(),
            themes=theme_manager.list_themes(),
            theme_css=theme_manager.get_theme_css()
        )

    return app
