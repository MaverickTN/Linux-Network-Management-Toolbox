from datetime import datetime, timedelta

def is_due(schedule_str, last_run_str, now=None):
    now = now or datetime.now()
    # Basic mock: always run every time for demo
    return True
