# lnmt/core/logging_utils.py

import logging
from datetime import datetime
import sys

LOG_FILE = "/var/log/lnmt/lnmt.log"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log_event(message, level="info"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    else:
        logging.info(f"[{level.upper()}] {message}")

def log_warning(message):
    log_event(message, level="warning")

def log_error(message):
    log_event(message, level="error")

setup_logging()
