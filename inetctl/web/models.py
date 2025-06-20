from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(16), nullable=False)   # lnmtadm, lnmt, lnmtv
    email = db.Column(db.String(128))
    theme = db.Column(db.String(32), default="dark")
    notifications = db.Column(db.String(128), default="all") # Comma-separated event types, e.g., 'all', 'critical', etc.

    # Add additional fields as needed (e.g., last_login, password_changed, etc.)

    def __repr__(self):
        return f"<UserProfile({self.username}, {self.role}, {self.theme})>"

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
