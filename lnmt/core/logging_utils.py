# lnmt/core/logging_utils.py

import logging
from datetime import datetime
import os

LOG_DIR = "/var/log/lnmt"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "lnmt.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_event(message):
    logging.info(message)

def log_warning(message):
    logging.warning(message)

def log_error(message):
    logging.error(message)

def log_cli_action(user, action, details=None):
    msg = f"[CLI] User: {user}, Action: {action}"
    if details:
        msg += f", Details: {details}"
    log_event(msg)

def log_web_action(user, action, details=None):
    msg = f"[WEB] User: {user}, Action: {action}"
    if details:
        msg += f", Details: {details}"
    log_event(msg)

def get_recent_logs(lines=100):
    try:
        with open(LOG_FILE, "r") as f:
            return "".join(f.readlines()[-lines:])
    except Exception:
        return ""
