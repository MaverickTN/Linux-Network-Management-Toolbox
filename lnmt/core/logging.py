import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

LOG_DIR = "/var/log/lnmt"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "lnmt.log")

logger = logging.getLogger("lnmt")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_event(message, level="info"):
    ts = datetime.utcnow().isoformat()
    if level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    elif level == "debug":
        logger.debug(message)
    else:
        logger.info(message)
    # For web: Could also queue toasts or notifications here
    print(f"{ts} [{level.upper()}] {message}")

def log_step(action, status="ok"):
    log_event(f"STEP: {action} [{status}]", "info")
