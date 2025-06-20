import threading
import queue
import time
import uuid
from typing import Callable, Any, Dict, List

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"

class Job:
    def __init__(self, action: Callable, args=None, kwargs=None, description="", user=None, steps:List[str]=None):
        self.job_id = str(uuid.uuid4())
        self.action = action
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}
        self.description = description
        self.user = user
        self.steps = steps or []
        self.step_messages = []
        self.current_step = 0
        self.status = JobStatus.PENDING
        self.result = None
        self.error = None
        self.created = time.time()
        self.updated = time.time()

    def run(self, log_callback=None, notify_callback=None):
        self.status = JobStatus.RUNNING
        self.updated = time.time()
        if notify_callback:
            notify_callback(self, "Job started", "info")
        try:
            if self.steps:
                for idx, step in enumerate(self.steps):
                    self.current_step = idx
                    self.step_messages.append(f"Step {idx+1}/{len(self.steps)}: {step}")
                    if log_callback:
                        log_callback(self, step)
                    if notify_callback:
                        notify_callback(self, step, "info")
                    # Simulate a step (could be replaced with actual step-by-step logic)
                    time.sleep(0.1)
            self.result = self.action(*self.args, **self.kwargs)
            self.status = JobStatus.SUCCESS
            if notify_callback:
                notify_callback(self, "Job completed successfully", "success")
        except Exception as e:
            self.status = JobStatus.ERROR
            self.error = str(e)
            if notify_callback:
                notify_callback(self, f"Job failed: {e}", "danger")
        finally:
            self.updated = time.time()

class JobQueueService:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
        self._log_callback = None
        self._notify_callback = None

    def set_log_callback(self, cb):
        self._log_callback = cb

    def set_notify_callback(self, cb):
        self._notify_callback = cb

    def submit(self, action: Callable, args=None, kwargs=None, description="", user=None, steps:List[str]=None):
        job = Job(action, args, kwargs, description, user, steps)
        self._jobs[job.job_id] = job
        self._queue.put(job)
        if self._notify_callback:
            self._notify_callback(job, "Job queued", "info")
        return job.job_id

    def _worker(self):
        while True:
            job: Job = self._queue.get()
            job.run(log_callback=self._log_callback, notify_callback=self._notify_callback)
            self._queue.task_done()

    def status(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            return {
                "job_id": job.job_id,
                "description": job.description,
                "user": job.user,
                "status": job.status,
                "result": job.result,
                "error": job.error,
                "steps": job.steps,
                "step_messages": job.step_messages,
                "current_step": job.current_step,
                "created": job.created,
                "updated": job.updated,
            }
        return None

    def all_jobs(self) -> List[Dict[str, Any]]:
        return [self.status(jid) for jid in self._jobs]

    def notify_all(self, message, level="info"):
        # Could integrate with websockets, broadcast, etc.
        print(f"[NOTIFY-{level.upper()}] {message}")

# Singleton for app-wide use
job_queue_service = JobQueueService()

def queue_cli_action(action, args=None, kwargs=None, description="", user=None, steps=None):
    return job_queue_service.submit(action, args, kwargs, description, user, steps)
