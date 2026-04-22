import base64
import uuid
from pathlib import Path
from typing import List
import fitz  # PyMuPDF fallback for images

from app.models.pipeline import RawDocument, ImageData
from app.utils.logger import logger


def extract_images_pymupdf(pdf_path: Path, source: str) -> List[ImageData]:
    """Extract images from PDF using PyMuPDF with Base64 encoding."""
    images = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                b64 = base64.b64encode(image_bytes).decode("utf-8")
                images.append(ImageData(
                    image_id=f"{source}_p{page_num+1}_img{img_index+1}_{uuid.uuid4().hex[:6]}",
                    base64_data=b64,
                    format=image_ext if image_ext in ["jpeg", "jpg", "png"] else "jpeg",
                    source=source,
                    page_number=page_num + 1,
                    caption=f"{source.title()} image from page {page_num+1}",
                ))
        doc.close()
        logger.info(f"Extracted {len(images)} images from {source} PDF via PyMuPDF")
    except Exception as e:
        logger.warning(f"PyMuPDF image extraction failed for {source}: {e}")
    return images


def extract_text_pymupdf(pdf_path: Path) -> str:
    """Fallback text extraction using PyMuPDF if OpenDataLoader unavailable."""
    text_parts = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("markdown")
            text_parts.append(f"\n\n## Page {page_num + 1}\n\n{text}")
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF text extraction failed: {e}")
    return "\n".join(text_parts)


def ingest_pdf(pdf_path: Path, source: str) -> RawDocument:
    """
    Main ingestion function.
    Tries OpenDataLoader first, falls back to PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file
        source: "inspection" or "thermal"
    
    Returns:
        RawDocument with markdown content + extracted images
    """
    logger.info(f"Starting ingestion of {source} PDF: {pdf_path}")
    markdown_content = ""
    images = []
    page_count = 0

    # ── Try OpenDataLoader first ──────────────────────────────────────────────
    try:
        import opendataloader_pdf
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp_dir:
            opendataloader_pdf.convert(
                input_path=[str(pdf_path)],
                output_dir=tmp_dir,
                format="markdown",
                image_output="embedded",
                image_format="jpeg",
            )
            # Find generated markdown file
            md_files = list(Path(tmp_dir).glob("**/*.md"))
            if md_files:
                markdown_content = md_files[0].read_text(encoding="utf-8")
                logger.info(f"OpenDataLoader extracted {len(markdown_content)} chars from {source}")
            else:
                raise FileNotFoundError("No markdown output from OpenDataLoader")

    except Exception as e:
        logger.warning(f"OpenDataLoader failed ({e}), falling back to PyMuPDF")
        markdown_content = extract_text_pymupdf(pdf_path)

    # ── Always extract images via PyMuPDF (most reliable) ────────────────────
    images = extract_images_pymupdf(pdf_path, source)

    # ── Get page count ────────────────────────────────────────────────────────
    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
    except Exception:
        page_count = 0

    logger.info(
        f"Ingestion complete for {source}: "
        f"{len(markdown_content)} chars, {len(images)} images, {page_count} pages"
    )

    return RawDocument(
        source=source,
        markdown_content=markdown_content,
        images=images,
        page_count=page_count,
    )