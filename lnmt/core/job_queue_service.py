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
        self.logger.debug(f"Job added to queue: {func.__name__} args={args} kwargs={kwargs}")

    def _worker(self):
        while self.running:
            try:
                func, args, kwargs = self.queue.get(timeout=1)
                self.logger.info(f"Executing job: {func.__name__}")
                result = func(*args, **kwargs)
                self.logger.debug(f"Job result: {result}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.exception(f"Job execution failed: {e}")
