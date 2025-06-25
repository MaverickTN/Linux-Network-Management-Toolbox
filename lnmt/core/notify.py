import smtplib
from email.message import EmailMessage
from datetime import datetime

LOG_PATH = "/etc/lnmt/notifications.log"
EMAIL_ENABLED = True  # Can be toggled via config
EMAIL_FROM = "lnmt@localhost"
EMAIL_TO = ["admin@localhost"]
EMAIL_SUBJECT = "[LNMT Alert] Notification"

def send_email(subject, body):
    if not EMAIL_ENABLED:
        return
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP("localhost") as smtp:
            smtp.send_message(msg)
    except Exception as e:
        log_local(f"EMAIL FAIL: {e}")

def log_local(message):
    now = datetime.utcnow().isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(f"[{now}] {message}\n")

def notify(event, details):
    body = f"LNMT Event: {event}\nDetails: {details}"
    log_local(body)
    send_email(f"[LNMT] {event}", body)
