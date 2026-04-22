from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.utils.job_store import JobStatus


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    message: str
    error: Optional[str] = None


class ReportLinks(BaseModel):
    html: str
    docx: str
    pdf: str


class ReportResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    download_links: Optional[ReportLinks] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    environment: str