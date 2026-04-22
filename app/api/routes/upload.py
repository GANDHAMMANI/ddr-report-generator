import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.models.response import UploadResponse
from app.utils.job_store import job_store, JobStatus
from app.utils.file_handler import save_upload, cleanup_job_files, get_output_dir
from app.utils.logger import logger

router = APIRouter()


async def run_pipeline(job_id: str, inspection_path: Path, thermal_path: Path):
    job = job_store.get_job(job_id)
    if not job:
        return

    try:
        # Stage 1: Ingestion
        job.update(JobStatus.EXTRACTING, "Extracting text and images from PDFs...", 10)
        logger.info(f"[{job_id}] Stage 1: Ingestion")

        from app.core.ingestion import ingest_pdf
        inspection_doc = await asyncio.to_thread(ingest_pdf, inspection_path, "inspection")
        thermal_doc    = await asyncio.to_thread(ingest_pdf, thermal_path, "thermal")

        # Collect ALL images from both docs
        all_images = inspection_doc.images + thermal_doc.images
        logger.info(f"[{job_id}] Total images collected: {len(all_images)}")

        # Stage 2: Extraction
        job.update(JobStatus.EXTRACTING, "Analyzing documents with AI...", 30)
        logger.info(f"[{job_id}] Stage 2: Extraction")

        from app.core.extractor import extract_inspection_data, extract_thermal_data
        inspection_data = await asyncio.to_thread(extract_inspection_data, inspection_doc)
        thermal_data    = await asyncio.to_thread(extract_thermal_data, thermal_doc)

        # Stage 3: Merging
        job.update(JobStatus.PROCESSING, "Merging inspection and thermal findings...", 55)
        logger.info(f"[{job_id}] Stage 3: Merging")

        from app.core.merger import merge_findings
        merged_data = await asyncio.to_thread(merge_findings, inspection_data, thermal_data)

        # Stage 4: DDR Generation
        job.update(JobStatus.GENERATING, "Generating DDR report sections...", 70)
        logger.info(f"[{job_id}] Stage 4: DDR Generation")

        from app.core.generator import generate_ddr
        ddr = await asyncio.to_thread(generate_ddr, merged_data)

        # Stage 4b: Distribute images across areas
        from app.core.image_handler import distribute_images_to_areas, finalize_image_placement
        ddr = distribute_images_to_areas(ddr, all_images)
        ddr = finalize_image_placement(ddr)

        # Stage 5: Export
        job.update(JobStatus.EXPORTING, "Exporting report to DOCX, PDF, and HTML...", 85)
        logger.info(f"[{job_id}] Stage 5: Export")

        output_dir = get_output_dir(job_id)

        from app.exporters.html_exporter import export_html
        from app.exporters.docx_exporter import export_docx
        from app.exporters.pdf_exporter  import export_pdf

        html_path = await asyncio.to_thread(export_html, ddr, output_dir)
        docx_path = await asyncio.to_thread(export_docx, ddr, output_dir)
        pdf_path  = await asyncio.to_thread(export_pdf,  ddr, output_dir)

        job.complete({
            "html": str(html_path),
            "docx": str(docx_path),
            "pdf":  str(pdf_path),
            "report_id":    ddr.report_id,
            "property_name": ddr.property_name,
            "generated_at": ddr.generated_at,
        })

        logger.info(f"[{job_id}] ✅ Pipeline complete")

    except Exception as e:
        logger.error(f"[{job_id}] ❌ Pipeline failed: {e}")
        job.fail(str(e))
    finally:
        cleanup_job_files(job_id)


@router.post("/upload", response_model=UploadResponse, tags=["Pipeline"])
async def upload_documents(
    background_tasks: BackgroundTasks,
    inspection_report: UploadFile = File(..., description="Visual inspection report PDF"),
    thermal_report:    UploadFile = File(..., description="Thermal imaging report PDF"),
):
    job = job_store.create_job()
    job_id = job.job_id
    logger.info(f"New job created: {job_id}")

    try:
        inspection_path = await save_upload(inspection_report, job_id, "inspection")
        thermal_path    = await save_upload(thermal_report,    job_id, "thermal")
    except HTTPException as e:
        job.fail(e.detail)
        raise

    background_tasks.add_task(run_pipeline, job_id, inspection_path, thermal_path)
    job.update(JobStatus.PENDING, "Files uploaded. Pipeline starting...", 5)

    return UploadResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Files uploaded successfully. DDR generation started.",
    )