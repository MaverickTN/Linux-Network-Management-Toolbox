#!/usr/bin/env python3

import time
from lnmt.core.job_queue_service import JobQueueService
from lnmt.core.schedule import load_schedules, remove_expired_blocks

def main():
    print("Starting LMNT Job Queue Service...")
    job_service = JobQueueService()
    job_service.start()

    # Optional: clean up old blocks at launch
    schedules = load_schedules()
    for mac in schedules.keys():
        remove_expired_blocks(mac)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Shutting down job queue service...")
        job_service.stop()

if __name__ == "__main__":
    main()
