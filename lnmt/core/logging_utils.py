# lnmt/core/logging_utils.py

import logging
import os
from datetime import datetime

LOG_DIR = "/var/log/lnmt"
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "lnmt.log")

def setup_logging(log_file=DEFAULT_LOG_FILE, level=logging.INFO):
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def log_event(event, level=logging.INFO, logger_name="lnmt"):
    logger = logging.getLogger(logger_name)
    if level == logging.DEBUG:
        logger.debug(event)
    elif level == logging.WARNING:
        logger.warning(event)
    elif level == logging.ERROR:
        logger.error(event)
    else:
        logger.info(event)

def log_cli_command(user, command, args):
    log_event(
        f"CLI command run by {user}: {command} {args}",
        level=logging.INFO,
        logger_name="lnmt.cli"
    )

def log_web_event(user, event, details=""):
    log_event(
        f"Web event by {user}: {event} {details}",
        level=logging.INFO,
        logger_name="lnmt.web"
    )
