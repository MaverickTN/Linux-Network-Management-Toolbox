import sqlite3
import time
from pathlib import Path

DB_FILE = Path("./inetctl_stats.db")

def setup_database():
    """Ensures the event_log table exists and has the username column."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('INFO', 'WARNING', 'ERROR')),
            source TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """)
        
        # Safely add the 'username' column if it doesn't already exist.
        # This makes the upgrade non-destructive.
        cursor.execute("PRAGMA table_info(event_log)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'username' not in columns:
            cursor.execute("ALTER TABLE event_log ADD COLUMN username TEXT")

        conn.commit()
    except sqlite3.Error as e:
        print(f"CRITICAL [logger.setup_database]: Could not set up event_log table: {e}")
    finally:
        if conn: conn.close()

def log_event(level: str, source: str, message: str, username: str):
    """
    Writes a structured event to the event_log table.

    Args:
        level (str): INFO, WARNING, ERROR.
        source (str): The component creating the log (e.g., 'schedule:apply').
        message (str): The log message.
        username (str): The user responsible for the event (e.g., 'admin', 'SYSTEM').
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO event_log (timestamp, level, source, message, username) VALUES (?, ?, ?, ?, ?)",
            (int(time.time()), level.upper(), source, message, username)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"CRITICAL [logger.log_event]: Failed to write to log database: {e}")
        print(f"FALLBACK LOG: [{username}]-[{level}]-[{source}] {message}")
    finally:
        if conn: conn.close()

# Ensure the database table exists and is up-to-date.
setup_database()