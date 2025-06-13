import sqlite3
import time
from pathlib import Path

# Use the same database file as the stats collector
DB_FILE = Path("./inetctl_stats.db")

def setup_database():
    """Ensures the event_log table exists in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        # Use IF NOT EXISTS to make this operation safe to run every time
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('INFO', 'WARNING', 'ERROR')),
            source TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """)
        conn.commit()
    except sqlite3.Error as e:
        # This is a critical failure, as logging won't work
        print(f"CRITICAL [logger.setup_database]: Could not set up event_log table: {e}")
    finally:
        if conn:
            conn.close()

def log_event(level: str, source: str, message: str):
    """
    Writes a structured event to the event_log table.

    Args:
        level (str): INFO, WARNING, ERROR.
        source (str): The component creating the log (e.g., 'schedule:apply').
        message (str): The log message.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO event_log (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
            (int(time.time()), level.upper(), source, message)
        )
        conn.commit()
    except sqlite3.Error as e:
        # If logging fails, we print to stdout/stderr as a fallback.
        print(f"CRITICAL [logger.log_event]: Failed to write to log database: {e}")
        print(f"FALLBACK LOG: [{level}]-[{source}] {message}")
    finally:
        if conn:
            conn.close()

# Ensure the database table exists the first time this module is imported.
setup_database()