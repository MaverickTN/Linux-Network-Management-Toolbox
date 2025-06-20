import logging
import logging.handlers
import os

LOG_DIR = "/var/log/lnmt"
LOG_FILE = os.path.join(LOG_DIR, "lnmt.log")

def setup_logging():
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
        except Exception:
            # Fall back to local log file if unable to create system log dir
            global LOG_FILE
            LOG_FILE = "lnmt.log"
    logger = logging.getLogger("lnmt")
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s [%(funcName)s:%(lineno)d] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

def log_auth_event(username, role, event_type, status, message):
    logger = logging.getLogger("lnmt")
    logger.info(f"AUTH: user={username} role={role} event={event_type} status={status} msg={message}")

def log_queue_event(event, status, details=""):
    logger = logging.getLogger("lnmt")
    logger.info(f"QUEUE: event={event} status={status} details={details}")

def log_error(message):
    logger = logging.getLogger("lnmt")
    logger.error(f"ERROR: {message}")

def log_timer_event(timer_name, step, status, details=""):
    logger = logging.getLogger("lnmt")
    logger.info(f"TIMER: {timer_name} step={step} status={status} details={details}")

def log_cli_event(command, user, status, details=""):
    logger = logging.getLogger("lnmt")
    logger.info(f"CLI: command={command} user={user} status={status} details={details}")
