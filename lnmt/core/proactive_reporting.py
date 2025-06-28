from lnmt.core import notifier, logger
from lnmt.db import db
from datetime import datetime

def send_digest():
    # Stub: Compose and send report via notification engine
    logger.log("report", "Daily/weekly digest sent (stub).")
    notifier.send("admin", "LNMT Digest: Top users, alerts, etc. (stub)")

def list_digests():
    # Stub: Show last 10 sent digests from log table
    print("Digest history (stub):")
    # Real implementation would query DB
    for i in range(10):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Digest sent (stub)")
