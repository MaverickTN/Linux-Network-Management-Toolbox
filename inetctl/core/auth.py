import sqlite3
from pathlib import Path
from flask_login import UserMixin
from passlib.context import CryptContext

DB_FILE = Path("./inetctl_stats.db")
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

class User(UserMixin):
    """A user class for Flask-Login."""
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

def setup_users_table():
    """Ensures the users table and a default admin (if needed) exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'operator', 'viewer'))
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"CRITICAL [auth.setup_users_table]: Could not set up users table: {e}")
    finally:
        if conn: conn.close()

def hash_password(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain-text password against a stored hash."""
    return pwd_context.verify(password, password_hash)

def add_user(username: str, password_hash: str, role: str) -> bool:
    """Adds a new user to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        if conn: conn.close()

def get_user_by_name(username: str):
    """Retrieves a single user by their username."""
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user_row = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user_row: return User(user_id=user_row['id'], username=user_row['username'], role=user_row['role']), user_row['password_hash']
    return None, None
    
def get_user_by_id(user_id: int) -> User:
    """Retrieves a user by their ID (required for Flask-Login)."""
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user_row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_row: return User(user_id=user_row['id'], username=user_row['username'], role=user_row['role'])
    return None

def get_all_users():
    """Retrieves all users from the database for display purposes."""
    conn = sqlite3.connect(DB_FILE); conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    users = cursor.execute("SELECT id, username, role FROM users ORDER BY username ASC").fetchall()
    conn.close()
    return users

# Ensure the users table is created when this module is first imported.
setup_users_table()