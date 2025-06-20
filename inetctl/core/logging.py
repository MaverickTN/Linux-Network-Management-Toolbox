# inetctl/core/logging.py

import logging
import logging.handlers
import os
import threading
from datetime import datetime

LOG_DIR = "/var/log/inetctl"
LOG_FILE = "toolbox.log"
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 10

if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        # fallback to local directory if permission denied
        LOG_DIR = "."

_log_path = os.path.join(LOG_DIR, LOG_FILE)

# Configure rotating file handler
file_handler = logging.handlers.RotatingFileHandler(
    _log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(threadName)s %(module)s:%(lineno)d: %(message)s'
)
file_handler.setFormatter(formatter)

logger = logging.getLogger("inetctl")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    logger.addHandler(file_handler)

_log_lock = threading.Lock()
_step_callbacks = []

def log_event(message, level="info", **kwargs):
    """Log an event with optional extra fields."""
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "success": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    msg = f"{message} | {kwargs}" if kwargs else message
    with _log_lock:
        logger.log(level_map.get(level, logging.INFO), msg)
    # Real-time broadcast to users (stub, for websocket or notification hook)
    _broadcast_step({"message": message, "level": level, "timestamp": datetime.now().isoformat(), **kwargs})

def log_step(step, job_id=None, user=None, level="info"):
    """Log and broadcast a step in a multi-step operation."""
    msg = f"Step: {step}"
    if user:
        msg += f" (user: {user})"
    if job_id:
        msg += f" [job:{job_id}]"
    log_event(msg, level=level, step=step, user=user, job_id=job_id)

def add_step_callback(callback):
    """Register a function to receive step notifications (for WebSocket/Flask-SocketIO/etc)."""
    _step_callbacks.append(callback)

def _broadcast_step(step_obj):
    """Broadcast step to all callbacks (real-time UI notification, etc)."""
    for cb in _step_callbacks:
        try:
            cb(step_obj)
        except Exception as ex:
            logger.error(f"Step callback failed: {ex}")

def get_recent_logs(limit=100):
    """Return recent log lines (for web UI/status)."""
    try:
        with open(_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-limit:]
    except Exception:
        return []

def cli_log(message, style="info", theme="dark"):
    """Print message in CLI color (integrated with theme.py)."""
    from .theme import cli_color
    print(cli_color(message, style, theme))

def flush_logs():
    """Flush all handlers."""
    for handler in logger.handlers:
        handler.flush()
