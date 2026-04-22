from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from app.models.response import StatusResponse, ReportResponse, ReportLinks
from app.utils.job_store import job_store, JobStatus
from app.utils.logger import logger

router = APIRouter()


@router.get("/status/{job_id}", response_model=StatusResponse, tags=["Pipeline"])
async def get_job_status(job_id: str):
    """
    Poll the processing status of a DDR generation job.
    
    Progress stages:
    - 5%   → Pending
    - 10%  → Extracting PDFs
    - 30%  → AI extraction
    - 55%  → Merging findings
    - 70%  → Generating DDR
    - 85%  → Exporting files
    - 100% → Done
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
    )


@router.get("/report/{job_id}", response_model=ReportResponse, tags=["Pipeline"])
async def get_report(job_id: str):
    """
    Get the completed DDR report with download links.
    Only available when job status is 'done'.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status == JobStatus.FAILED:
        return ReportResponse(
            job_id=job_id,
            status=job.status,
            message="Report generation failed",
            error=job.error,
        )

    if job.status != JobStatus.DONE:
        return ReportResponse(
            job_id=job_id,
            status=job.status,
            message=job.message,
        )

    return ReportResponse(
        job_id=job_id,
        status=job.status,
        message=job.message,
        download_links=ReportLinks(
            html=f"/api/v1/report/{job_id}/download/html",
            docx=f"/api/v1/report/{job_id}/download/docx",
            pdf=f"/api/v1/report/{job_id}/download/pdf",
        ),
    )


@router.get("/report/{job_id}/download/html", tags=["Downloads"])
async def download_html(job_id: str):
    """Download DDR report as HTML."""
    return _serve_file(job_id, "html", "ddr_report.html", "text/html")


@router.get("/report/{job_id}/download/docx", tags=["Downloads"])
async def download_docx(job_id: str):
    """Download DDR report as Word document."""
    return _serve_file(
        job_id, "docx", "ddr_report.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.get("/report/{job_id}/download/pdf", tags=["Downloads"])
async def download_pdf(job_id: str):
    """Download DDR report as PDF."""
    return _serve_file(job_id, "pdf", "ddr_report.pdf", "application/pdf")


@router.get("/report/{job_id}/preview", response_class=HTMLResponse, tags=["Downloads"])
async def preview_html(job_id: str):
    """Preview DDR report directly in browser."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(status_code=400, detail="Report not ready yet")

    html_path = Path(job.result["html"])
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="HTML report file not found")

    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


def _serve_file(job_id: str, fmt: str, filename: str, media_type: str) -> FileResponse:
    """Helper to validate job and serve a file download."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=400,
            detail=f"Report not ready. Current status: {job.status}"
        )

    file_path = Path(job.result[fmt])
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{fmt.upper()} report file not found"
        )

    logger.info(f"Serving {fmt.upper()} download for job {job_id}")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )