# lnmt/core/log_manager.py

import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path.home() / ".lnmt" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "lnmt.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def log_event(event, level="info", user=None):
    msg = f"[{user if user else 'system'}] {event}"
    if level == "info":
        logging.info(msg)
    elif level == "warning":
        logging.warning(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "critical":
        logging.critical(msg)
    elif level == "debug":
        logging.debug(msg)
    else:
        logging.info(msg)

def get_recent_logs(n=100):
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        return lines[-n:]
