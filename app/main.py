import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.api.routes import health, upload, report
from app.config import settings
from app.utils.logger import logger

# ── Rock solid path resolution — works on Windows + Linux + Mac ───────────────
# __file__ is always the most reliable anchor
THIS_FILE = Path(__file__).resolve()        # → E:\ddr-report-generator\app\main.py
APP_DIR   = THIS_FILE.parent               # → E:\ddr-report-generator\app
ROOT_DIR  = APP_DIR.parent                 # → E:\ddr-report-generator
TEMPLATES_DIR = APP_DIR / "templates"      # → E:\ddr-report-generator\app\templates
STATIC_DIR    = APP_DIR / "static"         # → E:\ddr-report-generator\app\static

# ── App Init ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DDR Report Generator",
    description="AI-powered Detailed Diagnostic Report generator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ──────────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")

# ── UI Page ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    """Serve the main upload UI at http://localhost:8000"""
    ui_path = TEMPLATES_DIR / "ddr_report.html"
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return HTMLResponse(content=f"<h1>Template not found</h1><pre>Looking at: {ui_path}</pre>")


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("DDR Report Generator started")
    logger.info(f"   ROOT_DIR       : {ROOT_DIR}")
    logger.info(f"   TEMPLATES_DIR  : {TEMPLATES_DIR}")
    logger.info(f"   ddr_report.html     : {(TEMPLATES_DIR / 'ddr_report.html').exists()}")
    logger.info(f"   UI             : http://localhost:{settings.app_port}")
    logger.info(f"   API Docs       : http://localhost:{settings.app_port}/docs")


@app.on_event("shutdown")
async def shutdown():
    logger.info("DDR Report Generator shutting down...")