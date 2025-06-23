import threading
import queue
import uuid
from lnmt.logger import log_queue_event, setup_logging

class JobQueueService:
    def __init__(self):
        self.job_queue = queue.Queue()
        self.jobs = {}  # job_id -> {"status": ..., "result": ..., "error": ...}
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        setup_logging()

    def start(self):
        if not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self.worker, daemon=True)
            self.worker_thread.start()

    def enqueue(self, func, *args, **kwargs):
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {"status": "pending"}
        log_queue_event("enqueue", "pending", f"job_id={job_id}")
        self.job_queue.put((job_id, func, args, kwargs))
        return job_id

    def worker(self):
        while True:
            job_id, func, args, kwargs = self.job_queue.get()
            log_queue_event("start", "running", f"job_id={job_id}")
            self.jobs[job_id]["status"] = "running"
            try:
                result = func(*args, **kwargs)
                self.jobs[job_id]["status"] = "success"
                self.jobs[job_id]["result"] = result
                log_queue_event("finish", "success", f"job_id={job_id}")
            except Exception as e:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["error"] = str(e)
                log_queue_event("finish", "error", f"job_id={job_id} error={e}")

    def get_status(self, job_id):
        return self.jobs.get(job_id, {"status": "unknown"})

# Usage pattern (for reference):
# job_queue = JobQueueService()
# job_queue.start()
# job_id = job_queue.enqueue(your_function, arg1, arg2)
