from lnmt.db import db
from lnmt.core import logger, notifier
from datetime import datetime

def show_status():
    print("Self-healing monitored modules (stub):")
    for mod in ["traffic", "notifier", "pihole", "dns"]:
        print(f"{mod}: OK (stub)")

def show_log():
    logs = db.query("SELECT timestamp, module, action, status, attempts, error FROM self_heal_log ORDER BY timestamp DESC LIMIT 10")
    for l in logs:
        print(f"{l['timestamp']} {l['module']} {l['action']} {l['status']} attempts={l['attempts']} {l['error']}")

def test_heal(module):
    print(f"Simulating self-heal on {module} (stub).")
    # Would trigger restart logic, log, and notify admin

def health_check_loop():
    # Stub: run every minute, check health, restart if needed, log
    pass

def restart_module(module):
    # Attempt app-level restart, log outcome, notify if needed (stub)
    print(f"Restarted module {module} (stub).")
    logger.log("self_heal", f"Restarted {module}.")
    notifier.send("admin", f"{module} auto-restarted by self-healing engine (stub).")
