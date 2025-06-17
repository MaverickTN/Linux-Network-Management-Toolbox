import threading
import queue
import uuid
import time
from datetime import datetime

class JobQueueService:
    def __init__(self):
        self.job_queue = queue.Queue()
        self.job_status = {}
        self.log = []
        self.running = True
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()

    def add_job(self, action, **kwargs):
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "action": action,
            "kwargs": kwargs,
            "status": "pending",
            "message": f"Job {action} queued.",
            "created": datetime.now().isoformat(),
            "steps": []
        }
        self.job_status[job_id] = job
        self.job_queue.put(job)
        self.log_step(job_id, f"Job created: {action}")
        return job_id

    def get_status(self, job_id):
        job = self.job_status.get(job_id)
        if not job:
            return "notfound", "Job ID not found"
        return job["status"], job.get("message", "")

    def log_step(self, job_id, message):
        job = self.job_status.get(job_id)
        if job:
            step = {
                "time": datetime.now().isoformat(),
                "message": message
            }
            job.setdefault("steps", []).append(step)
            self.log.append({"job_id": job_id, **step})

    def worker(self):
        while self.running:
            try:
                job = self.job_queue.get(timeout=1)
            except queue.Empty:
                continue
            job["status"] = "running"
            self.log_step(job["id"], f"Job running: {job['action']}")
            try:
                # Simulated execution step-by-step; replace with actual logic
                self.log_step(job["id"], "Pre-execution checks...")
                time.sleep(0.5)
                if job["action"] == "toggle_access":
                    self.log_step(job["id"], f"Toggling access for {job['kwargs'].get('mac')}")
                    # Insert block/allow/shorewall code here
                    time.sleep(1)
                elif job["action"] == "update_host":
                    self.log_step(job["id"], f"Updating host config for {job['kwargs'].get('mac')}")
                    # Insert host update logic here
                    time.sleep(1)
                # ... add more action handlers as needed
                job["status"] = "success"
                job["message"] = "Job completed successfully."
                self.log_step(job["id"], "Job completed successfully.")
            except Exception as ex:
                job["status"] = "failed"
                job["message"] = f"Job failed: {ex}"
                self.log_step(job["id"], f"Error: {ex}")
            finally:
                self.job_queue.task_done()

    def stop(self):
        self.running = False
        self.worker_thread.join()

    def get_log(self, count=50):
        """Return the last N log entries"""
        return self.log[-count:]

    def get_job_steps(self, job_id):
        job = self.job_status.get(job_id)
        if not job:
            return []
        return job.get("steps", [])

# Instantiate one global service if needed
job_queue_service = JobQueueService()
