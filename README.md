# DDR Report Generator

An AI-powered **Detailed Diagnostic Report (DDR)** generator that converts raw building inspection and thermal imaging PDFs into structured, client-ready diagnostic reports automatically.

---

## What It Does

```
Upload 2 PDFs → AI processes everything → Download DDR in DOCX + PDF + HTML
```

---

## Pipeline Architecture

```
Stage 1 → PDF Ingestion       (OpenDataLoader v2.0 — #1 benchmark)
Stage 2 → AI Extraction       (ChromaDB RAG + Groq Llama 4 Scout)
Stage 3 → Merge & Conflict    (Groq Llama 4 Scout)
Stage 4 → DDR Generation      (Groq Llama 3.3 70B)
Stage 5 → Export              (DOCX + PDF + HTML)
```

---

## Tech Stack

| Layer | Tool | Reason |
|---|---|---|
| Web Framework | FastAPI | Production-grade async API |
| PDF Ingestion | OpenDataLoader v2.0 + PyMuPDF | #1 open source PDF benchmark |
| Vector Search | ChromaDB + sentence-transformers | Semantic retrieval over large docs |
| LLM — Extraction | Groq Llama 4 Scout | 30,000 TPM — highest free tier |
| LLM — Merging | Groq Llama 4 Scout | Separate TPM bucket |
| LLM — Generation | Groq Llama 3.3 70B | Best quality for final output |
| DOCX Export | python-docx | Word document generation |
| PDF Export | ReportLab + pdfkit | PDF generation |
| HTML Export | Jinja2 | Browser preview |
| Validation | Pydantic v2 | Type-safe pipeline data |

---

## Why Groq API Instead of Local Models

> **Important Note on Model Choice**

This project uses **Groq API** (cloud-based) due to current system hardware constraints — specifically insufficient GPU VRAM to run large language models locally at acceptable inference speeds.

**My preferred production approach** would be to run everything fully locally using:

```
PDF Parsing  → OpenDataLoader v2.0       (already local, no GPU needed)
Embeddings   → sentence-transformers     (already local, CPU-friendly)
Vector DB    → ChromaDB                  (already local, in-memory)
LLM          → Ollama + Llama 3.3 70B   (requires 48GB+ VRAM)
           or → Ollama + Qwen 2.5 14B   (requires 16GB VRAM)
```

**Benefits of full local deployment:**
- Complete data privacy — inspection reports never leave your machine
- No API rate limits or token restrictions
- No internet dependency
- No API costs at scale
- Faster processing with dedicated hardware

The architecture is already designed for this — swapping Groq for Ollama requires only changing the client initialization in `extractor.py`, `merger.py`, and `generator.py`.

---

## DDR Output Structure

```
1. Property Issue Summary
2. Area-wise Observations    (with images from source documents)
3. Probable Root Cause
4. Severity Assessment       (with reasoning per area)
5. Recommended Actions       (Immediate / Short-term / Long-term)
6. Additional Notes
7. Missing or Unclear Information
```

---

## Key Features

- **Semantic Image Placement** — Images extracted from PDFs and placed under correct sections using page number matching
- **Conflict Detection** — Automatically flags when inspection and thermal documents refer to different properties
- **RAG Pipeline** — ChromaDB vector search retrieves relevant content from large PDFs instead of blind truncation
- **Multi-model Strategy** — Three different Groq models used across pipeline stages to avoid rate limits
- **3 Export Formats** — Word, PDF, and HTML from single pipeline run
- **Handles Missing Data** — Explicitly writes "Not Available" instead of hallucinating

---

## Quick Start

### 1. Clone
```bash
git clone https://github.com/GANDHAMMANI/ddr-report-generator
cd ddr-report-generator
```

### 2. Install
```bash
pip install -r requirements.txt
```

> Requires Java 11+ for OpenDataLoader PDF parsing

### 3. Configure
```bash
cp .env.example .env
# Add your GROQ_API_KEY from https://console.groq.com
```

### 4. Run
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Open
```
http://localhost:8000        → Upload UI
http://localhost:8000/docs   → API docs
```

---

## Docker

```bash
docker-compose up --build
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/upload` | Upload 2 PDFs, get job_id |
| GET | `/api/v1/status/{job_id}` | Poll processing status |
| GET | `/api/v1/report/{job_id}` | Get download links |
| GET | `/api/v1/report/{job_id}/preview` | Preview in browser |
| GET | `/api/v1/report/{job_id}/download/html` | Download HTML |
| GET | `/api/v1/report/{job_id}/download/docx` | Download DOCX |
| GET | `/api/v1/report/{job_id}/download/pdf` | Download PDF |
| GET | `/api/v1/health` | Health check |

---

## Limitations

- Groq free tier has token rate limits (mitigated by multi-model strategy)
- Image placement accuracy depends on page number extraction quality
- Property name detection can fail when documents use non-standard formats
- PDF generation uses ReportLab fallback when wkhtmltopdf is not installed

---

## Future Improvements

- Replace Groq with local Ollama models for full offline capability and data privacy
- Add vision language model (LLaVA / Qwen-VL) for semantic image understanding
- Add Redis job queue for production-scale concurrent processing
- Fine-tune on real DDR report datasets for higher domain accuracy
- Add support for more document formats (DOCX, images, scanned PDFs via OCR)

---

## Project Structure

```
ddr-report-generator/
├── app/
│   ├── api/routes/          # FastAPI endpoints
│   ├── core/                # AI pipeline
│   │   ├── ingestion.py     # OpenDataLoader PDF extraction
│   │   ├── rag_retriever.py # ChromaDB semantic search
│   │   ├── extractor.py     # Groq structured extraction
│   │   ├── merger.py        # Merge + conflict detection
│   │   ├── generator.py     # DDR 7-section generation
│   │   └── image_handler.py # Image placement
│   ├── exporters/           # DOCX, PDF, HTML export
│   ├── models/              # Pydantic data models
│   ├── templates/           # Jinja2 HTML template
│   └── utils/               # Logger, job store, file handler
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── requirements.txt
```

---

## Built By

Gandham Mani Saketh
