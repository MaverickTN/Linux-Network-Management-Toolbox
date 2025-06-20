# inetctl/core/notifications.py

import threading
import json
from queue import Queue
from datetime import datetime

# Global event bus for notifications
notification_queue = Queue()

class NotificationEvent:
    def __init__(self, level, message, user=None, job=None, step=None, timestamp=None, extra=None):
        self.level = level
        self.message = message
        self.user = user
        self.job = job
        self.step = step
        self.timestamp = timestamp or datetime.now().isoformat()
        self.extra = extra or {}

    def as_dict(self):
        return {
            "level": self.level,
            "message": self.message,
            "user": self.user,
            "job": self.job,
            "step": self.step,
            "timestamp": self.timestamp,
            **self.extra
        }

def send_notification(level, message, user=None, job=None, step=None, extra=None):
    """Place notification event on the global queue for processing."""
    event = NotificationEvent(level, message, user, job, step, extra=extra)
    notification_queue.put(event)
    # If running in the web context, you might want to immediately push to sockets, etc.

def process_notifications(handlers=None, blocking=False):
    """
    Background thread or direct call to process queued notifications.
    'handlers' is a list of callables taking a NotificationEvent.
    """
    if handlers is None:
        handlers = [print_notification]

    def run():
        while True:
            event = notification_queue.get()
            if event is None:  # Sentinel for shutdown
                break
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Notification handler error: {e}")

    if blocking:
        run()
    else:
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t

def print_notification(event):
    """Default handler: print to CLI (used for debugging or simple notifications)."""
    from inetctl.theme import cli_color, get_theme
    theme = get_theme()
    color = event.level
    msg = f"[{event.timestamp}]"
    if event.user:
        msg += f" [user:{event.user}]"
    if event.job:
        msg += f" [job:{event.job}]"
    if event.step:
        msg += f" [step:{event.step}]"
    msg += f" {cli_color(event.message, color, theme_key=theme['name'].lower())}"
    print(msg)

# Example web socket or toast handler (to be plugged in from Flask/web app)
def websocket_notify_handler(event):
    # This would interface with Flask-SocketIO, etc.
    # socketio.emit('notification', event.as_dict(), broadcast=True)
    pass

def toast_notify_handler(event):
    # Placeholder for integrating with frontend JS toasts
    pass

# Example usage:
# send_notification("info", "System initialized", user="admin")
# In your app startup, you might run:
# process_notifications([print_notification, websocket_notify_handler])

