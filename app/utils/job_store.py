import uuid
import time
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from app.config import settings


class JobStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    GENERATING = "generating"
    EXPORTING = "exporting"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0                        # 0-100
    message: str = "Job created"
    result: Optional[Dict[str, Any]] = None  # Final report paths
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def update(self, status: JobStatus, message: str, progress: int):
        self.status = status
        self.message = message
        self.progress = progress
        self.updated_at = time.time()

    def fail(self, error: str):
        self.status = JobStatus.FAILED
        self.error = error
        self.updated_at = time.time()

    def complete(self, result: Dict[str, Any]):
        self.status = JobStatus.DONE
        self.result = result
        self.progress = 100
        self.message = "DDR Report generated successfully"
        self.updated_at = time.time()


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(self) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id)
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        self._cleanup_expired()
        return self._jobs.get(job_id)

    def _cleanup_expired(self):
        now = time.time()
        expired = [
            jid for jid, job in self._jobs.items()
            if now - job.created_at > settings.job_ttl_seconds
        ]
        for jid in expired:
            del self._jobs[jid]


# Singleton instance
job_store = JobStore()