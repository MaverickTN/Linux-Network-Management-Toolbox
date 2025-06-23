# lnmt/core/job_queue.py

import threading
import time
import uuid
from collections import deque

from lnmt.core.logging import log_queue_event

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class Job:
    def __init__(self, func, args=(), kwargs=None, user=None, description=None, steps=None):
        self.job_id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.user = user
        self.status = JobStatus.PENDING
        self.result = None
        self.error = None
        self.description = description or func.__name__
        self.start_time = None
        self.end_time = None
        self.steps = steps or []
        self.current_step = None

    def run(self):
        self.status = JobStatus.RUNNING
        self.start_time = time.time()
        try:
            if self.steps:
                for idx, (step_name, step_func) in enumerate(self.steps):
                    self.current_step = step_name
                    log_queue_event(self.job_id, f"Step {idx+1}: {step_name} started", self.user, step=step_name, status="running")
                    step_func()
                    log_queue_event(self.job_id, f"Step {idx+1}: {step_name} completed", self.user, step=step_name, status="success")
            self.result = self.func(*self.args, **self.kwargs)
            self.status = JobStatus.SUCCESS
            log_queue_event(self.job_id, f"Job completed", self.user, step="final", status="success")
        except Exception as e:
            self.error = str(e)
            self.status = JobStatus.ERROR
            log_queue_event(self.job_id, f"Job failed: {self.error}", self.user, step=self.current_step, status="error")
        finally:
            self.end_time = time.time()

class JobQueueService:
    def __init__(self):
        self.jobs = {}
        self.queue = deque()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def add_job(self, func, args=(), kwargs=None, user=None, description=None, steps=None):
        job = Job(func, args, kwargs, user, description, steps)
        with self.lock:
            self.jobs[job.job_id] = job
            self.queue.append(job)
            log_queue_event(job.job_id, f"Job queued: {job.description}", user, status="queued")
        return job.job_id

    def _worker(self):
        while True:
            job = None
            with self.lock:
                if self.queue:
                    job = self.queue.popleft()
            if job:
                log_queue_event(job.job_id, f"Job started: {job.description}", job.user, status="started")
                job.run()
            else:
                time.sleep(0.2)

    def get_job(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def get_status(self, job_id):
        job = self.get_job(job_id)
        if job:
            return {
                "status": job.status,
                "result": job.result,
                "error": job.error,
                "description": job.description,
                "user": job.user,
                "start_time": job.start_time,
                "end_time": job.end_time,
                "current_step": job.current_step,
            }
        return None

    def list_jobs(self, n=20):
        with self.lock:
            return [job for job in list(self.jobs.values())[-n:]]

# Singleton instance for app-wide use
job_queue = JobQueueService()
