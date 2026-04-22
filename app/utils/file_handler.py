import shutil
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings
from app.utils.logger import logger


MAX_BYTES = settings.max_file_size_mb * 1024 * 1024


async def save_upload(file: UploadFile, job_id: str, label: str) -> Path:
    """Save uploaded PDF to disk, return path."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{label} must be a PDF file")

    dest_dir = settings.upload_dir / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{label}.pdf"

    size = 0
    async with aiofiles.open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > MAX_BYTES:
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"{label} exceeds {settings.max_file_size_mb}MB limit"
                )
            await out.write(chunk)

    logger.info(f"Saved {label} → {dest_path} ({size / 1024:.1f} KB)")
    return dest_path


def cleanup_job_files(job_id: str):
    """Remove upload temp files after processing."""
    upload_path = settings.upload_dir / job_id
    if upload_path.exists():
        shutil.rmtree(upload_path)
        logger.info(f"Cleaned up uploads for job {job_id}")


def get_output_dir(job_id: str) -> Path:
    """Get/create output directory for a job."""
    out_dir = settings.output_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir