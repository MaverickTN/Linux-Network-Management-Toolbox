# inetctl/core/logging.py

import sys
from datetime import datetime
from pathlib import Path

from inetctl.theme import cli_color, get_theme

DEFAULT_LOGFILE = "/var/log/lnmt.log"

class LNMTLogger:
    def __init__(self, logfile=DEFAULT_LOGFILE, theme="dark"):
        self.logfile = Path(logfile)
        self.theme = theme

    def log(self, message, level="INFO", color="primary", to_stdout=True, step=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] [{level}]"
        if step:
            prefix += f" [STEP: {step}]"
        colored = cli_color(f"{prefix} {message}", color, self.theme)

        if to_stdout:
            print(colored, file=sys.stdout if level != "ERROR" else sys.stderr)
        # Always write to log file (uncolored)
        try:
            self.logfile.parent.mkdir(parents=True, exist_ok=True)
            with self.logfile.open("a") as f:
                f.write(f"{prefix} {message}\n")
        except Exception as e:
            # Fail silently or print to stderr if desired
            print(f"Logging error: {e}", file=sys.stderr)

    def info(self, message, step=None):
        self.log(message, level="INFO", color="primary", step=step)

    def success(self, message, step=None):
        self.log(message, level="SUCCESS", color="success", step=step)

    def warning(self, message, step=None):
        self.log(message, level="WARNING", color="warning", step=step)

    def error(self, message, step=None):
        self.log(message, level="ERROR", color="danger", to_stdout=True, step=step)

    def step(self, message, step_name):
        self.info(message, step=step_name)

    def critical(self, message, step=None):
        self.log(message, level="CRITICAL", color="danger", to_stdout=True, step=step)

# For general use
logger = LNMTLogger()

# Helper function for direct logging (simple usage)
def log(message, level="INFO", color="primary", step=None):
    logger.log(message, level, color, step=step)

def step_notify(message, step_name):
    logger.step(message, step_name)
