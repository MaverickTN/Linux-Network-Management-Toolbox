import json
import os
from pathlib import Path
from lnmt.core.user_profile_manager import get_profile

TOAST_LOG = "/var/lib/lnmt/toast_notifications.log"

def log_toast(user, message, level="info"):
    """Append a toast event to the persistent log."""
    Path(TOAST_LOG).parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "user": user,
        "message": message,
        "level": level
    }
    with open(TOAST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def get_recent_toasts(user=None, limit=20):
    if not os.path.exists(TOAST_LOG):
        return []
    lines = []
    with open(TOAST_LOG, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                if user is None or event.get("user") == user:
                    lines.append(event)
            except Exception:
                continue
    return lines[-limit:]

def toast_enabled(user):
    profile = get_profile(user)
    if not profile:
        return True
    return profile.get("notification_settings", {}).get("toast", True)

def send_toast(user, message, level="info"):
    """Send a toast notification, if enabled."""
    if toast_enabled(user):
        log_toast(user, message, level)
        # Web: Use websocket or Ajax push (not implemented here)
        # CLI: Print colorized output if in TTY
        # This is a placeholder; actual dispatch will depend on integration
        print(f"[{level.upper()}] ({user}) {message}")

def notify_all_users(message, level="info"):
    """Broadcast a toast to all profiles."""
    from lnmt.core.user_profile_manager import get_all_profiles
    for user in get_all_profiles():
        send_toast(user, message, level)
