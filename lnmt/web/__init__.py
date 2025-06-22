from flask import Flask
from .models import init_db
from .auth import auth_bp

def create_app(config=None):
    app = Flask(__name__)
    app.secret_key = "ChangeMeToAStrongSecret"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inetctl_web.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    init_db(app)

    # Register blueprints
    app.register_blueprint(auth_bp)

    # You would register the main web UI blueprint here as well
    # from .main import main_bp
    # app.register_blueprint(main_bp)

    return app
