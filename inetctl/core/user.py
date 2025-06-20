from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

    def get_id(self):
        return self.username

    def __repr__(self):
        return f"<User {self.username}>"
