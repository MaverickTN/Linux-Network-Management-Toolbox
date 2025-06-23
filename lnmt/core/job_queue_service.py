# lnmt/core/job_queue_service.py

import threading
import queue
import logging
from datetime import datetime

class JobQueueService:
    def __init__(self):
        self.queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        self.logger = logging.getLogger("JobQueueService")

    def start(self):
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            self.logger.info("Job queue started.")

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()

    def add_job(self, func, *args, **kwargs):
        self.queue.put((func, args, kwargs))
        self.logger.info(f"Job added: {func.__name__} with args={args} kwargs={kwargs}")

    def _worker(self):
        while self.running:
            try:
                func, args, kwargs = self.queue.get(timeout=1)
                self.logger.info(f"Starting job: {func.__name__}")
                func(*args, **kwargs)
                self.logger.info(f"Completed job: {func.__name__} at {datetime.now()}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in job: {e}")

job_queue = JobQueueService()
