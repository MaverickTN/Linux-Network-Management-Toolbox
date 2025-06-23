# lnmt/core/job_queue.py

import threading
import queue
import logging
import time

class JobQueueService:
    def __init__(self):
        self.job_queue = queue.Queue()
        self.history = []
        self._stop_event = threading.Event()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()
        self.logger = logging.getLogger("lnmt.JobQueueService")

    def enqueue(self, job, *args, **kwargs):
        self.job_queue.put((job, args, kwargs))
        self.logger.info(f"Job enqueued: {job.__name__}")

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                job, args, kwargs = self.job_queue.get(timeout=1)
                self.logger.info(f"Job started: {job.__name__}")
                try:
                    result = job(*args, **kwargs)
                    status = "success"
                except Exception as e:
                    result = str(e)
                    status = "error"
                    self.logger.error(f"Job failed: {job.__name__} ({e})")
                self.history.append({
                    "job": job.__name__,
                    "args": args,
                    "kwargs": kwargs,
                    "status": status,
                    "result": result,
                    "timestamp": time.time(),
                })
                self.job_queue.task_done()
            except queue.Empty:
                continue

    def stop(self):
        self._stop_event.set()
        self.worker.join()

    def get_history(self, limit=50):
        return self.history[-limit:]
