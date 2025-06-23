# lnmt/core/job_queue_service.py

import threading
import queue
import logging
import time
import uuid

logger = logging.getLogger("lnmt.job_queue")

class Job:
    def __init__(self, func, args=(), kwargs=None, description="", user=None):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.description = description
        self.user = user
        self.status = "pending"
        self.result = None
        self.error = None
        self.steps = []
        self.timestamp = time.time()

class JobQueueService:
    def __init__(self):
        self.queue = queue.Queue()
        self.active_jobs = {}
        self.log = []
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def submit(self, func, *args, description="", user=None, **kwargs):
        job = Job(func, args, kwargs, description, user)
        self.queue.put(job)
        self.active_jobs[job.id] = job
        logger.info(f"Job submitted: {job.description} (id={job.id})")
        return job.id

    def get_status(self, job_id):
        job = self.active_jobs.get(job_id)
        if job:
            return job.status, job.result, job.error, job.steps
        return "not_found", None, None, []

    def _worker_loop(self):
        while True:
            job = self.queue.get()
            job.status = "running"
            try:
                self._log_step(job, f"Starting job: {job.description}")
                job.result = job.func(*job.args, **job.kwargs)
                job.status = "success"
                self._log_step(job, "Job completed successfully.")
            except Exception as e:
                job.error = str(e)
                job.status = "failed"
                self._log_step(job, f"Job failed: {e}")
            self.log.append(job)
            self.queue.task_done()

    def _log_step(self, job, message):
        job.steps.append({"timestamp": time.time(), "message": message})
        logger.info(f"[Job {job.id}] {message}")

    def get_all_jobs(self):
        return list(self.active_jobs.values())

# Singleton instance for import use
job_queue_service = JobQueueService()
