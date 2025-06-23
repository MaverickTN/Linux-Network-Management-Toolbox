# lnmt/core/logger.py

import logging
import os
from datetime import datetime

LOG_DIR = "/var/log/lnmt"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "lnmt.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def get_logger(name="lnmt"):
    return logging.getLogger(name)

def log_event(event, level="info"):
    logger = get_logger()
    msg = f"{event} | {datetime.now().isoformat()}"
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "debug":
        logger.debug(msg)
    else:
        logger.info(msg)
